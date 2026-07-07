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


def test_admin_usage_requires_secret(monkeypatch, seeded_engine):
    monkeypatch.setenv("OTM_ADMIN_SECRET", "s3cret")
    app = create_app(engine=seeded_engine, client_factory=lambda: _FakeClient(_script()))
    client = TestClient(app)
    assert client.get("/admin/usage").status_code == 403
    ok = client.get("/admin/usage", headers={"x-admin-secret": "s3cret"})
    assert ok.status_code == 200
    assert "spent_usd" in ok.json()


# --- Usage-bearing fake so telemetry reports a nonzero est_cost_usd ---
class _Usage:
    def __init__(self, i, o):
        self.input_tokens = i
        self.output_tokens = o


def _script_billed():
    s = _script()
    for r in s:
        r.usage = _Usage(1000, 500)
    return s


def test_stream_bills_full_consume(monkeypatch, seeded_engine):
    """FIX C1 (part 1): a fully-consumed stream bills the telemetry cost exactly
    once into today's UTC ledger."""
    monkeypatch.setenv("OTM_DEMO_ENABLED", "1")
    from datetime import datetime, timezone
    from otm_agent.demo_guard import usage_summary
    app = create_app(engine=seeded_engine,
                     client_factory=lambda: _FakeClient(_script_billed()))
    client = TestClient(app)
    resp = client.get("/ask/stream", params={"query": "Who funds AZ-06?"})
    assert resp.status_code == 200
    day = datetime.now(timezone.utc).date()
    # 3 turns x usage(1000,500) -> 3000 in / 1500 out -> est_cost_usd > 0.
    assert usage_summary(seeded_engine, day)["spent_usd"] > 0


def test_stream_bills_at_telemetry_not_after_answer(monkeypatch, seeded_engine):
    """FIX C1 (part 2, the discriminator): billing must fire when the telemetry
    step is observed *inside* the loop — before the answer is built and the
    trailing `answer` message is yielded — so a client that disconnects at/after
    the telemetry event is still billed. (A real mid-stream disconnect isn't
    observable through TestClient, which drains the generator to completion, so
    we assert ordering instead.) Pre-fix, billing ran after `yield answer_msg`,
    giving the reverse order."""
    monkeypatch.setenv("OTM_DEMO_ENABLED", "1")
    import otm_agent.http as http_mod
    import otm_agent.demo_guard as dg_mod
    order: list[str] = []
    real_answer = http_mod.build_answer_from_trace

    def rec_bill(*a, **k):
        order.append("bill")

    def rec_answer(*a, **k):
        order.append("answer")
        return real_answer(*a, **k)

    monkeypatch.setattr(dg_mod, "bill", rec_bill)
    monkeypatch.setattr(http_mod, "build_answer_from_trace", rec_answer)
    app = create_app(engine=seeded_engine,
                     client_factory=lambda: _FakeClient(_script_billed()))
    client = TestClient(app)
    resp = client.get("/ask/stream", params={"query": "Who funds AZ-06?"})
    assert resp.status_code == 200
    assert order == ["bill", "answer"]


def test_proxy_secret_enforced_when_set(monkeypatch, seeded_engine):
    """FIX C2: OTM_PROXY_SECRET, when set, must be verified on the agent."""
    app = create_app(engine=seeded_engine,
                     client_factory=lambda: _FakeClient(_script()))
    client = TestClient(app)
    # Dev default: secret UNSET -> request allowed (not 403).
    r = client.get("/ask/stream", params={"query": "Who funds AZ-06?"})
    assert r.status_code != 403
    # Secret SET + missing header -> 403.
    monkeypatch.setenv("OTM_PROXY_SECRET", "shh")
    r = client.get("/ask/stream", params={"query": "Who funds AZ-06?"})
    assert r.status_code == 403
    # Secret SET + correct header -> not 403.
    r = client.get("/ask/stream", params={"query": "Who funds AZ-06?"},
                   headers={"x-otm-proxy-secret": "shh"})
    assert r.status_code != 403
    # Admin gate: OTM_ADMIN_SECRET unset -> 403 even past the proxy gate
    # (covers the previously-missing admin-secret-absent branch).
    r = client.get("/admin/usage", headers={"x-otm-proxy-secret": "shh"})
    assert r.status_code == 403


def test_ask_post_budget_breaker(monkeypatch, seeded_engine):
    """FIX I1: POST /ask must be guarded like /ask/stream when the demo guard is
    enabled — over-budget requests never call the paid agent."""
    monkeypatch.setenv("OTM_DEMO_ENABLED", "1")
    monkeypatch.setenv("OTM_DEMO_DAILY_USD", "1.00")
    from datetime import datetime, timezone
    bill(seeded_engine, datetime.now(timezone.utc).date(), 2.0)  # already over cap

    def _boom():
        raise AssertionError("agent must not be called once the budget is exhausted")

    app = create_app(engine=seeded_engine, client_factory=_boom)
    client = TestClient(app)
    resp = client.post("/ask", json={"query": "Who funds NY-14?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["trace"] == []
    assert "limit" in body["answer"]["text"].lower()


def test_budget_exceeded_boundary(seeded_engine):
    """Small add: billing EXACTLY daily_usd trips the breaker (pins >= vs >)."""
    from datetime import date
    from otm_agent.demo_guard import load_demo_config, budget_exceeded
    cfg = load_demo_config()  # default daily_usd == 5.00
    d = date(2099, 1, 1)
    bill(seeded_engine, d, cfg.daily_usd)
    assert budget_exceeded(seeded_engine, cfg, d) is True
