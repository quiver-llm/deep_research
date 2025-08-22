"""Tests for the WorkflowDetailHandlingSystem."""
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from message_ecs.systems import World, Entity
from message_ecs.components import (
    MessageInfo,
    MessageContent,
    MessageDelivery,
    MessageStatus,
    MessageProcessing,
    WorkflowRunDetail
)
from message_ecs.dify_systems.detail_handling_system import WorkflowDetailHandlingSystem


@pytest.fixture
def world():
    return World()


def test_process_workflow_detail_message(world: World):
    # Setup
    system = WorkflowDetailHandlingSystem()
    world.add_system(system)

    # Create test data matching the API schema
    test_data = {
        'workflow_run_id': 'test-run-123',
        'workflow_id': 'test-workflow-123',
        'status': 'succeeded',
        'inputs': {'text': 'test input'},
        'outputs': {'result': 'test output'},
        'total_steps': 5,
        'total_tokens': 100,
        'created_at': 1672531200,  # 2023-01-01 00:00:00 UTC
        'finished_at': 1672531230,  # 2023-01-01 00:00:30 UTC
        'elapsed_time': None
    }

    # Create test entity
    entity = world.create_entity()
    entity.add_components(
        MessageInfo(message_id='test-msg-1'),
        MessageContent(content_type='workflow_detail', data=test_data),
        MessageDelivery(destination='workflow-detail')
    )

    # Process the entity
    world.update(0.1)

    # Verify results
    detail = entity.get_component(WorkflowRunDetail)
    assert detail is not None
    assert detail.workflow_run_id == 'test-run-123'
    assert detail.workflow_id == 'test-workflow-123'
    assert detail.status == 'succeeded'
    assert detail.inputs == {'text': 'test input'}
    assert detail.outputs == {'result': 'test output'}
    assert detail.total_steps == 5
    assert detail.total_tokens == 100
    assert detail.elapsed_time == 30.0
    assert isinstance(detail.created_at, datetime)
    assert detail.created_at.tzinfo == timezone.utc
    assert detail.created_at.timestamp() == 1672531200

    # Check processing status
    processing = entity.get_component(MessageProcessing)
    assert processing is not None
    assert processing.completed_at is not None
    assert processing.processing_time is not None

    # Check message status
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.COMPLETED


def test_handle_invalid_message(world: World):
    # Setup
    system = WorkflowDetailHandlingSystem()
    world.add_system(system)

    # Create test entity with invalid data (missing workflow_run_id)
    entity = world.create_entity()
    entity.add_components(
        MessageInfo(message_id='test-msg-2'),
        MessageContent(content_type='invalid', data={'some_field': 'value'}),
        MessageDelivery(destination='other-destination')
    )

    # Process the entity
    world.update(0.1)

    # Should not have processed the message (no WorkflowRunDetail component added)
    detail = entity.get_component(WorkflowRunDetail)
    assert detail is None

    # Message should still be in pending state
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.PENDING
