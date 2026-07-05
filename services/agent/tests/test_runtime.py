import json
import os
import pytest
from otm_agent.runtime import run_query, stream_query, anthropic_tools, AgentResult


class _Blk:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Resp:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class _Messages:
    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._script.pop(0)


class _FakeClient:
    def __init__(self, script):
        self.messages = _Messages(script)


def test_anthropic_tools_shape():
    tools = anthropic_tools()
    assert {"resolve_entity", "funding_summary", "emit_scene",
            "industry_breakdown", "top_employers"} <= {t["name"] for t in tools}
    assert all(t["input_schema"]["type"] == "object" for t in tools)


def test_run_query_threads_real_oracle_data(seeded_engine):
    script = [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("tool_use", [_Blk(type="tool_use", id="t2", name="emit_scene",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text",
                                text="Ciscomani reported 500.00 in itemized receipts for 2024.")]),
    ]
    client = _FakeClient(script)
    result = run_query(client, "Who funds the representative in AZ-06?", seeded_engine)

    assert isinstance(result, AgentResult)
    names = [s["name"] for s in result.trace if s["type"] == "tool_use"]
    assert names == ["resolve_entity", "emit_scene"]
    assert "500.00" in result.final_text

    results = [s for s in result.trace if s["type"] == "tool_result"]
    assert any(r["name"] == "resolve_entity"
               and r["payload"].get("candidate", {}).get("cand_id") == "H2AZ06099"
               for r in results)

    # The second model call must have received the resolve_entity tool_result
    # carrying real oracle data, proving the handler dispatched against Postgres.
    second_call_messages = client.messages.calls[1]["messages"]
    tool_result_blocks = [b for m in second_call_messages
                          if m["role"] == "user" and isinstance(m["content"], list)
                          for b in m["content"]
                          if isinstance(b, dict) and b.get("type") == "tool_result"]
    joined = " ".join(b["content"] for b in tool_result_blocks)
    assert "H2AZ06099" in joined


def test_stream_query_yields_steps_incrementally(seeded_engine):
    script = [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text", text="Reported 500.00 for 2024.")]),
    ]
    steps = list(stream_query(_FakeClient(script),
                              "Who funds AZ-06?", seeded_engine))
    types = [s["type"] for s in steps]
    assert types[0] == "tool_use"
    assert types[1] == "tool_result"
    assert types[-1] == "result"
    assert steps[-1]["text"] == "Reported 500.00 for 2024."


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"),
                    reason="needs ANTHROPIC_API_KEY for the model path")
def test_run_query_real_model(seeded_engine):
    from anthropic import Anthropic
    result = run_query(Anthropic(), "Who funds the representative in AZ-06?",
                       seeded_engine)
    names = [s["name"] for s in result.trace if s["type"] == "tool_use"]
    assert "resolve_entity" in names
    assert "500.00" in result.final_text
