# /home/litec/dev/open-webui/tools/deep_research/event_management/handlers.py

from typing import Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod
import aiohttp

# Relative import from the same package:
from .event_handler_registry import IEventHandler

class OpenWebUIEventHandler(IEventHandler):
    def __init__(self, base_url: str, user_id: str):
        self.base_url = base_url
        self.user_id = user_id
        self.config = {"base_url": base_url, "user_id": user_id}

    async def handle(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"status": "OpenWebUI handled", "user_id": self.user_id}

class AnotherEventHandler(IEventHandler):
    def __init__(self, some_param: str):
        self.some_param = some_param
        self.config = {"some_param": some_param}

    async def handle(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"status": "Another handled", "param": self.some_param}

class IWorkflowHandler(ABC):
    """Interface for workflow execution handlers."""

    @abstractmethod
    async def execute_workflow(self, payload: Dict[str, Any]):
        """Execute a workflow request.

        Implementations should accept a payload with keys like
        'inputs', 'response_mode', and 'user', and either return a
        JSON-like dict (blocking) or an async generator yielding
        dict chunks (streaming).
        """
        pass


class DifyWorkflowHandler(IWorkflowHandler):
    """Minimal client to execute Dify workflows via POST /workflows/run.

    Usage with WorkflowRunSystem:
      handler = DifyWorkflowHandler(api_base_url, api_key)
      await handler.execute_workflow(payload)

    Behavior:
      - If payload["response_mode"] == "streaming": performs a blocking request
        and yields a single final-like event chunk. This mirrors the fallback
        strategy used elsewhere in the project.
      - If "blocking": returns the JSON dict response directly.
    """

    def __init__(self, api_base_url: str, api_key: str, timeout: int = 30):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def execute_workflow(self, payload: Dict[str, Any]):
        """Execute workflow per dify_execute_workflow.md schema.

        Expects payload keys:
          - inputs: Dict[str, Any]
          - response_mode: "streaming" | "blocking"
          - user: str

        Returns:
          - streaming: AsyncGenerator yielding one final 'workflow_finish' event dict
          - blocking: Dict[str, Any] JSON response
        """
        url = f"{self.api_base_url}/workflows/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        mode = payload.get("response_mode", "streaming")
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            if mode == "streaming":
                # Fallback: do a blocking request and yield one final-like chunk
                blocking_payload = dict(payload)
                blocking_payload["response_mode"] = "blocking"
                async with session.post(url, headers=headers, json=blocking_payload) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                async def _gen() -> AsyncGenerator[Dict[str, Any], None]:
                    # Try to wrap response as a proper workflow_finish event
                    if isinstance(data, dict) and "data" in data:
                        yield {"type": "workflow_finish", "content": data["data"]}
                    else:
                        yield {"event": "workflow_finish", "data": data}
                return _gen()
            else:
                # blocking
                async with session.post(url, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    return await resp.json()