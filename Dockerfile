FROM ubuntu:22.04

RUN apt-get update
RUN apt-get install -y protobuf-compiler python3 python3-pip cmake
RUN pip3 install grpcio grpcio-tools
RUN pip3 install protobuf==3.20.*



COPY ./ /RaftReplicatedStore
WORKDIR /RaftReplicatedStore

CMD ["sh", "run.sh"]



