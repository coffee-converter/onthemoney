import json
from datetime import datetime, timezone
from typing import Callable
from fastapi import FastAPI, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import Engine
from otm_agent.runtime import run_query, stream_query
from otm_agent.response import build_answer_from_trace
from otm_agent.geo import district_centroid
from otm_agent.scene import build_scene
from otm_agent import demo_guard as dg
from otm_data.db import get_engine
from otm_data.oracle import (
    district_candidates, contributions_by_state, candidate_finance,
)


class AskRequest(BaseModel):
    query: str


def _default_client_factory():
    from anthropic import Anthropic
    return Anthropic()


def _final_text(trace: list[dict]) -> str:
    for step in reversed(trace):
        if step["type"] == "result":
            return step["text"]
    return ""


def create_app(engine: Engine | None = None,
               client_factory: Callable[[], object] | None = None) -> FastAPI:
    app = FastAPI(title="On The Money agent service")
    app.state.engine = engine or get_engine()
    app.state.client_factory = client_factory or _default_client_factory

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/ask")
    def ask(req: AskRequest):
        eng = app.state.engine
        client = app.state.client_factory()
        result = run_query(client, req.query, eng)
        answer = build_answer_from_trace(eng, result.trace, result.final_text)
        return {"trace": result.trace, "answer": answer}

    @app.get("/ask/stream")
    def ask_stream(query: str, request: Request):
        eng = app.state.engine
        cfg = dg.load_demo_config()

        async def event_gen():
            # Fast path: guard disabled (dev/tests) — behave exactly as before.
            if not cfg.enabled:
                client = app.state.client_factory()
                trace: list[dict] = []
                for step in stream_query(client, query, eng):
                    trace.append(step)
                    yield {"event": step["type"], "data": json.dumps(step)}
                answer = build_answer_from_trace(eng, trace, _final_text(trace))
                yield {"event": "answer", "data": json.dumps(answer)}
                return

            ip = dg.client_ip(request.headers)
            now = datetime.now(timezone.utc)

            if len(query) > cfg.max_query_chars:
                yield dg.limit_answer_event(
                    "That question is too long for the demo. Please shorten it.")
                return
            if dg.rate_limited(eng, cfg, ip, now):
                yield dg.limit_answer_event(dg.RATE_MSG)
                return

            qhash = dg.query_hash(query)
            cached = dg.cache_get(eng, qhash)
            if cached is not None:
                for msg in cached:  # zero-cost replay; not billed
                    yield msg
                return

            if dg.budget_exceeded(eng, cfg, now.date()):
                yield dg.limit_answer_event(dg.BUDGET_MSG)
                return

            # Miss: run the agent, buffering messages to cache on a clean finish.
            client = app.state.client_factory()
            trace: list[dict] = []
            buffered: list[dict] = []
            cost = 0.0
            failed = False
            for step in stream_query(client, query, eng):
                trace.append(step)
                if step["type"] == "telemetry":
                    cost = float(step.get("est_cost_usd", 0) or 0)
                    if step.get("tool_failures", 0):
                        failed = True
                if step["type"] == "tool_result" and "error" in step.get("payload", {}):
                    failed = True
                msg = {"event": step["type"], "data": json.dumps(step)}
                buffered.append(msg)
                yield msg
            answer = build_answer_from_trace(eng, trace, _final_text(trace))
            answer_msg = {"event": "answer", "data": json.dumps(answer)}
            buffered.append(answer_msg)
            yield answer_msg

            if cost:
                dg.bill(eng, now.date(), cost)
            if not failed:
                dg.cache_put(eng, qhash, buffered)

        return EventSourceResponse(event_gen())

    @app.get("/district/{state}/{district}/candidates")
    def district_roster(state: str, district: str):
        cands = district_candidates(app.state.engine, state=state.upper(),
                                    district=district)
        return {"candidates": [
            {"cand_id": c.cand_id, "name": c.name, "party": c.party,
             "itemized": f"{c.itemized:.2f}",
             "receipts": f"{c.receipts:.2f}" if c.receipts is not None else None,
             "individual_total": (f"{c.individual_total:.2f}"
                                  if c.individual_total is not None else None)}
            for c in cands
        ]}

    @app.get("/candidate/{cand_id}/scene")
    def candidate_scene(cand_id: str, state: str, district: str):
        eng = app.state.engine
        centroid = district_centroid(state.upper(), district)
        flows = contributions_by_state(eng, cand_id)
        scene = (build_scene(state=state.upper(), district=district,
                             centroid=centroid, state_flows=flows)
                 if centroid is not None else None)
        fin = candidate_finance(eng, cand_id)
        return {
            "scene": scene,
            "receipts": f"{fin.receipts:.2f}" if fin else None,
            "individual_total": f"{fin.individual_total:.2f}" if fin else None,
        }

    return app


def main() -> None:
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
