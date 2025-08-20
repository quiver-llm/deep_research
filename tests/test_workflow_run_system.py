import pytest
import asyncio
from typing import Any, Dict, AsyncGenerator, List
import json

from message_ecs.systems import World
from message_ecs.components import MessageInfo, MessageContent, MessageDelivery, MessageProcessing, MessageStatus
from message_ecs.models import MessageType
from message_ecs.dify_systems import WorkflowRunSystem
from event_management.event_models import WorkflowFinishEvent
from tests.event_data import WORKFLOW_FINISH_EVENT_JSON


class MockWorkflowHandler:
    async def execute_workflow(self, payload: Dict[str, Any]):
        # Switch on response_mode
        mode = payload.get("response_mode", "streaming")
        if mode == "blocking":
            # Return a dict shaped like WorkflowCompletionResponse
            return {
                "workflow_run_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
                "task_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
                "data": {
                    "id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
                    "workflow_id": "3c90c3cc-0d44-4b50-8888-8dd25736052a",
                    "status": "running",
                    "outputs": {},
                    "error": None,
                    "elapsed_time": 1.23,
                    "total_tokens": 10,
                    "total_steps": 0,
                    "created_at": 123,
                    "finished_at": 123,
                },
            }
        else:
            # Streaming: yield a few chunks simulating SSE data
            async def _gen() -> AsyncGenerator[Dict[str, Any], None]:
                yield {"event": "node_start", "data": {"node": "A"}}
                yield {"event": "node_finish", "data": {"node": "A", "status": "succeeded"}}
                yield {"event": "workflow_finish", "data": {"status": "succeeded"}}
            return _gen()


@pytest.fixture
def handler():
    return MockWorkflowHandler()


@pytest.fixture
def world():
    return World()


def test_workflow_run_blocking(world: World, handler: MockWorkflowHandler):
    world.add_system(WorkflowRunSystem(handler))

    entity = world.create_message_entity(
        message_type=MessageType.COMMAND,
        content={
            "inputs": {"user_query": "Translate this", "target_language": "French"},
            "response_mode": "blocking",
            "user": "user_workflow_123",
        },
        destination="dify",
    )

    world.update(0.1)

    metadata = entity.get_component(MessageInfo)
    processing = entity.get_component(MessageProcessing)
    content = entity.get_component(MessageContent)

    assert metadata.status == MessageStatus.COMPLETED
    assert processing.started_at and processing.completed_at
    assert processing.processing_time is not None and processing.processing_time >= 0

    # Check response surfaced
    assert "dify_workflow" in metadata.metadata
    wf_meta = metadata.metadata["dify_workflow"]
    assert "response" in wf_meta
    resp = wf_meta["response"]
    assert resp.get("workflow_run_id")
    assert resp.get("task_id")
    # content should have workflow finished data echoed
    assert "workflow_finished_data" in content.data
    assert isinstance(content.data["workflow_finished_data"], dict)


def test_workflow_run_streaming(world: World, handler: MockWorkflowHandler):
    world.add_system(WorkflowRunSystem(handler))

    entity = world.create_message_entity(
        message_type=MessageType.EVENT,
        content={
            "inputs": {"user_query": "Summarize this"},
            "response_mode": "streaming",
            "user": "user_workflow_456",
        },
        destination="dify",
    )

    world.update(0.1)

    metadata = entity.get_component(MessageInfo)
    processing = entity.get_component(MessageProcessing)
    content = entity.get_component(MessageContent)

    assert metadata.status == MessageStatus.COMPLETED
    assert processing.started_at and processing.completed_at

    assert "dify_workflow" in metadata.metadata
    wf_meta = metadata.metadata["dify_workflow"]
    assert "chunks" in wf_meta and isinstance(wf_meta["chunks"], list)
    assert len(wf_meta["chunks"]) >= 1
    assert "last" in wf_meta

    # last chunk echoed on content
    assert content.data.get("response_stream_last") == wf_meta["last"]


def test_workflow_run_streaming_emits_workflow_finish_event(world: World):
    class MockHandlerStreamingFinish:
        async def execute_workflow(self, payload: Dict[str, Any]):
            async def _gen() -> AsyncGenerator[Dict[str, Any], None]:
                # Some intermediate chunk
                yield {"event": "node_start", "data": {"node": "A"}}
                # Final workflow_finish chunk using provided example JSON
                event_dict = json.loads(WORKFLOW_FINISH_EVENT_JSON)
                # The system supports both {'event','data'} and full event dict; feed full dict
                yield event_dict
            return _gen()

    handler = MockHandlerStreamingFinish()
    world.add_system(WorkflowRunSystem(handler))

    # Capture handler invocation
    calls: List[WorkflowFinishEvent] = []

    async def on_workflow_finish(event: WorkflowFinishEvent):
        calls.append(event)

    entity = world.create_message_entity(
        message_type=MessageType.EVENT,
        content={
            "inputs": {"user_query": "test"},
            "response_mode": "streaming",
            "user": "user_workflow_finish",
            "handlers": {"workflow_finish": on_workflow_finish},
        },
        destination="dify",
    )

    world.update(0.1)

    metadata = entity.get_component(MessageInfo)
    content = entity.get_component(MessageContent)

    assert metadata.status == MessageStatus.COMPLETED
    # Event parsed and stored
    finish_event = metadata.metadata["dify_workflow"].get("finish_event")
    assert finish_event is not None
    assert isinstance(finish_event, WorkflowFinishEvent)
    # Also echoed to content
    assert content.data.get("workflow_finish_event") is finish_event
    # Handler was called
    assert len(calls) == 1
    assert isinstance(calls[0], WorkflowFinishEvent)
