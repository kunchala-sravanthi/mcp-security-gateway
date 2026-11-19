import asyncio

import pytest

from app.approval.broker import ApprovalBroker


@pytest.mark.asyncio
async def test_approval_resolves_true():
    broker = ApprovalBroker(timeout_seconds=2)
    task = asyncio.create_task(broker.request_approval("demo", "add", {"a": 1, "b": 2}))
    await asyncio.sleep(0)
    event, request = broker.ui_events.get_nowait()
    assert event == "request"
    broker.resolve_from_ui(request.request_id, True)
    assert await task is True


@pytest.mark.asyncio
async def test_timeout_denies():
    broker = ApprovalBroker(timeout_seconds=1)
    assert await broker.request_approval("demo", "echo", {"message": "hi"}) is False
