"""
Handler for file uploads to Dify API.
"""
import logging
from typing import Dict, Any, Optional, BinaryIO, Union
from pathlib import Path
import aiohttp
import mimetypes

from base import MessageHandler, PipelineError

class DifyFileUploadHandler(MessageHandler[Dict[str, Any]]):
    """Handler for uploading files to Dify API."""

    def __init__(self, client: 'DifyClient'):
        """Initialize with a DifyClient instance."""
        self.client = client
        self.logger = logging.getLogger(f"DEEP_PIPELINE.{self.__class__.__name__}")

    async def upload_file(
        self,
        file_data: Union[bytes, str, BinaryIO, Path],
        user_id: str,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to Dify.

        Args:
            file_data: File data as bytes, file path, or file-like object
            user_id: User identifier
            file_name: Optional custom file name

        Returns:
            Dict containing file upload response
        """
        try:
            # Handle different file input types
            if isinstance(file_data, (str, Path)):
                file_path = Path(file_data)
                if not file_path.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                file_name = file_name or file_path.name
                with open(file_path, 'rb') as f:
                    return await self._upload_file_data(f, file_name, user_id)

            elif isinstance(file_data, bytes):
                if not file_name:
                    raise ValueError("file_name is required when passing bytes")
                # Convert bytes to file-like object
                import io
                return await self._upload_file_data(
                    io.BytesIO(file_data), 
                    file_name, 
                    user_id
                )

            elif hasattr(file_data, 'read'):  # File-like object
                if not file_name:
                    raise ValueError("file_name is required for file-like objects")
                return await self._upload_file_data(file_data, file_name, user_id)

            else:
                raise ValueError("Unsupported file_data type")

        except Exception as e:
            self.logger.error(f"File upload failed: {str(e)}", exc_info=True)
            raise PipelineError(f"File upload failed: {str(e)}") from e

    async def _upload_file_data(
        self, 
        file_obj: BinaryIO, 
        file_name: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Internal method to handle the actual file upload.
    
        Args:
            file_obj: File-like object in binary mode
            file_name: Name of the file
            user_id: User identifier

        Returns:
            Dict containing the upload response
        """
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_name)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Prepare form data
        data = aiohttp.FormData()
        data.add_field(
            'file',
            file_obj,
            filename=file_name,
            content_type=mime_type
        )
        data.add_field('user', user_id)

        # Make the request
        return await self.client.send_request(
            'files/upload',
            method='POST',
            data=data
        )

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a file upload message.

        Args:
            message: Dictionary containing 'file' and 'user' keys

        Returns:
            Upload response from Dify
        """
        return await self.upload_file(
            file_data=message['file'],
            user_id=message['user'],
            file_name=message.get('file_name')
        )
