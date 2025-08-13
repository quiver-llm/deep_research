"""
OpenWebUI service implementation for handling frontend interactions.
"""
import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
from urllib.parse import urljoin

from fastapi import Request
from pydantic import BaseModel

from deep_research.base import ServiceBase, PipelineError


class ChatMessage(BaseModel):
    """Model for chat messages."""
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class OpenWebUIService(ServiceBase):
    """Service for handling OpenWebUI interactions."""
    
    def __init__(
        self, 
        base_url: str = "http://localhost:3000",
        api_key: str = "",
        debug: bool = False
    ):
        """Initialize the OpenWebUI service.
        
        Args:
            base_url: Base URL of the OpenWebUI API
            api_key: API key for authentication
            debug: Enable debug logging
        """
        super().__init__(debug=debug)
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.logger = logging.getLogger(f"DEEP_PIPELINE.{self.__class__.__name__}")
    
    async def get_chat_context(self, request: Request) -> Dict[str, Any]:
        """Extract chat context from the request."""
        try:
            # Get chat ID from URL parameters
            chat_id = request.path_params.get("chat_id")
            
            # Get user information from request state
            user_id = getattr(request.state, "user_id", "anonymous")
            
            return {
                "chat_id": chat_id,
                "user_id": user_id,
                "headers": dict(request.headers)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get chat context: {str(e)}", exc_info=self.debug)
            return {"chat_id": None, "user_id": "anonymous"}
    
    def format_messages(
        self, 
        messages: List[Dict[str, Any]]
    ) -> List[ChatMessage]:
        """Format messages for processing."""
        formatted = []
        
        for msg in messages:
            try:
                # Ensure required fields are present
                if not all(k in msg for k in ["role", "content"]):
                    self.logger.warning("Skipping invalid message format")
                    continue
                
                formatted_msg = ChatMessage(
                    role=msg["role"],
                    content=msg["content"],
                    metadata=msg.get("metadata", {})
                )
                formatted.append(formatted_msg)
                
            except Exception as e:
                self.logger.error(f"Error formatting message: {str(e)}", exc_info=self.debug)
        
        return formatted
    
    async def process_files(
        self, 
        files: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process uploaded files.
        
        Args:
            files: List of file objects with 'id', 'name', 'type', 'size', etc.
            
        Returns:
            List of processed file information
        """
        processed_files = []
        
        for file in files:
            try:
                file_info = {
                    "id": file.get("id"),
                    "name": file.get("name", "unnamed"),
                    "type": file.get("type", "application/octet-stream"),
                    "size": file.get("size", 0),
                    "metadata": file.get("metadata", {})
                }
                processed_files.append(file_info)
                
            except Exception as e:
                self.logger.error(f"Error processing file: {str(e)}", exc_info=self.debug)
        
        return processed_files
    
    def format_response(
        self, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format a response for the OpenWebUI frontend."""
        return {
            "role": "assistant",
            "content": content,
            "metadata": metadata or {}
        }
    
    async def handle_error(
        self, 
        error: Exception,
        event_emitter: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Handle errors and format error responses."""
        error_msg = f"An error occurred: {str(error)}"
        self.logger.error(error_msg, exc_info=self.debug)
        
        if event_emitter and hasattr(event_emitter, 'error_update'):
            await event_emitter.error_update(error_msg)
        
        return self.format_response(
            "I'm sorry, but I encountered an error processing your request. "
            "Please try again later.",
            {"error": error_msg}
        )
