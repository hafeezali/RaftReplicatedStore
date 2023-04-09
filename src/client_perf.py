import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
import time

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
TODO:
'''
class ClientPerf:

    def __init__(self):
        self.server_addr = 'localhost:50051'
        self.sequence_number = 0

    def get_sequence_number(self):
        return self.sequence_number

    def set_sequence_number(self, seq_num):
        self.sequence_number = seq_num

    def increment_sequence_number(self):
        self.sequence_number += 1

    def redirectToLeaderGet(self, leader_id, key):
        print("Redirecting to leader with id: " + leader_id)
        self.server_addr = peer_list_mappings[leader_id]
        return self.requestGet(key)
        
    def redirectToLeaderPut(self, leader_id, key,value, clientid):
        print(leader_id)
        self.server_addr = peer_list_mappings[leader_id]
        return self.requestPut(key, value, clientid)    

    def requestGet(self, key):
        with grpc.insecure_channel(self.server_addr) as channel:
            stub = raftdb_grpc.ClientStub(channel)
            request = raftdb.GetRequest(key=key)

            try:
                response = stub.Get(request, timeout=config.RPC_TIMEOUT)
                leader_id = response.leaderId
                # print(leader_id)
                while response.code == config.RESPONSE_CODE_REDIRECT and (leader_id == None or leader_id == '') :
                    print('Waiting for election to happen')
                    time.sleep(config.CLIENT_SLEEP_TIME)
                    response = stub.Get(request, timeout=config.RPC_TIMEOUT)
                    leader_id = response.leaderId
                    
                if response.code == config.RESPONSE_CODE_REDIRECT :
                    response = self.redirectToLeaderGet(response.leaderId.replace("'", ""), key)
                    return response
                    
                elif response.code == config.RESPONSE_CODE_OK:
                    # print(f"GET for key: {key} Succeeded, value: {response.value}\n")
                    return True, response.value
                
                else:
                    print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")
                    return False, -1

            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Client request for Get key: {key} timed out, details: {status_code} {e.details()}\n")
                else:
                    print(f'Connection to {leader_id} failed. Trying the next server, details: {status_code} {e.details()}')
                    leader_id = self.get_next_server(leader_id)
                    return self.redirectToLeaderGet(leader_id, key)

    def requestPut(self, key, value, clientid):
        sequence_number = self.get_sequence_number()
        # print(f"Client id {clientid}, seq number: {sequence_number}")
        with grpc.insecure_channel(self.server_addr) as channel:
            stub = raftdb_grpc.ClientStub(channel)
            request = raftdb.PutRequest(key=key, value=value, clientid = clientid, sequence_number = sequence_number)
            
            try:
                response = stub.Put(request, timeout=config.RPC_TIMEOUT)

                leader_id = response.leaderId
                # print(leader_id)
                while response.code == config.RESPONSE_CODE_REDIRECT and (leader_id == None or leader_id == '' or leader_id == 'No leader') :
                    print('Waiting for election to happen')
                    time.sleep(config.CLIENT_SLEEP_TIME)
                    response = stub.Put(request, timeout=config.RPC_TIMEOUT)
                    leader_id = response.leaderId

                if response.code == config.RESPONSE_CODE_REDIRECT :
                    response = self.redirectToLeaderPut(response.leaderId.replace("'", ""), key, value, clientid)
                    self.increment_sequence_number()
                    return response
                elif response.code == config.RESPONSE_CODE_OK:
                    # print(f"Put of key: {key}, value: {value} succeeded!\n")
                    self.increment_sequence_number()
                    return True

                elif response.code == config.RESPONSE_CODE_REJECT:
                    print(f"Put of key: {key}, value: {value} failed! Please try again.\n")
                    self.increment_sequence_number()
                    return False
                        
                else:
                    print("Something went wrong, exiting put method with response code: " + str(response.code) + "\n")
                    self.increment_sequence_number()
                    return False
                
            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    print(f"Client request for Put key: {key}, value: {value} timed out, details: {status_code} {e.details()}\n")
                else :
                    print(f'Some other error, details: {status_code} {e.details()}')  
                self.increment_sequence_number() 
                return False 

        

# if __name__ == '__main__':
    # print("Staring Interactive Client")
    # client = ClientPerf()
    # starting_seq_num = int(input("Enter Starting Sequence Number\n"))
    # client.set_sequence_number(starting_seq_num)
        
    # while True:
    #     reqType = int(input("Options - Get: 1, Put: 2, Quit: 3\n"))
    #     if reqType == 1:
    #         key = int(input("Enter key\n"))
    #         client.requestGet(key)
    #     elif reqType == 2:
    #         inputs = list(map(int, input("\nEnter key, value, clientid [ex: 1 2 3]\n").strip().split()))[:3]
    #         client.requestPut(*inputs)
    #     elif reqType == 3:
    #         print("SEEEE YAAA\n")
    #         break
    #     else:
    #         print("Invalid input\n")
        