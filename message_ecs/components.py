from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union
from enum import Enum
from datetime import datetime, timezone

from base import IComponent


class MessageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class MessageInfo(IComponent):
    """Base execution information for all messages"""
    message_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    status: MessageStatus = MessageStatus.PENDING
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with timezone-naive datetimes for serialization."""
        result = self.__dict__.copy()
        if isinstance(self.timestamp, datetime) and self.timestamp.tzinfo is not None:
            result['timestamp'] = self.timestamp.replace(tzinfo=None)
        return result


@dataclass
class MessageContent(IComponent):
    """Base class for message content components"""
    content_type: str
    data: Dict[str, Any]

@dataclass
class MessageProcessing(IComponent):
    """Component for tracking message processing state"""
    processor_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with timezone-naive datetimes for serialization."""
        result = {}
        for field, value in self.__dict__.items():
            if isinstance(value, datetime) and value.tzinfo is not None:
                result[field] = value.replace(tzinfo=None)
            else:
                result[field] = value
        return result

@dataclass
class MessageDelivery(IComponent):
    """Component for tracking message delivery"""
    destination: str
    priority: int = 0
    delivery_attempts: int = 0
    source: Optional[str] = None


@dataclass
class WorkflowRunDetail(IComponent):
    """Component for tracking workflow run details"""
    workflow_run_id: str
    workflow_id: Optional[str] = None
    status: Optional[str] = None  # running, succeeded, failed, stopped
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    total_steps: Optional[int] = None
    total_tokens: Optional[int] = None
    created_at: Optional[datetime] = None  # datetime with timezone
    finished_at: Optional[datetime] = None  # datetime with timezone
    elapsed_time: Optional[float] = None  # in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Convert timestamps to datetime if they're provided as integers/float
        if isinstance(self.created_at, (int, float)):
            self.created_at = datetime.fromtimestamp(self.created_at, tz=timezone.utc)
        if isinstance(self.finished_at, (int, float)):
            self.finished_at = datetime.fromtimestamp(self.finished_at, tz=timezone.utc)
        
        # Calculate elapsed_time if both timestamps are available
        if self.created_at and self.finished_at:
            self.elapsed_time = (self.finished_at - self.created_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with timezone-naive datetimes for serialization."""
        result = {}
        for field, value in self.__dict__.items():
            if isinstance(value, datetime) and value.tzinfo is not None:
                result[field] = value.replace(tzinfo=None)
            elif field == 'elapsed_time' and value is not None:
                # Ensure elapsed_time is a float for JSON serialization
                result[field] = float(value)
            else:
                result[field] = value
        return result
