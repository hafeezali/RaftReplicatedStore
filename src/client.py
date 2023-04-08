import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
import time

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
TODO:
1. Sequence number must be monotonically increasing.
2. Redirection can happen in 2 scenarios:
 - No leader is elected yet. We need to sleep for this
 - Different leader elected. We should retry immediately here
3. Fine tune CLIENT_SLEEP_TIME 
'''
class Client:

	def __init__(self):
		self.server_addr = 'localhost:50051'

	def redirectToLeaderGet(self, leader_id, key):
		print("Redirecting to leader with id: " + leader_id)
		self.server_addr = peer_list_mappings[leader_id]
		return self.requestGet(key)
		
	def redirectToLeaderPut(self, leader_id, key,value, clientid, sequence_number):
		print(leader_id)
		self.server_addr = peer_list_mappings[leader_id]
		return self.requestPut(key, value, clientid, sequence_number)	

	def requestGet(self, key):
		with grpc.insecure_channel(self.server_addr) as channel:
			stub = raftdb_grpc.ClientStub(channel)
			request = raftdb.GetRequest(key=key)

			try:
				response = stub.Get(request, timeout=config.RPC_TIMEOUT)
				leader_id = response.leaderId
				print(leader_id)
				while response.code == config.RESPONSE_CODE_REDIRECT and (leader_id == None or leader_id == '') :
					print('Waiting for election to happen')
					time.sleep(config.CLIENT_SLEEP_TIME)
					response = stub.Get(request, timeout=config.RPC_TIMEOUT)
					leader_id = response.leaderId
					
				if response.code == config.RESPONSE_CODE_REDIRECT :
					response = self.redirectToLeaderGet(response.leaderId.replace("'", ""), key)

				elif response.code == config.RESPONSE_CODE_OK:
					print(f"GET for key: {key} Succeeded, value: {response.value}\n")
				else:
					print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")

			except grpc.RpcError as e:
				status_code = e.code()
				if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
					print(f"Client request for Get key: {key} timed out, details: {status_code} {e.details()}\n")
				else:
					print(f'Some other error, details: {status_code} {e.details()}') 

	def requestPut(self, key, value, clientid, sequence_number):
			with grpc.insecure_channel(self.server_addr) as channel:
				stub = raftdb_grpc.ClientStub(channel)
				request = raftdb.PutRequest(key=key, value=value, clientid = clientid, sequence_number = sequence_number)
				
				try:
					response = stub.Put(request, timeout=config.RPC_TIMEOUT)

					leader_id = response.leaderId
					print(leader_id)
					while response.code == config.RESPONSE_CODE_REDIRECT and (leader_id == None or leader_id == '') :
						print('Waiting for election to happen')
						time.sleep(40)
						response = stub.Put(request, timeout=config.RPC_TIMEOUT)
						leader_id = response.leaderId

					if response.code == config.RESPONSE_CODE_REDIRECT :
						time.sleep(20)
						response = self.redirectToLeaderPut(response.leaderId.replace("'", ""), key, value, clientid, sequence_number)
					elif response.code == config.RESPONSE_CODE_OK:
						print(f"Put of key: {key}, value: {value} succeeded!\n")

					elif response.code == config.RESPONSE_CODE_REJECT:
						print(f"Put of key: {key}, value: {value} failed! Please try again.\n")
						
					else:
						print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")
						break
				except grpc.RpcError as e:
					status_code = e.code()
					if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
						print(f"Client request for Put key: {key}, value: {value} timed out, details: {status_code} {e.details()}\n")
					else :
						print(f'Some other error, details: {status_code} {e.details()}')	


if __name__ == '__main__':
	client = Client()
	while True:
		reqType = int(input("Options - Get: 1, Put: 2, Quit: 3\n"))
		if reqType == 1:
			key = int(input("Enter key\n"))
			client.requestGet(key)
		elif reqType == 2:
			inputs = list(map(int, input("\nEnter key, value, clientid, seq_number [ex: 1 2 3 4]\n").strip().split()))[:4]
			client.requestPut(*inputs)
		elif reqType == 3:
			print("SEEEE YAAA\n")
			break
		else:
			print("Invalid input\n")