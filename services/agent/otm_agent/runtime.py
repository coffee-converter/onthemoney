import json
from dataclasses import dataclass
from sqlalchemy import Engine
from otm_agent.config import get_settings
from otm_agent.registry import tool_specs, get_spec

SYSTEM_PROMPT = (
    "You answer questions about U.S. House campaign finance for the 2024 cycle "
    "using only the provided tools. Plan the steps a question needs, call tools "
    "to gather facts, and choose a map view that fits the question. Report only "
    "what the tools return and state figures exactly as returned. Stay strictly "
    "descriptive and non-partisan: no endorsements, predictions, or judgments.\n\n"
    "Data tools:\n"
    "- resolve_entity(state, district): the district's leading candidate and "
    "committees (turns a district into a cand_id).\n"
    "- funding_summary(cand_id): returns 'receipts' (the official total raised), "
    "'individual_total' (official amount from individuals), 'total' (the itemized "
    "individual sum, a subset), and top donors. Report 'receipts' as the total "
    "raised and 'individual_total' as from individuals; never present 'total' as "
    "the official total.\n"
    "- industry_breakdown(cand_id): itemized donations by industry.\n"
    "- top_employers(cand_id): the employers whose people give the most.\n"
    "- state_field(state): each district's leading candidate across a state.\n\n"
    "Map tools (call exactly one, matched to the question):\n"
    "- highlight_district(state, district): just locate and label a district, no "
    "flows. Use for 'where is <district>'.\n"
    "- emit_scene(state, district): the district plus its money-flow map. Use for "
    "'who funds <district>' and single-district funding questions.\n"
    "- render_map(points and/or regions, title): a custom map you compose. Use "
    "'points' for sized/colored markers, or 'regions' for a choropleth that shades "
    "district polygons. Shade regions by a numeric 'value' (a funding heat map) OR "
    "give each region an explicit 'color' hex (e.g. to color districts by the "
    "incumbent's party). Places are district ids (AZ-01) or state codes. Gather the "
    "values with state_field or the funding tools first.\n\n"
    "For plain 'who funds <district>': resolve_entity, funding_summary, then "
    "emit_scene; lead with the official total raised, then from individuals, then "
    "top donors.\n"
    "For analytical questions (industries, employers, comparisons): gather the "
    "breakdowns, present ranked figures as a compact Markdown table, add one factual "
    "takeaway, and pick the fitting map view. When you use render_map, every point's "
    "place and value must come from tool results - never invent coordinates or "
    "numbers.\n"
    "If a district has no candidate or receipts, say so plainly."
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
