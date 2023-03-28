# RaftReplicatedStore


Installation:

python -m pip install grpcio
python -m pip install grpcio-tools

Generating gRPC code:

python -m grpc_tools.protoc -I./protos --python_out=./src/protos --pyi_out=./src/protos --grpc_python_out=./src/protos ./protos/raftdb.proto