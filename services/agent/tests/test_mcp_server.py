import json
import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect
from otm_agent.mcp_server import build_mcp_server


@pytest.mark.asyncio
async def test_mcp_lists_tools(seeded_engine):
    server = build_mcp_server(seeded_engine)
    async with connect(server) as client:
        result = await client.list_tools()
    names = {t.name for t in result.tools}
    assert names == {"resolve_entity", "funding_summary", "emit_scene"}


@pytest.mark.asyncio
async def test_mcp_calls_tool_over_protocol(seeded_engine):
    server = build_mcp_server(seeded_engine)
    async with connect(server) as client:
        result = await client.call_tool("resolve_entity",
                                        {"state": "AZ", "district": "06"})
    payload = json.loads(result.content[0].text)
    assert payload["found"] is True
    assert payload["candidate"]["cand_id"] == "H2AZ06099"
    assert payload["committees"] == ["C00770886"]
