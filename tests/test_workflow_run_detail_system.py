import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from message_ecs.models import MessageType
from message_ecs.systems import World, Entity
from message_ecs.components import (
    MessageInfo,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus,
    WorkflowRunDetail
)
from message_ecs.dify_systems.workflow_run_detail_system import WorkflowRunDetailSystem


class MockWorkflowDetailHandler:
    def __init__(self):
        self.calls = []
        self.mock_data = {
            "test-run-123": {
                "workflow_id": "test-workflow-123",
                "status": "succeeded",
                "inputs": {"text": "test input"},
                "outputs": {"result": "test output"},
                "total_steps": 5,
                "total_tokens": 100,
                "created_at": datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                "finished_at": datetime(2023, 1, 1, 0, 0, 30, tzinfo=timezone.utc),
                "elapsed_time": None,
                "metadata": {"test": "value"}
            }
        }

    async def get_workflow_run_detail(self, workflow_run_id: str) -> Dict[str, Any]:
        self.calls.append(workflow_run_id)
        if workflow_run_id in self.mock_data:
            return self.mock_data[workflow_run_id]
        raise ValueError("Workflow run not found")


@pytest.fixture
def handler():
    return MockWorkflowDetailHandler()


@pytest.fixture
def world():
    return World()


def test_workflow_run_detail_success(world: World, handler: MockWorkflowDetailHandler):
    # Add the system to the world
    world.add_system(WorkflowRunDetailSystem(handler))

    # Create a test entity with a workflow run ID
    entity = world.create_message_entity(
        message_type=MessageType.EVENT,
        content={"workflow_run_id": "test-run-123"},
        destination="workflow-detail",
        message_id="test-msg-1",
        status=MessageStatus.PENDING
    )
    world.entities[entity.id] = entity

    # Process the entity
    world.update(0.1)

    # Check the results
    metadata = entity.get_component(MessageInfo)
    processing = entity.get_component(MessageProcessing)
    detail = entity.get_component(WorkflowRunDetail)

    assert metadata.status == MessageStatus.COMPLETED
    assert processing is not None
    assert processing.started_at is not None
    assert processing.completed_at is not None
    assert processing.processing_time >= 0

    # Check the workflow run detail component
    assert detail is not None
    assert detail.workflow_run_id == "test-run-123"
    assert detail.workflow_id == "test-workflow-123"
    assert detail.status == "succeeded"
    assert detail.inputs == {"text": "test input"}
    assert detail.outputs == {"result": "test output"}
    assert detail.error is None
    assert detail.total_steps == 5
    assert detail.total_tokens == 100
    assert detail.elapsed_time == 30.0

    # Check the handler was called correctly
    assert len(handler.calls) == 1
    assert handler.calls[0] == "test-run-123"


def test_workflow_run_detail_not_found(world: World, handler: MockWorkflowDetailHandler):
    world.add_system(WorkflowRunDetailSystem(handler))

    entity = world.create_message_entity(
        message_type=MessageType.EVENT,
        content={"workflow_run_id": "not-found"},
        destination="workflow-detail",
        message_id="test-msg-2",
        status=MessageStatus.PENDING
    )
    world.entities[entity.id] = entity

    # Process the entity - should raise an exception
    with pytest.raises(ValueError, match="Workflow run not found"):
        world.update(0.1)

    # Check the entity was marked as failed
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.FAILED
    assert "Workflow run not found" in str(metadata.error)


def test_workflow_run_elapsed_time_calculation(world: World, handler: MockWorkflowDetailHandler):
    world.add_system(WorkflowRunDetailSystem(handler))

    # Create timestamps with timezone
    created_at = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    finished_at = datetime(2023, 1, 1, 12, 5, 30, tzinfo=timezone.utc)  # 5 minutes and 30 seconds later

    # Create a workflow run detail with timestamps
    detail = WorkflowRunDetail(
        workflow_run_id="test-run-123",
        created_at=created_at,
        finished_at=finished_at
    )

    # Check that elapsed time is calculated correctly
    expected_elapsed = 330.0  # 5 minutes and 30 seconds in seconds
    assert detail.elapsed_time == expected_elapsed

    # Test with timestamps as integers (epoch seconds)
    detail = WorkflowRunDetail(
        workflow_run_id="test-run-123",
        created_at=created_at.timestamp(),
        finished_at=finished_at.timestamp()
    )
    assert detail.elapsed_time == expected_elapsed
    assert isinstance(detail.created_at, datetime)
    assert isinstance(detail.finished_at, datetime)
    assert detail.created_at.tzinfo == timezone.utc
    assert detail.finished_at.tzinfo == timezone.utc


def test_workflow_run_detail_invalid_message(world: World, handler: MockWorkflowDetailHandler):
    world.add_system(WorkflowRunDetailSystem(handler))

    # Create an entity without a workflow_run_id
    entity = Entity.create_message_entity(
        message_type=MessageType.EVENT,
        content={"some_other_field": "value"},  # Missing workflow_run_id
        destination="workflow-detail",
        message_id="test-msg-3",
        status=MessageStatus.PENDING
    )
    world.entities[entity.id] = entity

    # Process the entity - should be skipped
    world.update(0.1)

    # Check the entity was not processed by our system
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.PENDING  # Not processed by our system
