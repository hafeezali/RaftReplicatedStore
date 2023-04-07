import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
import time

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

class Client:

	def __init__(self):
		self.server_addr = 'localhost:50051'

	def redirectToLeader(self, leader_id):
		print(leader_id)
		self.server_addr = peer_list_mappings[leader_id]

	def requestGet(self, key):
		# implement server update logic
		while True:
			with grpc.insecure_channel(self.server_addr) as channel:
				stub = raftdb_grpc.ClientStub(channel)
				request = raftdb.GetRequest(key=key)

				try:
					response = stub.Get(request, timeout=100)

					leader_id = response.leaderId

					if response.code == config.RESPONSE_CODE_REDIRECT:
						print(f"REDIRECT - {leader_id}")
						if leader_id == None or leader_id == '':
							time.sleep(config.CLIENT_SLEEP_TIME)
						else:
							self.redirectToLeader(response.leaderId.replace("'", ""))

					elif response.code == config.RESPONSE_CODE_OK:
						print(f"GET for key: {key} Succeeded, value: {response.value}\n")
						# print(response.value)
						break
					else:
						print("Something went wrong, exiting put method\n")
						break
				except grpc.RpcError as e:
					status_code = e.code()
					if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                        # timeout, will retry if we are still leader
						print(f"Client request for Get key: {key} timed out, details: {status_code} {e.details()}\n")
					else:
						print(f'Some other error, details: {status_code} {e.details()}') 



	def requestPut(self, key, value, clientid, sequence_number):
		# implement server update logic
		while True:
			with grpc.insecure_channel(self.server_addr) as channel:
				stub = raftdb_grpc.ClientStub(channel)
				request = raftdb.PutRequest(key=key, value=value, clientid = clientid,sequence_number = sequence_number )
				
				try:
					response = stub.Put(request, timeout=config.RPC_TIMEOUT)

					leader_id = response.leaderId

					if response.code == config.RESPONSE_CODE_REDIRECT:
						if leader_id == None or leader_id == '':
							time.sleep(config.CLIENT_SLEEP_TIME)
						else:
							self.redirectToLeader(response.leaderId.replace("'", ""))
							# Then code will retry automatically

					elif response.code == config.RESPONSE_CODE_OK:
						print(f"Put of key: {key}, value: {value} succeeded!\n")
						break
					elif response.code == config.RESPONSE_CODE_REJECT:
						print(f"Put of key: {key}, value: {value} failed! Please try again.\n")
						break
					else:
						print("Something went wrong, exiting put method\n")
						break

				except grpc.RpcError as e:
					status_code = e.code()
					if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                        # timeout, will retry if we are still leader
						print(f"Client request for Put key: {key}, value: {value} timed out, details: {status_code} {e.details()}\n")



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