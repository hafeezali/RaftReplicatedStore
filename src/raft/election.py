import time
from threading import Lock, Thread
from queue import Queue
import raft.config as config
import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from raft.store import Store
from raft.consensus import Consensus


class Election:
    def __init__(self, consensus: Consensus, store: Store, queue: Queue):
        self.timeout_thread = None
        self.status = config.STATE.FOLLOWER
        self.term = 0
        self.num_votes = 0
        self.store = store
        self.__transport = consensus
        self.__lock = Lock()
        self.q = queue
        self.election_timeout()

    def begin_election(self):
        '''
        once the election timeout has passed, this function starts the leader election
        '''
        # logger.info('starting election')
        self.term += 1
        self.num_votes = 0
        self.status = config.STATE.CANDIDATE

        # Calculate majority, TODO: update once transport layer is done
        self.replicas = self.__transport.peers
        self.majority = ((1 + len(self.replicas)) // 2) + 1 ##### NEED TO CHECK
        
        # Wait for election timeout
        self.election_timeout()

        # vote for ourself
        self.submit_vote()

        # request votes from all replicas
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
            
            self.timeout_thread = Thread(target=self.replica_loop)
            self.timeout_thread.start()

        except Exception as e:
            raise e
        
    def random_timeout():
        '''
        return random timeout number
        '''
        return random.randrange(config.MIN_TIMEOUT, config.MAX_TIMEOUT) / 1000
    
    def reset_election_timeout(self):
        '''
        If we get a heartbeat from the leader, reset election timeout
        '''
        self.election_time = time.time() + self.random_timeout()

    def replica_loop(self):
        '''
        Followers execute this loop, and wait for heartbeats from leader
        '''
        while self.status != config.STATE.LEADER:
            wait_time = self.election_time - time.time()
            if wait_time < 0:
                if self.__transport.peers:
                    self.begin_election()
            else:
                time.sleep(wait_time)
        
    def submit_vote(self):
        self.num_votes += 1
        if self.num_votes >= self.majority:
            with self.__lock:
                self.status = config.STATE.LEADER
                if self.q.empty():
                    self.q.put({'election': self})
                else:
                    election = self.q.get()
                    election.update({'election': self})
                    self.q.put(election)
            self.elected_leader()

    def elected_leader(self):
        '''
        If this node is elected as the leader, start sending
        heartbeats to the follower nodes
        '''
        for replica in self.replicas:
            Thread(target=self.sendAppendEntry, args=(replica,)).start()

        
    def sendAppendEntry(self, follower):
        # To send heartbeats
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftStub(channel)
            term_index = self.__store.termIndex-1
            request = raftdb.LogEntry(
                        term=self.__store.log[term_index].term, 
                        termIndex=term_index,
                        Entry=None,lastCommitIndex=self.__store.lastCommitIndex, 
                        commit = 0)
            start = time.time()
            response = stub.AppendEntries(request)
            if response.code != 200 :
                ## Need heartbeat response from append entries, added term proto to be sent back
                if self.term < response.term:
                    self.status = config.STATE.FOLLOWER
                    self.term = response.term
                    self.election_timeout()
            wait_time = time.time() - start
            time.sleep((config.HB_TIME - wait_time) / 1000) ### CHECK

        
    def request_votes(self):
        '''
        Request votes from other nodes in the cluster.
        '''
        for replica in self.replicas:
            Thread(target=self.send_vote_request, args=(replica, self.term)).start()
            
    def send_vote_request(self, voter: str, term: int):
  
        term_index = self.__store.termIndex
        request = raftdb.VoteRequest(term=term, termIndex=term_index)

        while self.status == config.STATE.CANDIDATE and self.term == term:

            with grpc.insecure_channel(voter) as channel:
                stub = raftdb_grpc.RaftStub(channel)
                vote_response = stub.RequestVote(request)
                
                if vote_response:
                    vote = vote_response['success']
                    # logger.debug(f'choice from {voter} is {choice}')
                    if vote == True and self.status == config.STATE.CANDIDATE:
                        self.submit_vote()
                    elif not vote:
                        voter_term = vote_response['term']
                        if voter_term > self.term:
                            self.status = config.STATE.FOLLOWER
                            ### Update self term?
                            self.term = voter_term
                    break


    def choose_vote(self, candidate_term: int, candidate_term_index: int) -> bool:
        '''
        Decide whether to vote for candidate or not on receiving request vote RPC.
       
        Returns True if current node's term is less than candidate term 
        OR
        if current node's term is same as candidate term and has fewer or equal entries in log

        Returns False otherwise
        '''
        self.reset_election_timeout()
        my_term_index = self.__store.termIndex

        if self.term < candidate_term or (self.term == candidate_term and my_term_index <= candidate_term_index): 
            self.reset_election_timeout()
            self.term = candidate_term
            return True, self.term, my_term_index
        else:
            return False, self.term, my_term_index
   