"""
System for handling file uploads to Dify API.
"""
from datetime import datetime
from message_ecs.systems import System, Entity
from message_ecs.components import (
    MessageInfo, MessageContent, MessageDelivery, MessageProcessing, MessageStatus
)
from dify_file_upload_handler import DifyFileUploadHandler
from async_utils import run_async

class FileUploadSystem(System):
    """System for uploading files to Dify API."""

    def __init__(self, handler: 'DifyFileUploadHandler'):
        self.handler = handler

    def get_required_components(self) -> tuple:
        return (MessageInfo, MessageContent, MessageDelivery, MessageProcessing)

    def process_entity(self, entity: Entity, delta_time: float):
        metadata = entity.get_component(MessageInfo)
        content = entity.get_component(MessageContent)
        delivery = entity.get_component(MessageDelivery)
        processing = entity.get_component(MessageProcessing)

        # Skip if already completed or already started
        if metadata.status == MessageStatus.COMPLETED:
            return

        # Ensure processing component exists
        if not processing:
            processing = MessageProcessing(processor_id=str(id(self)))
            entity.add_component(processing)

        # Mark as processing and increment attempt count
        processing.started_at = datetime.now()
        metadata.status = MessageStatus.PROCESSING
        delivery.delivery_attempts += 1

        try:
            # Process the file upload
            # Accept both new 'files' (list) and legacy 'file' (str or list) keys
            files = content.data.get("files")
            if files is None:
                legacy = content.data.get("file")
                if isinstance(legacy, list):
                    files = legacy
                elif legacy is not None:
                    files = [legacy]
                else:
                    files = []

            user_id = content.data.get("user")

            if not files or not user_id:
                raise ValueError("Missing required file data or user ID")

            # Initialize metadata if not exists
            if not metadata.metadata:
                metadata.metadata = {}

            # Upload the file (handler method is async)
            responses = []
            for file in files:
                responses.append(run_async(
                    self.handler.upload_file(
                        file_data=file,
                        user_id=user_id
                    )
                ))

            # Store response in metadata
            metadata.metadata["file_upload"] = responses
            content.data["uploaded_file"] = responses

            # Update status
            metadata.status = MessageStatus.COMPLETED
            processing.completed_at = datetime.now()
            processing.processing_time = (
                processing.completed_at - processing.started_at
            ).total_seconds()

            return responses
        except Exception as e:
            metadata.status = MessageStatus.FAILED
            metadata.error = str(e)
            metadata.retry_count += 1
            return {"status": "failed", "error": str(e)}
