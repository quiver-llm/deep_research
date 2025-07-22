from pydantic import BaseModel, HttpUrl, Field, ConfigDict, field_serializer
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime

class FileType(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"

class FileMetadata(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    file_name: str
    file_size: int
    mime_type: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('created_at')
    def serialize_dt(self, dt: datetime, _info) -> str:
        return dt.isoformat()

class DifyFile(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    id: str
    local_path: Optional[str] = None
    remote_id: Optional[str] = None
    type: FileType
    metadata: FileMetadata
    dify_payload: Optional[Dict[str, Any]] = None

class MessageContent(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    text: str
    files: List[DifyFile] = []

class Conversation(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True
    )
    
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('created_at', 'updated_at')
    def serialize_dt(self, dt: datetime, _info) -> str:
        return dt.isoformat()

class DifyAPIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status_code: int