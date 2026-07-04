import json
from typing import Callable
from fastapi import FastAPI
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import Engine
from otm_agent.runtime import run_query, stream_query
from otm_agent.response import build_answer_from_trace
from otm_data.db import get_engine


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
    def ask_stream(query: str):
        eng = app.state.engine
        client = app.state.client_factory()

        async def event_gen():
            trace: list[dict] = []
            for step in stream_query(client, query, eng):
                trace.append(step)
                yield {"event": step["type"], "data": json.dumps(step)}
            answer = build_answer_from_trace(eng, trace, _final_text(trace))
            yield {"event": "answer", "data": json.dumps(answer)}

        return EventSourceResponse(event_gen())

    return app


def main() -> None:
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
