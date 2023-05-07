import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
import time
from threading import Lock
import concurrent

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
TODO:
1. [TO_START] Fine tune CLIENT_SLEEP_TIME 
'''
class Client:

    def __init__(self):
        self.server_addr = 'localhost:50051'
        self.sequence_number = 0
        self.leader_id = 'server-1'
        self.super_majority = len(peer_list_mappings)
        self.lock = Lock()
        self.put_sent_to_server = dict()
        self.put_sent_to_leader = dict()
        self.put_tried_counter = dict()


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
                print("Leader_id: " + str(self.leader_id))
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
                    print("Something went wrong, exiting get method with response code: " + str(response.code) + "\n")

            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Client request for Get key: {key} timed out, details: {status_code} {e.details()}\n")
                else:
                    print(f'Connection to {self.leader_id} failed. Trying the next server, details: {status_code} {e.details()}')
                    time.sleep(1000)
                    self.leader_id = self.get_next_server(self.leader_id)
                    self.redirectToLeaderGet(self.leader_id, key)

    # Send requestPut to all peers - use futures. Wait for supermajority (f + ceil(f/2) + 1). Wait for leader id.
    # Retry if not receiving super majority or super majority times out.
    # Retry timeout is different from grpc timeout. grpc timeout must not be retried.
    '''
    - If the value of self.leader is not set for the client, first get the leader using the leader RPC
        - If there is no leader in the system, then the server would send code = redirect. Try until you get a leader
        - Once you get the code = OK and a leader in the system, set the leader id 
    - If the value of leader is set
        - add keys to the maps to track RPCs being sent
        - fire threads to all the servers
        - wait until a put timeout (can remove this step of waiting for timeout, can wait infinitely)
        - if supermajority achieved and leader, put is completed   
 '''
    def requestPut(self, key, value, clientid, sequence_number):
        if self.leader_id == None or self.leader_id == '' or self.leader_id == 'No leader' :
            with grpc.insecure_channel(self.server_addr) as channel:
                stub = raftdb_grpc.ClientStub(channel)
                request = raftdb.LeaderRequest()
            
            try:
                response = stub.Leader(request, timeout=config.RPC_TIMEOUT)

                self.leader_id = response.leaderId.replace("'", "")
                while response.code == config.RESPONSE_CODE_REDIRECT :
                    print('Waiting for election to happen')
                    time.sleep(config.CLIENT_SLEEP_TIME)
                    response = stub.Leader(request, timeout=config.RPC_TIMEOUT)
                    self.leader_id = response.leaderId.replace("'", "")

                if response.code == config.RESPONSE_CODE_OK :
                   self.leader_id = response.leaderId.replace("'", "") 

            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Get leader request timed out, details: {status_code} {e.details()}\n")
                else:
                    print(f'Connection to {self.leader_id} failed. You may try the request in sometime')       

# the client knows the leader
        if self.leader_id != None and self.leader_id != '' and self.leader_id != 'No leader' :
            key = (clientid, sequence_number)
            with self.lock :
                self.put_sent_to_leader[key] = 0
                self.put_sent_to_server[key] = 0
                self.put_tried_counter[key] = 0

            with concurrent.futures.ThreadPoolExecutor() as executor:
                responses = []
                start_time = time.time()
                for server, address in peer_list_mappings.items():
                    responses.append(
                    executor.submit(self.sendPut, server_add = address, key = key, value = value, sequence_number = sequence_number, clientid = clientid)
                    )  
                
                 
                while time.time() - start_time < config.PUT_TIMEOUT :
                    time.sleep(10)
            
                if self.put_sent_to_server[key] >= self.super_majority and self.put_sent_to_leader[key] == 1:
                    print(f"Put completed for  key: {key}, value: {value}") 

                else :
                    print(f"Something wrong happened in the put for key : {key}, value : {value}. You might want to retry.") 

                if self.put_tried_counter[key] == len(peer_list_mappings) :
                    self.put_sent_to_server.pop(key)
                    self.put_sent_to_leader.pop(key)
                    self.put_tried_counter.pop(key)       

    def sendPut(self,server_add, key, value, sequence_number, clientid) :
        key = (clientid, sequence_number)
        with grpc.insecure_channel(server_add) as channel:
            stub = raftdb_grpc.ClientStub(channel)
            request = raftdb.PutRequest(key = key, value = value, clientid = clientid, sequence_number = sequence_number)
            try:
                response = stub.Put(request, timeout=config.RPC_TIMEOUT)                       
                if response.code == config.RESPONSE_CODE_OK:
                    print(f"Put of key: {key}, value: {value} succeeded!\n")
                    with self.lock :
                        self.put_sent_to_server[key] += 1
                        if server_add == self.leader_id :
                            self.put_sent_to_leader[key] = 1

                elif response.code == config.RESPONSE_CODE_REJECT:
                    print(f"Put of key: {key}, value: {value} failed! Please try again.\n")
						
                else:
                    print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")
						
            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Client request for Put key: {key}, value: {value} timed out, details: {status_code} {e.details()}\n")
            with self.lock :
                    self.put_tried_counter[key] += 1
                
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
        