import json
import pytest
from datetime import datetime, timezone

from message_ecs.systems import World
from message_ecs.models import MessageType
from message_ecs.components import MessageStatus, MessageInfo, MessageContent
from message_ecs.dify_systems.event_handling_system import EventHandlingSystem

from event_management.event_models import (
    NodeStartEvent,
    NodeFinishEvent,
    IterationFinishEvent,
    WorkflowFinishEvent,
)
from event_management.content_models import NodeType, NodeStatus
from tests.event_data import (
    NODE_START_EVENT_JSON,
    NODE_FINISH_LLM_JSON,
    NODE_FINISH_IF_ELSE_JSON,
    NODE_FINISH_VARIABLE_AGGREGATOR_JSON,
    NODE_FINISH_TEMPLATE_TRANSFORM_JSON,
    ITERATION_FINISH_EVENT_JSON,
    WORKFLOW_FINISH_EVENT_JSON,
)


@pytest.fixture
def world():
    w = World()
    w.add_system(EventHandlingSystem())
    return w


def _process_event(world: World, event_json: str):
    content = {"event": json.loads(event_json)}
    entity = world.create_message_entity(
        message_type=MessageType.EVENT,
        content=content,
        destination="local",
    )
    world.update(0.0)
    return entity


TEST_EVENTS = [
    (NODE_START_EVENT_JSON, NodeStartEvent, NodeType.ANSWER),
    (NODE_FINISH_LLM_JSON, NodeFinishEvent, NodeType.LLM),
    (NODE_FINISH_IF_ELSE_JSON, NodeFinishEvent, NodeType.IF_ELSE),
    (NODE_FINISH_VARIABLE_AGGREGATOR_JSON, NodeFinishEvent, NodeType.VARIABLE_AGGREGATOR),
    (NODE_FINISH_TEMPLATE_TRANSFORM_JSON, NodeFinishEvent, NodeType.TEMPLATE_TRANSFORM),
    (ITERATION_FINISH_EVENT_JSON, IterationFinishEvent, NodeType.ITERATION),
    (WORKFLOW_FINISH_EVENT_JSON, WorkflowFinishEvent, None),
]


@pytest.mark.parametrize("event_json,expected_type,expected_node_type", TEST_EVENTS)
def test_ecs_event_parsing_success(world: World, event_json, expected_type, expected_node_type):
    entity = _process_event(world, event_json)

    info = entity.get_component(MessageInfo)
    content = entity.get_component(MessageContent)

    assert info.status == MessageStatus.COMPLETED
    assert "parsed_event" in content.data
    parsed = content.data["parsed_event"]
    assert isinstance(parsed, expected_type)

    if expected_node_type is not None:
        assert parsed.content.node_type == expected_node_type


def test_ecs_event_invalid_type(world: World):
    entity = _process_event(world, json.dumps({"type": "invalid_type", "content": {}}))
    info = entity.get_component(MessageInfo)
    assert info.status == MessageStatus.FAILED
    assert info.error and "Unknown event type" in info.error


def test_ecs_event_missing_content(world: World):
    entity = _process_event(world, json.dumps({"type": "node_start"}))
    info = entity.get_component(MessageInfo)
    assert info.status == MessageStatus.FAILED


def test_timestamp_parsing(world: World):
    # node_start uses integer timestamp
    entity = _process_event(world, NODE_START_EVENT_JSON)
    content = entity.get_component(MessageContent)
    event = content.data["parsed_event"]
    assert isinstance(event.content.created_at, datetime)
    assert event.content.created_at.tzinfo == timezone.utc

    # workflow_finish timestamps
    entity2 = _process_event(world, WORKFLOW_FINISH_EVENT_JSON)
    content2 = entity2.get_component(MessageContent)
    wf_event = content2.data["parsed_event"]
    assert isinstance(wf_event, WorkflowFinishEvent)
    assert wf_event.content.finished_at is not None
    assert isinstance(wf_event.content.finished_at, datetime)
    assert wf_event.content.finished_at.tzinfo == timezone.utc
