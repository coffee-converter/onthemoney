import json
from sqlalchemy import Engine
from claude_agent_sdk import (
    tool, create_sdk_mcp_server, query, ClaudeAgentOptions,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage,
)
from otm_agent.config import get_settings
from otm_agent.registry import tool_specs, get_spec
from otm_agent.runtime import SYSTEM_PROMPT

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


def _make_adapter(name: str):
    async def _adapter(args) -> dict:
        return _text(get_spec(name).handler(_require_engine(), args))
    return _adapter


def _build_tools():
    # One adapter per registered tool, so new tools are picked up automatically.
    return [tool(s.name, s.description, s.input_schema)(_make_adapter(s.name))
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
