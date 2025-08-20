import asyncio
import pytest

from event_management.event_emitter import EventEmitter


class AsyncCaptureEmitter:
    """Async callable that captures events passed to it."""
    def __init__(self):
        self.events = []

    async def __call__(self, event):
        # simulate minimal async work
        await asyncio.sleep(0)
        self.events.append(event)


@pytest.mark.asyncio
async def test_emit_sends_correct_payload():
    cap = AsyncCaptureEmitter()
    emitter = EventEmitter(event_emitter=cap)

    await emitter.emit(
        description="Hello",
        status="in_progress",
        done=False,
        hidden=True,
    )

    assert len(cap.events) == 1
    evt = cap.events[0]
    assert evt["type"] == "status"
    assert evt["data"]["status"] == "in_progress"
    assert evt["data"]["description"] == "Hello"
    assert evt["data"]["done"] is False
    assert evt["data"]["hidden"] is True


@pytest.mark.asyncio
async def test_progress_error_success_helpers_send_expected_status():
    cap = AsyncCaptureEmitter()
    emitter = EventEmitter(event_emitter=cap)

    await emitter.progress_update("Working")
    await emitter.error_update("Boom")
    await emitter.success_update("Done")

    assert [e["data"]["status"] for e in cap.events] == [
        "in_progress",
        "error",
        "success",
    ]
    assert [e["data"]["description"] for e in cap.events] == [
        "Working",
        "Boom",
        "Done",
    ]
    # success should be hidden True per implementation
    assert cap.events[-1]["data"]["hidden"] is True


@pytest.mark.asyncio
async def test_emit_with_no_callback_does_not_raise():
    emitter = EventEmitter(event_emitter=None)
    # Should not raise even without a callback
    await emitter.emit(description="No-op", status="ignored", done=True, hidden=False)


def test_get_closure_info_returns_dict_from_emitter_closure():
    class MockEventEmitter:
        def __init__(self, request_info_data):
            self._request_info = request_info_data

        async def __call__(self, event_data):
            return event_data

        @property
        def __closure__(self):
            class Cell:
                def __init__(self, content):
                    self.cell_contents = content
            return (Cell(self._request_info),)

    wrapped = MockEventEmitter({"chat_id": "c1", "message_id": "m1"})
    emitter = EventEmitter(event_emitter=wrapped)
    info = emitter.get_closure_info()
    assert info == {"chat_id": "c1", "message_id": "m1"}
