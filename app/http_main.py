"""Authenticated HTTP entry point for the MCP Security Gateway."""
from __future__ import annotations

import asyncio
import hmac
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import mcp.types as types
import uvicorn
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Route

from app.approval.broker import ApprovalBroker
from app.config.settings import Settings, load_settings
from app.ui.popup import ApprovalUI

logger = logging.getLogger("mcp_gateway.http")


class BearerTokenMiddleware:
    """Protect the MCP endpoint with a bearer token."""

    def __init__(self, app, expected_token: str):
        self.app = app
        self.expected_token = expected_token.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/mcp":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"")

        supplied_token = b""
        if authorization.startswith(b"Bearer "):
            supplied_token = authorization[len(b"Bearer "):]

        if not hmac.compare_digest(supplied_token, self.expected_token):
            body = b'{"error":"Unauthorized"}'
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"www-authenticate", b"Bearer"),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": body,
            })
            logger.warning("Rejected HTTP request: missing or invalid bearer token")
            return

        await self.app(scope, receive, send)


async def run_http_server(
    settings: Settings,
    broker: ApprovalBroker,
    token: str,
) -> None:
    """Connect to upstream MCP and expose an authenticated HTTP endpoint."""

    project_root = Path(__file__).resolve().parents[1]

    params = StdioServerParameters(
        command=settings.upstream_command,
        args=settings.upstream_args,
        env=None,
        cwd=str(project_root),
    )

    logger.info("Starting upstream MCP server: %s %s", params.command, params.args)

    async with stdio_client(params) as (upstream_read, upstream_write):
        async with ClientSession(upstream_read, upstream_write) as upstream:
            await upstream.initialize()
            upstream_tools = await upstream.list_tools()

            logger.info(
                "Connected upstream; discovered %d tools",
                len(upstream_tools.tools),
            )

            server = Server("mcp-security-gateway-http")

            @server.list_tools()
            async def list_tools() -> list[types.Tool]:
                result = await upstream.list_tools()
                return result.tools

            @server.call_tool()
            async def call_tool(
                name: str,
                arguments: dict[str, Any],
            ) -> types.CallToolResult:
                logger.info("Intercepted HTTP tool call: %s", name)

                approved = await broker.request_approval(
                    server_name="configured-upstream",
                    tool_name=name,
                    arguments=arguments or {},
                )

                if not approved:
                    logger.warning("Blocked HTTP tool call: %s", name)
                    return types.CallToolResult(
                        isError=True,
                        content=[
                            types.TextContent(
                                type="text",
                                text=f"Request blocked by the user: tool '{name}' was not executed.",
                            )
                        ],
                    )

                logger.info("Approved HTTP tool call: %s", name)

                try:
                    return await upstream.call_tool(name, arguments or {})
                except Exception as exc:
                    logger.exception("Upstream execution failed: %s", name)
                    return types.CallToolResult(
                        isError=True,
                        content=[
                            types.TextContent(
                                type="text",
                                text=f"Upstream execution failed: {type(exc).__name__}",
                            )
                        ],
                    )

            session_manager = StreamableHTTPSessionManager(
                app=server,
                json_response=False,
                stateless=False,
            )

            @asynccontextmanager
            async def lifespan(app: Starlette):
                async with session_manager.run():
                    yield

            app = Starlette(
                routes=[
                    Route("/mcp", endpoint=session_manager.asgi_app),
                ],
                lifespan=lifespan,
            )

            protected_app = BearerTokenMiddleware(app, token)

            logger.info("Authenticated MCP endpoint: http://127.0.0.1:8000/mcp")

            config = uvicorn.Config(
                protected_app,
                host="127.0.0.1",
                port=8000,
                log_level="info",
            )

            await uvicorn.Server(config).serve()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    token = os.environ.get("MCP_GATEWAY_TOKEN")
    if not token:
        raise SystemExit(
            "Security error: MCP_GATEWAY_TOKEN is not configured."
        )

    try:
        settings = load_settings()
    except Exception as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    broker = ApprovalBroker(settings.approval_timeout_seconds)
    errors: list[BaseException] = []

    def run_worker() -> None:
        try:
            asyncio.run(run_http_server(settings, broker, token))
        except BaseException as exc:
            errors.append(exc)
            logger.exception("HTTP gateway stopped unexpectedly")

    worker = threading.Thread(
        target=run_worker,
        name="mcp-http-server",
        daemon=True,
    )
    worker.start()

    ui = ApprovalUI(broker)

    try:
        ui.run()
    finally:
        if worker.is_alive():
            logger.warning("Approval UI closed; HTTP worker will stop when the process exits.")

        if errors:
            logger.error("HTTP gateway error: %s", errors[-1])


if __name__ == "__main__":
    main()
