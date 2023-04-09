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

    def __init__(self, client: ClientPerf):
        self.client = client
        self.client_id = 2
        self.num_elements = 2

    def test_get_latency(self):
        print("Testing GET Latency")
        get_latencies = []
        for i in range(self.num_elements):
            response = (False, -1)
            start_time = time.time()
            while response[0] == False:
                response = self.client.requestGet(i)
            end_time = time.time()
            elapsed_time = start_time - end_time
            get_latencies.append(elapsed_time)

        print(f"GET Latency Stats for {self.num_elements} elements:")
        print("Max Time for GET: " + str(max(get_latencies)))
        print("Min Time for GET: " + str(min(get_latencies)))
        print("Average Time for GET: " + str(mean(get_latencies)))

    def add_items_to_store(self):
        print("Testing PUT Latency")
        put_latencies = []
        
        # Create a list of 100 random numbers between 10 and 30
        random_list = random.sample(range(10, 30), self.num_elements)
        for i, item in enumerate(random_list):
            inputs = [i, item, self.client_id]
            response = False
            start_time = time.time()
            while response == False:
                response = self.client.requestPut(*inputs)
            end_time = time.time()
            elapsed_time = start_time - end_time
            put_latencies.append(elapsed_time)
        print(f"PUT Latency Stats for {self.num_elements} elements:")
        print("Max Time for PUT: " + str(max(put_latencies)))
        print("Min Time for PUT: " + str(min(put_latencies)))
        print("Average Time for PUT: " + str(mean(put_latencies)))
            
    def run_tests(self):
        # run tests
        print("Running tests")
        self.add_items_to_store()
        self.test_get_latency()


if __name__ == "__main__":
    client = ClientPerf()

    parser = argparse.ArgumentParser(
                    prog='Performance tests',
                    description='Run a client for the replicated data store',
                    epilog='Usage: python3 src/client.py --interactive False --sequence-number 2 --perf-tests True')
    
    parser.add_argument('-s', '--seq-num', type=int, default=1, help='Starting sequence number')

    args = parser.parse_args()
    starting_seq_num = args.seq_num
    print(starting_seq_num)

    client.set_sequence_number(starting_seq_num)

    tester = PerformanceTests(client)
    tester.run_tests()
    

        


