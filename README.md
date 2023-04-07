# RaftReplicatedStore

## Installation:

python3 -m pip install grpcio
python3 -m pip install grpcio-tools

## Generating gRPC code:

python3 -m grpc_tools.protoc -I./protos --python_out=./src/protos --pyi_out=./src/protos --grpc_python_out=./src/protos ./protos/raftdb.proto

## Open issues:

1. After generaring proto files, modify import of raftdb_pb2 and raftdb_pb2_grpc to protos.raftdb_pb2 and protos.raftdb_pb2_grpc 
2. Stupid gitignore not working
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



Add pics of protos and algos from the slides here
