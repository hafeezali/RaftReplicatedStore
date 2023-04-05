import time
from threading import Lock, Thread
from queue import Queue
import raft.config as config
import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from store.database import Database
from raft.consensus import Consensus
from logs.log import Log


# this class needs to implement Raft Service (probably Election Service)
class Election(raftdb_grpc.RaftElectionService):

    # What is queue and why is that needed? Is database needed? Isn't just log enough?
    def __init__(self, peers: list, log: Log, serverId: int):
        self.timeout_thread = None
        # self.term = 0 -- moved to log
        self.num_votes = 0
        self.peers = peers
        self.serverId = serverId
        # self.leaderId = -1 -- moved to log
        # self.__lock = Lock() -- not needed

        self.__log = log

        self.election_timeout()

    # What triggers an election when leader dies? Should there be a thread that keep track of heartbeats and server state and triggers an election accordingly?
    def begin_election(self):
        '''
        Once the election timeout has passed, this function starts the leader election
        '''
        # logger.info('starting election')
        with self.__log.lock:
            self.__log.term += 1
            self.__log.status = config.STATE.CANDIDATE
        self.num_votes = 0
        

        # Calculate majority, TODO: update once transport layer is done
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
            # logger.info('starting timeout')
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
        self.election_time = time.time() + self.random_timeout()

    def follower_loop(self):
        '''
        Followers execute this loop, and wait for heartbeats from leader
        '''
        while self.__log.status != config.STATE.LEADER:
            wait_time = self.election_time - time.time()
            if wait_time < 0:
                if self.peers:
                    self.begin_election()
            else:
                time.sleep(wait_time)
        
    def update_votes(self):
        self.num_votes += 1
        if self.num_votes >= self.majority:
            # why is this lock even needed here? what is the significance? The election process is run by only one thread no?
            with self.__log.lock:
                self.__log.status = config.STATE.LEADER
            
            self.leaderId = self.serverId
            self.elected_leader()

    def elected_leader(self):
        '''
        If this node is elected as the leader, start sending
        heartbeats to the follower nodes
        '''
        for peer in self.peers:
            Thread(target=self.sendHeartbeat, args=(peer,)).start()

        
    def sendHeartbeat(self, follower):
        # To send heartbeats
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftStub(channel)
            request = raftdb.Heartbeat(
                term = self.__log.term,
                serverId = self.serverId
            )
            start = time.time()
            term = self.__log.term
            while self.__log.term == term and self.__log.status == config.STATE.LEADER:
                response = stub.Heartbeat(request)
                if response.code != config.RESPONSE_CODE_OK:
                # In what scenario can we get a code != 200? Is there a timeout on these rpcs? What if the node is down? Due to membership change or just node crash for extended duration? 
                # Need heartbeat response from append entries, added term proto to be sent back
                    if response.term > self.__log.term:
                        # We are not the most up to date term, revert to follower
                        with self.__log.lock:
                            self.__log.term = response.term
                            self.__log.status = config.STATE.FOLLOWER

                        # Our heartbeat was rejected, so update leader ID to current leader
                        self.leaderId = response.leaderId
                        break
                    # else:
                        # There is some other error??
                        # For now it will just retry
                else:
                    # We got an OK response, sleep for sometime and then send heartbeat again
                    wait_time = time.time() - start
                    time.sleep((config.HB_TIME - wait_time) / 1000)


    # Heartbeat RPC Handler
    # Executed by follower
    def Heartbeat(self, sender_term, sender_serverId):
        '''
        Check the term of the sender. If sender term is greater than ours,

        if we are candidate or leader, immediately set our state to follower

        If our term is less or equal (and we are not the leader), return 200
        Else return 500, along with our term so leader will know there is a
        higher term in the system.

        '''
        if self.__log.term < sender_term:
            with self.__log.lock:
                if self.__log.status == config.STATE.CANDIDATE or \
                    self.__log.status == config.STATE.LEADER:
                    self.__log.status = config.STATE.FOLLOWER

                    # Update our term to match sender term
                    self.__log.term = sender_term

            # Update leader ID so that we can redirect requests to the leader
            self.leaderId = sender_serverId
            return config.RESPONSE_CODE_OK, self.__log.term, self.leaderId
        
        elif self.__log.term == sender_term and self.__log.status != config.STATE.LEADER:
            self.leaderId = sender_serverId
            return config.RESPONSE_CODE_OK, self.__log.term, self.leaderId
        else:
            # return the leader ID we have to the peer sending heartbeat, so it can 
            # update its own leader id since it will revert to follower.
            return config.RESPONSE_CODE_REJECT, self.__log.term, self.leaderId


    def request_votes(self):
        # Request votes from other nodes in the cluster.
        
        for peer in self.peers:
            Thread(target=self.send_vote_request, args=(peer, self.__log.term)).start()
            
    def send_vote_request(self, voter: str, term: int):
  
        # Assumption is this idx wont increase when sending heartbeats right?
        candidate_last_log_index = self.__log.log_idx
        candidate_term = self.__log.term

        # get term of last item in log
        # can just do log.term -- current term -- different from last log term
        candidate_last_log_term = self.__log.get(candidate_last_log_index).term

        request = raftdb.VoteRequest(term=candidate_term, 
                                     lastLogTerm=candidate_last_log_term,
                                     lastLogIndex=candidate_last_log_index,
                                     candidateId=self.serverId)

        while self.__log.status == config.STATE.CANDIDATE and self.__log.term == candidate_term:

            with grpc.insecure_channel(voter) as channel:
                stub = raftdb_grpc.RaftStub(channel)
                vote_response = stub.RequestVote(request)
                
                # can this thread become dangling when a node dies? in a scneario where we never get a vote response back?
                if vote_response:
                    vote = vote_response.success
                    if vote == True and self.__log.status == config.STATE.CANDIDATE:
                        self.update_votes()
                    elif not vote:
                        voter_term = vote_response.term
                        if voter_term > self.__log.term:
                            with self.__log.lock:
                                self.__log.status = config.STATE.FOLLOWER
                                ### Update self term? - Yes
                                self.__log.term = voter_term
                    break

    # where is the RequestVode handler?
    # RPC Request Vote Handler
    def RequestVote(self, candidate_term: int, candidate_last_log_term: int,
                    candidate_last_log_index: int, candidate_Id: int):
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
        # TODO: Update how voted for is used based on changes in Log.py

        # what's with so many election timeouts here?
        # Reset election timeout so that the follower does not immediately start a new election
        self.reset_election_timeout()
        voter_term = self.__log.term
        voter_last_log_index = self.__log.logIndex
        # can just get the term from log.term -- not the same!!
        voter_last_log_term = self.__log.get(voter_last_log_index).term

        if candidate_term > voter_term:
            with self.__log.lock:
                self.__log.term = candidate_term

                # Step down if we are the leader or candidate
                if self.__log.status == config.STATE.CANDIDATE or \
                    self.__log.status == config.STATE.LEADER:
                    self.__log.status = config.STATE.FOLLOWER
            return True, candidate_term

        elif candidate_term < voter_term:
            # Reject request vote
            return False, self.__log.term
        
        else:
            # voter term and candidate term are equal
            voted_for_term = self.__log.voted_for['term']
            voted_for_id = self.__log.voted_for['server_id']
            if voted_for_term == candidate_term: 
                if voted_for_id > 0 and voted_for_id != candidate_Id:
                    # already voted for someone else
                    return False, self.__log.term
            
            elif voted_for_term < candidate_term or \
                (voted_for_term == candidate_term and voted_for_id == candidate_Id): 
                # We have not voted for anyone, or we have already voted for this candidate
                # Check log to see if candidate's is more complete than ours

                if voter_last_log_term < candidate_last_log_term or \
                    (voter_last_log_term == candidate_last_log_term and voter_last_log_index <= candidate_last_log_index): 
                    self.reset_election_timeout()
                    # this update should probably happen in the log layer
                    # Actually, why is it that we're updating term here? What is the exact reason? Perhaps can be used by consensus to decide whethere to accept entry or not but that can done in other ways. Is there any other reason? In an election, a node can vote for multiple leaders anyway right?
                    # Only one will get majority I think... No? 
  
                    with self.__log.lock:
                        self.__log.term = candidate_term # Technically not needed since terms are equal
                        self.__log.voted_for['term'] = candidate_term
                        self.__log.voted_for['server_id'] = candidate_Id

                    return True, self.__log.term
                else:
                    return False, self.__log.term
            else:
                return False, self.__log.term
   