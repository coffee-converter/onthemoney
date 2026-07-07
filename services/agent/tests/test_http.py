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


import json
from datetime import date
from otm_agent.demo_guard import bill, query_hash


def _events(resp):
    out = []
    for block in resp.text.strip().split("\n\n"):
        ev = {ln.split(": ", 1)[0]: ln.split(": ", 1)[1]
              for ln in block.splitlines() if ": " in ln}
        if ev:
            out.append(ev)
    return out


def test_stream_budget_breaker(monkeypatch, seeded_engine):
    monkeypatch.setenv("OTM_DEMO_ENABLED", "1")
    monkeypatch.setenv("OTM_DEMO_DAILY_USD", "1.00")
    from datetime import datetime, timezone
    bill(seeded_engine, datetime.now(timezone.utc).date(), 2.0)  # already over cap
    # A client_factory that raises proves the agent is never called once the budget is exhausted.
    def _boom():
        raise AssertionError("agent must not be called once the budget is exhausted")
    app = create_app(engine=seeded_engine, client_factory=_boom)
    client = TestClient(app)
    resp = client.get("/ask/stream", params={"query": "Who funds NY-14?"})
    events = _events(resp)
    assert any(e.get("event") == "answer" and "limit" in e.get("data", "").lower()
               for e in events)


def test_stream_cache_hit_skips_agent(monkeypatch, seeded_engine):
    monkeypatch.setenv("OTM_DEMO_ENABLED", "1")
    from otm_agent.demo_guard import cache_put
    q = "Where is IL-04?"
    cache_put(seeded_engine, query_hash(q),
              [{"event": "answer", "data": json.dumps({"text": "CACHED", "confidence": "high",
                "total": None, "receipts": None, "individual_total": None,
                "citations": [], "scene": None})}])
    # A client_factory that raises proves the agent is never called on a hit.
    def _boom():
        raise AssertionError("agent must not be called on cache hit")
    app = create_app(engine=seeded_engine, client_factory=_boom)
    client = TestClient(app)
    resp = client.get("/ask/stream", params={"query": q})
    assert "CACHED" in resp.text
