import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from store.database import Database
from raft.election import Election
from logs.log import Log
import raft.config as config

# Shouldn't this be implementing RaftServicer? Probably have to split that stupid shit RaftService to ConsensusService and ElectionService
# change this in protos -> todo
class Consensus(raftdb_grpc.ConsensusServicer) :

    def __init__(self, peers: list, store, log):
        self.__peers = peers
        # TODO: need to pass more params to Election
        self.__election = Election(peers=peers, store=store, log=log)
        self.__log = log
        self.counter = dict()
        self.commit_done = dict()
       
    
    # why are we calling it command instead of entry?
    def handlePut(self,entry):
        key = (entry.clientid, entry.sequence_number)
        self.counter[key] = 0
        self.waitForCommit[key] = 0
    # case where the leader fails, checks if already applied to the state machine
        last_committed_entry = self.__log.lastCommittedEntry(entry.clientid)

        if last_committed_entry!= -1 and last_committed_entry.sequence_number == entry.sequence_number:
            return 'OK'

        # probably get the index in the log when appending to use when committing later
        
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
            responses.append(executor.submit(
                        self.waitForCommit, client_request = key, log_index_to_commit = log_index_to_commit
                )
            )    
            # when do the executors start? on submit? If so, the append entries aren't sent in parallel
            
            while self.waitForCommit[key] != 1 :
                print("waiting for commit") 

            self.commit_done.pop(key)
            return 'OK'
    
    def waitForCommit(self, client_request, log_index_to_commit) :
        majority = len(self.__peers)/2 + 1
        while self.counter[client_request]!= majority :
            print("waiting for majority")

        self.__log.commit(log_index_to_commit)
        while self.__log.is_applied(log_index_to_commit) :
              print("waiting to go to db")

        self.waitForCommit[client_request] = 1 

    def create_log_entry_request(self, prev_log_index, entry):
        prev_term = -1
        if prev_log_index != -1:
            prev_term = self.__log.get(prev_log_index).term,
        
        request = raftdb.LogEntry(
            term = self.__log.get_term(), 
            logIndex = prev_log_index + 1,
            Entry = entry,
            prev_term = prev_term,
            prev_log_index = prev_log_index,
            # don't know what is this
            lastCommitIndex = self.__log.get_last_commit_index())
        return request         

    # Proably wanna rename this to correct_follower_log and broadcast entry. And maybe split into two methods?
    def broadcastEntry(self, follower : str, entry, log_index_to_commit):
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftStub(channel)
            prev_log_index = self.__log.get_log_idx() - 1
            request = self.create_log_entry_request(prev_log_index, entry)
            response = stub.AppendEntries(request)
            
            if response.code == 500 and response.term > self.__log.get_term() :
                self.__log.update_status(config.STATE.CANDIDATE)
                self.__log.update_term(response.term)

            else :
                while response.code != 200 :
                    prev_log_index = prev_log_index - 1
                    request = self.create_log_entry_request(prev_log_index, entry)
                    response = stub.AppendEntries(request)

                while prev_log_index < log_index_to_commit - 1:
                    prev_log_index = prev_log_index + 1
                    request = request = self.create_log_entry_request(prev_log_index, entry)
                    response = stub.AppendEntries(request)
	        
            key = (entry.clientid, entry.sequence_number)
            self.counter[key] += 1
            if self.counter[key] == len(self.__peers) :
                self.counter.pop(key)
            

    def AppendEntries(self, request, context):
        # If previous term and log index for request matches the last entry in log, append
        # Else, return error. Leader will decrement next index for replica and retry
        if request.term < self.__log.get_term() :
            return raftdb.LogEntryResponse(code=500, term = self.__log.get_term())
            
        if request.prev_term == -1 and request.prev_log_index == -1:
            # delete follower log if master log is empty
            self.__log.clear()

            self.__log.append({'key' : request.Entry.key,
                                'value' :request.Entry.value,
                                'term' : request.term, 
                                'clientid': request.Entry.clientid,
                                'sequence_number' : request.Entry.sequence_number
                                })  
            return raftdb.LogEntryResponse(code=200, term = self.__log.get_term())
        # can be simplified to request.prev_term == self.__log.term no? Actually do we need to have current index as a separate global var? Where else is that used?
        # What happens when the node is participating in an election and it receives an appendEntries rpc? Maybe this happens due to a network partition for heartbeat timeout period?? Guess this is handled because the node after casting a vote updates it's term? need to check this
        # random bs above 
        elif self.log.get_log_idx() >= request.prev_log_index and self.log.get(request.prev_log_index).term == request.prev_term : 
            value = {'key' : request.Entry.key,
                                'value' :request.Entry.value,
                                'term' : request.term,
                                'clientid': request.Entry.clientid,
                                'sequence_number' : request.Entry.sequence_number}
            self.__log.insert_at(self.__log.log_idx, value) 
            self.__log.commit_upto(request.lastCommitIndex)   
            return raftdb.LogEntryResponse(code=200, term = self.__log.get_term()) 
        else:
            return raftdb.LogEntryResponse(code=500, term = self.__log.get_term())


# When implementing commit, what happens if some random replica didnt participate in appendEntries but got a commit for some logIndex? How does follower know that the log it is committing is the log the leader is asking it to commit? term and logIndex might not be enough? Or is it?
    
