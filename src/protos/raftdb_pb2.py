# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: raftdb.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0craftdb.proto\"\x19\n\nGetRequest\x12\x0b\n\x03key\x18\x01 \x03(\x05\"S\n\nPutRequest\x12\x0b\n\x03key\x18\x01 \x03(\x05\x12\r\n\x05value\x18\x02 \x03(\x05\x12\x10\n\x08\x63lientid\x18\x03 \x01(\x05\x12\x17\n\x0fsequence_number\x18\x04 \x01(\x05\"<\n\x0bGetResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\r\n\x05value\x18\x02 \x03(\x05\x12\x10\n\x08leaderId\x18\x03 \x01(\t\"-\n\x0bPutResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\x10\n\x08leaderId\x18\x02 \x01(\t\"n\n\x10HeartbeatRequest\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x10\n\x08serverId\x18\x02 \x01(\t\x12\x17\n\x0flastCommitIndex\x18\x03 \x01(\x05\x12\x0f\n\x07log_idx\x18\x04 \x01(\x05\x12\x10\n\x08log_term\x18\x05 \x01(\x05\"A\n\x11HeartbeatResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\x0c\n\x04term\x18\x02 \x01(\x05\x12\x10\n\x08leaderId\x18\x03 \x01(\t\"\xf4\x01\n\x08LogEntry\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x10\n\x08logIndex\x18\x02 \x01(\x05\x12\x11\n\tprev_term\x18\x03 \x01(\x05\x12\x16\n\x0eprev_log_index\x18\x04 \x01(\x05\x12\x17\n\x0flastCommitIndex\x18\x05 \x01(\x05\x12\x1e\n\x05\x65ntry\x18\x06 \x01(\x0b\x32\x0f.LogEntry.Entry\x12\x14\n\x0c\x63urrent_term\x18\x07 \x01(\x05\x1aN\n\x05\x45ntry\x12\x0b\n\x03key\x18\x01 \x03(\x05\x12\r\n\x05value\x18\x02 \x03(\x05\x12\x10\n\x08\x63lientid\x18\x03 \x01(\x05\x12\x17\n\x0fsequence_number\x18\x04 \x01(\x05\"E\n\x10LogEntryResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\x0c\n\x04term\x18\x02 \x01(\x05\x12\x15\n\rlastSafeIndex\x18\x03 \x01(\x05\"\xe3\x01\n\x0f\x43orrectionEntry\x12,\n\x07\x65ntries\x18\x01 \x03(\x0b\x32\x1b.CorrectionEntry.Correction\x12\x17\n\x0flastCommitIndex\x18\x02 \x01(\x05\x12\x14\n\x0c\x63urrent_term\x18\x03 \x01(\x05\x1as\n\nCorrection\x12\x0b\n\x03key\x18\x01 \x03(\x05\x12\r\n\x05value\x18\x02 \x03(\x05\x12\x10\n\x08\x63lientid\x18\x03 \x01(\x05\x12\x17\n\x0fsequence_number\x18\x04 \x01(\x05\x12\x0c\n\x04term\x18\x05 \x01(\x05\x12\x10\n\x08logIndex\x18\x06 \x01(\x05\"L\n\x17\x43orrectionEntryResponse\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x05\x12\x0c\n\x04term\x18\x02 \x01(\x05\x12\x15\n\rlastSafeIndex\x18\x03 \x01(\x05\"[\n\x0bVoteRequest\x12\x0c\n\x04term\x18\x01 \x01(\x05\x12\x13\n\x0blastLogTerm\x18\x02 \x01(\x05\x12\x14\n\x0clastLogIndex\x18\x03 \x01(\x05\x12\x13\n\x0b\x63\x61ndidateId\x18\x04 \x01(\t\"?\n\x0cVoteResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0c\n\x04term\x18\x02 \x01(\x05\x12\x10\n\x08leaderId\x18\x03 \x01(\t2P\n\x06\x43lient\x12\"\n\x03Get\x12\x0b.GetRequest\x1a\x0c.GetResponse\"\x00\x12\"\n\x03Put\x12\x0b.PutRequest\x1a\x0c.PutResponse\"\x00\x32y\n\x13RaftElectionService\x12\x34\n\tHeartbeat\x12\x11.HeartbeatRequest\x1a\x12.HeartbeatResponse\"\x00\x12,\n\x0bRequestVote\x12\x0c.VoteRequest\x1a\r.VoteResponse\"\x00\x32~\n\tConsensus\x12/\n\rAppendEntries\x12\t.LogEntry\x1a\x11.LogEntryResponse\"\x00\x12@\n\x10\x41ppendCorrection\x12\x10.CorrectionEntry\x1a\x18.CorrectionEntryResponse\"\x00\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'raftdb_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _GETREQUEST._serialized_start=16
  _GETREQUEST._serialized_end=41
  _PUTREQUEST._serialized_start=43
  _PUTREQUEST._serialized_end=126
  _GETRESPONSE._serialized_start=128
  _GETRESPONSE._serialized_end=188
  _PUTRESPONSE._serialized_start=190
  _PUTRESPONSE._serialized_end=235
  _HEARTBEATREQUEST._serialized_start=237
  _HEARTBEATREQUEST._serialized_end=347
  _HEARTBEATRESPONSE._serialized_start=349
  _HEARTBEATRESPONSE._serialized_end=414
  _LOGENTRY._serialized_start=417
  _LOGENTRY._serialized_end=661
  _LOGENTRY_ENTRY._serialized_start=583
  _LOGENTRY_ENTRY._serialized_end=661
  _LOGENTRYRESPONSE._serialized_start=663
  _LOGENTRYRESPONSE._serialized_end=732
  _CORRECTIONENTRY._serialized_start=735
  _CORRECTIONENTRY._serialized_end=962
  _CORRECTIONENTRY_CORRECTION._serialized_start=847
  _CORRECTIONENTRY_CORRECTION._serialized_end=962
  _CORRECTIONENTRYRESPONSE._serialized_start=964
  _CORRECTIONENTRYRESPONSE._serialized_end=1040
  _VOTEREQUEST._serialized_start=1042
  _VOTEREQUEST._serialized_end=1133
  _VOTERESPONSE._serialized_start=1135
  _VOTERESPONSE._serialized_end=1198
  _CLIENT._serialized_start=1200
  _CLIENT._serialized_end=1280
  _RAFTELECTIONSERVICE._serialized_start=1282
  _RAFTELECTIONSERVICE._serialized_end=1403
  _CONSENSUS._serialized_start=1405
  _CONSENSUS._serialized_end=1531
# @@protoc_insertion_point(module_scope)
