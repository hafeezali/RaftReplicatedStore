import concurrent.futures
import random
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from raft.store import Store
from raft.election import Election

class Consensus() :
	def __init__(self,peers: list):
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
                		sendAppendEntry, follower = follower, command = command
            		)
				)

			completed = concurrent.futures.as_completed(responses)
			if len(completed) > len(self.__peers)/2 + 1 :
				self.rocksdb.put(command.key, command.value)
				return 'OK'
			
	

	def sendAppendEntry(self, follower : str, command):
		with grpc.insecure_channel(follower) as channel:
			stub = raftdb_grpc.RaftStub(channel)
			term_index = self.__store.termIndex-1
			request = raftdb.LogEntry(term=self.__store.log[term_index].term, termIndex=term_index,
					Entry={'key' : command.key,'value' : command.value},lastCommitIndex=self.__store.lastCommitIndex, commit = 0)
			response = stub.AppendEntries(request)
			while response.code != 1 :
				term_index = term_index - 1
				request = raftdb.LogEntry(term=self.__store.log[term_index].term, termIndex=term_index,
					Entry={'key' : command.key,'value' : command.value},lastCommitIndex=self.__store.lastCommitIndex, commit = 0)
				response = stub.AppendEntries(request)

			while term_index!= self.__store.termIndex:
				term_index = term_index + 1
				request = raftdb.LogEntry(term=self.__store.log[term_index].term, termIndex=term_index,
					Entry={'key' : self.__store.log[term_index].key,'value' : self.__store.log[term_index].value},lastCommitIndex=self.__store.lastCommitIndex, commit= 1)
				response = stub.AppendEntries(request)
			print(response.value)
		

			

	def AppendEntry(self, request, context) :
		if request.commit == 0 :
			if request.term == self.__store.log[request.termIndex].term :
				return raftdb.LogEntryResponse(code=200)
			else :
				return raftdb.LogEntryResponse(code='ERR')
			
		else :
			self.__store.log.append({'key' : request.Entry.key,
									'value' :request.Entry.value,
									'term' : request.term})
			return raftdb.LogEntryResponse(code=200)



	
