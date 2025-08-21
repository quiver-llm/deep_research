"""Tests for DifyEventHandler class."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from event_management.dify_event_handler import DifyEventHandler
from event_management.event_emitter import EventEmitter
from event_management.event_models import (
    NodeStartEvent,
    NodeFinishEvent,
    WorkflowFinishEvent
)
from event_management.content_models import NodeType, NodeStatus

# Sample event data fixtures


@pytest.fixture
def sample_node_start_event() -> Dict[str, Any]:
    return {
        "type": "node_start",
        "content": {
            "id": "node_123",
            "node_id": "node_123",
            "node_type": NodeType.LLM,
            "title": "Test Node",
            "index": 1,
            "predecessor_node_id": None,
            "extras": {},
            "parallel_id": None,
            "parallel_start_node_id": None,
            "parent_parallel_id": None,
            "parent_parallel_start_node_id": None,
            "iteration_id": None,
            "loop_id": None,
            "parallel_run_id": None,
            "agent_strategy": None
        }
    }

@pytest.fixture
def sample_node_finish_event() -> Dict[str, Any]:
    return {
        "type": "node_finish",
        "content": {
            "id": "node_123",
            "node_id": "node_123",
            "node_type": NodeType.LLM,
            "title": "Test Node",
            "index": 1,
            "outputs": {"text": "Generated text"},
            "status": NodeStatus.SUCCEEDED,
            "elapsed_time": 0.5,
            "execution_metadata": {},
            "total_tokens": 10,
            "files": []
        }
    }

@pytest.fixture
def sample_workflow_finish_event() -> Dict[str, Any]:
    return {
        "type": "workflow_finish",
        "content": {
            "id": "run_123",
            "workflow_id": "workflow_123",
            "sequence_number": 1,
            "status": "completed",
            "outputs": {"result": "success"},
            "error": None,
            "elapsed_time": 1.5,
            "total_tokens": 100,
            "total_steps": 5,
            "created_by": {"id": "user_123", "name": "Test User"},
            "created_at": 1672531200,
            "finished_at": 1672531201.5,
            "exceptions_count": 0,
            "files": []
        }
    }

@pytest.fixture
def mock_emitter():
    emitter = MagicMock()
    emitter.emit = AsyncMock()
    return emitter


@pytest.fixture
def dify_handler(mock_emitter):
    return DifyEventHandler(
        api_key="test_api_key",
        endpoint="https://api.dify.ai",
        event_emitter=mock_emitter
    )


@pytest.mark.asyncio
async def test_handle_node_start(dify_handler, mock_emitter, sample_node_start_event):
    """Test handling a node_start event."""
    # Initialize the event_type_map with our mock handler
    mock_handler = AsyncMock()
    dify_handler.event_type_map = {"node_start": mock_handler}

    # Process the event
    result = await dify_handler.handle(sample_node_start_event)

    # Verify the handler was called with the parsed event
    assert mock_handler.await_count == 1
    assert isinstance(mock_handler.await_args[0][0], NodeStartEvent)
    assert mock_handler.await_args[0][0].content.node_id == "node_123"

    # Verify the parsed event is returned
    assert isinstance(result, NodeStartEvent)
    assert result.content.node_id == "node_123"

    # No error should be emitted
    mock_emitter.emit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_node_finish(dify_handler, mock_emitter, sample_node_finish_event):
    """Test handling a node_finish event."""
    # Initialize the event_type_map with our mock handler
    mock_handler = AsyncMock()
    dify_handler.event_type_map = {"node_finish": mock_handler}

    # Process the event
    result = await dify_handler.handle(sample_node_finish_event)

    # Verify the handler was called with the parsed event
    assert mock_handler.await_count == 1
    event = mock_handler.await_args[0][0]
    assert isinstance(event, NodeFinishEvent)
    assert event.type == "node_finish"
    assert event.content.node_id == "node_123"
    assert event.content.node_type == NodeType.LLM
    assert event.content.status == NodeStatus.SUCCEEDED
    assert event.content.outputs == {"text": "Generated text"}
    assert event.content.elapsed_time == 0.5
    assert event.content.total_tokens == 10
    assert event.content.files == []

    # Verify the parsed event is returned
    assert isinstance(result, NodeFinishEvent)
    assert result.content.node_id == "node_123"
    assert result.content.status == NodeStatus.SUCCEEDED

    # No error should be emitted
    mock_emitter.emit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_workflow_finish(dify_handler, mock_emitter, sample_workflow_finish_event):
    """Test handling a workflow_finish event."""
    # Initialize the event_type_map with our mock handler
    mock_handler = AsyncMock()
    dify_handler.event_type_map = {"workflow_finish": mock_handler}

    # Process the event
    result = await dify_handler.handle(sample_workflow_finish_event)

    # Verify the handler was called with the parsed event
    assert mock_handler.await_count == 1
    assert isinstance(mock_handler.await_args[0][0], WorkflowFinishEvent)
    content = mock_handler.await_args[0][0].content
    assert content.id == "run_123"
    assert content.workflow_id == "workflow_123"
    assert content.status == "completed"
    assert content.outputs == {"result": "success"}
    assert content.elapsed_time == 1.5
    assert content.total_tokens == 100
    assert content.total_steps == 5
    assert content.created_by == {"id": "user_123", "name": "Test User"}
    assert content.exceptions_count == 0
    assert content.files == []

    # Verify the parsed event is returned
    assert isinstance(result, WorkflowFinishEvent)
    assert result.content.id == "run_123"
    assert result.content.workflow_id == "workflow_123"
    assert result.content.status == "completed"

    # No error should be emitted
    mock_emitter.emit.assert_not_called()

@pytest.mark.asyncio
async def test_handle_unknown_event_type(dify_handler, mock_emitter):
    """Test handling an unknown event type."""
    # Clear any existing handlers
    dify_handler.event_type_map = {}

    # Try to handle an unknown event type
    unknown_event = {
        "type": "unknown_event",
        "content": {
            "id": "test_id",
            "node_id": "test_node_id",
            "node_type": "test_type",
            "title": "Test Node"
        }
    }

    with pytest.raises(ValueError) as excinfo:
        await dify_handler.handle(unknown_event)

    # Verify the error message
    assert "Unknown event type: unknown_event" in str(excinfo.value)

    # Error should be emitted
    mock_emitter.emit.assert_called_once()
    emit_args = mock_emitter.emit.await_args[0]
    assert emit_args[0] == "status"
    assert "error" in emit_args[1]["status"]
    assert "Unknown event type: unknown_event" in str(emit_args[1]["description"])

@pytest.mark.asyncio
async def test_handle_invalid_event_data(dify_handler, mock_emitter):
    """Test handling invalid event data."""
    # Clear any existing handlers
    dify_handler.event_type_map = {}

    # Test with invalid event type data (missing required fields)
    invalid_typed_event = {
        "type": "node_start",
        "content": {
            # Missing required fields like node_id, node_type, etc.
            "title": "Invalid Node"
        }
    }

    with pytest.raises(ValueError) as excinfo:
        await dify_handler.handle(invalid_typed_event)

    # Verify the error message indicates a validation error
    error_message = str(excinfo.value).lower()
    assert any(msg in error_message for msg in ["validation error", "field required"])

    # Error should be emitted for invalid event data
    mock_emitter.emit.assert_called_once()
    emit_args = mock_emitter.emit.await_args[0]
    assert emit_args[0] == "status"
    assert "error" in emit_args[1]["status"]
    assert any(msg in str(emit_args[1]["description"]).lower() 
                for msg in ["validation error", "field required"])

@pytest.mark.asyncio
async def test_init_without_emitter():
    """Test initialization without an event emitter."""
    # Should be able to initialize without an event emitter
    handler = DifyEventHandler(
        api_key="test_api_key",
        endpoint="https://api.dify.ai"
    )

    assert handler.api_key == "test_api_key"
    assert handler.endpoint == "https://api.dify.ai"
    assert handler.event_emitter is None
    assert isinstance(handler.event_type_map, dict)
    assert isinstance(handler.event_map, dict)
    assert handler.config == {
        "api_key": "test_api_key",
        "endpoint": "https://api.dify.ai"
    }
