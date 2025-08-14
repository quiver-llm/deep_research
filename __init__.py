"""
Dify Pipeline Integration for OpenWebUI.

This module provides the main entry point for the Dify pipeline integration with OpenWebUI.
"""
import logging
from typing import Any, Dict, Optional, AsyncGenerator

from fastapi import Request
from pydantic import BaseModel

from .pipeline import ResearchPipeline, create_pipeline
from .config import get_pipeline_config, get_settings
from .base import EventEmitter
from .event_management.event_handler_registry import IEventHandler

# Initialize logging
settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DEEP_PIPELINE")

# Global pipeline instance
_pipeline: Optional[ResearchPipeline] = None


def get_pipeline() -> ResearchPipeline:
    """Get or create the pipeline instance."""
    global _pipeline
    if _pipeline is None:
        config = get_pipeline_config()
        _pipeline = create_pipeline(config)
    return _pipeline


class ToolInput(BaseModel):
    """Input model for the tool."""
    query: str = ""
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    files: Optional[list] = None


async def deep_research(
    request: Request,
    body: Dict[str, Any],
    user: Dict[str, Any],
    event_emitter: Optional[EventEmitter] = None,
    **kwargs
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Process a research request using the Dify pipeline.
    
    This is the main entry point called by OpenWebUI when the tool is invoked.
    
    Args:
        request: The FastAPI request object
        body: The request body containing the message and metadata
        user: The user making the request
        event_emitter: Optional event emitter for status updates
        **kwargs: Additional keyword arguments
        
    Yields:
        Response chunks as they are generated
    """
    logger.info("Starting deep research pipeline")
    
    try:
        # Get the pipeline instance
        pipeline = get_pipeline()
        
        # Process the request through the pipeline
        async for chunk in pipeline.process_request(
            request=request,
            body=body,
            user=user,
            event_emitter=event_emitter
        ):
            yield chunk
            
    except Exception as e:
        logger.error(f"Error in deep research pipeline: {str(e)}", exc_info=True)
        yield {
            "role": "assistant",
            "content": "An error occurred while processing your request. Please try again later.",
            "metadata": {"error": str(e)}
        }


# Register the tool with OpenWebUI
__all__ = ["deep_research", "ToolInput"]
