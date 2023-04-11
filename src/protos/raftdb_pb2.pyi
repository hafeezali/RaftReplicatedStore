from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetRequest(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, key: _Optional[_Iterable[int]] = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ["code", "leaderId", "value"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LEADERID_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    code: int
    leaderId: str
    value: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, code: _Optional[int] = ..., value: _Optional[_Iterable[int]] = ..., leaderId: _Optional[str] = ...) -> None: ...

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
    __slots__ = ["current_term", "entry", "lastCommitIndex", "logIndex", "prev_log_index", "prev_term", "term"]
    class Entry(_message.Message):
        __slots__ = ["clientid", "key", "sequence_number", "value"]
        CLIENTID_FIELD_NUMBER: _ClassVar[int]
        KEY_FIELD_NUMBER: _ClassVar[int]
        SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        clientid: int
        key: _containers.RepeatedScalarFieldContainer[int]
        sequence_number: int
        value: _containers.RepeatedScalarFieldContainer[int]
        def __init__(self, key: _Optional[_Iterable[int]] = ..., value: _Optional[_Iterable[int]] = ..., clientid: _Optional[int] = ..., sequence_number: _Optional[int] = ...) -> None: ...
    CURRENT_TERM_FIELD_NUMBER: _ClassVar[int]
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    LASTCOMMITINDEX_FIELD_NUMBER: _ClassVar[int]
    LOGINDEX_FIELD_NUMBER: _ClassVar[int]
    PREV_LOG_INDEX_FIELD_NUMBER: _ClassVar[int]
    PREV_TERM_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    current_term: int
    entry: LogEntry.Entry
    lastCommitIndex: int
    logIndex: int
    prev_log_index: int
    prev_term: int
    term: int
    def __init__(self, term: _Optional[int] = ..., logIndex: _Optional[int] = ..., prev_term: _Optional[int] = ..., prev_log_index: _Optional[int] = ..., lastCommitIndex: _Optional[int] = ..., entry: _Optional[_Union[LogEntry.Entry, _Mapping]] = ..., current_term: _Optional[int] = ...) -> None: ...

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
    key: _containers.RepeatedScalarFieldContainer[int]
    sequence_number: int
    value: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, key: _Optional[_Iterable[int]] = ..., value: _Optional[_Iterable[int]] = ..., clientid: _Optional[int] = ..., sequence_number: _Optional[int] = ...) -> None: ...

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
