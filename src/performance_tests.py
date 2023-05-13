import time
import random
import argparse
from numpy import mean
from threading import Thread, Lock

from client_perf import ClientPerf

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
TODO:

'''

put_latency = 0
get_latency = 0
add_lock = Lock()

total_put_time = 0
totatl_get_time = 0
num_requests = 0
get_latencies = []

class PerformanceTests:

    def __init__(self, client: ClientPerf, client_id, key_start):
        self.client = client
        self.client_id = client_id
        self.num_elements = 1000
        self.values = []
        self.key_start = key_start
        self.average_put_latencies = []
        self.average_get_latencies = []

    def test_get_latency(self, iteration):
        print("Testing GET Latency")
        get_latencies = []
        for i in range(self.num_elements):
            response = (False, -1)
            start_time = time.time()
            while response[0] == False:
                inp = list()
                inp.append(i+self.key_start)
                response = self.client.requestGet(inp)
            end_time = time.time()
            if response[1] != self.values[i]:
                print(f"!!!!!!!!!! GET returned a weird value, expected: {self.values[i]}, actual {response[1]}")
            elapsed_time = end_time - start_time
            get_latencies.append(elapsed_time)

        # print(f"Iteration: {iteration} GET Latency Stats for {self.num_elements} elements:")
        # print("Max Time for GET: " + str(max(get_latencies)))
        # print("Min Time for GET: " + str(min(get_latencies)))
        total_get_latency = sum(get_latencies)
        with add_lock:
            global totatl_get_time
            totatl_get_time += total_get_latency
        average_get_latency = mean(get_latencies)
        self.average_get_latencies.append(average_get_latency)
        print(f"{self.client_id} Iteration: {iteration} Average Time for GET: " + str(average_get_latency))

    def add_items_to_store(self, iteration):
        print("Testing PUT Latency")
        put_latencies = []

        self.values = random.sample(range(10, 3000), self.num_elements)
        
        for i, item in enumerate(self.values):
            key = list()
            key.append(i + self.key_start)
            value = list()
            value.append(item)
            inputs = [key, value, self.client_id]
            response = False
            start_time = time.time()
            while response == False:
                response = self.client.requestPut(*inputs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            put_latencies.append(elapsed_time)
        # print(f"Iteration: {iteration} PUT Latency Stats for {self.num_elements} elements:")
        # print("Max Time for PUT: " + str(max(put_latencies)))
        # print("Min Time for PUT: " + str(min(put_latencies)))
        total_put_latency = sum(put_latencies)
        with add_lock:
            global total_put_time
            total_put_time += total_put_latency
        average_put_latency = mean(put_latencies)
        print(f"{self.client_id} Iteration: {iteration} Average Time for PUT: " + str(average_put_latency))
        self.average_put_latencies.append(average_put_latency)
            
    def run_tests(self):
        # run tests
        num_runs = 1
        # self.get_same_key()
        print("Running tests")
        for i in range(num_runs):
            self.add_items_to_store(i)
            # # time.sleep(20)
            # self.test_get_latency(i)

        avg_put_latency = mean(self.average_put_latencies)
        print(f"{self.client_id}: Average PUT Latency for adding {self.num_elements} items over {num_runs} runs: {avg_put_latency}")
            
        # avg_get_latency = mean(self.average_get_latencies)
        # print(f"{self.client_id} Average GET Latency for adding {self.num_elements} items over {num_runs} runs: {avg_get_latency}")
        
        with add_lock:
            global put_latency 
            put_latency += avg_put_latency
        #     global get_latency
        #     get_latency += avg_get_latency
    def get_same_key(self):
        key = []
        key.append(1)
        value = []
        value.append(1)
        for i in range(100):
            response = (False, -1)
            while response[0] == False:
                response = self.client.requestGet(key)
            
            if response[1] != value:
                print(f"!!!!!!!!!! GET returned a weird value, expected: -999, actual {value}")

        print("----------------------------------")
        print("Test Get Same Key Ran Successfully")   
        print("----------------------------------")
    # def get_same_key(self):
    #     global num_requests
    #     global get_latencies

    #     for i in range(50000000):
    #         response = (False, -1)
    #         start_time = time.time()
    #         while response[0] == False:
    #             response = self.client.requestGet(1)
    #             num_requests += 1
    #         end_time = time.time()
    #         if response[1] != 1:
    #             print(f"!!!!!!!!!! GET returned a weird value, expected: 1, actual {response[1]}")
    #         elapsed_time = end_time - start_time
    #         get_latencies.append(elapsed_time)

def start_clients(num_clients, id, key, start_seq_num):
    starting_seq_num = start_seq_num
    start_client_id = id
    key_start = key
    testers = []
    for i in range(num_clients):
        client = ClientPerf()
        client.set_sequence_number(starting_seq_num)
        tester = PerformanceTests(client, start_client_id, key_start)
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

    total_num_requests = num_clients * 100 * 10
    print(f"Number of Clients: {num_clients}")
    print(f"Total number of requests: {total_num_requests}")
    # print(f"PUT Throughput: {total_num_requests/total_put_time}")
    # print(f"GET Throughput: {total_num_requests/totatl_get_time}")
    print(f"The put latency average over all threads: {put_latency/num_clients} ")
    # print(f"The put latency average over all threads: {get_latency/num_clients} ")

def print_observed_tp():
    global get_latencies
    global num_requests
    t = time.time()
    t2 = t + 300

    while t2 - time.time() > 0:
        total_time_gets = sum(get_latencies)
        if num_requests > 0:
            print(f"num_requests {num_requests} observed tp: {total_time_gets / num_requests}")
        time.sleep(1)

# def leader_failure(client_id, key_start, starting_seq_num):
#     client = ClientPerf()
#     client.set_sequence_number(starting_seq_num)
#     tester = PerformanceTests(client, client_id, key_start)

#     t1 = Thread(target=tester.get_same_key)
#     t2 = Thread(target=print_observed_tp)
#     t1.start()
#     t2.start()

#     t2.join()
#     t1.join()


if __name__ == "__main__":
    

    parser = argparse.ArgumentParser(
                    prog='Performance tests',
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
    # print(f"Client ID: {client_id}, Starting Sequence Number: {starting_seq_num}")

    start_clients(num_clients, client_id, key_start, starting_seq_num)
    # leader_failure(client_id, key_start, starting_seq_num)
    

        


