import time
import random
import argparse
from numpy import mean
from threading import Thread, Lock
import subprocess

from client_perf import ClientPerf

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
The functional tests here are implemented as mentioned in the text file.
for running these tests command :  python3 src/func_tests.py -s 1 -c 1 -k 1 -n 1
Can comment out leader and follower failure test to avoid restarting of the docker as the system currently gets stuck
'''

add_lock = Lock()
num_requests = 0

class FunctionalTests:

    def __init__(self, client: ClientPerf, client_id, key_start):
        self.client = client
        self.client_id = client_id
        self.num_elements = 10
        self.values = []
        self.key_start = key_start
        self.leader_id = 1

    # function to test get functionality
    def test_get(self):

        for i in range(self.num_elements):
            response = (False, -1)
            while response[0] == False:
                inp = list()
                inp.append(i+self.key_start)
                response = self.client.requestGet(inp)
            expected_output = list()
            expected_output.append(self.values[i])    
            if response[1] != expected_output :
                print(f"!!!!!!!!!! GET returned a weird value, expected: {expected_output}, actual {response[1]}")
        
        print("-----------------------------")
        print("Test Get Key Ran Successfully")  
        print("-----------------------------")

    # functionality to test put functionality 
    def add_items_to_store(self):

        # adding fixed values to keep track
        self.values = [1,2,3,4,5,6,7,8,9,10]
        
        
        for i, item in enumerate(self.values):
            key = list()
            key.append(i + self.key_start)
            value = list()
            value.append(item)
            inputs = [key, value, self.client_id]
            # the response contains the leader id too now
            response = (False, 1)
            
            while response[0] == False:
                response = self.client.requestPut(*inputs)
            self.leader_id = response[1]

        print("-------------------------")
        print("Test Put ran successfully")    
        print("-------------------------")
    
    def get_same_key(self):
        key = []
        key.append(100)
        value = []
        value.append(-999)
        for i in range(100):
            response = (False, -1)
            while response[0] == False:
                response = self.client.requestGet(key)
            
            if response[1] != value:
                print(f"!!!!!!!!!! GET returned a weird value, expected: -999, actual {value}")

        print("----------------------------------")
        print("Test Get Same Key Ran Successfully")   
        print("----------------------------------")

    # currently getting stuck in the Is Applied loop because of the last entry not getting marked as committed 
    # Checked functionality after removing start and stop
    def leader_failure(self) :
        print(f"{self.leader_id} is the leader")
        container_name = 'raftreplicatedstore-' + self.leader_id + '-1'
        first_leader = self.leader_id
        print("stopping the leader server")
        result = subprocess.run(['docker', 'stop', container_name], capture_output=True, text=True)
        print(result)
        # executing the get and put commands 
        self.test_get()
        input = [[100], [1000], self.client_id]
        response = self.client.requestPut(*input)
        if response[0] == False :
            print("!!!!!!!!! Error in put after the leader fails !!!!!!!!!")
        else :
            new_leader = response[1]    
        if new_leader == self.leader_id :
            print("!!!!!!!!! Some problem in leader failure as still old leader is there in the system !!!!!!!!!")
        else :
            self.leader_id = new_leader    
        input = [[200], [2000], self.client_id]  
        response = self.client.requestPut(*input)
        if response[0] == False :
            print("!!!!!!!!! Error in put after the leader fails !!!!!!!!!")

        container_name = 'raftreplicatedstore-' + self.leader_id + '-1'
        # previous leader comes back up
        result = subprocess.run(['docker', 'start', container_name], capture_output=True, text=True)
        print(result)

        input = [[300], [3000], self.client_id]  
        response = self.client.requestPut(*input)
        if response[0] == False :
            print("!!!!!!!!! Error in put after the previous leader comes back up !!!!!!!!!")
        else :
            new_leader = response[1]

        if first_leader == new_leader :
            print("!!!!!!!!! Something wrong in the logic as old leader is becoming the new leader !!!!!!!!!")

        self.leader_id = new_leader
        key = [200]
        value = [2000]
        response = self.client.requestGet(key) 
        if response[1] != value  :
            print("!!!!!!!!! Something wrong !!!!!!!!!")


    # currently creating an error in the follower logs because the last entry is not marked as committed
    def follower_failure(self) :
        print(f"{self.leader_id} is the leader")
        if self.leader_id == 'server-1':
            follower = 'server-2'

        if self.leader_id == 'server-2':
            follower = 'server-3'  

        if self.leader_id == 'server-3':
            follower = 'server-1'   

        container_name = 'raftreplicatedstore-' + follower + '-1'
        print("stopping the follower server")
        result = subprocess.run(['docker', 'stop', container_name], capture_output=True, text=True)
        print(result)
        # executing the get and put commands 
        self.test_get()
        input = [[100], [1000], self.client_id]
        response = self.client.requestPut(*input)
        if response[0] == False :
            print("!!!!!!!!! Error in put after the follower fails !!!!!!!!!")
        input = [[200], [2000], self.client_id]  
        response = self.client.requestPut(*input)
        if response[0] == False :
            print("!!!!!!!!! Error in put after the follower fails !!!!!!!!!")

        # follower comes back up
        container_name = 'raftreplicatedstore-' + follower + '-1'
        result = subprocess.run(['docker', 'start', container_name], capture_output=True, text=True)
        print(result)
        

        print("Executing put after the follower comes back up")
        input = [[300], [3000], self.client_id]  
        response = self.client.requestPut(*input)
        if response[0] == False :
            print("!!!!!!!!! Error in put after the previous follower comes back up !!!!!!!!!")
        else :
            new_leader = response[1]

        if follower == new_leader :
            print("!!!!!!!!! Something wrong in the logic as follower is becoming the new leader !!!!!!!!!")
        else :
            print(f"{self.leader_id} is the leader")
        key = [200]
        value = [2000]
        response = self.client.requestGet(key) 
        if response[1] != value  :
            print("!!!!!!!!! Something wrong !!!!!!!!!")    


    def run_tests(self):
        # run tests
        print("Running tests")
        self.get_same_key()
        self.add_items_to_store()
        self.test_get()
        # self.leader_failure()
        self.follower_failure()

def start_clients(num_clients, id, key, start_seq_num):
    starting_seq_num = start_seq_num
    start_client_id = id
    key_start = key
    testers = []
    for i in range(num_clients):
        client = ClientPerf()
        client.set_sequence_number(starting_seq_num)
        tester = FunctionalTests(client, start_client_id, key_start)
        start_client_id += 1
        key_start += 100
        testers.append(tester)

    threads = []
    
    for tester_ in testers:
        t = Thread(target=tester_.run_tests)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print(f"Number of Clients: {num_clients}")
   


if __name__ == "__main__":
    

    parser = argparse.ArgumentParser(
                    prog='Functional tests',
                    description='Run a client for the replicated data store',
                    epilog='Usage: python3 src/client.py -c <client-id> -s <star seq num>')
    
    parser.add_argument('-s', '--seq-num', type=int, default=1, help='Starting sequence number')
    parser.add_argument('-c', '--client-id', type=int, default=2, help='Client ID')
    parser.add_argument('-k', '--key',  type=int, default=0, help='key start index')
    parser.add_argument('-n', '--num-clients', type=int, default=0, help='number of clients')

    args = parser.parse_args()
    starting_seq_num = args.seq_num
    client_id = args.client_id
    key_start = args.key
    num_clients = args.num_clients

    start_clients(num_clients, client_id, key_start, starting_seq_num)
    

 


