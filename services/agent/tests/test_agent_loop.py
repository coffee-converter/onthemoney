import os
import pytest
from otm_agent import agent


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"),
                    reason="needs ANTHROPIC_API_KEY for the model path")
@pytest.mark.asyncio
async def test_run_agent_reports_and_steers(seeded_engine):
    agent.bind_engine(seeded_engine)
    trace = await agent.run_agent("Who funds the representative in AZ-06?")
    tool_names = [s["name"] for s in trace if s["type"] == "tool_use"]
    assert "mcp__otm__resolve_entity" in tool_names
    assert "mcp__otm__emit_scene" in tool_names
    final = " ".join(s.get("text", "") for s in trace if s["type"] == "result")
    assert "500.00" in final
