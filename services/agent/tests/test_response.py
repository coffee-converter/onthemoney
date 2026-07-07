from otm_agent.runtime import run_query
from otm_agent.response import build_answer_from_trace


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

    def create(self, **kwargs):
        return self._script.pop(0)


class _FakeClient:
    def __init__(self, script):
        self.messages = _Messages(script)


def _az06_trace(engine):
    script = [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("tool_use", [_Blk(type="tool_use", id="t2", name="emit_scene",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text",
                                text="AZ-06 reported 500.00 in itemized receipts for 2024.")]),
    ]
    return run_query(_FakeClient(script), "Who funds AZ-06?", engine)


def test_build_answer_high_confidence_with_citations(seeded_engine):
    result = _az06_trace(seeded_engine)
    ans = build_answer_from_trace(seeded_engine, result.trace, result.final_text)
    assert ans["confidence"] == "high"
    assert ans["total"] == "500.00"
    assert ans["scene"]["highlight"] == {"state": "AZ", "district": "06"}
    assert any(c["url"].endswith("/C00770886/") for c in ans["citations"])


def test_build_answer_uses_funding_summary_tool_total(seeded_engine):
    # Even when the prose reformats the number with $ and commas, confidence
    # stays high because the exact tool figure is used for verification.
    trace = [
        {"type": "tool_use", "name": "resolve_entity",
         "input": {"state": "AZ", "district": "06"}},
        {"type": "tool_result", "name": "resolve_entity",
         "payload": {"found": True, "candidate": {"cand_id": "H2AZ06099"},
                     "committees": ["C00770886"]}},
        {"type": "tool_result", "name": "funding_summary",
         "payload": {"total": "500.00", "donors": []}},
        {"type": "result", "text": "AZ-06 reported $500.00 in itemized receipts."},
    ]
    ans = build_answer_from_trace(seeded_engine, trace,
                                  "AZ-06 reported $500.00 in itemized receipts.")
    assert ans["confidence"] == "high"
    assert ans["total"] == "500.00"


def test_build_answer_downgrades_when_total_wrong(seeded_engine):
    script = [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text", text="AZ-06 reported 999.00.")]),
    ]
    result = run_query(_FakeClient(script), "Who funds AZ-06?", seeded_engine)
    ans = build_answer_from_trace(seeded_engine, result.trace, result.final_text)
    assert ans["confidence"] == "insufficient"
    assert ans["total"] is None


def test_grounded_analytical_answer_is_not_insufficient(seeded_engine):
    # A state_field/analytical trace (no resolve_entity) is still grounded.
    trace = [
        {"type": "tool_use", "name": "state_field", "input": {"state": "AZ"}},
        {"type": "tool_result", "name": "state_field",
         "payload": {"state": "AZ", "candidates": [
             {"district": "06", "cand_id": "H2AZ06099", "name": "X",
              "party": "DEM", "itemized": "500.00"}]}},
        {"type": "result", "text": "Here are Arizona's leading candidates."},
    ]
    ans = build_answer_from_trace(seeded_engine, trace,
                                  "Here are Arizona's leading candidates.")
    assert ans["confidence"] == "high"


def test_errored_grounded_tool_is_not_treated_as_grounded(seeded_engine):
    # A grounded analytical tool that raised is recovered into an {"error": ...}
    # payload so the request can finish; it must NOT count as grounding, or a
    # crashed tool would still produce a confident, data-free "high" answer.
    trace = [
        {"type": "tool_use", "name": "industry_breakdown", "input": {"cand_id": "X"}},
        {"type": "tool_result", "name": "industry_breakdown",
         "payload": {"error": "industry_breakdown failed (ValueError)"}},
        {"type": "result", "text": "Their top industries are finance and real estate."},
    ]
    ans = build_answer_from_trace(seeded_engine, trace,
                                  "Their top industries are finance and real estate.")
    assert ans["confidence"] == "insufficient"
