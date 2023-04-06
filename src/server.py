from raft.election import Election
from raft.consensus import Consensus
from concurrent import futures
from store.database import Database
from logs.log import Log
import os
import grpc
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
from logger import Logging
from threading import Thread


class Server(raftdb_grpc.ClientServicer):

    def __init__(self, type, server_id, peer_list):
        # who updates state? does this need be here or in election layer?
        self.logger = Logging(server_id).get_logger()
        self.store = Database(type=type, server_id=server_id, logger=self.logger)
        self.log = Log(server_id, self.store, self.logger)
        self.election = Election(peers=peer_list,log=self.log, logger=self.logger, serverId=server_id)

        # Start thread for election service
        Thread(target=self.election.run_election_service()).start()

        self.consensus = Consensus(peers=peer_list, log=self.log, logger=self.logger)

    def Get(self, request, context):
        # Implement leader check logic
        # Make sure this is strongly consistent -- if we allow only one outstanding client request, the system must be strongly consistent by default
        return raftdb.GetResponse(code = 200, value = self.store.get(request.key))

    def Put(self, request, context):
        # Implement leader check logic
        # What happens when we dont get majority? Retry or fail? -- Im guessing fail and respond to client
        # can i not just directly pass request to command?
        # now the request also includes client id and sequence number
        if self.consensus.handlePut(request) == 'OK':
            return raftdb.PutResponse(code = 200)
        else :
            # add more appropriate error message
            return raftdb.PutResponse(code = 500)

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
    

    Thread(target=start_server_thread, args=(client_port, grpc_client_server, )).start()
    Thread(target=start_server_thread, args=(peer_port, grpc_peer_server, )).start()

if __name__ == '__main__':
    # Implement arg parse to read server arguments
    # type = 'memory'
    # server_id = 'server_1'
    # client_port = '50051'
    # raft_port = '50052'

    peer_list = peer_list=os.getenv('PEERS').split(',')
    server = Server(type=os.getenv('TYPE'), server_id = os.getenv('SERVERID'),peer_list=peer_list)
    serve(server)