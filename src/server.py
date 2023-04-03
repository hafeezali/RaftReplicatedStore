from raft.election import Election
from raft.consensus import Consensus
from concurrent import futures
from store.database import Database
from logs.log import Log

import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc

class Server(raftdb_grpc.ClientServicer):

	def __init__(self, type, server_id, client_port, raft_port, peer_list):
		self.store = Database(type='memory', server_id='server_1')
		# who updates state? does this need be here or in election layer?
		self.state = STATE['FOLLOWER']
		self.log = Log(server_id, self.store)
		self.client_port = client_port
		self.raft_port = raft_port
		self.consensus = Consensus(peers=peer_list, self.store, self.log)

	def Get(self, request, context):
		# Implement leader check logic
		# Make sure this is strongly consistent -- if we allow only one outstanding client request, the system must be strongly consistent by default
		return raftdb.GetResponse(code = 200, value = self.store.get(request.key))

	def Put(self, request, context):
		# Implement leader check logic
		# What happens when we dont get majority? Retry or fail? -- Im guessing fail and respond to client
		command = {
			'key' : request.key,
			'value' : request.value
		}
		# can i not just directly pass request to command?
		if self.consensus.handlePut(command) == 'OK':
			return raftdb.PutResponse(code = 200)
		else :
			# add more appropriate error message
			return raftdb.PutResponse(code = 500)

def serve(server):
	port = '50051'
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	raftdb_grpc.add_ClientServicer_to_server(, server)
	server.add_insecure_port('[::]:' + port)
	server.start()
	server.wait_for_termination()

if __name__ == '__main__':
	# Implement arg parse to read server arguments
	type = 'memory'
	server_id = 'server_1'
	client_port = '50051'
	raft_port = '50052'

	Server server = Server(type, server_id, client_port, raft_port)
	serve(server)