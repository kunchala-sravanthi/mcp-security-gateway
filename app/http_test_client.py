
"""Test the authenticated MCP gateway over Streamable HTTP."""
import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    url = "http://127.0.0.1:8000/mcp"

    token = os.environ.get("MCP_GATEWAY_TOKEN")
    if not token:
        raise RuntimeError("MCP_GATEWAY_TOKEN environment variable is missing.")

    headers = {
        "Authorization": f"Bearer {token}"
    }

    async with streamablehttp_client(
        url,
        headers=headers,
    ) as (read_stream, write_stream, _):

        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            result = await session.list_tools()

            print("Tools exposed by authenticated HTTP gateway:")
            for tool in result.tools:
                print(f" - {tool.name}: {tool.description}")

            print("\nCalling add(15, 25)...")
            print("Check the approval popup.")

            response = await session.call_tool(
                "add",
                arguments={"a": 15, "b": 25},
            )

            print("\nTool response:")
            print(response)


if __name__ == "__main__":
    asyncio.run(main())
