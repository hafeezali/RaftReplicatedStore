import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc

class Client:

	def __init__(self):
		self.server_addr = 'localhost:50051'

	def requestGet(self, key):
		with grpc.insecure_channel(self.server_addr) as channel:
			stub = raftdb_grpc.ClientRequestStub(channel)
			request = raftdb.ClientReq(type=1, key=key)
			response = stub.SendRequest(request)
			print(response.value)

	def requestPut(self, key, value):
		with grpc.insecure_channel(self.server_addr) as channel:
			stub = raftdb_grpc.ClientRequestStub(channel)
			request = raftdb.ClientReq(type=2, key=key, value=value)
			response = stub.SendRequest(request)
			print(response.value)

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
			client.requestPut(key, value)
		else:
			print("Invalid input\n")