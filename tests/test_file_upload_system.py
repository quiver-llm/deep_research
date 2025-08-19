"""
Tests for the FileUploadSystem and related components.
"""
import pytest
from pathlib import Path
from typing import Dict, Any, AsyncGenerator
from unittest.mock import AsyncMock
from message_ecs.systems import World
from message_ecs.components import MessageInfo, MessageContent, MessageDelivery, MessageProcessing, MessageStatus
from message_ecs.dify_systems.file_upload_system import FileUploadSystem
from dify_file_upload_handler import DifyFileUploadHandler

# Sample test data
SAMPLE_FILE_PATH = "test_file.txt"
SAMPLE_USER_ID = "test_user_123"
SAMPLE_RESPONSE = {
    "id": "file_123",
    "name": SAMPLE_FILE_PATH,
    "size": 1024,
    "extension": ".txt",
    "mime_type": "text/plain",
    "created_by": SAMPLE_USER_ID,
    "created_at": "2023-01-01T00:00:00Z"
}

class MockDifyHandler:
    """Mock for DifyMessageHandler with async methods."""

    async def process_message(self, message: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        # Simulate a single blocking-like chunk
        yield {
            "content": f"echo: {message.get('query', '')}",
            "metadata": {
                "model": "mock",
                "conversation_id": message.get("conversation_id") or "conv_mock",
            },
        }

    async def stop_generation(self, task_id: str, user: str) -> Dict[str, Any]:
        return {"result": "success", "task_id": task_id, "user": user}

    async def get_suggested_questions(self, message_id: str, user: str) -> Dict[str, Any]:
        return {"result": "success", "data": ["Q1?", "Q2?"], "message_id": message_id, "user": user}

@pytest.fixture
def mock_handler():
    """Create a mock DifyFileUploadHandler."""
    handler = MockDifyHandler()
    handler.upload_file = AsyncMock(return_value=SAMPLE_RESPONSE)
    return handler

@pytest.fixture
def test_file():
    """Create a test file for upload testing."""
    file_path = SAMPLE_FILE_PATH
    with open(file_path, "w") as f:
        f.write("test content")
    return file_path

@pytest.fixture
def world():
    """Create a test world with required systems (synchronous)."""
    return World()

def test_file_upload_success(world: World, mock_handler: MockDifyHandler, test_file: str):
    """Test successful file upload."""
    # Create and add the file upload system
    upload_system = FileUploadSystem(handler=mock_handler)
    world.add_system(upload_system)

    # Create a test entity with file upload data
    entity = world.create_entity()
    entity.add_component(MessageInfo(message_id="test_upload"))
    entity.add_component(
        MessageContent(
            content_type="file_upload",
            data={
                "files": [test_file],
                "user": SAMPLE_USER_ID
            }
        )
    )
    entity.add_component(MessageDelivery(destination="dify"))
    entity.add_component(MessageProcessing())

    # Process the entity
    world.update(0.1)

    # Get updated components
    metadata = entity.get_component(MessageInfo)
    content = entity.get_component(MessageContent)

    # Assert the upload was successful
    assert metadata.status == MessageStatus.COMPLETED
    assert "file_upload" in metadata.metadata
    assert SAMPLE_RESPONSE in metadata.metadata.get("file_upload", [])
    assert "uploaded_file" in content.data
    assert SAMPLE_RESPONSE in content.data.get("uploaded_file", [])

    # Verify the handler was called correctly
    # Verify the handler was awaited once with expected args
    assert mock_handler.upload_file.await_count == 1
    mock_handler.upload_file.assert_any_await(
        file_data=test_file,
        user_id=SAMPLE_USER_ID,
    )

def test_file_upload_missing_data(mock_handler: MockDifyHandler, world: World):
    """Test file upload with missing required data."""
    # Create and add the file upload system
    mock_handler.upload_file.side_effect = ValueError("Missing required file data")
    upload_system = FileUploadSystem(handler=mock_handler)
    world.add_system(upload_system)

    # Create entity with missing file data
    entity = world.create_entity()
    entity.add_component(
        MessageInfo(message_id="test_upload_fail")
    )
    entity.add_component(
        MessageContent(
            content_type="file_upload",
            data=({
                "inputs": {"foo": "bar"},
                "query": "hello",
                "response_mode": "blocking",
                "user": "user@example.com",
                "conversation_id": "conv_123",
                "files": [{
                    "file": [],
                    "user": SAMPLE_USER_ID
                }],
                "auto_generate_name": True,
            })
        )
    )
    entity.add_component(
        MessageDelivery(destination="dify")
    )
    entity.add_component(
        MessageProcessing()
    )

    # Process the entity
    world.update(0.1)

    # Verify failure state
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.FAILED
    assert "Missing required file data" in metadata.error
    assert metadata.retry_count == 1

def test_file_upload_retry_mechanism(mock_handler: MockDifyHandler, world: World, test_file: str):
    """Test that failed uploads are retried."""
    # Make the first attempt fail, then succeed
    mock_handler.upload_file.side_effect = [
        Exception("Temporary network error"),
        SAMPLE_RESPONSE
    ]

    upload_system = FileUploadSystem(handler=mock_handler)
    world.add_system(upload_system)

    entity = world.create_entity()
    entity.add_component(
        MessageInfo(message_id="test_retry"),
    )
    entity.add_component(
        MessageContent(
            content_type="file_upload",
            data={
                "file": [test_file],
                "user": SAMPLE_USER_ID
            }
        )
    )
    entity.add_component(
        MessageDelivery(destination="dify"),
    )
    entity.add_component(
        MessageProcessing()
    )

    # First update - should fail
    world.update(0.1)
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.FAILED
    assert metadata.retry_count == 1

    # Reset status and try again
    metadata.status = MessageStatus.PENDING
    processing = entity.get_component(MessageProcessing)
    processing.started_at = None

    # Second update - should succeed
    world.update(0.1)
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.COMPLETED
    assert metadata.retry_count == 1  # Should not increment on success

    # Verify handler was called twice
    assert mock_handler.upload_file.await_count == 2
