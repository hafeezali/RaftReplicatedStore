import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from logs.log import Log
import raft.config as config 
from threading import Lock, Thread
from concurrent import futures
import time

'''
TODO:
1. Should sleep time while waiting for follower responses be 10 secs? Seems like a lot no? Fine-tune this
2. In broadcast_entry code, if response code == 500 and if follower term is higher, how should we respond to client? 
    - We should just step down and redirect client to new leader
3. In broadcase_entry code, if response code == 500 and if follower term is higher, we should step down as leader and update status, term, 
4. While performing append entries, if a new leader is elected, we need to step down as leader. At the very least, we shouldn't commit this entry and let the new leader clean the logs.
5. The commit done while loop may never exit
6. We need a different response code for sitauations where the follower log is inconsistent with the leader log
7. We are not setting the correct entry when correcting the log. Also, confirm that when log idx goes all the way to 0, we are still handling it properly
8. Shouldn't "while prev_log_index < log_index_to_commit - 1:" be <=
9, In AppendEntries, should we get term, multiple times or fetch it once. Pros vs cons?
10. In AppendEntries, self.__log.commit_upto(request.lastCommitIndex) should be commit_upto(min(request.lastCommitIndex, index_from_insert_at))
11. If majority is not received, we have to retry until it succeeds otherwise find a way to clear the leader log. Retry must happen from within consensus
'''

