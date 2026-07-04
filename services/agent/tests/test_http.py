from fastapi.testclient import TestClient
from otm_agent.http import create_app


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


def _script():
    return [
        _Resp("tool_use", [_Blk(type="tool_use", id="t1", name="resolve_entity",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("tool_use", [_Blk(type="tool_use", id="t2", name="emit_scene",
                                input={"state": "AZ", "district": "06"})]),
        _Resp("end_turn", [_Blk(type="text",
                                text="AZ-06 reported 500.00 in itemized receipts for 2024.")]),
    ]


def _client(seeded_engine):
    app = create_app(engine=seeded_engine,
                     client_factory=lambda: _FakeClient(_script()))
    return TestClient(app)


def test_health(seeded_engine):
    resp = _client(seeded_engine).get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ask_returns_answer_and_trace(seeded_engine):
    resp = _client(seeded_engine).post("/ask", json={"query": "Who funds AZ-06?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]["confidence"] == "high"
    assert body["answer"]["total"] == "500.00"
    assert body["answer"]["scene"]["highlight"] == {"state": "AZ", "district": "06"}
    tool_uses = [s for s in body["trace"] if s["type"] == "tool_use"]
    assert {s["name"] for s in tool_uses} == {"resolve_entity", "emit_scene"}


def test_ask_stream_emits_events(seeded_engine):
    resp = _client(seeded_engine).get("/ask/stream", params={"query": "Who funds AZ-06?"})
    assert resp.status_code == 200
    body = resp.text
    assert "event: tool_use" in body
    assert "event: tool_result" in body
    assert "event: answer" in body
    assert "500.00" in body
