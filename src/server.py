from raft.election import Election
from raft.consensus import Consensus
from concurrent import futures
from store.database import Database
from logs.log import Log
import os
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
from logger import Logging
from threading import Thread

'''
TODO:
1. Look into how max_workers should be fine-tuned? Maybe performance testing might help figure that out?
2. What happens when we dont get majority when trying a put? We need to retry
3. There might be some inconsistency at the db level here - Puts are happening from log, whereas gets are happening here. Do SELECT and INSERT/UPDATE overlap in sqlite3? 
    Hopefully latching is implemented for in-mem dict by default...
4. When does the __init__ here finish execution?
'''
class Server(raftdb_grpc.ClientServicer):

    def __init__(self, type, server_id, peer_list):

        self.server_id = server_id
        self.logger = Logging(server_id).get_logger()
        self.store = Database(type=type, server_id=server_id, logger=self.logger)
        self.log = Log(server_id, self.store, self.logger)
        self.election = Election(peers=peer_list,log=self.log, logger=self.logger, serverId=server_id)

        # Start thread for election service
        Thread(target=self.election.run_election_service()).start()

        self.consensus = Consensus(peers=peer_list, log=self.log, logger=self.logger)
        self.logger.info("Finished starting server... " + self.server_id)

    def Get(self, request, context):
        # Strongly consistent -- if we allow only one outstanding client request, the system must be strongly consistent by default
        self.logger.info("Get request received for key: " + str(request.key))
        leader_id = self.log.get_leader()

        if leader_id == self.server_id:
            return raftdb.GetResponse(code = config.RESPONSE_CODE_OK, value = self.store.get(request.key), leaderId = leader_id)
        else:
            self.logger.info(f"Redirecting client to leader {leader_id}")
            return raftdb.GetResponse(code = config.RESPONSE_CODE_REDIRECT, value = None, leaderId = leader_id)

    def Put(self, request, context):
        self.logger.info("Put request received for key: " + str(request.key) + ", and value: " + str(request.value) + ", from client: " + str(request.clientid))
        leader_id = self.log.get_leader()

        if leader_id == self.server_id:
            response = self.consensus.handlePut(request)
            if response == 'OK':
                return raftdb.PutResponse(code = config.RESPONSE_CODE_OK, leaderId = leader_id)
            else:
                # Only scenario we will get 500 (config.RESPONSE_CODE_REJECT) is when node has become follower when previously it was leader
                if response == config.RESPONSE_CODE_REJECT:

                    self.logger.info("Put request failed... Redirecting it to new leader")
                    return raftdb.PutResponse(code = config.RESPONSE_CODE_REDIRECT, leaderId = self.log.get_leader())
        else:
            self.logger.info(f"Redirecting client to leader {leader_id}")
            return raftdb.PutResponse(code = config.RESPONSE_CODE_REDIRECT, leaderId = leader_id)
        

def start_server_thread(port, grpc_server):
    grpc_server.add_insecure_port('[::]:' + port)
    grpc_server.start()
    grpc_server.wait_for_termination()

def serve(server):
    client_port = '50051'
    peer_port = '50052'
    
    grpc_client_server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    raftdb_grpc.add_ClientServicer_to_server(server, grpc_client_server)

    grpc_peer_server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    raftdb_grpc.add_RaftElectionServiceServicer_to_server(server.election, grpc_peer_server)
    raftdb_grpc.add_ConsensusServicer_to_server(server.consensus, grpc_peer_server)
    
    print("Starting threads for grpc servers to serve the client and other peers")
    client_thread = Thread(target=start_server_thread, args=(client_port, grpc_client_server, ))
    peer_thread = Thread(target=start_server_thread, args=(peer_port, grpc_peer_server, ))
    
    client_thread.start()
    peer_thread.start()

    client_thread.join()
    peer_thread.join()

if __name__ == '__main__':

    server_id = os.getenv('SERVERID')
    print(f"Starting Server {server_id}")
    
    peer_list = peer_list=os.getenv('PEERS').split(',')

    type = os.getenv('TYPE').replace("'", "")
    server = Server(type=type, server_id=server_id, peer_list=peer_list)

    serve(server)