class Consensus(raftdb_grpc.ConsensusServicer) :

    def __init__(self, peers: list, log, logger):
        self.__peers = peers
        self.__log = log
        self.lock = Lock()
        self.counter = dict()
        self.commit_done = dict()
        self.logger = logger

    def handlePut(self,entry):
        self.logger.debug(f'Handling the put request for client id - {entry.clientid} and sequence number - {entry.sequence_number}')

        # case where the leader fails, checks if already applied to the state machine
        last_committed_seq = self.__log.get_last_committed_sequence_for(entry.clientid)

        if last_committed_seq == entry.sequence_number:
            self.logger.debug(f'The request has already been executed.')
            return 'OK'

        # initialize counter and commit_done to check majority and commit
        key = (entry.clientid, entry.sequence_number)
        with self.lock :
            self.counter[key] = 0
            self.commit_done[key] = 0

        self.logger.debug(f'Appending the entry to log of {self.__log.server_id}')
        log_index_to_commit = self.__log.append({'key' : entry.key,
                            'value' : entry.value,
                            'term' : self.__log.get_term(),
                            'clientid': entry.clientid,
                            'sequence_number' : entry.sequence_number})

        self.logger.debug('Broadcasting append entries')
        with concurrent.futures.ThreadPoolExecutor() as executor:
            responses = []
            for follower in self.__peers:
                responses.append(
                    executor.submit(self.broadcastEntry, follower = follower, entry = entry, log_index_to_commit = log_index_to_commit)
                )              
        
        while self.commit_done[key] != 1 :
            time.sleep(100/1000)
            self.logger.debug("Waiting for responses from followers for key: " + str(entry.key) + ", value: " + str(entry.value)) 

        self.commit_done.pop(key)

        self.logger.debug(f'Committing the entry {entry}')

        self.__log.commit(log_index_to_commit)

        while self.__log.is_applied(log_index_to_commit) :
            time.sleep(100/1000)
            self.logger.info("Waiting for log to commit entry for key: " + str(entry.key))

        return 'OK'

    def create_log_entry_request(self, prev_log_index, entry):
        self.logger.debug("Creating log entry request for index: " + str(prev_log_index + 1))

        prev_term = -1
        if prev_log_index != -1:
            prev_term = self.__log.get(prev_log_index)['term']
        
        term = self.__log.get_term()
        lastCommitIndex = self.__log.get_last_commit_index()
        
        self.logger.debug(f'Trying to create the request object term - {term}, prev_term - {prev_term}, lastcommitidx - {lastCommitIndex}')

        raft_entry = raftdb.LogEntry.Entry(
            key = entry.key,
            value = entry.value,
            clientid = entry.clientid,
            sequence_number = entry.sequence_number)

        request = raftdb.LogEntry(
            term = term, 
            logIndex = prev_log_index + 1,
            entry = raft_entry,
	        prev_term = prev_term,
            prev_log_index = prev_log_index,
            lastCommitIndex = lastCommitIndex)

        return request         

    def broadcastEntry(self, follower : str, entry, log_index_to_commit):
        with grpc.insecure_channel(follower, options=(('grpc.enable_http_proxy', 0),)) as channel:
            self.logger.debug(f'Broadcasting append entry to {follower}')

            stub = raftdb_grpc.ConsensusStub(channel)

            prev_log_index = log_index_to_commit - 1
            request = self.create_log_entry_request(prev_log_index, entry)

            try:
                response = stub.AppendEntries(request)

                if response.code == 500 and response.term > self.__log.get_term():
                    self.logger.debug('There is a server with larger term, updating term and status')
                    self.__log.update_status(config.STATE.CANDIDATE)
                    self.__log.update_term(response.term)
                else :
                    while response.code != 200 :
                        self.logger.debug('The entry is not matching the corresponding entry in the follower log')
                        prev_log_index = prev_log_index - 1
                        request = self.create_log_entry_request(prev_log_index, entry)
                        response = stub.AppendEntries(request)

                    while prev_log_index < log_index_to_commit - 1:
                        self.logger.debug('Inserting correct entry in the server log')
                        prev_log_index = prev_log_index + 1
                        request = self.create_log_entry_request(prev_log_index, entry)
                        response = stub.AppendEntries(request)

                    key = (entry.clientid, entry.sequence_number)
                    majority = len(self.__peers)/2 + 1
                    with self.lock :
                        self.counter[key] += 1
                        if self.counter[key] >= majority and key in self.commit_done:
                            self.logger.debug('We have obtained responses from majority of follower nodes for key: ' + str(entry.key))
                            self.commit_done[key] = 1
                        if self.counter[key] == len(self.__peers):
                            self.logger.debug(f'All the peers have {key} in their log')
                            self.counter.pop(key)
            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    self.logger.debug(f'Request vote failed with timeout error, peer: {voter}, {status_code} details: {e.details()}')
                else :
                    self.logger.debug(f'Some other error, details: {status_code} {e.details()}') 
            except Exception as e:
                self.logger.debug(f'Some other non-grpc error, details: {status_code} {e.details()}')             

    def AppendEntries(self, request, context):
        # If previous term and log index for request matches the last entry in log, append
        # Else, return error. Leader will decrement next index for replica and retry
        entry = request.entry

        self.logger.debug('Trying to append key: ' + str(entry.key))

        if request.term < self.__log.get_term() :
            self.logger.debug('Inside appendEntry handler, my term is greater than the server term')
            return raftdb.LogEntryResponse(code=config.RESPONSE_CODE_REJECT, term = self.__log.get_term())

        if request.prev_term == -1 and request.prev_log_index == -1:
            self.logger.debug('Leader log is empty, clearing follower log and adding first entry')

            self.__log.clear()
            self.__log.append({'key' : entry.key,
                                'value' :entry.value,
                                'term' : entry.term, 
                                'clientid': entry.clientid,
                                'sequence_number' : entry.sequence_number
                                })
            return raftdb.LogEntryResponse(code=config.RESPONSE_CODE_OK, term = self.__log.get_term())
        elif self.__log.get_log_idx() >= request.prev_log_index and self.__log.get(request.prev_log_index)['term'] == request.prev_term:
            self.logger.debug(f'Previous entry matches in the log for key - {entry.key} and value - {entry.value}')

            value = {'key' : entry.key,
                        'value' :entry.value,
                        'term' : entry.term,
                        'clientid': entry.clientid,
                        'sequence_number' : entry.sequence_number}
            self.__log.insert_at(request.logIndex, value) 
            self.__log.commit_upto(request.lastCommitIndex)
            return raftdb.LogEntryResponse(code=config.RESPONSE_CODE_OK, term = self.__log.get_term()) 
        else:
            self.logger.debug(f'Previous entry does not match in the log for key - {entry.key} and value - {entry.value}')
            return raftdb.LogEntryResponse(code=config.RESPONSE_CODE_REJECT, term = self.__log.get_term())
    
