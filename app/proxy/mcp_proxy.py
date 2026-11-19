
"""Low-level MCP proxy: downstream server -> approval -> upstream MCP server."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from app.approval.broker import ApprovalBroker
from app.config.settings import Settings

logger = logging.getLogger(__name__)


async def run_proxy(settings: Settings, broker: ApprovalBroker) -> None:
    """Launch the upstream MCP server and expose its tools through this proxy."""
    project_root = Path(__file__).resolve().parents[2]

    params = StdioServerParameters(
        command=settings.upstream_command,
        args=settings.upstream_args,
        env=None,
        cwd=str(project_root),
    )

    logger.info("Starting upstream MCP server: %s %s", params.command, params.args)
    logger.info("Upstream working directory: %s", params.cwd)

    async with stdio_client(params) as (upstream_read, upstream_write):
        async with ClientSession(upstream_read, upstream_write) as upstream:
            await upstream.initialize()
            upstream_tools = await upstream.list_tools()
            logger.info(
                "Connected upstream; discovered %d tools",
                len(upstream_tools.tools),
            )

            server = Server("mcp-security-gateway")

            @server.list_tools()
            async def list_tools() -> list[types.Tool]:
                """Expose the upstream tool definitions unchanged."""
                result = await upstream.list_tools()
                return result.tools

            @server.call_tool()
            async def call_tool(
                name: str,
                arguments: dict[str, Any],
            ) -> types.CallToolResult:
                """Pause each tool invocation until the user approves or denies it."""
                logger.info("Intercepted tool call: %s", name)

                approved = await broker.request_approval(
                    server_name="configured-upstream",
                    tool_name=name,
                    arguments=arguments or {},
                )

                if not approved:
                    logger.warning("Blocked tool call: %s", name)
                    return types.CallToolResult(
                        isError=True,
                        content=[
                            types.TextContent(
                                type="text",
                                text=(
                                    f"Request blocked by the user: "
                                    f"tool '{name}' was not executed."
                                ),
                            )
                        ],
                    )

                logger.info("Approved tool call: %s", name)

                try:
                    return await upstream.call_tool(name, arguments or {})
                except Exception as exc:
                    logger.exception("Upstream tool execution failed: %s", name)
                    return types.CallToolResult(
                        isError=True,
                        content=[
                            types.TextContent(
                                type="text",
                                text=f"Upstream execution failed: {type(exc).__name__}",
                            )
                        ],
                    )

            async with mcp.server.stdio.stdio_server() as (
                read_stream,
                write_stream,
            ):
                await server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="mcp-security-gateway",
                        server_version="0.1.0",
                        capabilities=server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )
