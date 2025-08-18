import pytest
import asyncio
from typing import Any, Dict, AsyncGenerator

from message_ecs.systems import World
from message_ecs.components import MessageMetadata, MessageContent, MessageDelivery, MessageProcessing, MessageStatus
from message_ecs.models import MessageType
from message_ecs.dify_systems import ChatMessageSystem, StopGenerationSystem, SuggestedQuestionsSystem


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
def handler():
    return MockDifyHandler()


@pytest.fixture
def world():
    return World()


def test_chat_message_system(world: World, handler: MockDifyHandler):
    # Register system
    world.add_system(ChatMessageSystem(handler))

    # Create entity with required components/fields
    entity = world.create_message_entity(
        message_type=MessageType.TEXT,
        content={
            "inputs": {"foo": "bar"},
            "query": "hello",
            "response_mode": "blocking",
            "user": "user@example.com",
            "conversation_id": "conv_123",
            "files": [],
            "auto_generate_name": True,
        },
        destination="dify",
    )

    # Process
    world.update(0.1)

    # Assertions
    metadata = entity.get_component(MessageMetadata)
    processing = entity.get_component(MessageProcessing)
    content = entity.get_component(MessageContent)

    assert metadata.status == MessageStatus.COMPLETED
    assert processing.started_at and processing.completed_at
    assert processing.processing_time is not None and processing.processing_time >= 0

    assert "dify" in metadata.metadata
    assert "chunks" in metadata.metadata["dify"]
    assert "last" in metadata.metadata["dify"]
    last = metadata.metadata["dify"]["last"]
    assert last["content"].startswith("echo: hello")

    # Response echoed on content
    assert "response" in content.data
    assert content.data["response"]["content"].startswith("echo: hello")


def test_stop_generation_system(world: World, handler: MockDifyHandler):
    # Register system
    world.add_system(StopGenerationSystem(handler))

    # Create entity
    entity = world.create_message_entity(
        message_type=MessageType.COMMAND,
        content={
            "task_id": "task_abc",
            "user": "user@example.com",
        },
        destination="dify",
    )

    world.update(0.1)

    metadata = entity.get_component(MessageMetadata)
    processing = entity.get_component(MessageProcessing)

    assert metadata.status == MessageStatus.COMPLETED
    assert "dify_stop" in metadata.metadata
    assert metadata.metadata["dify_stop"]["response"]["result"] == "success"
    assert processing.started_at and processing.completed_at


def test_suggested_questions_system(world: World, handler: MockDifyHandler):
    # Register system
    world.add_system(SuggestedQuestionsSystem(handler))

    # Create entity
    entity = world.create_message_entity(
        message_type=MessageType.EVENT,
        content={
            "message_id": "msg_123",
            "user": "user@example.com",
        },
        destination="dify",
    )

    world.update(0.1)

    metadata = entity.get_component(MessageMetadata)
    processing = entity.get_component(MessageProcessing)
    content = entity.get_component(MessageContent)

    assert metadata.status == MessageStatus.COMPLETED
    assert "dify_suggested" in metadata.metadata
    resp = metadata.metadata["dify_suggested"]["response"]
    assert resp["result"] == "success"
    assert content.data.get("suggested_questions") == ["Q1?", "Q2?"]
    assert processing.started_at and processing.completed_at
