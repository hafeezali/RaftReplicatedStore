import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from raft.store import Store
from raft.election import Election
from logs.log import Log

# Shouldn't this be implementing RaftServicer? Probably have to split that stupid shit RaftService to ConsensusService and ElectionService
class Consensus() :

    def __init__(self, peers: list, store, log):
        self.__peers = peers
        # TODO: need to pass more params to Election
        self.__election = Election(store=store, log=log)
        # why is store needed in consensus?
        self.__store = store
        self.__log = log
    
    # why are we calling it command instead of entry?
    def handlePut(self, command):
        # probably get the index in the log when appending to use when committing later
        self.__log.append({'key' : command.key,
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
            # when do the executors start? on submit? If so, the append entries aren't sent in parallel
            completed = concurrent.futures.as_completed(responses)
            if len(completed) > len(self.__peers)/2 + 1 :
                # TODO: Put value in database - are we supposed to update state here? Or just add it as ready for commit in log?
                # What happens when we get two consecutive updates but the latter gets committed but the former isn't? 
                # 1, 2 => 1 doesnt get consensus, but 2 gets. Do we mark 2 as committed before retrying 1? Do we even retry 1 or just remove that from log? Can we remove from log? but actually why wont it ever get accepted eventually if future ones are getting accepted.... i guess we're safe
                self.__log.commit()
                # self.rocksdb.put(command.key, command.value)
                return 'OK'
    
    def create_log_entry_request(self, log_index, command):
        prev_term = -1
        if log_index != 0:
            prev_term = self.__log.get(log_index - 1).term,
        
        request = raftdb.LogEntry(
            term = self.__log.get(log_index).term, 
            logIndex = log_index,
            Entry = {'key' : command.key,
                    'value' : command.value
                    },
            prev_term = prev_term,
            prev_log_index = log_index - 1,
            lastCommitIndex = self.__log.lastCommitIndex)
        return request         

    # Proably wanna rename this to correct_follower_log and broadcast entry. And maybe split into two methods?
    def sendAppendEntry(self, follower : str, command):
        with grpc.insecure_channel(follower) as channel:
            stub = raftdb_grpc.RaftStub(channel)
            log_index = self.__log.logIndex
            request = self.create_log_entry_request(log_index, command)
            response = stub.AppendEntries(request)

            while response.code != 200 :
                log_index = log_index - 1
                request = self.create_log_entry_request(log_index, command)
                response = stub.AppendEntries(request)

            while log_index != self.__log.logIndex:
                log_index = log_index + 1
                request = request = self.create_log_entry_request(log_index, command)
                response = stub.AppendEntries(request)

    def AppendEntries(self, request, context):
        # If previous term and log index for request matches the last entry in log, append
        # Else, return error. Leader will decrement next index for replica and retry

        if request.prev_term == -1 and request.prev_log_index == -1:
            # delete follower log if master log is empty
            self.__log.clear()

            self.__log.append({'key' : request.Entry.key,
                                'value' :request.Entry.value,
                                'term' : request.term})  
            return raftdb.LogEntryResponse(code=200)
        # can be simplified to request.prev_term == self.__log.term no? Actually do we need to have current index as a separate global var? Where else is that used?
        elif request.prev_term == self.__log.get(self.__log.log_idx).term \
                and request.prev_log_index == self.__log.log_idx:
            
            self.__log.append({'key' : request.Entry.key,
                                'value' :request.Entry.value,
                                'term' : request.term})    
            return raftdb.LogEntryResponse(code=200)
        elif request is not None and request.Entry is None:
            # ack for heartbeat
            # if leader receives heartbeat with a higher term, it should revert to follower, right?
            return raftdb.LogEntryResponse(code=200) 
        else:
            return raftdb.LogEntryResponse(code=500)


# When implementing commit, what happens if some random replica didnt participate in appendEntries but got a commit for some logIndex? How does follower know that the log it is committing is the log the leader is asking it to commit? term and logIndex might not be enough? Or is it?
    
