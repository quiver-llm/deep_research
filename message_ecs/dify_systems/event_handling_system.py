"""
ECS-style system for handling Dify events using dataclasses components.
This mirrors the behavior of event_management/dify_event_handler.py but fits the
existing ECS World/System pattern.
"""
from datetime import datetime
from typing import Any, Dict, Optional, Callable, Awaitable

from message_ecs.systems import System, Entity
from message_ecs.components import (
    MessageInfo,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus,
)
from async_utils import run_async

# Event models and emitter from event_management
from event_management.event_models import (
    DifyEvent,
    NodeStartEvent,
    NodeFinishEvent,
    IterationFinishEvent,
    WorkflowFinishEvent,
)
from event_management.event_emitter import EventEmitter


class EventHandlingSystem(System):
    """System that parses and processes Dify events.

    Expects MessageContent.data to contain:
    - "event": Dict[str, Any] raw event payload
    - "emitter": EventEmitter (optional)
    - "handlers": Dict[str, Callable[[DifyEvent], Awaitable[None]]] (optional)
    """

    def __init__(self):
        # mirror map used by DifyEventHandler
        self.event_map = {
            "node_start": NodeStartEvent,
            "node_finish": NodeFinishEvent,
            "iteration_finish": IterationFinishEvent,
            "workflow_finish": WorkflowFinishEvent,
        }

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
            raw_event: Dict[str, Any] = content.data.get("event")
            emitter: Optional[EventEmitter] = content.data.get("emitter")
            custom_handlers: Optional[Dict[str, Callable[[DifyEvent], Awaitable[None]]]] = (
                content.data.get("handlers")
            )

            if not raw_event:
                raise ValueError("Missing or invalid event payload: 'event'")

            event_type = raw_event.get("type")
            if not event_type:
                raise ValueError("Missing or invalid event type: 'type'")

            model_class = self.event_map.get(event_type)
            if not model_class:
                raise ValueError(f"Unknown event type: {event_type}")

            # Parse/validate using Pydantic models
            parsed: DifyEvent = model_class.model_validate(raw_event)

            # optional: run custom handler
            if custom_handlers and event_type in custom_handlers:
                handler = custom_handlers[event_type]
                # handler is async -> run via run_async
                run_async(handler(parsed))

            # success path
            metadata.metadata.setdefault("dify_event", {})
            metadata.metadata["dify_event"]["parsed"] = parsed
            content.data["parsed_event"] = parsed

            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now()
            processing.processing_time = (
                processing.completed_at - processing.started_at
            ).total_seconds()

            return {"status": "success", "event_type": event_type}

        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            metadata.retry_count += 1
            # emit error if we have an emitter
            emitter = content.data.get("emitter")
            if isinstance(emitter, EventEmitter):
                run_async(
                    emitter.emit(
                        description=f"Error processing event: {str(e)}",
                        status="error",
                        done=True,
                        hidden=False,
                    )
                )
            return {"status": "failed", "error": str(e)}
