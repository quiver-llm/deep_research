import json
from datetime import datetime
from typing import Any, Dict, Optional, Type, Union, List

from message_ecs.components import (
    MessageInfo,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus,
    WorkflowRunDetail,
)
from message_ecs.systems import System, Entity
from async_utils import run_async


class WorkflowRunDetailSystem(System):
    """System for retrieving workflow run details.

    Handles the GET /workflows/run/{workflow_run_id} endpoint.
    """

    def __init__(self, handler: Any):
        # handler must expose an async API:
        #   - async def get_workflow_run_detail(self, workflow_run_id: str) -> Dict[str, Any]
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

        # Skip if not a workflow run detail request
        if not (isinstance(content.data, dict) and 'workflow_run_id' in content.data):
            return

        if not processing:
            processing = MessageProcessing(processor_id=str(id(self)))
            entity.add_component(processing)

        processing.started_at = datetime.now()
        metadata.status = MessageStatus.PROCESSING
        delivery.delivery_attempts += 1

        try:
            workflow_run_id = content.data['workflow_run_id']

            # Call the handler to get workflow run details
            async def _get_details() -> Dict[str, Any]:
                return await self.handler.get_workflow_run_detail(workflow_run_id)

            details = run_async(_get_details())

            # Create WorkflowRunDetail component
            run_detail = WorkflowRunDetail(
                workflow_run_id=workflow_run_id,
                workflow_id=details.get('workflow_id'),
                status=details.get('status'),
                inputs=details.get('inputs'),
                outputs=details.get('outputs'),
                error=details.get('error'),
                total_steps=details.get('total_steps'),
                total_tokens=details.get('total_tokens'),
                created_at=details.get('created_at'),
                finished_at=details.get('finished_at'),
                elapsed_time=details.get('elapsed_time'),
                metadata=details.get('metadata', {})
            )

            entity.add_component(run_detail)

            # Update message metadata
            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now()
            processing.processing_time = (processing.completed_at - processing.started_at).total_seconds()

            # Store the response in metadata for reference
            metadata.metadata['workflow_run_detail'] = {
                'retrieved_at': datetime.now().isoformat(),
                'workflow_run_id': workflow_run_id,
                'status': run_detail.status
            }

        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            if processing:
                processing.completed_at = datetime.now()
                if processing.started_at:
                    processing.processing_time = (processing.completed_at - processing.started_at).total_seconds()
            raise
