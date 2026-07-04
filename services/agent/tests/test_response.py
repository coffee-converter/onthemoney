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
