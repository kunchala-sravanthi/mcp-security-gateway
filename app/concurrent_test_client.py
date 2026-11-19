
import asyncio
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.main"],
        env=None,
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Available tools:", [t.name for t in tools.tools])

            print("Submitting two simultaneous MCP requests...")

            results = await asyncio.gather(
                session.call_tool("add", {"a": 10, "b": 20}),
                session.call_tool("add", {"a": 100, "b": 200}),
            )

            for index, result in enumerate(results, 1):
                print(f"\nRequest {index}")

                for item in result.content:
                    if getattr(item, "text", None):
                        print("Result:", item.text)

                print("Status:", "BLOCKED" if result.isError else "COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
