"""
Tests for the ResearchPipeline class in pipeline.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from typing import AsyncGenerator
from deep_research.pipeline import ResearchPipeline, PipelineConfig, PipelineError

class TestResearchPipeline:
    """Test suite for ResearchPipeline class"""
    
    @pytest.fixture
    def mock_config(self) -> PipelineConfig:
        """Create a mock PipelineConfig for testing"""
        return PipelineConfig(
            dify_base_url="https://api.dify.ai",
            dify_api_key="test-api-key",
            openwebui_base_url="http://localhost:3000",
            openwebui_api_key="test-webui-key",
            debug=True
        )
    
    @pytest.fixture
    def mock_dify_client(self) -> MagicMock:
        """Create a mock DifyClient"""
        return MagicMock()
    
    @pytest.fixture
    def mock_dify_handler(self) -> MagicMock:
        """Create a mock DifyMessageHandler"""
        handler = MagicMock()
        
        # Return a true async iterator (not a coroutine)
        async def mock_process_message(*args, **kwargs):
            yield {"content": "Test response 1", "metadata": {}}
            yield {"content": "Test response 2", "metadata": {}}
        
        handler.process_message = AsyncMock(side_effect=mock_process_message)
        return handler
    
    @pytest.fixture
    def mock_webui_service(self) -> MagicMock:
        """Create a mock OpenWebUIService"""
        service = MagicMock()
        service.get_chat_context = AsyncMock(return_value={"chat_id": "test-chat-id"})
        service.process_files = AsyncMock(return_value=[])
        service.format_response = lambda content, metadata: {"content": content, "metadata": metadata}
        service.handle_error = AsyncMock(return_value={"error": "Test error"})
        return service
    
    @pytest.fixture
    def pipeline(
        self, 
        mock_config: PipelineConfig,
        mock_dify_client: MagicMock,
        mock_dify_handler: MagicMock,
        mock_webui_service: MagicMock
    ) -> ResearchPipeline:
        """Create a ResearchPipeline instance with mocked dependencies"""
        with patch('deep_research.pipeline.DifyClient', return_value=mock_dify_client), \
             patch('deep_research.pipeline.DifyMessageHandler', return_value=mock_dify_handler), \
             patch('deep_research.pipeline.OpenWebUIService', return_value=mock_webui_service):
            return ResearchPipeline(mock_config)
    
    @pytest.mark.asyncio
    async def test_process_request_success(self, pipeline: ResearchPipeline):
        """Test successful message processing"""
        # Setup test data
        request = MagicMock(spec=Request)
        body = {
            "messages": [
                {"role": "user", "content": "Test message"}
            ]
        }
        user = {"email": "test@example.com", "id": "123"}
        
        # Call the method
        responses = []
        async for response in pipeline.process_request(request, body, user):
            responses.append(response)
        
        # Assertions
        assert len(responses) == 2
        assert responses[0]["content"] == "Test response 1"
        assert responses[1]["content"] == "Test response 2"
        
        # Verify service interactions
        pipeline.webui_service.get_chat_context.assert_awaited_once_with(request)
        pipeline.dify_handler.process_message.assert_awaited_once_with({
            "content": "Test message",
            "conversation_id": "test-chat-id",
            "user": "test@example.com",
            "files": [],
            "response_mode": "streaming"
        })
    
    @pytest.mark.asyncio
    async def test_process_request_no_messages(self, pipeline: ResearchPipeline):
        """Test handling of request with no messages"""
        request = MagicMock(spec=Request)
        body = {"messages": []}  # Empty messages list
        user = {"email": "test@example.com", "id": "123"}
        messages = []
        # Call the method and verify it raises PipelineError
        with pytest.raises(PipelineError, match="No messages provided"):
            async for message in pipeline.process_request(request, body, user, raise_error=True):
                messages.append(message)
        assert len(messages) == 0
        
        body = {"messages": [{"role": "system", "content": "Test system message"}]}
        with pytest.raises(PipelineError, match="No user message found in the conversation"):
            async for message in pipeline.process_request(request, body, user, raise_error=True):
                messages.append(message)
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_process_request_with_files(self, pipeline: ResearchPipeline):
        """Test message processing with file attachments"""
        # Setup test data with files
        request = MagicMock(spec=Request)
        body = {
            "messages": [
                {"role": "user", "content": "Test message with files"}
            ],
            "files": ["file1.txt", "file2.pdf"]
        }
        user = {"email": "test@example.com", "id": "123"}
        
        # Mock file processing
        pipeline.webui_service.process_files.return_value = [
            {"name": "file1.txt", "content": "Test content"},
            {"name": "file2.pdf", "content": b"%PDF-test"}
        ]
        
        # Call the method
        responses = []
        async for response in pipeline.process_request(request, body, user):
            responses.append(response)
        
        # Verify file processing was called
        pipeline.webui_service.process_files.assert_awaited_once()
        
        # Verify process_message was called with files
        pipeline.dify_handler.process_message.assert_awaited_once()
        call_args = pipeline.dify_handler.process_message.call_args[0][0]
        assert call_args["content"] == "Test message with files"
        assert len(call_args["files"]) == 2
    
    @pytest.mark.asyncio
    async def test_process_request_error_handling(self, pipeline: ResearchPipeline):
        """Test error handling during request processing"""
        # Setup test with error
        request = MagicMock(spec=Request)
        body = {"messages": [{"role": "user", "content": "Test error"}]}
        user = {"email": "test@example.com", "id": "123"}
        
        # Make process_message raise an exception
        error = Exception("Test error")
        pipeline.dify_handler.process_message = AsyncMock(side_effect=error, )
        
        # Call the method and collect responses
        responses = []
        async for response in pipeline.process_request(request, body, user):
            responses.append(response)
        
        # Verify error response
        assert len(responses) == 1
        assert responses[0]["error"] == "Test error"


# Helper class for async generators in tests
class AsyncGeneratorWrapper:
    """Helper class to wrap a list as an async generator correctly."""
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        # Must return an async iterator; returning a coroutine causes the TypeError seen.
        async def _gen():
            for item in self.items:
                yield item
        return _gen()
