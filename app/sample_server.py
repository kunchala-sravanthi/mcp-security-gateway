"""Safe sample MCP server used to validate the gateway."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Assessment Demo MCP Server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers. Safe demonstration tool."""
    return a + b


@mcp.tool()
def echo(message: str) -> str:
    """Return the supplied message without changing it."""
    return f"Echo: {message}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
