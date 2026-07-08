import json
from sqlalchemy import Engine
from mcp.server.lowlevel import Server
import mcp.types as types
from otm_agent.registry import tool_specs, get_spec

# A standalone MCP server exposing the FEC oracle tools. Any MCP client, or the
# in-process runtime loop, can consume it.
# Tool definitions come straight from the shared registry, so schemas and
# handlers are never duplicated.


def build_mcp_server(engine: Engine) -> Server:
    server = Server("otm")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(name=s.name, description=s.description,
                       inputSchema=s.input_schema)
            for s in tool_specs()
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        payload = get_spec(name).handler(engine, arguments)
        return [types.TextContent(type="text", text=json.dumps(payload))]

    return server


def main() -> None:
    import anyio
    from mcp.server.stdio import stdio_server
    from otm_data.db import get_engine

    server = build_mcp_server(get_engine())

    async def _run() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    anyio.run(_run)


if __name__ == "__main__":
    main()
