"""
ECS-style system for handling Dify workflow run details.
This system processes workflow run detail messages and creates corresponding components.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from message_ecs.systems import System, Entity
from message_ecs.components import (
    MessageInfo,
    MessageContent,
    MessageDelivery,
    MessageProcessing,
    MessageStatus,
    WorkflowRunDetail,
)
from async_utils import run_async


class WorkflowDetailHandlingSystem(System):
    """System that processes workflow run detail messages.
    
    Expects MessageContent.data to contain:
    - "workflow_run_id": str - The ID of the workflow run
    - Other workflow detail fields as per the API schema
    """

    def get_required_components(self) -> tuple:
        return (MessageInfo, MessageContent, MessageDelivery)

    def process_entity(self, entity: Entity, delta_time: float):
        metadata = entity.get_component(MessageInfo)
        content = entity.get_component(MessageContent)
        delivery = entity.get_component(MessageDelivery)
        processing = entity.get_component(MessageProcessing)

        if not (metadata and content and delivery):
            return

        # Skip if already processed
        if metadata.status == MessageStatus.COMPLETED:
            return

        # Skip if not a workflow detail message
        if not isinstance(content.data, dict) or 'workflow_run_id' not in content.data:
            return

        # Initialize processing if not already started
        if not processing:
            processing = MessageProcessing(processor_id=str(id(self)))
            entity.add_component(processing)

        # Mark as processing
        processing.started_at = datetime.now(timezone.utc)
        metadata.status = MessageStatus.PROCESSING
        delivery.delivery_attempts += 1

        try:
            detail_data = content.data
            
            # Create WorkflowRunDetail component from the message data
            run_detail = self._create_workflow_run_detail(detail_data)
            
            # Add the component to the entity
            entity.add_component(run_detail)
            
            # Mark as completed
            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now(timezone.utc)
            processing.processing_time = (processing.completed_at - processing.started_at).total_seconds()
            
            # Store reference in metadata
            metadata.metadata['workflow_run_detail'] = {
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'workflow_run_id': run_detail.workflow_run_id,
                'status': run_detail.status
            }
            
        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            if processing:
                processing.completed_at = datetime.now(timezone.utc)
                if processing.started_at:
                    processing.processing_time = (
                        processing.completed_at - processing.started_at
                    ).total_seconds()

    def _create_workflow_run_detail(self, data: Dict[str, Any]) -> WorkflowRunDetail:
        """Create a WorkflowRunDetail component from raw API data."""
        # Map the API response fields to our component fields
        return WorkflowRunDetail(
            workflow_run_id=data['workflow_run_id'],
            workflow_id=data.get('workflow_id'),
            status=data.get('status'),
            inputs=data.get('inputs', {}),
            outputs=data.get('outputs'),
            error=data.get('error'),
            total_steps=data.get('total_steps'),
            total_tokens=data.get('total_tokens'),
            created_at=data.get('created_at'),  # Will be converted in __post_init__
            finished_at=data.get('finished_at'),  # Will be converted in __post_init__
            elapsed_time=data.get('elapsed_time'),
            metadata={
                'raw_data': data  # Store original data for reference
            }
        )
