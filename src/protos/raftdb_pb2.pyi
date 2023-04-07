from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GetRequest(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: int
    def __init__(self, key: _Optional[int] = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ["code", "leaderId", "value"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    code: int
    leaderId: str
    value: int
    def __init__(self, code: _Optional[int] = ..., value: _Optional[int] = ..., leaderId: _Optional[str] = ...) -> None: ...

class HeartbeatRequest(_message.Message):
    __slots__ = ["serverId", "term"]
    SERVERID_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    serverId: str
    term: int
    def __init__(self, term: _Optional[int] = ..., serverId: _Optional[str] = ...) -> None: ...

class HeartbeatResponse(_message.Message):
    __slots__ = ["code", "leaderId", "term"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    code: int
    leaderId: str
    term: int
    def __init__(self, code: _Optional[int] = ..., term: _Optional[int] = ..., leaderId: _Optional[str] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ["clientid", "key", "lastCommitIndex", "logIndex", "prev_log_index", "prev_term", "sequence_number", "term", "value"]
    CLIENTID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    LASTCOMMITINDEX_FIELD_NUMBER: _ClassVar[int]
    LOGINDEX_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_INDEX_FIELD_NUMBER: _ClassVar[int]
    PREV_TERM_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    clientid: int
    key: int
    lastCommitIndex: int
    logIndex: int
    prev_log_index: int
    prev_term: int
    sequence_number: int
    term: int
    value: int
    def __init__(self, key: _Optional[int] = ..., value: _Optional[int] = ..., clientid: _Optional[int] = ..., sequence_number: _Optional[int] = ..., term: _Optional[int] = ..., logIndex: _Optional[int] = ..., prev_term: _Optional[int] = ..., prev_log_index: _Optional[int] = ..., lastCommitIndex: _Optional[int] = ...) -> None: ...

class LogEntryResponse(_message.Message):
    __slots__ = ["code", "term"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    code: int
    term: int
    def __init__(self, code: _Optional[int] = ..., term: _Optional[int] = ...) -> None: ...

class PutRequest(_message.Message):
    __slots__ = ["clientid", "key", "sequence_number", "value"]
    CLIENTID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    clientid: int
    key: int
    sequence_number: int
    value: int
    def __init__(self, key: _Optional[int] = ..., value: _Optional[int] = ..., clientid: _Optional[int] = ..., sequence_number: _Optional[int] = ...) -> None: ...

class PutResponse(_message.Message):
    __slots__ = ["code", "leaderId"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    code: int
    leaderId: str
    def __init__(self, code: _Optional[int] = ..., leaderId: _Optional[str] = ...) -> None: ...

class VoteRequest(_message.Message):
    __slots__ = ["candidateId", "lastLogIndex", "lastLogTerm", "term"]
    CANDIDATEID_FIELD_NUMBER: _ClassVar[int]
    LASTLOGINDEX_FIELD_NUMBER: _ClassVar[int]
    LASTLOGTERM_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    candidateId: str
    lastLogIndex: int
    lastLogTerm: int
    term: int
    def __init__(self, term: _Optional[int] = ..., lastLogTerm: _Optional[int] = ..., lastLogIndex: _Optional[int] = ..., candidateId: _Optional[str] = ...) -> None: ...

class VoteResponse(_message.Message):
    __slots__ = ["leaderId", "success", "term"]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    leaderId: str
    success: bool
    term: int
    def __init__(self, success: bool = ..., term: _Optional[int] = ..., leaderId: _Optional[str] = ...) -> None: ...
