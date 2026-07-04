import json
import pytest
from otm_agent import agent


@pytest.mark.asyncio
async def test_handle_resolve_entity(seeded_engine):
    agent.bind_engine(seeded_engine)
    out = await agent.handle_resolve_entity({"state": "AZ", "district": "06"})
    payload = json.loads(out["content"][0]["text"])
    assert payload["candidate"]["cand_id"] == "H2AZ06099"
    assert payload["committees"] == ["C00770886"]


@pytest.mark.asyncio
async def test_handle_funding_summary(seeded_engine):
    agent.bind_engine(seeded_engine)
    out = await agent.handle_funding_summary({"cand_id": "H2AZ06099"})
    payload = json.loads(out["content"][0]["text"])
    assert payload["total"] == "500.00"
    assert payload["donors"][0]["name"] == "DOE, JOHN"


@pytest.mark.asyncio
async def test_handle_emit_scene(seeded_engine):
    agent.bind_engine(seeded_engine)
    out = await agent.handle_emit_scene({"state": "AZ", "district": "06"})
    payload = json.loads(out["content"][0]["text"])
    assert payload["highlight"] == {"state": "AZ", "district": "06"}
    assert payload["camera"]["zoom"] == 7


@pytest.mark.asyncio
async def test_server_builds():
    # SdkMcpTool wrappers assemble into an in-process MCP server without error.
    assert agent.build_server() is not None
