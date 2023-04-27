import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
import time

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
TODO:
1. Fine tune CLIENT_SLEEP_TIME 
'''
class Client:

    def __init__(self):
        self.server_addr = 'localhost:50051'
        self.sequence_number = 0
        self.leader_id = 'server-1'

    def get_sequence_number(self):
        return self.sequence_number

    def set_sequence_number(self, seq_num):
        self.sequence_number = seq_num

    def increment_sequence_number(self):
        self.sequence_number += 1

    def redirectToLeaderGet(self, leader_id, key):
        print("Redirecting to leader with id: " + leader_id)
        self.server_addr = peer_list_mappings[leader_id]
        self.leader_id = leader_id
        return self.requestGet(key)
        
    def redirectToLeaderPut(self, leader_id, key, value, clientid, sequence_number):
        print("Redirecting to leader with id: " + leader_id)
        self.server_addr = peer_list_mappings[leader_id]
        self.leader_id = leader_id
        return self.requestPut(key, value, clientid, sequence_number)

    def get_next_server(self, leader_id):
        id_ = int(leader_id[-1]) + 1
        if id_ == len(peer_list_mappings) + 1:
            id_ = 1
        new_leader_id = 'server-' + str(id_)
        return new_leader_id

    def requestGet(self, key):
        with grpc.insecure_channel(self.server_addr) as channel:
            stub = raftdb_grpc.ClientStub(channel)
            request = raftdb.GetRequest(key=key)

            try:
                response = stub.Get(request, timeout=config.RPC_TIMEOUT)
                self.leader_id = response.leaderId.replace("'", "")
                print(self.leader_id)
                while response.code == config.RESPONSE_CODE_REDIRECT and (self.leader_id == None or self.leader_id == '' or self.leader_id == 'No leader') :
                    print('Waiting for election to happen')
                    time.sleep(config.CLIENT_SLEEP_TIME)
                    response = stub.Get(request, timeout=config.RPC_TIMEOUT)
                    self.leader_id = response.leaderId.replace("'", "")
                    
                if response.code == config.RESPONSE_CODE_REDIRECT :
                    response = self.redirectToLeaderGet(response.leaderId.replace("'", ""), key)

                elif response.code == config.RESPONSE_CODE_OK:
                    value_list = list(response.value)
                    for i in range(0,len(value_list)) :
                        if value_list[i] == -999 :
                            print(f"Key {key[i]} does not exist")
                        else :
                            print(f"GET for key: {key[i]} Succeeded, value: {value_list[i]}\n")
                
                else:
                    print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")

            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Client request for Get key: {key} timed out, details: {status_code} {e.details()}\n")
                else:
                    print(f'Connection to {self.leader_id} failed. Trying the next server, details: {status_code} {e.details()}')
                    time.sleep(1000)
                    self.leader_id = self.get_next_server(self.leader_id)
                    self.redirectToLeaderGet(self.leader_id, key)

    def requestPut(self, key, value, clientid, sequence_number):
        with grpc.insecure_channel(self.server_addr) as channel:
            stub = raftdb_grpc.ClientStub(channel)
            request = raftdb.PutRequest(key=key, value=value, clientid = clientid, sequence_number = sequence_number)
            
            try:
                response = stub.Put(request, timeout=config.RPC_TIMEOUT)

                self.leader_id = response.leaderId.replace("'", "")
                while response.code == config.RESPONSE_CODE_REDIRECT and (self.leader_id == None or self.leader_id == '' or self.leader_id == 'No leader') :
                    print('Waiting for election to happen')
                    time.sleep(config.CLIENT_SLEEP_TIME)
                    response = stub.Put(request, timeout=config.RPC_TIMEOUT)
                    self.leader_id = response.leaderId.replace("'", "")

                if response.code == config.RESPONSE_CODE_REDIRECT :
                    response = self.redirectToLeaderPut(response.leaderId.replace("'", ""), key, value, clientid, sequence_number)
                
                elif response.code == config.RESPONSE_CODE_OK:
                    print(f"Put of key: {key}, value: {value} succeeded!\n")

                elif response.code == config.RESPONSE_CODE_REJECT:
                    print(f"Put of key: {key}, value: {value} failed! Please try again.\n")
						
                else:
                    print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")
						
            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Client request for Put key: {key}, value: {value} timed out, details: {status_code} {e.details()}\n")
                else:
                    print(f'Connection to {self.leader_id} failed. Trying the next server, details: {status_code} {e.details()}')
                    time.sleep(1000)
                    self.leader_id = self.get_next_server(self.leader_id)
                    self.redirectToLeaderPut(self.leader_id, key, value, clientid, sequence_number)

if __name__ == '__main__':
    client = Client()
    starting_seq_num = int(input("Enter starting sequence number\n"))
    client.set_sequence_number(starting_seq_num)

    while True:
        reqType = int(input("Options - Get: 1, Put: 2, Quit: 3\n"))
        if reqType == 1:
            keys = list(map(int, input("Enter key(s)\n").strip().split()))
            client.requestGet(keys)
        elif reqType == 2:
            keys = list(map(int, input("Enter key(s)\n").strip().split()))
            values = list(map(int, input("Enter values(s)\n").strip().split()))
            clientId = int(input("\nEnter clientid \n"))
            inputs = list()
            inputs.append(keys)
            inputs.append(values)
            inputs.append(clientId)
            inputs.append(client.get_sequence_number())
            client.requestPut(*inputs)
            client.increment_sequence_number()
        elif reqType == 3:
            print("SEEEE YAAA\n")
            break
        else:
            print("Invalid input\n")
        