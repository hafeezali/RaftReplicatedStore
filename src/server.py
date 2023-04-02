from raft.election import elect
from raft.consensus import Consensus
from concurrent import futures

import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc

STATE = {
	'CANDIDATE': 1,
	'FOLLOWER': 2,
	'LEADER': 3	
}

class Server(raftdb_grpc.ClientServicer):

	def __init__(self):
		self.store = dict()
		self.state = STATE['FOLLOWER']
		self.log = list()
		self.port = '50051'
		self._consensus = Consensus(peers=peer_list)

	def recover(self):
		pass

	def Get(self, request, context):
		return raftdb.GetResponse(code = 200, value = self.store[request.key])

	def Put(self, request, context):
		self.store[request.key] = request.value
		command = {
			'key' : request.key,
			'value' : request.value
		}
		if self._consensus.handlePut(command) == 'OK':
			return raftdb.PutResponse(code = 200)
		else :
			#some error code
			return raftdb.PutResponse(code = 200)

	def insertToLog(self, message):
		pass

	def commitLog(self, index):
		pass

	def accept(self, message):
		pass

def serve():
	port = '50051'
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	raftdb_grpc.add_ClientServicer_to_server(Server(), server)
	server.add_insecure_port('[::]:' + port)
	server.start()
	server.wait_for_termination()

if __name__ == '__main__':
	server = serve()