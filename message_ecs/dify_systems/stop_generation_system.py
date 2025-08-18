from datetime import datetime
from typing import Any, Dict

from message_ecs.components import (
    MessageMetadata,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus,
)
from message_ecs.systems import System, Entity
from dify_client import DifyMessageHandler
from async_utils import run_async


class StopGenerationSystem(System):
    """System to stop an ongoing streaming generation task in Dify."""

    def __init__(self, handler: DifyMessageHandler):
        self.handler = handler

    def get_required_components(self) -> tuple:
        return (MessageMetadata, MessageContent, MessageDelivery)

    def process_entity(self, entity: Entity, delta_time: float):
        metadata = entity.get_component(MessageMetadata)
        content = entity.get_component(MessageContent)
        delivery = entity.get_component(MessageDelivery)
        processing = entity.get_component(MessageProcessing)

        if not (metadata and content and delivery):
            return

        if metadata.status == MessageStatus.COMPLETED:
            return
        if processing and processing.started_at:
            return

        if not processing:
            processing = MessageProcessing(processor_id=str(id(self)))
            entity.add_component(processing)

        processing.started_at = datetime.now()
        metadata.status = MessageStatus.PROCESSING
        delivery.delivery_attempts += 1

        try:
            task_id = content.data.get("task_id")
            user = content.data.get("user")
            if not task_id or not user:
                raise ValueError("StopGenerationSystem requires 'task_id' and 'user' in content.data")

            resp: Dict[str, Any] = run_async(self.handler.stop_generation(task_id, user))

            metadata.metadata.setdefault("dify_stop", {})
            metadata.metadata["dify_stop"]["response"] = resp

            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now()
            processing.processing_time = (
                processing.completed_at - processing.started_at
            ).total_seconds()

            return {"status": "success", "response": resp}

        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            metadata.retry_count += 1
            raise
