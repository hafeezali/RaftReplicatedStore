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

    def __init__(self, client: ClientPerf, client_id, key_start, perc):
        self.client = client
        self.client_id = client_id
        self.num_elements = 1000
        self.values = []
        self.key_start = key_start
        self.average_put_latencies = []
        self.average_get_latencies = []
        self.percentage = perc

    def run_mixed_workload(self, iteration):
        get_latencies = []
        put_latencies = []
        num_reads = 0
        num_writes = 0
        write_percentage = self.percentage
        for _ in range(self.num_elements):
            r = random.randint(1, 100)
            if r > write_percentage:
                # Issue read to a random key 
                r = random.randint(0, len(self.values)-1)
                response = (False, -1)
                start_time = time.time()
                while response[0] == False:
                    response = self.client.requestGet([r + self.key_start])
                end_time = time.time()
                num_reads += 1
                elapsed_time = end_time - start_time
                get_latencies.append(elapsed_time)

            else:
                # Issue write
                r = random.randint(3000, 5000)
                inputs = [[r], [r], self.client_id]
                response = False
                start_time = time.time()
                while response == False:
                    response = self.client.requestPut(*inputs)
                end_time = time.time()
                num_writes += 1
                elapsed_time = end_time - start_time
                put_latencies.append(elapsed_time)

        total_put_latency = sum(put_latencies)
        total_get_latency = sum(get_latencies)
        
        with add_lock:
            global total_put_time
            global totatl_get_time
            total_put_time += total_put_latency
            totatl_get_time += total_get_latency

        average_put_latency = mean(put_latencies)
        average_get_latency = mean(get_latencies)
        print(f"{self.client_id} Iteration: {iteration}, Number of Writes: {num_writes}, Average Time for PUT: " + str(average_put_latency))
        print(f"{self.client_id} Iteration: {iteration}, Number of Reads: {num_reads}, Average Time for GET: " + str(average_get_latency))
        self.average_put_latencies.append(average_put_latency)
        self.average_get_latencies.append(average_get_latency)

    def setup_kv_store(self):
        print("Adding and getting some items to store for setup")

        self.values = random.sample(range(10, 3000), self.num_elements)
        
        for i, item in enumerate(self.values):
            key = list()
            key.append(i + self.key_start)
            value = list()
            value.append(item)
            inputs = [key, value, self.client_id]
            response = False
            while response == False:
                response = self.client.requestPut(*inputs)
        print("Done adding initial elements to store")

        print("making gets on random subset of items so that for v3 some will not be recent reads")
        for i in range(len(self.values)):
            r = random.randint(1,3)
            if r == 1:
                response = False
                while response == False:
                    response = self.client.requestGet([i + self.key_start])

        print("Done with initial gets")
        print("Setup complete!!")
        print("-----------------")
            
    def run_tests(self):
        # run tests
        num_runs = 1
        self.setup_kv_store()
        print("Running tests")
        for i in range(num_runs):
            self.run_mixed_workload(i)

        avg_put_latency = mean(self.average_put_latencies)
        print(f"{self.client_id}: Average PUT Latency: {avg_put_latency}")
            
        avg_get_latency = mean(self.average_get_latencies)
        print(f"{self.client_id} Average GET Latency: {avg_get_latency}")
        
        with add_lock:
            global put_latency 
            put_latency += avg_put_latency
            global get_latency
            get_latency += avg_get_latency


def start_clients(num_clients, id, key, start_seq_num, perc):
    starting_seq_num = start_seq_num
    start_client_id = id
    key_start = key
    testers = []
    for i in range(num_clients):
        client = ClientPerf()
        client.set_sequence_number(starting_seq_num)
        tester = PerformanceTests(client, start_client_id, key_start, perc)
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
    print(f"The put latency average over all threads: {put_latency/num_clients} ")
    print(f"The get latency average over all threads: {get_latency/num_clients} ")


if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(
                    prog='Run Workloads',
                    description='Run a client for the replicated data store',
                    epilog='Usage: python3 src/client.py -c <client-id> -s <star seq num>')
    
    parser.add_argument('-s', '--seq-num', type=int, default=1, help='Starting sequence number')
    parser.add_argument('-c', '--client-id', type=int, default=2, help='Client ID')
    parser.add_argument('-k', '--key',  type=int, default=0, help='key start index')
    parser.add_argument('-n', '--num-clients', type=int, default=0, help='number of clients')
    parser.add_argument('-p', '--percentage', type=int, default=50, help='workload specific percentage' )

    args = parser.parse_args()
    starting_seq_num = args.seq_num
    client_id = args.client_id
    key_start = args.key
    num_clients = args.num_clients
    percentage = args.percentage
    # print(f"Client ID: {client_id}, Starting Sequence Number: {starting_seq_num}")

    start_clients(num_clients, client_id, key_start, starting_seq_num, percentage)
    

        


