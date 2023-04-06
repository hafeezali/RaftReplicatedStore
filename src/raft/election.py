import time
from threading import Lock, Thread
from queue import Queue
import raft.config as config
import concurrent.futures as futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from logs.log import Log


# this class needs to implement Raft Service (probably Election Service)
class Election(raftdb_grpc.RaftElectionService):

    # What is queue and why is that needed? Is database needed? Isn't just log enough?
    def __init__(self, peers: list, log: Log, serverId: int, logger):
        self.timeout_thread = None
        self.num_votes = 0
        self.peers = peers
        self.serverId = serverId
        self.__log = log
        self.logger = logger

    def run_election_service(self):
        self.logger.debug('Starting Election Timeout')
        self.election_timeout()


    # What triggers an election when leader dies? Should there be a thread that keep track of heartbeats and server state and triggers an election accordingly?
    def begin_election(self):
        '''
        Once the election timeout has passed, this function starts the leader election
        '''
        self.__log.set_self_candidate()
        self.logger.debug(f'Starting a new election for term {self.__log.get_term()}')
        self.num_votes = 0
        
        # Calculate majority
        self.majority = ((1 + len(self.peers)) // 2) + 1 
        
        # Wait for election timeout
        self.election_timeout()

        # vote for ourself
        self.update_votes()

        # request votes from all peers
        self.request_votes()


    def election_timeout(self):
        '''
        Wait for timeout before starting an election incase we get heartbeat from a leader
        '''
        try:

            self.logger.info('Waiting for Election timeout')
            self.reset_election_timeout()

            if self.timeout_thread and self.timeout_thread.is_alive():
                return
            
            self.timeout_thread = Thread(target=self.follower_loop)
            self.timeout_thread.start()

        except Exception as e:
            raise e
        

    def random_timeout(self):
        '''
        return random timeout number
        '''
        return random.randrange(config.MIN_TIMEOUT, config.MAX_TIMEOUT) / 1000
    

    def reset_election_timeout(self):
        '''
        If we get a heartbeat from the leader, reset election timeout
        '''

        self.logger.debug('Resetting Election Timeout')
        self.election_time = time.time() + self.random_timeout()


    def follower_loop(self):
        '''
        Followers execute this loop, and wait for heartbeats from leader
        '''
        self.logger.info('Starting follower loop')
        while self.__log.get_status() != config.STATE['LEADER']:
            wait_time = self.election_time - time.time()
            if wait_time < 0:
                if self.peers:
                    self.begin_election()
            else:
                time.sleep(wait_time)
        

    def update_votes(self):
        self.num_votes += 1
        if self.num_votes >= self.majority:
            self.logger.info(f'Received majority of votes for term {self.__log.get_term()}')
            # why is this lock even needed here? what is the significance? The election process is run by only one thread no?
            self.__log.set_self_leader()
            self.elected_leader()


    def elected_leader(self):
        '''
        If this node is elected as the leader, start sending
        heartbeats to the follower nodes
        '''

        self.logger.info(f'Elected leader!!! for term {self.__log.get_term()}')
        for peer in self.peers:
            Thread(target=self.sendHeartbeat, args=(peer,)).start()

        
    def sendHeartbeat(self, follower):
        # To send heartbeats
        term = self.__log.get_term()
        self.logger.info(f'Sending heartbeat for term {term} to {follower}')
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftElectionServiceStub(channel)
            request = raftdb.HeartbeatRequest(
                term = term,
                serverId = self.serverId
            )
            start = time.time()
            
            while self.__log.get_term() == term and self.__log.get_status() == config.STATE['LEADER']:
                try:
                    response = stub.Heartbeat(request, timeout=config.RPC_TIMEOUT)
                    if response.code != config.RESPONSE_CODE_OK:
                    # In what scenario can we get a code != 200? Is there a timeout on these rpcs? What if the node is down? Due to membership change or just node crash for extended duration? 
                    # Need heartbeat response from append entries, added term proto to be sent back
                        if response.term > self.__log.get_term():
                            # We are not the most up to date term, revert to follower
                            # Our heartbeat was rejected, so update leader ID to current leader
                            self.logger.info(f'Stepping down from leader for {term}, new term: {response.term}')
                            self.__log.revert_to_follower(response.term, response.leaderId)
                            break
                    else:
                        # We got an OK response, sleep for sometime and then send heartbeat again
                        wait_time = time.time() - start
                        time.sleep((config.HB_TIME - wait_time) / 1000)

                except grpc.RpcError as e:
                    status_code = e.code()
                    status_code.value
                    if status_code.value == grpc.StatusCode.DEADLINE_EXCEEDED:
                        # timeout, will retry if we are still leader
                        self.logger.debug(f'Heartbeat failed with timeout error for peer: {follower}, details: {e.details()}')



    # Heartbeat RPC Handler
    # Executed by follower
    def Heartbeat(self, request, context):
        '''
        Check the term of the sender. If sender term is greater than ours,

        if we are candidate or leader, immediately set our state to follower

        If our term is less or equal (and we are not the leader), return 200
        Else return 500, along with our term so leader will know there is a
        higher term in the system.

        '''
        self.logger.info(f'Received heartbeat from leader for {sender_term}')
        follower_term = self.__log.get_term()

        sender_term, sender_serverId = request.term, request.serverId
        
        if follower_term <= sender_term:
            # Update our term to match sender term
            # Update leader ID so that we can redirect requests to the leader

            # If this server was leader or candidate it will set to follower
            self.logger.info(f'Accepted heartbeat for term {sender_term}')
            self.__log.revert_to_follower(sender_term, sender_serverId)
            return config.RESPONSE_CODE_OK, sender_term, self.__log.get_leader()
        
        else:
            # return the leader ID we have to the peer sending heartbeat, so it can 
            # update its own leader id since it will revert to follower.
            self.logger.info(f'Rejected heartbeat for term: {sender_term}, current term: {follower_term}')
            return config.RESPONSE_CODE_REJECT, follower_term, self.__log.get_leader()


    def request_votes(self):
        # Request votes from other nodes in the cluster.
        term = self.__log.get_term()
        self.logger.info(f'Requesting votes for term: {term}')
        for peer in self.peers:
            Thread(target=self.send_vote_request, args=(peer, term)).start()
            

    def send_vote_request(self, voter: str, term: int):
  
        # Assumption is this idx wont increase when sending heartbeats right?
        candidate_last_log_index = self.__log.get_log_idx()
        candidate_term = term

        # get term of last item in log
        # can just do log.term -- current term -- different from last log term
        if candidate_last_log_index == -1 : 
            candidate_last_log_term = 0
        else :
            candidate_last_log_term = self.__log.get(candidate_last_log_index).term
        
        request = raftdb.VoteRequest(term = candidate_term, 
                                     lastLogTerm = candidate_last_log_term,
                                     lastLogIndex = candidate_last_log_index,
                                     candidateId = self.serverId)

        while self.__log.get_status() == config.STATE['CANDIDATE'] and self.__log.get_term() == candidate_term:
            
            self.logger.info(f'Requesting vote for term: {term} from {voter}')
            with grpc.insecure_channel(voter) as channel:
                self.logger.info(f'Channel for term {term} to {voter}')

                try: 
                    stub = raftdb_grpc.RaftElectionServiceStub(channel)
                    vote_response = stub.RequestVote(request, timeout=config.RPC_TIMEOUT)
                    
                    # can this thread become dangling when a node dies? in a scneario where we never get a vote response back?
                    if vote_response:
                        vote = vote_response.success
                        if vote == True and self.__log.get_status() == config.STATE['CANDIDATE']:
                            self.logger.info(f'Received vote for term: {term} from {voter}')
                            self.update_votes()
                        elif not vote:
                            voter_term = vote_response.term
                            if voter_term > self.__log.get_term():
                                self.logger.info(f'Did not receive vote for term: {term} from {voter}, voter term: {voter_term}')
                                self.__log.revert_to_follower(voter_term, vote_response.leaderId)
                        break

                except grpc.RpcError as e:
                    status_code = e.code()
                    status_code.value
                    if status_code.value == grpc.StatusCode.DEADLINE_EXCEEDED:
                        # timeout, will retry if we are still leader
                        self.logger.debug(f'Request vote failed with timeout error, peer: {voter}, details: {e.details()}')
                    else :
                        self.logger.debug(f'Some other error, details: {e.details()}') 

    # where is the RequestVode handler?
    # RPC Request Vote Handler
    # Executed by Follower
    def RequestVote(self, request, context):
        '''
        # Decide whether to vote for candidate or not on receiving request vote RPC.

        If candidateCurrentTerm > voterCurrentTerm, set voterCurrentTerm ← candidateCurrentTerm
        (step down if leader or candidate)
        If candidateCurrentTerm == voterCurrentTerm, votedFor is null or candidate_Id,
        and candidate's log is at least as complete as local log,
        grant vote and reset election timeout
        else reject
        to decide if log is more complete

        if voterLastLogTerm < candidateLastLogTerm : OK
        elif: voterLastLogTerm == candidateLastLogTerm and voterLastLogIndex <= candidateLastLogIndex: OK
        else: reject vote

        '''
        candidate_term, candidate_Id = request.term, request.candidateId
        candidate_last_log_term = request.lastLogTerm
        candidate_last_log_index = request.lastLogIndex

        self.logger.info(f'Received vote request for term: {candidate_term} from {candidate_Id}')
        # what's with so many election timeouts here?
        # Reset election timeout so that the follower does not immediately start a new election
        self.reset_election_timeout()
        voter_term = self.__log.get_term()
        voter_last_log_index = self.__log.get_log_idx()
        # can just get the term from log.term -- not the same!!
        voter_last_log_term = self.__log.get(voter_last_log_index).term

        if candidate_term > voter_term:
            # Step down if we are the leader or candidate    
            self.logger.info(f'Sending Success vote for term: {candidate_term} for {candidate_Id}')
            self.__log.revert_to_follower(candidate_term, candidate_Id)
            return True, candidate_term, candidate_Id

        elif candidate_term < voter_term:

            self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}, voter term: {voter_term}')
            # Reject request vote
            return False, self.__log.get_term(), self.__log.get_leader()
        
        else:
            # voter term and candidate term are equal
            voted_for_term, voted_for_id = self.__log.get_voted_for()
            if voted_for_term == candidate_term: 
                if voted_for_id > 0 and voted_for_id != candidate_Id:
                    # already voted for someone else

                    self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}, already voted for {voted_for_id}')
                    return False, self.__log.get_term(), self.__log.get_leader()
            
            elif voted_for_term < candidate_term or \
                (voted_for_term == candidate_term and voted_for_id == candidate_Id): 
                # We have not voted for anyone in this term, or we have already voted for this candidate
                
                # Check log to see if candidate's is more complete than ours
                if voter_last_log_term < candidate_last_log_term or \
                    (voter_last_log_term == candidate_last_log_term and voter_last_log_index <= candidate_last_log_index): 
                    self.reset_election_timeout()
                    # this update should probably happen in the log layer
                    # Actually, why is it that we're updating term here? What is the exact reason? Perhaps can be used by consensus to decide whethere to accept entry or not but that can done in other ways. Is there any other reason? In an election, a node can vote for multiple leaders anyway right?
                    # Only one will get majority I think... No? 

                    self.logger.info(f'Sending Success vote for term: {candidate_term} for {candidate_Id}')
                    self.__log.cast_vote(candidate_term, candidate_Id)
                    return True, self.__log.get_term(), self.__log.get_leader()
                
                else:
                    self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}')
                    return False, self.__log.get_term(), self.__log.get_leader()
                
            else:
                self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}')
                return False, self.__log.get_term(), self.__log.get_leader()
   