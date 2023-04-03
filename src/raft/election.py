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
class Election:

    # What is queue and why is that needed? Is database needed? Isn't just log enough?
    def __init__(self, replicas: list, store: Database, queue: Queue, log: Log):
        self.timeout_thread = None
        self.status = config.STATE.FOLLOWER
        self.term = 0
        self.num_votes = 0
        self.store = store
        self.replicas = replicas
        # What is this lock used for? 
        self.__lock = Lock()
        self.q = queue
        self.election_timeout()

    # What triggers an election when leader dies? Should there be a thread that keep track of heartbeats and server state and triggers an election accordingly?
    def begin_election(self):
        '''
        Once the election timeout has passed, this function starts the leader election
        '''
        # logger.info('starting election')
        self.term += 1
        self.num_votes = 0
        self.status = config.STATE.CANDIDATE

        # Calculate majority, TODO: update once transport layer is done
        self.majority = ((1 + len(self.replicas)) // 2) + 1 
        
        # Wait for election timeout
        self.election_timeout()

        # vote for ourself
        self.update_votes()

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

    def replica_loop(self):
        '''
        Followers execute this loop, and wait for heartbeats from leader
        '''
        while self.status != config.STATE.LEADER:
            wait_time = self.election_time - time.time()
            if wait_time < 0:
                if self.replicas:
                    self.begin_election()
            else:
                time.sleep(wait_time)
        
    def update_votes(self):
        self.num_votes += 1
        if self.num_votes >= self.majority:
            # why is this lock even needed here? what is the significance? The election process is run by only one thread no?
            with self.__lock:
                self.status = config.STATE.LEADER
                # What is this queue for? Can't we just store it in some state which can be accessed by the server up top?
                # Also current implementation doesnt have this up top
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
            Thread(target=self.sendHeartbeat, args=(replica,)).start()

        
    def sendHeartbeat(self, follower):
        # To send heartbeats
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftStub(channel)
            log_index = self.__log.log_idx
            request = raftdb.LogEntry(
                        term=self.term, 
                        logIndex=log_index,
                        Entry=None,
                        lastCommitIndex=self.__log.last_commit_idx, 
                        commit = 0)
            start = time.time()
            response = stub.AppendEntries(request)
            while response.code != 200:
                # In what scenario can we get a code != 200? Is there a timeout on these rpcs? What if the node is down? Due to membership change or just node crash for extended duration? 
                # Need heartbeat response from append entries, added term proto to be sent back
                response = stub.AppendEntries(request)
        
            wait_time = time.time() - start
            time.sleep((config.HB_TIME - wait_time) / 1000)
        
    def request_votes(self):
        # Request votes from other nodes in the cluster.
        
        for replica in self.replicas:
            Thread(target=self.send_vote_request, args=(replica, self.term)).start()
            
    def send_vote_request(self, voter: str, term: int):
  
        # Assumption is this idx wont increase when sending heartbeats right?
        candidate_last_index = self.__log.log_idx

        # get term of last item in log
        # can just do log.term -- current term
        candidate_term = self.__log.get(candidate_last_index).term
        request = raftdb.VoteRequest(term=candidate_term, logIndex=candidate_last_index)

        while self.status == config.STATE.CANDIDATE and self.term == term:

            with grpc.insecure_channel(voter) as channel:
                stub = raftdb_grpc.RaftStub(channel)
                vote_response = stub.RequestVote(request)
                
                # can this thread become dangling when a node dies? in a scneario where we never get a vote response back?
                if vote_response:
                    vote = vote_response['success']
                    # logger.debug(f'choice from {voter} is {choice}')
                    if vote == True and self.status == config.STATE.CANDIDATE:
                        self.update_votes()
                    elif not vote:
                        voter_term = vote_response['term']
                        if voter_term > self.term:
                            self.status = config.STATE.FOLLOWER
                            ### Update self term?
                            self.term = voter_term
                    break

# where is the RequestVode handler?
    def choose_vote(self, candidate_term: int, candidate_log_index: int) -> bool:
        '''
        Decide whether to vote for candidate or not on receiving request vote RPC.
       
        Returns True if current node's term is less than candidate term 
        OR
        if current node's term is same as candidate term and has fewer or equal entries in log

        Returns False otherwise
        '''
        # what's with so many election timeouts here?
        self.reset_election_timeout()
        voter_last_log_index = self.__log.logIndex
        # can just get the term from log.term
        voter_last_term = self.__log.get(voter_last_log_index).term

        if voter_last_term < candidate_term or \
                (voter_last_term == candidate_term and voter_last_log_index <= candidate_log_index): 
            self.reset_election_timeout()
            # this update should probably happen in the log layer
            # Actually, why is it that we're updating term here? What is the exact reason? Perhaps can be used by consensus to decide whethere to accept entry or not but that can done in other ways. Is there any other reason? In an election, a node can vote for multiple leaders anyway right?
            # Only one will get majority I think... No? 
            self.term = candidate_term
            return True, self.term, voter_last_log_index
        else:
            return False, self.term, voter_last_log_index
   