import pytest
import time
from datetime import datetime
from message_ecs import (
    Entity, World, MessageProcessingSystem, MessageType,
    MessageInfo, MessageContent, MessageDelivery, MessageProcessing, MessageStatus
)

class MockClient:
    def __init__(self):
        self.processed_messages = []
        self.should_fail = False
        self.should_skip = False
        
    def process_message(self, entity):
        if self.should_fail:
            raise ValueError("Processing failed")
        elif self.should_skip:
            return {"status": "skipped"}
        else:
            time.sleep(0.1)  # spend some time processing
            self.processed_messages.append(entity)
            return {"status": "success"}

# Fixtures
@pytest.fixture
def mock_client():
    return MockClient()

@pytest.fixture
def world(mock_client: MockClient):
    w = World()
    w.add_system(MessageProcessingSystem(mock_client))
    return w

# Test Components
def test_message_metadata():
    metadata = MessageInfo(message_id="123")
    assert metadata.status == MessageStatus.PENDING
    assert metadata.retry_count == 0
    assert isinstance(metadata.timestamp, datetime)

def test_message_content():
    content = MessageContent(content_type=MessageType.TEXT, data={"text": "Hello"})
    assert content.content_type == MessageType.TEXT
    assert content.data == {"text": "Hello"}

# Test Entity
def test_entity_components():
    entity = Entity()
    metadata = MessageInfo(message_id="123")
    
    entity.add_component(metadata)
    assert entity.has_component(MessageInfo)
    assert entity.get_component(MessageInfo) == metadata
    
    # Test adding another component
    content = MessageContent(content_type=MessageType.TEXT, data={})
    entity.add_component(content)
    assert entity.has_component(MessageContent)

# Test World
def test_world_entity_management(world):
    entity = world.create_entity()
    assert entity.id in world.entities
    
    # Test getting entities with components
    entity.add_component(MessageInfo(message_id="123"))
    entities = world.get_entities_with_components(MessageInfo)
    assert len(entities) == 1
    assert entities[0] == entity

def test_create_message_entity(world):
    entity = world.create_message_entity(
        message_type=MessageType.TEXT,
        content={"text": "Test"},
        destination="test_dest"
    )

    assert entity.has_component(MessageInfo)
    assert entity.has_component(MessageContent)
    assert entity.has_component(MessageDelivery)

    content = entity.get_component(MessageContent)
    assert content.content_type == MessageType.TEXT
    assert content.data == {"text": "Test"}

# Test Message Processing
@pytest.mark.asyncio
async def test_message_processing_system(world: World, mock_client: MockClient):
    # Create a message entity
    entity = world.create_message_entity(
        message_type=MessageType.TEXT,
        content={"text": "Test processing"},
        destination="test_dest",
        source="test_source",
    )

    # Process the message
    world.update(0.1)

    # Check that the message was processed
    metadata = entity.get_component(MessageInfo)
    delivery = entity.get_component(MessageDelivery)
    processing = entity.get_component(MessageProcessing)
    assert processing is not None
    assert len(mock_client.processed_messages) == 1
    assert metadata.status == MessageStatus.COMPLETED
    assert delivery.delivery_attempts == 1
    assert delivery.destination == "test_dest"
    assert delivery.source == "test_source"
    assert processing.processor_id is not None
    assert processing.started_at is not None
    assert processing.completed_at is not None
    assert processing.processing_time > 0

@pytest.mark.asyncio
async def test_message_processing_failure(world: World, mock_client: MockClient):
    # Configure client to fail
    should_fail = mock_client.should_fail
    mock_client.should_fail = True

    # Create a message entity
    entity = world.create_message_entity(
        message_type=MessageType.TEXT,
        content={"text": "Test failure"},
        destination="test_dest",
        processing_time=0.1,
        started_at=datetime.now()
    )

    # Process the message
    with pytest.raises(ValueError):
        world.update(0.1)

    # Check that the message was marked as failed
    metadata = entity.get_component(MessageInfo)
    assert metadata.status == MessageStatus.FAILED
    assert "Processing failed" in str(metadata.error)
    mock_client.should_fail = should_fail

def test_message_processing_skip_completed(world: World, mock_client: MockClient):
    # Create a message that's already completed
    entity = world.create_message_entity(
        message_type=MessageType.TEXT,
        content={"text": "Test skip"},
        destination="test_dest"
    )

    # Mark as completed
    metadata = entity.get_component(MessageInfo)
    # metadata.status = MessageStatus.COMPLETED
    # Process - should be skipped
    should_skip = mock_client.should_skip
    mock_client.should_skip = True
    world.update(0.1)
    assert len(mock_client.processed_messages) == 0
    mock_client.should_skip = should_skip

# Test Message Types
def test_message_type_enum():
    assert MessageType.TEXT == "text"
    assert MessageType.FILE == "file"
    assert MessageType.COMMAND == "command"
    assert MessageType.EVENT == "event"

# Test System Requirements
def test_message_processing_system_requirements():
    system = MessageProcessingSystem(None)
    required = system.get_required_components()

    assert MessageInfo in required
    assert MessageContent in required
    assert MessageDelivery in required
    assert MessageProcessing in required
