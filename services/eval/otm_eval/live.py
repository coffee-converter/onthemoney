from otm_eval.golden import GoldenItem
from otm_eval.system import SystemOutput
from otm_agent.runtime import run_query
from otm_agent.graph import supervise, parse_claimed_total


def system_output_from_live(engine, item: GoldenItem, client) -> SystemOutput:
    result = run_query(client, item.query, engine)
    tools = [s["name"] for s in result.trace if s["type"] == "tool_use"]

    committees: list[str] = []
    scene = None
    for step in result.trace:
        if step["type"] != "tool_result":
            continue
        payload = step["payload"]
        if step["name"] == "resolve_entity" and payload.get("found"):
            committees = payload.get("committees", [])
        if step["name"] == "emit_scene" and "highlight" in payload:
            scene = payload

    claimed = parse_claimed_total(result.final_text)
    verdict = supervise(engine, state=item.state, district=item.district,
                        claimed_total=claimed)
    total = claimed if verdict.verified else None
    return SystemOutput(
        id=item.id, tools_called=tools, committees=committees, total=total,
        confidence=verdict.confidence.value, scene=scene, text=result.final_text,
    )
