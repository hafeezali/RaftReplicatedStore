# RaftReplicatedStore

# Branch info:

main: Vanilla Raft Implementation
main_v2: Optimized Raft 
main_v3: Nil-ext Raft

## Team Members:

Group 3: 

Hafeez Ali Anees Ali, Sunaina Krishnamoorthy, Saanidhi Arora

## Installation:

python3 -m pip install grpcio
python3 -m pip install grpcio-tools

## Generating gRPC code:

python3 -m grpc_tools.protoc -I./protos --python_out=./src/protos --pyi_out=./src/protos --grpc_python_out=./src/protos ./protos/raftdb.proto

## Open issues:

1. After generaring proto files, modify import of raftdb_pb2 and raftdb_pb2_grpc to protos.raftdb_pb2 and protos.raftdb_pb2_grpc 
2. gitignore not working
3. Add documentation
	- lastCommitIndex : gives position in log
	- termIndex : index for given term

## TODO:

1. Server needs to handle redirection
2. Reject/block client request when election in progress
3. Need to implement a logger layer

Leader
1. leader has to decide if an entry is committed and apply to its state machine
2. once it commits, update last commit index to send in future rpcs
3. remove prev log index from proto and append entries

Follower
1. Once log is consistent with leader, check last commit index, and mark entries as committed
2. Apply to state machine

## State that has to be stored by each replica

Log
- Each entry must have: Command [Key, Value], Term, stored at a particular log index
- Last committed entry index
- last applied entry index

Server details
- server id
- state [leader, follower, candidate]
- who is the leader

Configuration
- How many machines in the system
- list of peers and their addresses

Database details


TODO ONE MORE THING

implement timeouts for Client request RPCs
scenario - client has sent a request, server adds to log, but before it can get majority and commit the entry, 
it has to step down as leader. So now the client has to timeout and retry, and will realize that the server it
was talking to is no longer the leader. So the client should retry the request with the new leader.


## Running docker:

To start:

docker build -t kvstore -f Dockerfile .
docker compose -f docker-compose.yaml up -d

To stop:

docker-compose down --remove-orphans


## Test Scenarios:

1. Remove leader node. Observe that PUT fails because of no-consensus. [SUCCESS]
- Start servers
- Send some puts. Have them succeed
- Kill leader node. Observe client getting redirected to new leader eventually for new PUT
- See PUT succeed
- Kill that leader as well
- Now PUTS/GETS should fail because system is not available (majority down)

2. After adding the same node back, it should become a follower. [SUCCESS]

3. Remove a follower node. Observe that PUT, GET succeeds.
- Follower should keep triggering election with no vain.
- After adding the same node back, it should become follower and have its logs cleaned.

4. Test durability
    1. kill leader node (all 3 one after the other) and try get

5. Safety - testing that you don’t have two leaders anytime

6. Log matching: we are testing starting nodes with diff configuration and seeing ki they are overwritten.

7. Request Votes, append entries and heart beat handlers are 3 inter-dependent processes. You can check if,
- Will your node serialize two concurrent request votes?
- Are ur append entries and heart beat handler serialized (ur scenario)?

## Measurements:

1. Availability, throughput, and latency
- Throughput in two ways : single client’s max throughput and aggregate throughput using multiple clients.

## Extra functionality: 

- Membership change, memcache, multi-put and multi-get.

## Issues:

1. We don’t have a staging area - So, after appending, if leader doesn’t get majority, we will not be able to delete it. We try infinitely. 
2. Currently, we are retrying if append entries fails in the consensus layer. So, if a node goes down (maybe because of membership changes), we will have a dangling thread which will eventually kill resources
3. Last entry will never get committed on followers. This is because we must have correction of logs running in a backend thread (perhaps heartbeat thread).
