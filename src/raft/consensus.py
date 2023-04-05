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
       
    
    # why are we calling it command instead of entry?
    def handlePut(self,entry):
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
                        self.broadcastEntry, follower = follower, entry = entry
                    )
                )
            # when do the executors start? on submit? If so, the append entries aren't sent in parallel
            completed = concurrent.futures.as_completed(responses)
            if len(completed) > len(self.__peers)/2 + 1 :
                # TODO: Put value in database - are we supposed to update state here? Or just add it as ready for commit in log?
                # What happens when we get two consecutive updates but the latter gets committed but the former isn't? 
                # 1, 2 => 1 doesnt get consensus, but 2 gets. Do we mark 2 as committed before retrying 1? Do we even retry 1 or just remove that from log? Can we remove from log? but actually why wont it ever get accepted eventually if future ones are getting accepted.... i guess we're safe
                self.__log.commit(log_index_to_commit)
                # sleep because this entry needs to be pushed to database as well - this should be handled in commit function itself
                while self.__log.is_applied(log_index_to_commit) :
                    print("waiting to go to db")
                # self.rocksdb.put(command.key, command.value)
                return 'OK'
    
    def create_log_entry_request(self, prev_log_index, entry):
        prev_term = -1
        if prev_log_index != -1:
            prev_term = self.__log.get(prev_log_index).term,
        
        request = raftdb.LogEntry(
            term = self.__log.get_term(), 
            logIndex = prev_log_index + 1,
            Entry = {'key' : entry.key,
                    'value' : entry.value,
                    'clientid' : entry.clientid,
                    'sequence_number' : entry.sequence_number
                    },
            prev_term = prev_term,
            prev_log_index = prev_log_index,
            lastCommitIndex = self.__log.lastCommitIndex)
        return request         

    # Proably wanna rename this to correct_follower_log and broadcast entry. And maybe split into two methods?
    def broadcastEntry(self, follower : str, entry):
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

                while prev_log_index < self.__log.get_log_idx() - 1:
                    prev_log_index = prev_log_index + 1
                    request = request = self.create_log_entry_request(prev_log_index, entry)
                    response = stub.AppendEntries(request)
	
            

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
        elif request.prev_term == self.__log.get(self.__log.log_idx).term \
                and request.prev_log_index == self.__log.log_idx:
            value = {'key' : request.Entry.key,
                                'value' :request.Entry.value,
                                'term' : request.term,
                                'clientid': request.Entry.clientid,
                                'sequence_number' : request.Entry.sequence_number}
            self.__log.insert_at(self.__log.log_idx, value) 
            self.__log.commit(request.lastCommitIndex)   
            return raftdb.LogEntryResponse(code=200, term = self.__log.get_term()) 
        else:
            return raftdb.LogEntryResponse(code=500, term = self.__log.get_term())


# When implementing commit, what happens if some random replica didnt participate in appendEntries but got a commit for some logIndex? How does follower know that the log it is committing is the log the leader is asking it to commit? term and logIndex might not be enough? Or is it?
    
