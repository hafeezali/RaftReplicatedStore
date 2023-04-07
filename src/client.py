import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from raft.config import RESPONSE_CODE_REDIRECT

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

class Client:

	def __init__(self):
		self.server_addr = 'localhost:50051'

	def redirectToLeader(self, leader_id):
		self.server_addr = peer_list_mappings[leader_id]

	def requestGet(self, key):
		# implement server update logic
		while True:
			with grpc.insecure_channel(self.server_addr) as channel:
				stub = raftdb_grpc.ClientStub(channel)
				request = raftdb.GetRequest(key=key)
				response = stub.Get(request)

				if response.code == RESPONSE_CODE_REDIRECT:
					self.redirectToLeader(response.leader_id)
				else:
					print(response.value)
					break

	def requestPut(self, key, value, clientid, sequence_number):
		# implement server update logic
		while True:
			with grpc.insecure_channel(self.server_addr) as channel:
				stub = raftdb_grpc.ClientStub(channel)
				request = raftdb.PutRequest(key=key, value=value, clientid = clientid,sequence_number = sequence_number )
				response = stub.Put(request)

				if response.code == RESPONSE_CODE_REDIRECT:
					self.redirectToLeader(response.leader_id)
				else:
					print(f"Put of key: {key}, value: {value} succeeded!\n")
					break


if __name__ == '__main__':
	client = Client()
	while True:
		reqType = int(input("Options - Get: 1, Put: 2, Quit: 3\n"))
		if reqType == 1:
			key = int(input("Enter key\n"))
			client.requestGet(key)
		elif reqType == 2:
			num = 4
			inputs = list(map(int, input("\nEnter key, value, clientid, seq_number [ex: 1 2 3 4]\n").strip().split()))[:num]
			client.requestPut(*inputs)
		elif reqType == 3:
			print("SEEEE YAAA\n")
			break
		else:
			print("Invalid input\n")