import json
from dataclasses import dataclass
from sqlalchemy import Engine
from otm_agent.config import get_settings
from otm_agent.registry import tool_specs, get_spec

SYSTEM_PROMPT = (
    "You answer questions about U.S. House campaign finance for the 2024 cycle "
    "using only the provided tools. Report only what the tools return. State "
    "figures exactly as returned. If a district has no candidate or no receipts, "
    "say so plainly. Stay strictly descriptive and non-partisan: no endorsements, "
    "no predictions, no value judgments. When funding_summary returns receipts "
    "(the official total raised) and individual_total, lead with the official "
    "total raised, then how much came from individuals, then the top itemized "
    "donors. Call emit_scene after reporting so the map reflects the answer."
)


@dataclass
class AgentResult:
    trace: list[dict]
    final_text: str


def anthropic_tools() -> list[dict]:
    return [{"name": s.name, "description": s.description,
             "input_schema": s.input_schema} for s in tool_specs()]


def stream_query(client, prompt: str, engine: Engine, *, model: str | None = None,
                 max_turns: int = 6):
    """Pure-Python Anthropic Messages API tool-use loop, yielding trace steps.

    `client` is any object exposing `messages.create(...)`; inject a fake in
    tests, or `anthropic.Anthropic()` in production. Yields step dicts of type
    `tool_use`, `tool_result`, `text`, and a final `result`. This is the
    deployed and evaluated request path (no Node, no CLI).
    """
    model = model or get_settings().model
    tools = anthropic_tools()
    messages: list[dict] = [{"role": "user", "content": prompt}]
    final_text = ""

    for _ in range(max_turns):
        resp = client.messages.create(
            model=model, max_tokens=1024, system=SYSTEM_PROMPT,
            tools=tools, messages=messages,
        )
        assistant_content: list[dict] = []
        tool_results: list[dict] = []
        turn_text = ""

        for block in resp.content:
            if block.type == "text":
                turn_text += block.text
                yield {"type": "text", "text": block.text}
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                yield {"type": "tool_use", "name": block.name, "input": block.input}
                assistant_content.append({"type": "tool_use", "id": block.id,
                                          "name": block.name, "input": block.input})
                payload = get_spec(block.name).handler(engine, block.input)
                yield {"type": "tool_result", "name": block.name, "payload": payload}
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": json.dumps(payload)})

        messages.append({"role": "assistant", "content": assistant_content})

        if resp.stop_reason == "tool_use":
            messages.append({"role": "user", "content": tool_results})
            continue

        final_text = turn_text
        break

    yield {"type": "result", "text": final_text}


def run_query(client, prompt: str, engine: Engine, *, model: str | None = None,
              max_turns: int = 6) -> AgentResult:
    """Collect `stream_query` into a full `AgentResult`."""
    trace: list[dict] = []
    final_text = ""
    for step in stream_query(client, prompt, engine, model=model,
                             max_turns=max_turns):
        trace.append(step)
        if step["type"] == "result":
            final_text = step["text"]
    return AgentResult(trace=trace, final_text=final_text)
