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


def test_stream_query_emits_telemetry_before_result(seeded_engine):
    script = [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text", text="Reported 500.00 for 2024.")]),
    ]
    steps = list(stream_query(_FakeClient(script), "Who funds AZ-06?", seeded_engine))
    tele = [s for s in steps if s["type"] == "telemetry"]
    assert len(tele) == 1
    t = tele[0]
    assert steps.index(t) == len(steps) - 2  # telemetry is second-to-last, result last
    assert steps[-1]["type"] == "result"
    assert t["tool_calls"] == 1
    assert t["tool_failures"] == 0
    assert t["turns"] == 2
    assert {"model", "input_tokens", "output_tokens", "elapsed_ms",
            "per_tool", "est_cost_usd"} <= set(t)
    assert [p["name"] for p in t["per_tool"]] == ["resolve_entity"]


def test_tool_exception_is_caught_counted_and_recovered(seeded_engine, monkeypatch):
    from otm_agent import runtime

    class _Spec:
        def handler(self, engine, inp):
            raise RuntimeError("boom")

    real_get_spec = runtime.get_spec

    def fake_get_spec(name):
        return _Spec() if name == "resolve_entity" else real_get_spec(name)

    monkeypatch.setattr(runtime, "get_spec", fake_get_spec)
    script = [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text", text="Could not resolve the district.")]),
    ]
    steps = list(stream_query(_FakeClient(script), "Who funds AZ-06?", seeded_engine))
    # The stream still completed with a result, not an exception.
    assert steps[-1]["type"] == "result"
    tr = next(s for s in steps if s["type"] == "tool_result")
    assert "error" in tr["payload"]
    tele = next(s for s in steps if s["type"] == "telemetry")
    assert tele["tool_failures"] == 1
    assert tele["per_tool"][0]["ok"] is False


def test_telemetry_tokens_accumulate_across_turns(seeded_engine):
    class _Usage:
        def __init__(self, i, o):
            self.input_tokens = i
            self.output_tokens = o

    class _RespU(_Resp):
        def __init__(self, stop_reason, content, usage):
            super().__init__(stop_reason, content)
            self.usage = usage

    script = [
        _RespU("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                 input={"state": "AZ", "district": "06"})], _Usage(100, 20)),
        _RespU("end_turn", [_Blk(type="text", text="Reported 500.00 for 2024.")], _Usage(50, 10)),
    ]
    tele = next(s for s in stream_query(_FakeClient(script), "q", seeded_engine)
                if s["type"] == "telemetry")
    assert tele["input_tokens"] == 150
    assert tele["output_tokens"] == 30


@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"),
                    reason="needs ANTHROPIC_API_KEY for the model path")
def test_run_query_real_model(seeded_engine):
    from anthropic import Anthropic
    result = run_query(Anthropic(), "Who funds the representative in AZ-06?",
                       seeded_engine)
    names = [s["name"] for s in result.trace if s["type"] == "tool_use"]
    assert "resolve_entity" in names
    assert "500.00" in result.final_text


from otm_agent.runtime import SYSTEM_PROMPT


def test_system_prompt_refuses_off_topic():
    low = SYSTEM_PROMPT.lower()
    assert "refuse" in low or "decline" in low
    assert "campaign finance" in low or "fec" in low


def test_model_call_uses_configured_max_tokens(monkeypatch, seeded_engine):
    monkeypatch.setenv("OTM_DEMO_AGENT_MAX_TOKENS", "256")
    captured = {}

    class _Resp:
        stop_reason = "end_turn"
        content = [type("B", (), {"type": "text", "text": "hi"})()]

    class _Msgs:
        def create(self, **kw):
            captured.update(kw)
            return _Resp()

    class _Client:
        messages = _Msgs()

    from otm_agent.runtime import run_query
    run_query(_Client(), "hello", seeded_engine)
    assert captured["max_tokens"] == 256
