import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from store.database import Database
from logs.log import Log
import raft.config as config 
from threading import Lock, Thread
from concurrent import futures
import time

# Shouldn't this be implementing RaftServicer? Probably have to split that stupid shit RaftService to ConsensusService and ElectionService
# change this in protos -> todo
class Consensus(raftdb_grpc.ConsensusServicer) :


    def __init__(self, peers: list, log, logger):
        self.__peers = peers
        self.__log = log
        self.lock = Lock()
        self.counter = dict()
        self.commit_done = dict()
        self.logger = logger
       
    
    # why are we calling it command instead of entry?
    def handlePut(self,entry):
        self.logger.debug(f'Handling the put request for client id - {entry.clientid} and sequence number - {entry.sequence_number}')    
        # case where the leader fails, checks if already applied to the state machine
        last_committed_seq = self.__log.get_last_committed_sequence_for(entry.clientid)

        if last_committed_seq == entry.sequence_number:
            self.logger.debug(f'The request has already been executed.')
            return 'OK'

        key = (entry.clientid, entry.sequence_number)
        with self.lock :
            self.counter[key] = 0
            self.commit_done[key] = 0
        # probably get the index in the log when appending to use when committing later
        self.logger.debug(f'Appending the entry to log of {self.__log.server_id}')
        log_index_to_commit = self.__log.append({'key' : entry.key,
                            'value' : entry.value,
                            'term' : self.__log.get_term(),
                            'clientid': entry.clientid,
                            'sequence_number' : entry.sequence_number})
        with concurrent.futures.ThreadPoolExecutor() as executor:
            responses = []
            for follower in self.__peers:
                responses.append(
                        executor.submit(
                        self.broadcastEntry, follower = follower, entry = entry, log_index_to_commit = log_index_to_commit
                    )
                )
              
            # when do the executors start? on submit? If so, the append entries aren't sent in parallel
            self.logger.debug('Broadcasting append entries')
            
            while self.commit_done[key] != 1 :
                time.sleep(100)
                print("waiting for commit") 

            self.commit_done.pop(key)
            self.logger.debug(f'Committing the entry {entry}')
            self.__log.commit(log_index_to_commit)
            while self.__log.is_applied(log_index_to_commit) :
                time.sleep(100)
                print("waiting to go to db")
            self.logger.debug(f'Applying the entry {entry} to the state machine')
            return 'OK'

    def create_log_entry_request(self, prev_log_index, entry):
        self.logger.debug("Inside create log entry request") 
        prev_term = -1
        if prev_log_index != -1:
            self.logger.debug("Fetching log entry at prev_log_index")
            prev_term = self.__log.get(prev_log_index)['term'],
        self.logger.debug("Fetching current term")
        term = self.__log.get_term()
        self.logger.debug("Fetching last commit index")
        lastCommitIndex = self.__log.get_last_commit_index()
        self.logger.debug("trying to create the request object")
        request = raftdb.LogEntry(
            term = term, 
            logIndex = prev_log_index + 1,
            key = entry.key,
		    value = entry.value,
		    clientid = entry.clientid,
	        sequence_number = entry.sequence_number,
	
            prev_term = prev_term,
            prev_log_index = prev_log_index,
            lastCommitIndex = lastCommitIndex)
        self.logger.debug("Generated to create the request object")
        return request         

    # Proably wanna rename this to correct_follower_log and broadcast entry. And maybe split into two methods?
    def broadcastEntry(self, follower : str, entry, log_index_to_commit):
        with grpc.insecure_channel(follower, options=(('grpc.enable_http_proxy', 0),)) as channel:
            self.logger.debug(f'Broadcasting append entry to {follower}')
            stub = raftdb_grpc.ConsensusStub(channel)
            self.logger.debug("Generated stub")
            prev_log_index = log_index_to_commit - 1
            request = self.create_log_entry_request(prev_log_index, entry)
            try:
                self.logger.debug("Send append entries rpc")
                response = stub.AppendEntries(request)
                self.logger.debug("Send append entries rpc done")
            except grpc.RpcError as e:
                status_code = e.code()
              
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    # timeout, will retry if we are still leader
                    self.logger.debug(f'Request vote failed with timeout error, peer: {voter}, {status_code} details: {e.details()}')
                else :
                    self.logger.debug(f'Some other error, details: {status_code} {e.details()}') 
            except Exception as e:
                self.logger.debug(f'Some other error, details: {status_code} {e.details()}') 
            
            if response.code == 500 and response.term > self.__log.get_term() :
                self.logger.debug('There is a server with larger term, updating term and status')
                self.__log.update_status(config.STATE.CANDIDATE)
                self.__log.update_term(response.term)

            else :
                # have a different response code for this scenario to differentiate from other errors. Term can change and this will never exit
                while response.code != 200 :
                    self.logger.debug('The entry is not matching the server log')
                    prev_log_index = prev_log_index - 1
                    request = self.create_log_entry_request(prev_log_index, entry)
                    response = stub.AppendEntries(request)

                while prev_log_index < log_index_to_commit - 1:
                    self.logger.debug('Inserting correct entry in the server log')
                    prev_log_index = prev_log_index + 1
                    request = request = self.create_log_entry_request(prev_log_index, entry)
                    response = stub.AppendEntries(request)
	        
                key = (entry.clientid, entry.sequence_number)
                majority = len(self.__peers)/2 + 1
                with self.lock :
                    self.counter[key] += 1
                    if self.counter[key] >= majority and key in self.commit_done:
                        self.logger.debug('Majority - wuhooooyayyyyy')
                        self.commit_done[key] = 1
                    if self.counter[key] == len(self.__peers) :
                        self.logger.debug(f'All the peers have {key} in their log, noicee')
                        self.counter.pop(key)
            

    def AppendEntries(self, request, context):
        # If previous term and log index for request matches the last entry in log, append
        # Else, return error. Leader will decrement next index for replica and retry
        if request.term < self.__log.get_term() :
            self.logger.debug('I am the appendEntry handler, my term is greater than the server term')
            return raftdb.LogEntryResponse(code=500, term = self.__log.get_term())
            
        if request.prev_term == -1 and request.prev_log_index == -1:
            # delete follower log if master log is empty
            self.logger.debug('Nothing in master log, clearing follower log and adding first entry')
            self.__log.clear()

            self.__log.append({'key' : request.key,
                                'value' :request.value,
                                'term' : request.term, 
                                'clientid': request.clientid,
                                'sequence_number' : request.sequence_number
                                })  
            return raftdb.LogEntryResponse(code=200, term = self.__log.get_term())
        # can be simplified to request.prev_term == self.__log.term no? Actually do we need to have current index as a separate global var? Where else is that used?
        # What happens when the node is participating in an election and it receives an appendEntries rpc? Maybe this happens due to a network partition for heartbeat timeout period?? Guess this is handled because the node after casting a vote updates it's term? need to check this
        # random bs above 
        elif self.log.get_log_idx() >= request.prev_log_index and self.log.get(request.prev_log_index).term == request.prev_term : 
            self.logger.debug(f'Previous entry matches in the log for key - {request.Entry.key} and value - {request.Entry.value}')
            value = {'key' : request.Entry.key,
                                'value' :request.Entry.value,
                                'term' : request.term,
                                'clientid': request.Entry.clientid,
                                'sequence_number' : request.Entry.sequence_number}
            self.__log.insert_at(request.logIndex, value) 
            self.__log.commit_upto(request.lastCommitIndex)   
            return raftdb.LogEntryResponse(code=200, term = self.__log.get_term()) 
        else:
            self.logger.debug(f'Previous entry does not match in the log for key - {request.Entry.key} and value - {request.Entry.value}')
            return raftdb.LogEntryResponse(code=500, term = self.__log.get_term())


# When implementing commit, what happens if some random replica didnt participate in appendEntries but got a commit for some logIndex? How does follower know that the log it is committing is the log the leader is asking it to commit? term and logIndex might not be enough? Or is it?
    
