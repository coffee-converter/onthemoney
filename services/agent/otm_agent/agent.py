import json
from dataclasses import asdict
from sqlalchemy import Engine
from claude_agent_sdk import (
    tool, create_sdk_mcp_server, query, ClaudeAgentOptions,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
from otm_agent.config import get_settings
from otm_agent.tools import resolve_entity, funding_summary
from otm_agent.geo import district_centroid
from otm_agent.scene import build_scene

SYSTEM_PROMPT = (
    "You answer questions about U.S. House campaign finance for the 2024 cycle "
    "using only the provided tools. Report only what the tools return. State "
    "figures exactly as returned. If a district has no candidate or no receipts, "
    "say so plainly. Stay strictly descriptive and non-partisan: no endorsements, "
    "no predictions, no value judgments. Always call emit_scene after reporting a "
    "funding figure so the map reflects the answer."
)

_engine: Engine | None = None


def bind_engine(engine: Engine) -> None:
    global _engine
    _engine = engine


def _require_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("engine not bound; call bind_engine() first")
    return _engine


def _text(payload: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


# Plain async handlers: unit-tested directly. The @tool wrappers below turn these
# into SdkMcpTool objects for the in-process MCP server.
async def handle_resolve_entity(args) -> dict:
    res = resolve_entity(_require_engine(), state=args["state"],
                         district=args["district"], cycle=int(args.get("cycle", 2024)))
    if res is None:
        return _text({"found": False})
    return _text({"found": True, "candidate": asdict(res.candidate),
                  "committees": res.committees})


async def handle_funding_summary(args) -> dict:
    fs = funding_summary(_require_engine(), args["cand_id"],
                         cycle=int(args.get("cycle", 2024)),
                         top_n=int(args.get("top_n", get_settings().top_n)))
    return _text({"total": fs.total, "donors": [asdict(d) for d in fs.donors]})


async def handle_emit_scene(args) -> dict:
    state, district = args["state"], args["district"]
    res = resolve_entity(_require_engine(), state=state, district=district)
    centroid = district_centroid(state, district)
    if res is None or centroid is None:
        return _text({"insufficient": True})
    fs = funding_summary(_require_engine(), res.candidate.cand_id)
    return _text(build_scene(state=state, district=district,
                             centroid=centroid, donors=fs.donors))


resolve_entity_tool = tool(
    "resolve_entity",
    "Resolve a U.S. House district to its 2024 candidate and committees",
    {"state": str, "district": str},
)(handle_resolve_entity)

funding_summary_tool = tool(
    "funding_summary",
    "Total itemized receipts and top donors for a candidate id",
    {"cand_id": str},
)(handle_funding_summary)

emit_scene_tool = tool(
    "emit_scene",
    "Build MapLibre scene commands for a district's funding view",
    {"state": str, "district": str},
)(handle_emit_scene)


def build_server():
    return create_sdk_mcp_server(
        name="otm", version="0.1.0",
        tools=[resolve_entity_tool, funding_summary_tool, emit_scene_tool],
    )


def agent_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=get_settings().model,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"otm": build_server()},
        allowed_tools=[
            "mcp__otm__resolve_entity",
            "mcp__otm__funding_summary",
            "mcp__otm__emit_scene",
        ],
    )


async def run_agent(prompt: str) -> list[dict]:
    trace: list[dict] = []
    async for message in query(prompt=prompt, options=agent_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    trace.append({"type": "tool_use", "name": block.name,
                                  "input": block.input})
                elif isinstance(block, TextBlock):
                    trace.append({"type": "text", "text": block.text})
        elif isinstance(message, ResultMessage):
            trace.append({"type": "result", "text": message.result})
    return trace
