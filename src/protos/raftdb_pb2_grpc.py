# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import raftdb_pb2 as raftdb__pb2


class ClientStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Get = channel.unary_unary(
                '/Client/Get',
                request_serializer=raftdb__pb2.GetRequest.SerializeToString,
                response_deserializer=raftdb__pb2.GetResponse.FromString,
                )
        self.Put = channel.unary_unary(
                '/Client/Put',
                request_serializer=raftdb__pb2.PutRequest.SerializeToString,
                response_deserializer=raftdb__pb2.PutResponse.FromString,
                )
        self.Leader = channel.unary_unary(
                '/Client/Leader',
                request_serializer=raftdb__pb2.LeaderRequest.SerializeToString,
                response_deserializer=raftdb__pb2.LeaderResponse.FromString,
                )


class ClientServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Get(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Put(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Leader(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ClientServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Get': grpc.unary_unary_rpc_method_handler(
                    servicer.Get,
                    request_deserializer=raftdb__pb2.GetRequest.FromString,
                    response_serializer=raftdb__pb2.GetResponse.SerializeToString,
            ),
            'Put': grpc.unary_unary_rpc_method_handler(
                    servicer.Put,
                    request_deserializer=raftdb__pb2.PutRequest.FromString,
                    response_serializer=raftdb__pb2.PutResponse.SerializeToString,
            ),
            'Leader': grpc.unary_unary_rpc_method_handler(
                    servicer.Leader,
                    request_deserializer=raftdb__pb2.LeaderRequest.FromString,
                    response_serializer=raftdb__pb2.LeaderResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Client', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Client(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Get(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Client/Get',
            raftdb__pb2.GetRequest.SerializeToString,
            raftdb__pb2.GetResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Put(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Client/Put',
            raftdb__pb2.PutRequest.SerializeToString,
            raftdb__pb2.PutResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Leader(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Client/Leader',
            raftdb__pb2.LeaderRequest.SerializeToString,
            raftdb__pb2.LeaderResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)


class RaftElectionServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Heartbeat = channel.unary_unary(
                '/RaftElectionService/Heartbeat',
                request_serializer=raftdb__pb2.HeartbeatRequest.SerializeToString,
                response_deserializer=raftdb__pb2.HeartbeatResponse.FromString,
                )
        self.RequestVote = channel.unary_unary(
                '/RaftElectionService/RequestVote',
                request_serializer=raftdb__pb2.VoteRequest.SerializeToString,
                response_deserializer=raftdb__pb2.VoteResponse.FromString,
                )


class RaftElectionServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Heartbeat(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def RequestVote(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_RaftElectionServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Heartbeat': grpc.unary_unary_rpc_method_handler(
                    servicer.Heartbeat,
                    request_deserializer=raftdb__pb2.HeartbeatRequest.FromString,
                    response_serializer=raftdb__pb2.HeartbeatResponse.SerializeToString,
            ),
            'RequestVote': grpc.unary_unary_rpc_method_handler(
                    servicer.RequestVote,
                    request_deserializer=raftdb__pb2.VoteRequest.FromString,
                    response_serializer=raftdb__pb2.VoteResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'RaftElectionService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class RaftElectionService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Heartbeat(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftElectionService/Heartbeat',
            raftdb__pb2.HeartbeatRequest.SerializeToString,
            raftdb__pb2.HeartbeatResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def RequestVote(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/RaftElectionService/RequestVote',
            raftdb__pb2.VoteRequest.SerializeToString,
            raftdb__pb2.VoteResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)


class ConsensusStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.AppendEntries = channel.unary_unary(
                '/Consensus/AppendEntries',
                request_serializer=raftdb__pb2.LogEntry.SerializeToString,
                response_deserializer=raftdb__pb2.LogEntryResponse.FromString,
                )
        self.AppendCorrection = channel.unary_unary(
                '/Consensus/AppendCorrection',
                request_serializer=raftdb__pb2.CorrectionEntry.SerializeToString,
                response_deserializer=raftdb__pb2.CorrectionEntryResponse.FromString,
                )
        self.ClearDurabilityLog = channel.unary_unary(
                '/Consensus/ClearDurabilityLog',
                request_serializer=raftdb__pb2.ClearDurabilityLogRequest.SerializeToString,
                response_deserializer=raftdb__pb2.ClearDurabilityLogResponse.FromString,
                )


class ConsensusServicer(object):
    """Missing associated documentation comment in .proto file."""

    def AppendEntries(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def AppendCorrection(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def ClearDurabilityLog(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_ConsensusServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'AppendEntries': grpc.unary_unary_rpc_method_handler(
                    servicer.AppendEntries,
                    request_deserializer=raftdb__pb2.LogEntry.FromString,
                    response_serializer=raftdb__pb2.LogEntryResponse.SerializeToString,
            ),
            'AppendCorrection': grpc.unary_unary_rpc_method_handler(
                    servicer.AppendCorrection,
                    request_deserializer=raftdb__pb2.CorrectionEntry.FromString,
                    response_serializer=raftdb__pb2.CorrectionEntryResponse.SerializeToString,
            ),
            'ClearDurabilityLog': grpc.unary_unary_rpc_method_handler(
                    servicer.ClearDurabilityLog,
                    request_deserializer=raftdb__pb2.ClearDurabilityLogRequest.FromString,
                    response_serializer=raftdb__pb2.ClearDurabilityLogResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Consensus', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Consensus(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def AppendEntries(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Consensus/AppendEntries',
            raftdb__pb2.LogEntry.SerializeToString,
            raftdb__pb2.LogEntryResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def AppendCorrection(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Consensus/AppendCorrection',
            raftdb__pb2.CorrectionEntry.SerializeToString,
            raftdb__pb2.CorrectionEntryResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def ClearDurabilityLog(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Consensus/ClearDurabilityLog',
            raftdb__pb2.ClearDurabilityLogRequest.SerializeToString,
            raftdb__pb2.ClearDurabilityLogResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
