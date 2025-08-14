"""
Main pipeline for processing messages between OpenWebUI and Dify.
"""
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator

from fastapi import Request
from pydantic import BaseModel, Field
from base import ServiceBase, PipelineError
from dify_client import DifyClient, DifyMessageHandler
from openwebui_service import OpenWebUIService


class PipelineConfig(BaseModel):
    """Configuration for the research pipeline."""
    dify_base_url: str = Field(..., description="Base URL for the Dify API")
    dify_api_key: str = Field(..., description="API key for Dify")
    openwebui_base_url: str = Field(
        default="http://localhost:3000",
        description="Base URL for the OpenWebUI API"
    )
    openwebui_api_key: str = Field(
        default="",
        description="API key for OpenWebUI (if required)"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug logging"
    )


class ResearchPipeline(ServiceBase):
    """Orchestrates the research pipeline between OpenWebUI and Dify."""
    
    def __init__(self, config: PipelineConfig):
        """Initialize the research pipeline."""
        super().__init__(debug=config.debug)
        self.config = config
        
        # Initialize services
        self.dify_client = DifyClient(
            base_url=config.dify_base_url,
            api_key=config.dify_api_key,
            debug=config.debug
        )
        
        self.dify_handler = DifyMessageHandler(self.dify_client)
        self.webui_service = OpenWebUIService(
            base_url=config.openwebui_base_url,
            api_key=config.openwebui_api_key,
            debug=config.debug
        )
        
        self.logger = logging.getLogger(f"DEEP_PIPELINE.{self.__class__.__name__}")
    
    async def process_request(
        self,
        request: Request,
        body: Dict[str, Any],
        user: Dict[str, Any],
        event_emitter: Optional[Any] = None,
        raise_error: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process an incoming request through the pipeline.

        Args:
            request: The FastAPI request object.
            body: The request body containing messages and metadata.
            user: A dictionary containing user information.
            event_emitter: Optional event emitter for status updates.
            raise_error: Whether to raise an error if no messages are provided.

        Yields:
            The processed response chunks formatted for OpenWebUI.
        """
        try:
            context = await self.webui_service.get_chat_context(request)
            self.logger.debug(f"Processing request with context: {context}")
            
            # Extract and validate messages
            messages = body.get("messages", [])
            if not messages and raise_error:
                raise PipelineError("No messages provided in request")
            
            # Get the last user message
            last_message = next(
                (msg for msg in reversed(messages) if msg.get("role") == "user"),
                None
            )
            
            if not last_message:
                raise PipelineError("No user message found in the conversation")
            
            # Process any files if present
            files = []
            if "files" in body:
                files = await self.webui_service.process_files(body["files"])
            
            # Prepare the message for Dify
            dify_message = {
                "content": last_message.get("content", ""),
                "conversation_id": context.get("chat_id"),
                "user": user.get("email") or f"user-{user.get('id', 'anonymous')}",
                "files": files,
                "response_mode": "streaming"  # or "blocking" for non-streaming
            }
            
            # Process the message through Dify
            async for chunk in await self.dify_handler.process_message(dify_message):
                # Format the response for OpenWebUI
                response = self.webui_service.format_response(
                    content=chunk.get("content", ""),
                    metadata=chunk.get("metadata", {})
                )
                yield response
                
        except PipelineError as e:
            self.logger.error(f"Pipeline error: {str(e)}", exc_info=self.config.debug)
            if raise_error:
                # In test/dev flows, allow caller to assert on specific errors
                raise
            error_response = await self.webui_service.handle_error(e, event_emitter)
            yield error_response
            
        except Exception as e:
            self.logger.error(
                f"Unexpected error in pipeline: {str(e)}",
                exc_info=self.config.debug
            )
            error_response = await self.webui_service.handle_error(
                PipelineError("An unexpected error occurred"),
                event_emitter
            )
            yield error_response
    
    async def close(self) -> None:
        """Clean up resources."""
        await self.dify_client.close()
    
    def __del__(self):
        """Ensure resources are cleaned up."""
        if hasattr(self, 'dify_client') and hasattr(self.dify_client, 'close'):
            # Don't call __del__ directly, just close if available
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(self.dify_client.close())
            except RuntimeError:
                # No running event loop (e.g., during interpreter shutdown or sync tests)
                # Best-effort: avoid raising noisy errors. aiohttp will clean up on exit.
                pass
            except Exception:
                # Never raise from destructor
                pass


def create_pipeline(config: Optional[Dict[str, Any]] = None) -> ResearchPipeline:
    """Create and configure a new research pipeline instance."""
    config = config or {}
    pipeline_config = PipelineConfig(**config)
    return ResearchPipeline(pipeline_config)
