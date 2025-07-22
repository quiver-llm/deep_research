from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Type, TypeVar, Generic
from datetime import datetime
from enum import Enum

T = TypeVar('T')

class MessageType(str, Enum):
    TEXT = "text"
    FILE = "file"
    COMMAND = "command"
    EVENT = "event"

class BaseMessage(BaseModel):
    """Base message model that all message types should inherit from"""
    message_id: str
    type: MessageType
    content: Dict[str, Any]
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Example specific message types
class TextMessage(BaseMessage):
    """Text message with content validation"""
    type: MessageType = MessageType.TEXT
    content: Dict[str, str]  # Could be more specific with TextContent model

class FileMessage(BaseMessage):
    """File message with file metadata"""
    type: MessageType = MessageType.FILE
    content: Dict[str, Any]  # Could be more specific with FileContent model

class CommandMessage(BaseMessage):
    """Command message for system operations"""
    type: MessageType = MessageType.COMMAND
    content: Dict[str, Any]  # Could be more specific with CommandContent model

class EventMessage(BaseMessage):
    """Event message for system events"""
    type: MessageType = MessageType.EVENT
    content: Dict[str, Any]  # Could be more specific with EventContent model

# Registry for message types
MESSAGE_TYPES = {
    MessageType.TEXT: TextMessage,
    MessageType.FILE: FileMessage,
    MessageType.COMMAND: CommandMessage,
    MessageType.EVENT: EventMessage,
}

def create_message(message_type: MessageType, **data) -> BaseMessage:
    """Factory function to create typed message instances"""
    if message_type not in MESSAGE_TYPES:
        raise ValueError(f"Unknown message type: {message_type}")
    return MESSAGE_TYPES[message_type](**data)
