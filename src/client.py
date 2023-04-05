import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc

class Client:

	def __init__(self):
		self.server_addr = 'localhost:50051'

	def requestGet(self, key):
		# implement server update logic
		with grpc.insecure_channel(self.server_addr) as channel:
			stub = raftdb_grpc.ClientStub(channel)
			request = raftdb.GetRequest(key=key)
			response = stub.Get(request)
			print(response.value)

	def requestPut(self, key, value, clientid, sequence_number):
		# implement server update logic
		with grpc.insecure_channel(self.server_addr) as channel:
			stub = raftdb_grpc.ClientStub(channel)
			request = raftdb.PutRequest(key=key, value=value, clientid = clientid,sequence_number = sequence_number )
			response = stub.Put(request)

if __name__ == '__main__':
	client = Client()
	while True:
		reqType = int(input("Enter 1 to get and 2 to put\n"))
		if reqType == 1:
			key = int(input("Enter key\n"))
			client.requestGet(key)
		elif reqType == 2:
			key = int(input("Enter key\n"))
			value = int(input("Enter value\n"))
			clientid = int(input("Enter clientid\n"))
			sequence_number = int(input("Enter seq_number\n"))
			client.requestPut(key, value, clientid, sequence_number)
		else:
			print("Invalid input\n")