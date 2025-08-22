"""
Base classes and interfaces for the Dify pipeline refactoring.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, AsyncGenerator, Callable, TypeVar, Generic


class IComponent(ABC):
    """Base interface for all ECS components.

    All component classes should inherit from this class to ensure they can be
    properly identified and handled by the ECS framework.
    """
    pass

T = TypeVar('T')

class MessageHandler(ABC, Generic[T]):
    """Abstract base class for message handlers."""

    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> T:
        """Process a message and return the result."""
        pass

class APIClient(ABC):
    """Abstract base class for API clients."""

    @abstractmethod
    async def send_request(
        self,
        endpoint: str,
        method: str = "GET",
        **kwargs
    ) -> Dict[str, Any]:
        """Send an HTTP request to the API."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close any resources used by the client."""
        pass

class ServiceBase(ABC):
    """Base class for services with common functionality."""

    def __init__(self, debug: bool = False):
        """Initialize the service with debug mode."""
        self.debug = debug
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up logging for the service."""
        self.logger = logging.getLogger(f"DEEP_PIPELINE.{self.__class__.__name__}")
        level = logging.DEBUG if self.debug else logging.INFO
        self.logger.setLevel(level)

        # Only add handlers if none exist
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

class EventEmitter:
    """Simple event emitter for pipeline events."""

    def __init__(self, callback: Optional[Callable[[Dict[str, Any]], Any]] = None):
        self.callback = callback or (lambda x: None)

    async def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event."""
        event = {"type": event_type, "data": data}
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback(event)
        else:
            self.callback(event)

class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass

# Import logging at the module level
import logging
import asyncio
