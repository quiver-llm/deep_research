"""
Message ECS System

This module provides an Entity-Component-System (ECS) architecture for processing
messages with different content types and handling them through specialized systems.
"""

from message_ecs.components import (
    MessageMetadata,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus
)
from message_ecs.models import (
    BaseMessage,
    MessageType,
    TextMessage,
    FileMessage,
    CommandMessage,
    EventMessage,
    create_message
)
from message_ecs.systems import World, Entity, System, MessageProcessingSystem

__all__ = [
    # Components
    'MessageMetadata',
    'MessageContent',
    'MessageDelivery',
    'MessageProcessing',
    'MessageStatus',
    
    # Models
    'BaseMessage',
    'MessageType',
    'TextMessage',
    'FileMessage',
    'CommandMessage',
    'EventMessage',
    'create_message',
    
    # Systems
    'World',
    'Entity',
    'System',
    'MessageProcessingSystem',
]

# Example usage
if __name__ == "__main__":
    # Example client implementation
    class MessageClient:
        def process_message(self, entity: Entity):
            content = entity.get_component(MessageContent)
            print(f"Processing message: {content.data}")
            # Process the message here
            return {"status": "success"}
    
    # Create world and systems
    world = World()
    client = MessageClient()
    world.add_system(MessageProcessingSystem(client))
    
    # Create and process a message
    message = world.create_message_entity(
        message_type=MessageType.TEXT,
        content={"text": "Hello, ECS!"},
        destination="user123",
        source="system",
        priority=1
    )
    
    # Update the world (processes all systems)
    world.update(0.1)
