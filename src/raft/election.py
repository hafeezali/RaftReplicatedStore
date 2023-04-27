import time
from threading import Lock, Thread
import raft.config as config
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from logs.log import Log

'''
TODO:
1. [DONE] Still possible that update votes can be called by two concurrent threads when node just became leader by one of the threads. Just adding a status check should fix the issue
2. [DONE] There was some type casting issue in RequestVote around candidate_term and voter_term
3. [DONE] If candidate term > voter term, check logs before sending vote
4. [DONE] If we send a vote, set leader id to None since we are updating our term, will find out leader through heartbeat
'''
class Election(raftdb_grpc.RaftElectionService):

    def __init__(self, peers: list, log: Log, serverId: int, logger):
        self.timeout_thread = None
        self.num_votes = 0
        self.peers = peers
        self.serverId = serverId
        self.__log = log
        self.logger = logger
        self.last_heartbeat_time = 0
        self.election_lock = Lock() # Adding for updating votes

    def run_election_service(self):
        self.logger.debug('Starting Election Timeout')
        self.election_timeout()

    def begin_election(self):
        '''
        Once the election timeout has passed, this function starts the leader election
        '''
        self.__log.set_self_candidate()
        self.logger.debug(f'Starting a new election for term {self.__log.get_term()}')
        self.reset_num_votes()
        
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
        self.election_timeout_time = self.random_timeout()
        self.election_time = time.time() + self.election_timeout_time
        self.logger.info('New election timeout time: ' + str(self.election_timeout_time))

    def follower_loop(self):
        '''
        Followers execute this loop, and wait for heartbeats from leader
        '''
        self.logger.info('Starting follower loop')
        while self.__log.get_status() != config.STATE['LEADER']:
            self.reset_election_timeout()
            time_since_last_heartbeat = time.time() - self.last_heartbeat_time
            self.logger.info('Time since last heartbeat: ' + str(time_since_last_heartbeat))
            if time_since_last_heartbeat > self.election_timeout_time:
                if self.peers:
                    self.begin_election()
            wait_time = self.election_time - time.time()
            time.sleep(wait_time)

    def get_num_votes(self):
        with self.election_lock:
            return self.num_votes
        
    def increment_num_votes(self):
        with self.election_lock:
            self.num_votes += 1

    def reset_num_votes(self):
        with self.election_lock:
            self.num_votes = 0

    def update_votes(self):
        self.logger.info("Updating number of votes")
        self.increment_num_votes()
        if self.get_num_votes() >= self.majority and self.__log.get_status() == config.STATE['CANDIDATE']:
            self.logger.info(f'Received majority of votes for term {self.__log.get_term()}')
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
        term = self.__log.get_term()
        self.logger.info(f'Sending heartbeat for term {term} to {follower}')
        with grpc.insecure_channel(follower, options=(('grpc.enable_http_proxy', 0),)) as channel:
            stub = raftdb_grpc.RaftElectionServiceStub(channel)
            log_idx = self.__log.get_log_idx()
            log_term = self.__log.get(log_idx)['term']
            request = raftdb.HeartbeatRequest(
                term = term,
                serverId = self.serverId,
                lastCommitIndex = self.__log.get_last_commit_index(),
                log_idx = log_idx,
                log_term = log_term
            )
            start = time.time()
            
            while self.__log.get_term() == term and self.__log.get_status() == config.STATE['LEADER']:
                try:
                    response = stub.Heartbeat(request, timeout=config.RPC_TIMEOUT)

                    if response.code != config.RESPONSE_CODE_OK:
                        if response.term > self.__log.get_term():
                            # We are not the most up to date term, revert to follower
                            # Our heartbeat was rejected, so update leader ID to current leader
                            self.logger.info(f'Stepping down from leader for {term}, new term: {response.term}')
                            self.__log.revert_to_follower(response.term, response.leaderId)
                            break
                    else:
                        # We got an OK response, sleep for sometime and then send heartbeat again
                        wait_time = time.time() - start
                        if config.HB_TIME > wait_time:
                            time.sleep((config.HB_TIME - wait_time) / 1000)

                except grpc.RpcError as e:
                    status_code = e.code()
                  
                    if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                        # timeout, will retry if we are still leader
                        self.logger.debug(f'Heartbeat failed with timeout error, peer: {follower}, {status_code} details: {e.details()}')
                    else :
                        # Network partition can cause this. We need to sleep to avoid sending too many of these errrors
                        time.sleep(config.HB_TIME / 2000)
                        self.logger.debug(f'Some other error, details: {status_code} {e.details()}') 

    def Heartbeat(self, request, context):
        '''
        Check the term of the sender. If sender term is greater than ours,
        if we are candidate or leader, immediately set our state to follower

        If our term is less or equal (and we are not the leader), return 200
        Else return 500, along with our term so leader will know there is a
        higher term in the system.

        '''
        follower_term = self.__log.get_term()

        sender_term, sender_serverId = request.term, request.serverId
        self.logger.info(f'Received heartbeat from leader for term: {sender_term} from leader: {sender_serverId}')
        
        if follower_term <= sender_term:
            # Update our term to match sender term
            # Update leader ID so that we can redirect requests to the leader

            # If this server was leader or candidate it will set to follower
            self.logger.info(f'Accepted heartbeat for term: {sender_term}')
            self.__log.revert_to_follower(sender_term, sender_serverId)
            # update last time we received heartbeat
            self.last_heartbeat_time = time.time()
            last_idx = self.__log.get_log_idx()
            last_term = self.__log.get(last_idx)['term']
            if request.log_term == last_term and request.log_idx == last_idx:
                self.__log.commit_upto(request.lastCommitIndex)
            return raftdb.HeartbeatResponse(code = config.RESPONSE_CODE_OK,
                                            term = sender_term,
                                            leaderId= self.__log.get_leader())
        else:
            # return the leader ID we have to the peer sending heartbeat, so it can 
            # update its own leader id since it will revert to follower.
            self.logger.info(f'Rejected heartbeat for term: {sender_term}, current term: {follower_term}')
            return raftdb.HeartbeatResponse(code = config.RESPONSE_CODE_REJECT,
                                            term = follower_term,
                                            leaderId= self.__log.get_leader())

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
        else:
            candidate_last_log_term = self.__log.get(candidate_last_log_index)['term']

        while self.__log.get_status() == config.STATE['CANDIDATE'] and self.__log.get_term() == candidate_term:
            
            self.logger.info(f'Requesting vote for term: {term} from {voter}')
            with grpc.insecure_channel(voter, options=(('grpc.enable_http_proxy', 0),)) as channel:
                self.logger.info(f'Channel for term {term} to {voter}')

                try: 
                    stub = raftdb_grpc.RaftElectionServiceStub(channel)
                    self.logger.info(f'Created stub for term {term} to {voter}, sending rpc')
                    request = raftdb.VoteRequest(term = candidate_term, 
                                     lastLogTerm = candidate_last_log_term,
                                     lastLogIndex = candidate_last_log_index,
                                     candidateId = self.serverId)
                    vote_response = stub.RequestVote(request, timeout = config.RPC_TIMEOUT)

                    self.logger.info(f'Vote Response for term {term} is {vote_response}')
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
                    else:
                        self.logger.info(f'No vote response for term: {term} from {voter}')

                except grpc.RpcError as e:
                    status_code = e.code()
                  
                    if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                        # timeout, will retry if we are still leader
                        self.logger.debug(f'Request vote failed with timeout error, peer: {voter}, {status_code} details: {e.details()}')
                    else :
                        self.logger.debug(f'Some other error, details: {status_code} {e.details()}') 

    def check_completeness_of_log(self, voter_last_log_term, voter_last_log_index,
                                        candidate_last_log_term, candidate_last_log_index,
                                        candidate_id, candidate_term):

        # Check log to see if candidate's is more complete than ours
        if voter_last_log_term < candidate_last_log_term or \
            (voter_last_log_term == candidate_last_log_term and voter_last_log_index <= candidate_last_log_index): 
            self.reset_election_timeout()

            self.logger.info(f'Sending Success vote for term: {candidate_term} for {candidate_id}')
            self.__log.cast_vote(candidate_term, candidate_id)
            ## Since we are casting vote, at this point we don't know who the leader for this term is 
            self.__log.update_leader('No leader')
            return raftdb.VoteResponse(success = True, term = self.__log.get_term(), leaderId = self.__log.get_leader())                
        else:
            self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_id}')
            return raftdb.VoteResponse(success = False, term = self.__log.get_term(), leaderId = self.__log.get_leader())
                

    def RequestVote(self, request, context):
        '''
        Decide whether to vote for candidate or not on receiving request vote RPC.

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
        self.logger.info(f'Candidate last log term: {candidate_last_log_term}, last log index {candidate_last_log_index}')
       
        # Reset election timeout so that the follower does not immediately start a new election
        self.reset_election_timeout()

        voter_term = self.__log.get_term()
        voter_last_log_index = self.__log.get_log_idx()
        
        self.logger.debug(f'voter term {voter_term}, voter log index {voter_last_log_index}')
        if voter_last_log_index == -1 : 
            self.logger.debug(f'voter last log index is -1, setting last log term to 0')
            voter_last_log_term = 0
        else:
            self.logger.debug(f'voter last log term not zero, getting term from log')
            voter_last_log_term = self.__log.get(voter_last_log_index)['term']


        # Decide if we are giving a vote to candidate
        if candidate_term > voter_term:
            # Step down if we are the leader or candidate    
            self.__log.revert_to_follower(candidate_term, 'No leader')
            # check our logs to see if they are more complete than the candidate's 
            return self.check_completeness_of_log(voter_last_log_term, voter_last_log_index,
                                        candidate_last_log_term, candidate_last_log_index,
                                        candidate_Id, candidate_term)

        elif candidate_term < voter_term:

            self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}, voter term: {voter_term}')
            # Reject request vote
            return raftdb.VoteResponse(success = False, term = self.__log.get_term(), leaderId = self.__log.get_leader())
        
        else:
            # voter term and candidate term are equal
            voted_for_term, voted_for_id = self.__log.get_voted_for()
            self.logger.info("voted_for_term: " + str(voted_for_term))
            self.logger.info("voted_for_id: " + str(voted_for_id))
            self.logger.info(f'candidate id == {candidate_Id}, candidate term == {candidate_term}')
            self.logger.info("############### VOTED FOR ##################################")
            if voted_for_term == candidate_term:
                if voted_for_id != candidate_Id:
                    # already voted for someone else

                    self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}, already voted for {voted_for_id}')
                    return raftdb.VoteResponse(success = False, term = self.__log.get_term(), leaderId = self.__log.get_leader())
            
            elif voted_for_term < candidate_term or \
                (voted_for_term == candidate_term and voted_for_id == candidate_Id): 
                # We have not voted for anyone in this term, or we have already voted for this candidate
                # If we are candidate for this term or leader, we would have already voted for ourself,
                # So at this point we are already follower.
                # Check log to see if candidate's is more complete than ours
                return self.check_completeness_of_log(voter_last_log_term, voter_last_log_index,
                                        candidate_last_log_term, candidate_last_log_index,
                                        candidate_Id, candidate_term)
            else:
                self.logger.info(f'Rejecting vote for term: {candidate_term} for {candidate_Id}')
                return raftdb.VoteResponse(success = False, term = self.__log.get_term(), leaderId = self.__log.get_leader())
   