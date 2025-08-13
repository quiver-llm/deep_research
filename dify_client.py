"""
Dify API client and message handler implementation.
"""
import json
import aiohttp
import logging
from typing import Any, Dict, Optional, AsyncGenerator
from urllib.parse import urljoin

from base import APIClient, MessageHandler, PipelineError

class DifyClient(APIClient):
    """Client for interacting with the Dify API."""
    
    def __init__(
        self, 
        base_url: str, 
        api_key: str, 
        user: str = "",
        timeout: int = 30,
        debug: bool = False
    ):
        """Initialize the Dify client."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.user = user
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(f"DEEP_PIPELINE.{self.__class__.__name__}")
        self.debug = debug
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
    
    async def _ensure_session(self) -> None:
        """Ensure the client session is initialized."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def send_request(
        self, 
        endpoint: str, 
        method: str = "GET",
        **kwargs
    ) -> Dict[str, Any]:
        """Send a request to the Dify API."""
        await self._ensure_session()
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.user:
            headers["X-User-Email"] = self.user
        
        try:
            self.logger.debug(f"Sending {method} request to {url}")
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            error_msg = f"Dify API request failed: {str(e)}"
            self.logger.error(error_msg, exc_info=self.debug)
            raise PipelineError(error_msg) from e
    
    async def close(self) -> None:
        """Close the client session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Ensure session is closed when the object is destroyed."""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            if self.session._connector_owner:
                self.session._connector._close()
            self.session._connector = None


class DifyMessageHandler(MessageHandler[AsyncGenerator[Dict[str, Any], None]]):
    """Handler for processing messages with the Dify API."""
    
    def __init__(self, client: DifyClient):
        """Initialize with a DifyClient instance."""
        self.client = client
        self.logger = logging.getLogger(f"DEEP_PIPELINE.{self.__class__.__name__}")
    
    async def process_message(
        self, 
        message: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a message using the Dify API."""
        try:
            payload = self._build_payload(message)
            response_mode = message.get('response_mode', 'streaming')
            
            if response_mode == 'streaming':
                async for chunk in self._stream_response(payload):
                    yield chunk
            else:
                response = await self._send_blocking_request(payload)
                yield self._format_response(response)
                
        except Exception as e:
            self.logger.error(f"Message processing failed: {str(e)}", exc_info=True)
            raise PipelineError(f"Failed to process message: {str(e)}") from e
    
    def _build_payload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Build the payload for the Dify API request."""
        return {
            "inputs": {},
            "query": message.get("content", ""),
            "response_mode": message.get("response_mode", "streaming"),
            "user": message.get("user", self.client.user or "anonymous"),
            "conversation_id": message.get("conversation_id"),
            "files": message.get("files", [])
        }
    
    async def _stream_response(
        self, 
        payload: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the response from Dify API.
        Temporary fallback implementation that performs a blocking request
        and yields a single formatted chunk. Replace with real streaming
        implementation (e.g., SSE) when available.
        """
        # Fallback to blocking call and yield one chunk
        response = await self._send_blocking_request(payload)
        yield self._format_response(response)
    
    async def _send_blocking_request(
        self, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a blocking request to Dify API."""
        payload["response_mode"] = "blocking"
        return await self.client.send_request(
            "chat-messages",
            method="POST",
            json=payload
        )
    
    def _format_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Format the Dify API response."""
        return {
            "content": response.get("answer", ""),
            "metadata": {
                "sources": response.get("sources", []),
                "model": response.get("model", "unknown"),
                "conversation_id": response.get("conversation_id")
            }
        }
