"""Thread-safe bridge between async MCP handlers and the Tkinter UI."""
from __future__ import annotations

import asyncio
import logging
import queue
import uuid
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ApprovalRequest:
    request_id: str
    server_name: str
    tool_name: str
    arguments: dict[str, Any]
    future: asyncio.Future[bool]
    loop: asyncio.AbstractEventLoop


class ApprovalBroker:
    """Queues approval requests and waits for a user's explicit decision."""

    def __init__(self, timeout_seconds: int = 120) -> None:
        self.timeout_seconds = timeout_seconds
        self.ui_events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._pending: dict[str, ApprovalRequest] = {}

    async def request_approval(
        self, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> bool:
        loop = asyncio.get_running_loop()
        request_id = str(uuid.uuid4())
        future: asyncio.Future[bool] = loop.create_future()
        request = ApprovalRequest(
            request_id=request_id,
            server_name=server_name,
            tool_name=tool_name,
            arguments=arguments or {},
            future=future,
            loop=loop,
        )
        self._pending[request_id] = request
        self.ui_events.put(("request", request))
        logger.info("Approval requested: id=%s tool=%s", request_id, tool_name)

        try:
            # Fail closed: timeout means deny, never silently approve.
            return await asyncio.wait_for(future, timeout=self.timeout_seconds)
        except asyncio.TimeoutError:
            logger.warning("Approval timed out; denying request %s", request_id)
            return False
        finally:
            self._pending.pop(request_id, None)
            self.ui_events.put(("resolved", request_id))

    def deny_all(self) -> None:
        """Fail closed for every pending request during UI shutdown."""
        for request_id in list(self._pending):
            self.resolve_from_ui(request_id, False)

    def resolve_from_ui(self, request_id: str, allowed: bool) -> None:
        """Called by the UI thread; schedules completion on the asyncio loop."""
        request = self._pending.get(request_id)
        if request is None or request.future.done():
            return
        request.loop.call_soon_threadsafe(self._complete, request, allowed)

    @staticmethod
    def _complete(request: ApprovalRequest, allowed: bool) -> None:
        if not request.future.done():
            request.future.set_result(allowed)
