import json
from sqlalchemy import Engine
from claude_agent_sdk import (
    tool, create_sdk_mcp_server, query, ClaudeAgentOptions,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
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
    "donors. Always call emit_scene after reporting so the map reflects the answer."
)

# This module is the local Claude Agent SDK demo entrypoint. The deployed and
# evaluated request path is the pure-Python Anthropic loop in runtime.py; both
# drive the same tools from registry.tool_specs().

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


# Thin async adapters over the registry handlers, exposed for direct unit tests.
async def handle_resolve_entity(args) -> dict:
    return _text(get_spec("resolve_entity").handler(_require_engine(), args))


async def handle_funding_summary(args) -> dict:
    return _text(get_spec("funding_summary").handler(_require_engine(), args))


async def handle_emit_scene(args) -> dict:
    return _text(get_spec("emit_scene").handler(_require_engine(), args))


_ADAPTERS = {
    "resolve_entity": handle_resolve_entity,
    "funding_summary": handle_funding_summary,
    "emit_scene": handle_emit_scene,
}


def _build_tools():
    return [tool(s.name, s.description, s.input_schema)(_ADAPTERS[s.name])
            for s in tool_specs()]


def build_server():
    return create_sdk_mcp_server(name="otm", version="0.1.0", tools=_build_tools())


def agent_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=get_settings().model,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"otm": build_server()},
        allowed_tools=[f"mcp__otm__{s.name}" for s in tool_specs()],
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
