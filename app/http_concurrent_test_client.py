
"""Test concurrent authenticated MCP tool calls over Streamable HTTP."""

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

            print("Authenticated HTTP connection established.")
            print("Submitting two concurrent tool requests.")

            async def call_add(label, a, b):
                print(f"\nSubmitting {label}: add({a}, {b})")

                result = await session.call_tool(
                    "add",
                    arguments={"a": a, "b": b},
                )

                print(f"\n{label} response:")
                print(result)

            await asyncio.gather(
                call_add("REQUEST-1", 15, 25),
                call_add("REQUEST-2", 100, 200),
            )


if __name__ == "__main__":
    asyncio.run(main())
