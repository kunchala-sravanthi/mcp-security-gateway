"""Local smoke-test client that launches the gateway as an MCP STDIO server."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT_DIR = Path(__file__).resolve().parents[1]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Call a sample tool through the approval gateway")
    parser.add_argument("--tool", choices=["add", "echo"], default="add")
    args = parser.parse_args()

    params = StdioServerParameters(
    command=sys.executable,
    args=["-m", "app.main"],
    env=None,
    cwd=str(ROOT_DIR),
)

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            listed = await session.list_tools()
            print("Tools exposed by gateway:", [tool.name for tool in listed.tools])

            if args.tool == "add":
                result = await session.call_tool("add", {"a": 4, "b": 5})
            else:
                result = await session.call_tool("echo", {"message": "Hello through MCP proxy"})

            print("Tool result:")
            for item in result.content:
                if getattr(item, "text", None):
                    print(item.text)
            if getattr(result, "isError", False):
                print("The tool call was denied or failed.")


if __name__ == "__main__":
    asyncio.run(main())
