from raft.election import Election
from raft.consensus import Consensus
from concurrent import futures
from store.database import Database
from logs.log import Log
import os
import grpc
import time
import protos.raftdb_pb2 as raftdb
import protos.raftdb_pb2_grpc as raftdb_grpc
import raft.config as config
from logger import Logging
from threading import Thread

'''
TODO:
1. [TO_START] Look into how max_workers should be fine-tuned? Maybe performance testing might help figure that out?
2. What happens when we dont get majority when trying a put? We need to retry
3. There might be some inconsistency at the db level here - Puts are happening from log, whereas gets are happening here. Do SELECT and INSERT/UPDATE overlap in sqlite3? 
    Hopefully latching is implemented for in-mem dict by default...
4. If get response is None, we need to set an appropriate error code and respond to client
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
        # Create thread to trigger consensus periodically in the background
        Thread(target=self.async_consensus).start()

        self.logger.info("Finished starting server... " + self.server_id)

    # non-nil ext operation. 
    # Check if key is present in durability log. If present, copy durability log to consensus log and achieve consensus on entire durability log. 
    # Clear the durability log
    # Create a map to store if key is present in durability log. This is used for quickly checking key in durability log. Clear map only after groupConsensus
    # We need lock for groupConsensus only until it is added to consensus log of leader but before replication.
    # Modify AppendEntries to take multiple entries instead of just one. Modify consensus layer to track last apply
    # How do we write a durability log -- list.
    # TODO: We can parallelize multiple get requests by having multiple consensus in parallel
    def Get(self, request, context):
        # Strongly consistent -- if we allow only one outstanding client request, the system must be strongly consistent by default
        self.logger.info("Get request received for key: " + str(request.key))
        leader_id = self.log.get_leader()
        if leader_id == self.server_id:
            values = list()
            for k in request.key:
                # check if that particular key is in the durability log, if not -> then directly query from the database, using the same old get function
                self.logger.info(f"{self.log.durability_log}")
                if self.log.get_dura_log_map(k) == -1 :
                    v = self.store.get(k)
                    self.logger.info(f"{v}")
                    values.append(v) 
                # if the key is there in the durability log, copy the entire durability log to consensus log, now start consensus on the consensus log for those added entries
                else :
                    start_idx, last_idx = self.log.copy_dura_to_consensus_log()
                    # copied everything to the consensus log, now should start consensus on those values
                    status = self.groupConsensus(start_idx, last_idx) 
                    if status == 'OK' :
                        v = self.store.get(k)
                        values.append(v)
                    else :
                        self.logger.info(f"Some issue with group consensus")    
            return raftdb.GetResponse(code = config.RESPONSE_CODE_OK, value = values, leaderId = leader_id)     
                    
            
        else:
            self.logger.info(f"Redirecting client to leader {leader_id}")
            return raftdb.GetResponse(code = config.RESPONSE_CODE_REDIRECT, value = None, leaderId = leader_id)
    
    '''
    This function is started by a thread in the background. It flushes the durability log to the consensus log
    Gets the consensus on the added values to the consensus
    All other things are handled in the group Consensus
    '''
    def async_consensus(self) :
        while True :
            self.logger.info(f"Starting consensus")
            if self.server_id == self.log.get_leader() :
                self.logger.info(f"Async consensus triggered")
                start_idx, last_idx = self.log.copy_dura_to_consensus_log()
                if last_idx != -1 :
                    status = self.groupConsensus(start_idx, last_idx)
                    if status != config.RESPONSE_CODE_OK:
                        self.logger.info(f"Some issue with async group consensus")
            time.sleep(100) 
            
             

    '''
    This function is used to start group consensus on the particular values of the consensus log
    '''          
    def groupConsensus(self, start_idx, last_idx):
        response = self.consensus.start_consensus(start_idx, last_idx)
        return response

    def Leader(self, request, context):
        leader_id = self.log.get_leader()
        if leader_id == None or leader_id == '' or leader_id == 'No leader' :
           return raftdb.LeaderResponse(code = config.RESPONSE_CODE_REDIRECT, leaderId = leader_id)
        else :
            return raftdb.LeaderResponse(code = config.RESPONSE_CODE_OK, leaderId = leader_id)
        
    
    def Put(self, request, context):
        self.logger.info("Put request received for key: " + str(request.key) + ", and value: " + str(request.value) + ", from client: " + str(request.clientid))
        response = self.consensus.handlePut(request)
        if response == 'OK':
            return raftdb.PutResponse(code = config.RESPONSE_CODE_OK)
        else:
            self.logger.info("Put request failed")
            return raftdb.PutResponse(code = config.RESPONSE_CODE_REJECT)
        

def start_server_thread(port, grpc_server):
    grpc_server.add_insecure_port('[::]:' + port)
    grpc_server.start()
    grpc_server.wait_for_termination()

def serve(server):
    client_port = '50051'
    peer_port = '50052'
    
    grpc_client_server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    raftdb_grpc.add_ClientServicer_to_server(server, grpc_client_server)

    grpc_peer_server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
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