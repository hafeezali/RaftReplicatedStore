from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ClientReq(_message.Message):
    __slots__ = ["key", "type", "value"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: int
    type: int
    value: int
    def __init__(self, type: _Optional[int] = ..., key: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class LogEntry(_message.Message):
    __slots__ = ["heartbeat", "key", "type", "value"]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    heartbeat: int
    key: int
    type: int
    value: int
    def __init__(self, heartbeat: _Optional[int] = ..., type: _Optional[int] = ..., key: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ["code", "value"]
    CODE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    code: int
    value: int
    def __init__(self, code: _Optional[int] = ..., value: _Optional[int] = ...) -> None: ...
