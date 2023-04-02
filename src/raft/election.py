import time
from threading import Lock, Thread
from queue import Queue
from raft.config import STATE
from raft.config import random_timeout
from raft.config import HB_TIME
from random import randrange
import raft.config as config


class Election:
    def __init__(self, transport: Transport, store: Store, queue: Queue):
        self.timeout_thread = None
        self.status = STATE.FOLLOWER
        self.term = 0
        self.num_votes = 0
        self.store = store
        self.__transport = transport
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
        self.status = STATE.CANDIDATE

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
        return randrange(config.LOW_TIMEOUT, config.HIGH_TIMEOUT) / 1000
    
    def reset_election_timeout(self):
        '''
        If we get a heartbeat from the leader, reset election timeout
        '''
        self.election_time = time.time() + random_timeout()

    def replica_loop(self):
        '''
        Followers execute this loop, and wait for heartbeats from leader
        '''
        while self.status != STATE.LEADER:
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
                self.status = STATE.LEADER
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
        # self.q.put({})
        # self.status == cfg.LEADER
        # if self.store.staged:
        #     # logger.info(f"STAGED>>>>>>>>>>>, {self.store.staged}")
        #     if self.store.staged.get('delete', False):
        #         self.store.delete(self.term, self.store.staged,
        #                           self.__transport, self.majority)
        #     else:
        #         self.store.put(self.term, self.store.staged,
        #                        self.__transport, self.majority)
        # logger.info(f"I'm the leader of the pack for the term {self.term}")
        # logger.debug('sending heartbeat to other replicas')
        for peer in self.replicas:
            Thread(target=self.append_entries, args=(peer,)).start()
        
    def append_entries(self, peer: str):
        '''
        Append Entries, currently sending no data, only heartbeat to followers
        If we receive a reply with term greater than ours, revert to follower state
        '''
        try:
            # if self.store.log:
            #     self.update_follower_commit(peer)
            
            message = {'term': self.term, 'addr': self.__transport.addr}
            while self.status == STATE.LEADER:
                # logger.debug(f'[PEER HEARTBEAT] {peer}')
                start = time.time()
                reply = self.__transport.heartbeat(peer=peer, message=message)
                if reply:
                    if reply['term'] > self.term:
                        self.term = reply['term']
                        self.status = STATE.FOLLOWER
                        self.election_timeout()
                wait_time = time.time() - start
                time.sleep((HB_TIME - wait_time) / 1000) ### CHECK
                # logger.debug(f'[PEER HEARTBEAT RESPONSE] {peer} {reply}')
        except Exception as e:
            raise e
        
    def request_votes(self):
        '''
        Request votes from other nodes in the cluster.
        '''
        for peer in self.replicas:
            Thread(target=self.send_vote_request,
                   args=(peer, self.term)).start()
            
    def send_vote_request(self, voter: str, term: int):
        '''
        send vote request message to the voter node
        this message contains the current term of this node,
        the latest commit id and any cached data
        :param voter: address of the voter node in `ip:port`
                      format
        :type voter: str
        :param term: current term of this node
        :type term: int
        '''
        message = {
            'candidate_term': term,
            'candidate_commit_id': self.store.commit_id
        }
  
        term_index = self.__store.termIndex - 1
        request = raftdb.VoteRequest(term=self.__store.log[term_index].term, termIndex=term_index)

        while self.status == STATE.CANDIDATE and self.term == term:
            vote_reply = self.__transport.vote_request(voter, message)
            if vote_reply:
                choice = vote_reply['choice']
                # logger.debug(f'choice from {voter} is {choice}')
                if choice and self.status == STATE.CANDIDATE:
                    self.submit_vote()
                elif not choice:
                    term = vote_reply['term']
                    if term > self.term:
                        self.status = STATE.FOLLOWER
                break


    def choose_vote(self, candidate_term: int, candidate_commit_id: int) -> bool:
        '''
        Decide whether to vote for candidate or not on receiving request vote RPC.
       
        Returns True if current node's term is less than candidate term 
        and current node's commit id is less than candidate's commit id.

        Returns False otherwise
        '''
        self.reset_election_timeout()
        if self.term < candidate_term and self.store.commit_id <= candidate_commit_id:
            self.reset_election_timeout()
            self.term = candidate_term
            return True, self.term
        else:
            return False, self.term
   