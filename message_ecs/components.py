from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type
from enum import Enum
from datetime import datetime


class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MessageMetadata:
    """Base metadata for all messages"""
    message_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    status: MessageStatus = MessageStatus.PENDING
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageContent:
    """Base class for message content components"""
    content_type: str
    data: Dict[str, Any]


@dataclass
class MessageDelivery:
    """Component for tracking message delivery"""
    destination: str
    source: Optional[str] = None
    priority: int = 0
    delivery_attempts: int = 0
    source_metadata: Optional[MessageMetadata] = None
    source_content: Optional[MessageContent] = None


@dataclass
class MessageProcessing:
    """Component for tracking message processing state"""
    processor_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None
