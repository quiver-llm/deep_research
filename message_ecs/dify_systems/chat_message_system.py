from datetime import datetime
from typing import Any, Dict, List, Optional

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


class ChatMessageSystem(System):
    """System for sending chat messages to Dify API."""

    def __init__(self, handler: DifyMessageHandler):
        self.handler = handler

    def get_required_components(self) -> tuple:
        return (MessageInfo, MessageContent, MessageDelivery)

    def process_entity(self, entity: Entity, delta_time: float):
        metadata = entity.get_component(MessageInfo)
        content = entity.get_component(MessageContent)
        delivery = entity.get_component(MessageDelivery)
        processing = entity.get_component(MessageProcessing)

        if not (metadata and content and delivery):
            return

        if metadata.status == MessageStatus.COMPLETED:
            return

        if not processing:
            processing = MessageProcessing(processor_id=str(id(self)))
            entity.add_component(processing)

        processing.started_at = datetime.now()
        metadata.status = MessageStatus.PROCESSING
        delivery.delivery_attempts += 1

        try:
            # Build message payload from content.data
            payload: Dict[str, Any] = {
                "inputs": content.data.get("inputs", {}),
                "query": content.data.get("query", ""),
                "response_mode": content.data.get("response_mode", "streaming"),
                "user": content.data.get("user"),
                "conversation_id": content.data.get("conversation_id"),
                "files": content.data.get("files", []),
                "auto_generate_name": content.data.get("auto_generate_name", True),
            }

            # Call handler.process_message (async generator)
            async def _consume():
                chunks: List[Dict[str, Any]] = []
                async for chunk in self.handler.process_message(payload):
                    chunks.append(chunk)
                return chunks

            chunks: List[Dict[str, Any]] = run_async(_consume())

            # Store response
            last_chunk: Optional[Dict[str, Any]] = chunks[-1] if chunks else None
            metadata.metadata.setdefault("dify", {})
            metadata.metadata["dify"]["chunks"] = chunks
            if last_chunk:
                metadata.metadata["dify"]["last"] = last_chunk
                # Optionally also place the content on MessageContent
                content.data["response"] = last_chunk

            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now()
            processing.processing_time = (
                processing.completed_at - processing.started_at
            ).total_seconds()

            return {"status": "success", "chunks": chunks}

        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            metadata.retry_count += 1
            raise
