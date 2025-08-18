from typing import Dict, Type, Any, Optional, List, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import time

from message_ecs.components import (
    MessageMetadata,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus
)
from message_ecs.models import MessageType

T = TypeVar('T')

class Entity:
    """Simple entity class that can hold components"""
    def __init__(self, entity_id: Optional[str] = None):
        self.id = entity_id or str(uuid.uuid4())
        self.components: Dict[Type[Any], Any] = {}

    def add_component(self, component: Any) -> 'Entity':
        self.components[type(component)] = component
        return self

    def get_component(self, component_type: Type[T]) -> Optional[T]:
        return self.components.get(component_type)

    def has_component(self, component_type: Type[Any]) -> bool:
        return component_type in self.components


class System:
    """Base system class for processing entities with specific components"""
    def process(self, world: 'World', delta_time: float):
        """Process all relevant entities in the world"""
        for entity in world.get_entities_with_components(*self.get_required_components()):
            self.process_entity(entity, delta_time)

    def get_required_components(self) -> tuple:
        """Return tuple of component types required by this system"""
        raise NotImplementedError()

    def process_entity(self, entity: Entity, delta_time: float):
        """Process a single entity"""        
        raise NotImplementedError()


class MessageProcessingSystem(System):
    """System for processing messages"""
    def __init__(self, client: Any):
        self.client = client

    def get_required_components(self) -> tuple:
        return (MessageMetadata, MessageContent, MessageDelivery)

    def process_entity(self, entity: Entity, delta_time: float):
        metadata = entity.get_component(MessageMetadata)
        content = entity.get_component(MessageContent)
        delivery = entity.get_component(MessageDelivery)
        processing = entity.get_component(MessageProcessing)

        # Basic guards: if any required component is missing, do nothing
        if not (metadata and content and delivery):
            return

        # Skip if already completed or already started
        if metadata.status == MessageStatus.COMPLETED:
            return
        if processing and processing.started_at:
            return

        # Ensure processing component exists
        if not processing:
            processing = MessageProcessing(processor_id=str(id(self)))
            entity.add_component(processing)

        # Mark as processing and attempt count
        processing.started_at = datetime.now()
        metadata.status = MessageStatus.PROCESSING
        delivery.delivery_attempts += 1

        try:
            # Process the message using the injected client
            result = self.client.process_message(entity)

            # If client decided to skip, revert status to pending and don't finalize
            if isinstance(result, dict) and result.get("status") == "skipped":
                metadata.status = MessageStatus.PENDING
                return result

            # Success: finalize processing
            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now()
            processing.processing_time = (
                processing.completed_at - processing.started_at
            ).total_seconds()

            return result

        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            metadata.retry_count += 1
            raise


class World:
    """The ECS world that contains all entities and systems"""
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.systems: List[System] = []

    def create_entity(self, entity_id: Optional[str] = None) -> Entity:
        """Create a new entity and add it to the world"""
        entity = Entity(entity_id)
        self.entities[entity.id] = entity
        return entity

    def add_system(self, system: System) -> 'World':
        """Add a system to the world"""
        self.systems.append(system)
        return self

    def update(self, delta_time: float):
        """Update all systems in the world"""
        for system in self.systems:
            system.process(self, delta_time)

    def get_entities_with_components(self, *component_types: Type[Any]) -> List[Entity]:
        """Get all entities that have all the specified components"""
        return [
            entity for entity in self.entities.values()
            if all(entity.has_component(t) for t in component_types)
        ]

    def create_message_entity(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        destination: str,
        source: Optional[str] = None,
        **metadata
    ) -> Entity:
        """Helper method to create a message entity with common components"""
        entity = self.create_entity()

        # Add standard message components
        entity.add_component(MessageMetadata(
            message_id=str(uuid.uuid4()),
            metadata=metadata
        ))

        entity.add_component(MessageContent(
            content_type=message_type.value,
            data=content
        ))

        entity.add_component(MessageDelivery(
            destination=destination,
            source=source
        ))

        return entity
