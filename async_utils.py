import asyncio
from typing import Any

def run_async(coro: Any):
    """Run an async coroutine from a sync context safely.

    - If already inside a running event loop, spin up a temporary loop to execute the coroutine.
    - Otherwise, use asyncio.run.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
            asyncio.set_event_loop(loop)
    else:
        return asyncio.run(coro)
