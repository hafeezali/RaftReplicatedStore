from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetRequest(_message.Message):
    __slots__ = ["key"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    key: int
    def __init__(self, key: _Optional[int] = ...) -> None: ...

class GetResponse(_message.Message):
    __slots__ = ["code", "value"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    code: int
    value: int
    def __init__(self, code: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ["entry", "lastCommitIndex", "term", "termIndex"]
    class Entry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: int
        value: int
        def __init__(self, key: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...
    ENTRY_FIELD_NUMBER: _ClassVar[int]
    LASTCOMMITINDEX_FIELD_NUMBER: _ClassVar[int]
    TERMINDEX_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    entry: LogEntry.Entry
    lastCommitIndex: int
    term: int
    termIndex: int
    def __init__(self, term: _Optional[int] = ..., termIndex: _Optional[int] = ..., lastCommitIndex: _Optional[int] = ..., entry: _Optional[_Union[LogEntry.Entry, _Mapping]] = ...) -> None: ...

class LogEntryResponse(_message.Message):
    __slots__ = ["code"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    code: int
    def __init__(self, code: _Optional[int] = ...) -> None: ...

class PutRequest(_message.Message):
    __slots__ = ["key", "value"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: int
    value: int
    def __init__(self, key: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class PutResponse(_message.Message):
    __slots__ = ["code"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    code: int
    def __init__(self, code: _Optional[int] = ...) -> None: ...

class VoteRequest(_message.Message):
    __slots__ = ["term", "termIndex"]
    TERMINDEX_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    term: int
    termIndex: int
    def __init__(self, term: _Optional[int] = ..., termIndex: _Optional[int] = ...) -> None: ...

class VoteResponse(_message.Message):
    __slots__ = ["bool", "term", "termIndex"]
    BOOL_FIELD_NUMBER: _ClassVar[int]
    TERMINDEX_FIELD_NUMBER: _ClassVar[int]
    TERM_FIELD_NUMBER: _ClassVar[int]
    bool: int
    term: int
    termIndex: int
    def __init__(self, bool: _Optional[int] = ..., term: _Optional[int] = ..., termIndex: _Optional[int] = ...) -> None: ...
