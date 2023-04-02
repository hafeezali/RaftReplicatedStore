import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from raft.store import Store
from raft.election import Election

class Consensus() :
    def __init__(self, peers: list):
        #need to edit it 
        self.__store = Store()
        self.__peers = peers
        self.__election = Election(store=self.__store)
    
    def handlePut(self, command) :
    
        self.__store.log.append({'key' : command.key,
                                  'value' : command.value,
                                 'term' : self.__election.term})
        with concurrent.futures.ThreadPoolExecutor() as executor:
            responses = []
            for follower in self.__peers:
                responses.append(
                        executor.submit(
                        self.sendAppendEntry, follower = follower, command = command
                    )
                )
            
            completed = concurrent.futures.as_completed(responses)
            if len(completed) > len(self.__peers)/2 + 1 :
                self.rocksdb.put(command.key, command.value)
                return 'OK'
            
    
    def create_log_entry_request(self, log_index, command):
        prev_term = -1
        if log_index != 0:
            prev_term = self.__store.log[log_index - 1].term,
        
        request = raftdb.LogEntry(
            term = self.__store.log[log_index].term, 
            logIndex = log_index,
            Entry = {'key' : command.key,
                    'value' : command.value
                    },
            prev_term = prev_term,
            prev_log_index = log_index - 1,
            lastCommitIndex = self.__store.lastCommitIndex)
        return request         

    def sendAppendEntry(self, follower : str, command):
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftStub(channel)
            log_index = self.__store.logIndex
            request = self.create_log_entry_request(log_index, command)
            response = stub.AppendEntries(request)

            while response.code != 200 :
                log_index = log_index - 1
                request = self.create_log_entry_request(log_index, command)
                response = stub.AppendEntries(request)

            while log_index!= self.__store.logIndex:
                log_index = log_index + 1
                request = request = self.create_log_entry_request(log_index, command)
                response = stub.AppendEntries(request)
            
        

            

    def AppendEntries(self, request, context) :
        # If previous term and log index for request matches the last entry in log, append
        # Else, return error. Leader will decrement next index for replica and retry

        if request.prev_term == -1 and request.prev_log_index == -1:
            # delete follower log if master log is empty
            self.__store.log.clear()

            self.__store.log.append({'key' : request.Entry.key,
                                    'value' :request.Entry.value,
                                    'term' : request.term})  
            return raftdb.LogEntryResponse(code=200)

        elif request.prev_term == self.__store.log[self.__store.logIndex].term \
                and request.prev_log_index == self.__store.logIndex:
            
            self.__store.log.append({'key' : request.Entry.key,
                                    'value' :request.Entry.value,
                                    'term' : request.term})    
            return raftdb.LogEntryResponse(code=200)
        
        elif request is not None and request.Entry is None:
            # ack for heartbeat
            return raftdb.LogEntryResponse(code=200) 
        else:
            return raftdb.LogEntryResponse(code='ERR')



    
