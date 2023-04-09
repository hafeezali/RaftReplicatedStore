import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
import time
import random
import argparse
from numpy import mean

from client_perf import ClientPerf

peer_list_mappings = { 'server-1': 'localhost:50051', 'server-2': 'localhost:50053', 'server-3': 'localhost:50055'}

'''
TODO:

'''
class PerformanceTests:

    def __init__(self, client: ClientPerf, client_id):
        self.client = client
        self.client_id = client_id
        self.num_elements = 1000
        self.values = []
        self.average_put_latencies = []
        self.average_get_latencies = []

    def test_get_latency(self, iteration):
        print("Testing GET Latency")
        get_latencies = []
        for i in range(self.num_elements):
            response = (False, -1)
            start_time = time.time()
            while response[0] == False:
                response = self.client.requestGet(i)
            end_time = time.time()
            if response[1] != self.values[i]:
                print(f"!!!!!!!!!! GET returned a weird value, expected: {self.values[i]}, actual {response[1]}")
            elapsed_time = end_time - start_time
            get_latencies.append(elapsed_time)

        # print(f"Iteration: {iteration} GET Latency Stats for {self.num_elements} elements:")
        # print("Max Time for GET: " + str(max(get_latencies)))
        # print("Min Time for GET: " + str(min(get_latencies)))
        average_get_latency = mean(get_latencies)
        self.average_get_latencies.append(average_get_latency)
        print(f"Iteration: {iteration} Average Time for GET: " + str(average_get_latency))

    def add_items_to_store(self, iteration):
        print("Testing PUT Latency")
        put_latencies = []

        self.values = random.sample(range(10, 3000), self.num_elements)
        
        for i, item in enumerate(self.values):
            inputs = [i, item, self.client_id]
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

        average_put_latency = mean(put_latencies)
        print(f"Iteration: {iteration} Average Time for PUT: " + str(average_put_latency))
        self.average_put_latencies.append(average_put_latency)
            
    def run_tests(self):
        # run tests
        num_runs = 10
        print("Running tests")
        for i in range(num_runs):
            self.add_items_to_store(i)
            # time.sleep(20)
            self.test_get_latency(i)

        avg_put_latency = mean(self.average_put_latencies)
        print(f"Average PUT Latency for adding {self.num_elements} items over {num_runs} runs: {avg_put_latency}")
            
        avg_get_latency = mean(self.average_get_latencies)
        print(f"Average GET Latency for adding {self.num_elements} items over {num_runs} runs: {avg_get_latency}")
        


if __name__ == "__main__":
    client = ClientPerf()

    parser = argparse.ArgumentParser(
                    prog='Performance tests',
                    description='Run a client for the replicated data store',
                    epilog='Usage: python3 src/client.py -c <client-id> -s <star seq num>')
    
    parser.add_argument('-s', '--seq-num', type=int, default=1, help='Starting sequence number')
    parser.add_argument('-c', '--client-id', type=int, default=2, help='Client ID')

    args = parser.parse_args()
    starting_seq_num = args.seq_num
    client_id = args.client_id
    print(f"Client ID: {client_id}, Starting Sequence Number: {starting_seq_num}")

    client.set_sequence_number(starting_seq_num)
    tester = PerformanceTests(client, client_id)
    tester.run_tests()
    

        


