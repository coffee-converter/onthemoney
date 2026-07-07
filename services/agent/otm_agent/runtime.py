import json
import time
from dataclasses import dataclass
from sqlalchemy import Engine
from otm_agent.config import get_settings, estimate_cost
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
    "- find_candidate(name): look up a person by name to get their real cand_id, "
    "state, and district. Use this first whenever the user names a person instead "
    "of a district - never guess someone's district from memory.\n"
    "- funding_summary(cand_id): returns 'receipts' (the official total raised), "
    "'individual_total' (official amount from individuals), 'total' (the itemized "
    "individual sum, a subset), and top donors. Report 'receipts' as the total "
    "raised and 'individual_total' as from individuals; never present 'total' as "
    "the official total.\n"
    "- industry_breakdown(cand_id): itemized donations by industry.\n"
    "- top_employers(cand_id): the employers whose people give the most.\n"
    "- donor_geography(cand_id): in-state vs out-of-state split of itemized money, "
    "the out-of-state share (%), and the top donor states. Use for 'how much is "
    "out-of-state' or 'where does their money come from'.\n"
    "- funding_timeline(cand_id): itemized money by month - ramp, quarter-end surges, "
    "late money.\n"
    "- donor_size_breakdown(cand_id): small-dollar vs large-dollar split and the "
    "small-dollar share (%). Use for 'is this candidate grassroots-funded'.\n"
    "- top_candidates(metric, limit): nationwide ranking by 'itemized', 'receipts', or "
    "'individual'. Use for 'best-funded in the country' / 'top raisers nationwide'.\n"
    "- race_summary(state, district): the whole district field, the leader's money gap "
    "and margin. Use for 'how competitive is <district>'.\n"
    "- state_field(state): each district's leading candidate across a state.\n\n"
    "Map tools (call exactly one, matched to the question):\n"
    "- highlight_district(state, district): just locate and label a district, no "
    "flows. Use for 'where is <district>'.\n"
    "- emit_scene(state, district): the district plus its money-flow map. Use for "
    "'who funds <district>' and single-district funding questions.\n"
    "- map_state(state, color_by, shape, label): the reliable way to map a whole "
    "state's House districts - 'regions' choropleth or 'points' bubbles, color_by "
    "'party' or 'money', label 'district'/'total'/'name'/'none'. You MUST use this "
    "(never hand-build render_map) for any request to show, map, or heat-map a whole "
    "state's districts - including analytical ones like 'which districts raised the "
    "most, as a heat map' (give the text ranking, then call map_state for the map).\n"
    "- map_nation(shape): the whole country at once - 'regions' shades every district "
    "by its state's total (a nationwide state heat map) or 'points' bubbles per state. "
    "Use for 'all states', 'nationwide', or 'which states raise the most' - including "
    "normalized ones like 'per district': its result includes a per-state summary "
    "(total, district count, per_district average) you rank and read from directly.\n"
    "- map_candidates(metric, limit): map a nationwide ranking of individual candidates "
    "as bubbles sized by money and colored by party. Use this (never hand-build "
    "render_map) for 'map the top/best-funded candidates'.\n"
    "- render_map(points and/or regions, title): a custom map you compose for cases "
    "map_state does not cover. Use "
    "'points' for sized/colored markers, or 'regions' for a choropleth that shades "
    "district polygons. Shade regions by a numeric 'value' (a funding heat map) OR "
    "give each region an explicit 'color' hex (e.g. to color districts by the "
    "incumbent's party). Give a region a 'label' to draw text on the district (e.g. "
    "its number when asked to label districts). Places are district ids (AZ-01) or "
    "state codes. Gather the values with state_field or the funding tools first.\n\n"
    "For plain 'who funds <district>': resolve_entity, funding_summary, then "
    "emit_scene; lead with the official total raised, then from individuals, then "
    "top donors.\n"
    "For analytical questions (industries, employers, comparisons): gather the "
    "breakdowns, present ranked figures as a compact Markdown table, add one factual "
    "takeaway, and pick the fitting map view. When you use render_map, every point's "
    "place and value must come from tool results - never invent coordinates or "
    "numbers.\n"
    "If a district has no candidate or receipts, say so plainly. Always gather with "
    "at least one tool and write a brief answer - never reply with no tool call or "
    "empty text."
    " If a request is not about U.S. House campaign finance, politely refuse and "
    "steer the user back to what this tool can answer; never act as a general "
    "assistant."
)


@dataclass
class AgentResult:
    trace: list[dict]
    final_text: str
    telemetry: dict | None = None


def anthropic_tools() -> list[dict]:
    return [{"name": s.name, "description": s.description,
             "input_schema": s.input_schema} for s in tool_specs()]


def stream_query(client, prompt: str, engine: Engine, *, model: str | None = None,
                 max_turns: int = 10):
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
    started = time.perf_counter()
    input_tokens = output_tokens = turns = tool_calls = tool_failures = 0
    per_tool: list[dict] = []

    for _ in range(max_turns):
        turns += 1
        from otm_agent.demo_guard import load_demo_config
        resp = client.messages.create(
            model=model, max_tokens=load_demo_config().max_tokens, system=SYSTEM_PROMPT,
            tools=tools, messages=messages,
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            input_tokens += getattr(usage, "input_tokens", 0) or 0
            output_tokens += getattr(usage, "output_tokens", 0) or 0
        assistant_content: list[dict] = []
        tool_results: list[dict] = []
        turn_text = ""

        for block in resp.content:
            if block.type == "text":
                turn_text += block.text
                yield {"type": "text", "text": block.text}
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                tool_calls += 1
                yield {"type": "tool_use", "name": block.name, "input": block.input}
                assistant_content.append({"type": "tool_use", "id": block.id,
                                          "name": block.name, "input": block.input})
                t0 = time.perf_counter()
                try:
                    payload = get_spec(block.name).handler(engine, block.input)
                    ok = True
                except Exception as exc:  # surface, count, and recover — never leak internals
                    payload = {"error": f"{block.name} failed ({type(exc).__name__})"}
                    ok = False
                    tool_failures += 1
                per_tool.append({"name": block.name,
                                 "ms": round((time.perf_counter() - t0) * 1000), "ok": ok})
                yield {"type": "tool_result", "name": block.name, "payload": payload}
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": json.dumps(payload)})

        messages.append({"role": "assistant", "content": assistant_content})

        if resp.stop_reason == "tool_use":
            messages.append({"role": "user", "content": tool_results})
            continue

        final_text = turn_text
        break

    yield {
        "type": "telemetry",
        "model": model,
        "turns": turns,
        "tool_calls": tool_calls,
        "tool_failures": tool_failures,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "elapsed_ms": round((time.perf_counter() - started) * 1000),
        "per_tool": per_tool,
        "est_cost_usd": round(estimate_cost(model, input_tokens, output_tokens), 4),
    }
    yield {"type": "result", "text": final_text}


def run_query(client, prompt: str, engine: Engine, *, model: str | None = None,
              max_turns: int = 10) -> AgentResult:
    """Collect `stream_query` into a full `AgentResult`."""
    trace: list[dict] = []
    final_text = ""
    telemetry: dict | None = None
    for step in stream_query(client, prompt, engine, model=model,
                             max_turns=max_turns):
        trace.append(step)
        if step["type"] == "result":
            final_text = step["text"]
        elif step["type"] == "telemetry":
            telemetry = step
    return AgentResult(trace=trace, final_text=final_text, telemetry=telemetry)
