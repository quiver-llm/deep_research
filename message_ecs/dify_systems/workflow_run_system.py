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
from async_utils import run_async
from event_management.event_models import WorkflowFinishEvent
from event_management.event_emitter import EventEmitter


class WorkflowRunSystem(System):
    """System for executing Dify workflows via /workflows/run.

    Expects MessageContent.data to contain a payload matching
    the WorkflowExecutionRequest schema from dify_execute_workflow.md:
      - inputs: Dict[str, Any]
      - response_mode: "streaming" | "blocking"
      - user: str
    """

    def __init__(self, handler: Any):
        # handler must expose an async API:
        #   - async def execute_workflow(self, payload: Dict[str, Any]) ->
        #         - if response_mode == "streaming": AsyncGenerator[Dict[str, Any], None]
        #         - if response_mode == "blocking": Dict[str, Any]
        self.handler : IWorkflowHandler = handler

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
            payload: Dict[str, Any] = {
                "inputs": content.data.get("inputs", {}),
                "response_mode": content.data.get("response_mode", "streaming"),
                "user": content.data.get("user"),
            }

            # Basic validation according to schema requirements
            if not isinstance(payload["inputs"], dict):
                raise ValueError("'inputs' must be an object (dict)")
            if payload["response_mode"] not in ("streaming", "blocking"):
                raise ValueError("'response_mode' must be 'streaming' or 'blocking'")
            if not isinstance(payload.get("user"), str) or not payload["user"].strip():
                raise ValueError("'user' must be a non-empty string")

            # Call handler.execute_workflow based on response_mode
            response_mode = payload["response_mode"]

            if response_mode == "streaming":
                async def _consume() -> List[Dict[str, Any]]:
                    chunks: List[Dict[str, Any]] = []
                    result = await self.handler.execute_workflow(payload)
                    # If result is an async generator/async iterator, consume it
                    if hasattr(result, "__aiter__"):
                        async for chunk in result:  # type: ignore[func-returns-value]
                            chunks.append(chunk)
                    else:
                        # Non-streaming response returned; normalize to a single chunk
                        chunks.append({"data": result})
                    return chunks

                chunks: List[Dict[str, Any]] = run_async(_consume())
                metadata.metadata.setdefault("dify_workflow", {})
                metadata.metadata["dify_workflow"]["chunks"] = chunks
                if chunks:
                    metadata.metadata["dify_workflow"]["last"] = chunks[-1]
                # echo last chunk onto content for convenience
                if chunks:
                    content.data["response_stream_last"] = chunks[-1]

                # If the last chunk indicates workflow_finish, parse and emit WorkflowFinishEvent
                finish_event_obj: Optional[WorkflowFinishEvent] = None
                last = chunks[-1] if chunks else None
                if isinstance(last, dict):
                    # Support either {'event': 'workflow_finish', 'data': {...}} or full event dict
                    if last.get("event") == "workflow_finish" and isinstance(last.get("data"), dict):
                        event_dict = {"type": "workflow_finish", "content": last["data"]}
                        try:
                            finish_event_obj = WorkflowFinishEvent.model_validate(event_dict)
                        except Exception:
                            finish_event_obj = None
                    elif last.get("type") == "workflow_finish" and isinstance(last.get("content"), dict):
                        try:
                            finish_event_obj = WorkflowFinishEvent.model_validate(last)
                        except Exception:
                            finish_event_obj = None

                if finish_event_obj is not None:
                    # store on metadata and content
                    metadata.metadata["dify_workflow"]["finish_event"] = finish_event_obj
                    content.data["workflow_finish_event"] = finish_event_obj
                    # optional handlers and emitter
                    handlers = content.data.get("handlers")
                    if isinstance(handlers, dict) and "workflow_finish" in handlers:
                        handler_fn = handlers["workflow_finish"]
                        try:
                            run_async(handler_fn(finish_event_obj))
                        except Exception:
                            pass
                    emitter = content.data.get("emitter")
                    if isinstance(emitter, EventEmitter):
                        # Send a simple success status update
                        try:
                            run_async(emitter.success_update("Workflow finished"))
                        except Exception:
                            pass
                result = {"status": "success", "mode": "streaming", "chunk_count": len(chunks)}

            else:  # blocking
                async def _call_blocking() -> Dict[str, Any]:
                    resp = await self.handler.execute_workflow(payload)
                    if not isinstance(resp, dict):
                        raise ValueError("Blocking workflow response must be a JSON object (dict)")
                    return resp

                resp: Dict[str, Any] = run_async(_call_blocking())

                # Per schema, expect fields like workflow_run_id, task_id, data
                metadata.metadata.setdefault("dify_workflow", {})
                metadata.metadata["dify_workflow"]["response"] = resp
                # surface some common fields if present
                if "workflow_run_id" in resp:
                    metadata.metadata["dify_workflow"]["workflow_run_id"] = resp["workflow_run_id"]
                if "task_id" in resp:
                    metadata.metadata["dify_workflow"]["task_id"] = resp["task_id"]
                if "data" in resp:
                    content.data["workflow_finished_data"] = resp["data"]
                content.data["response"] = resp
                result = {"status": "success", "mode": "blocking"}

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
