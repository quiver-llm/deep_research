from datetime import datetime
from typing import Any, Dict

from message_ecs.components import (
    MessageInfo,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus,
)
from message_ecs.systems import System, Entity
from dify_client import DifyMessageHandler
from async_utils import run_async


class SuggestedQuestionsSystem(System):
    """System to fetch next suggested questions for a message in Dify."""

    def __init__(self, handler: DifyMessageHandler):
        self.handler = handler

    def get_required_components(self) -> tuple:
        return (MessageInfo, MessageContent, MessageDelivery, MessageProcessing)

    def process_entity(self, entity: Entity, delta_time: float):
        metadata = entity.get_component(MessageInfo)
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
            message_id = content.data.get("message_id")
            user = content.data.get("user")
            if not message_id or not user:
                raise ValueError("SuggestedQuestionsSystem requires 'message_id' and 'user' in content.data")

            resp: Dict[str, Any] = run_async(self.handler.get_suggested_questions(message_id, user))

            metadata.metadata.setdefault("dify_suggested", {})
            metadata.metadata["dify_suggested"]["response"] = resp

            # Optionally expose suggestions on content
            if isinstance(resp, dict) and "data" in resp:
                content.data["suggested_questions"] = resp.get("data")

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
