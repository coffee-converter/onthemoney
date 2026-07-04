from dataclasses import asdict
from sqlalchemy import Engine
from otm_agent.answer import Citation, fec_committee_url
from otm_agent.graph import supervise, parse_claimed_total


def build_answer_from_trace(engine: Engine, trace: list[dict],
                            final_text: str) -> dict:
    """Assemble the API answer object from an agent trace.

    Reads the resolve_entity tool input (for state/district), the tool result
    payloads (committees + scene), and calibrates confidence by verifying the
    stated total against the oracle via supervise().
    """
    state = district = None
    committees: list[str] = []
    scene = None

    for step in trace:
        if step["type"] == "tool_use" and step["name"] == "resolve_entity":
            state = step["input"].get("state")
            district = step["input"].get("district")
        if step["type"] == "tool_result":
            payload = step["payload"]
            if step["name"] == "resolve_entity" and payload.get("found"):
                committees = payload.get("committees", [])
            if step["name"] == "emit_scene" and "highlight" in payload:
                scene = payload

    claimed = parse_claimed_total(final_text)
    if state and district:
        verdict = supervise(engine, state=state, district=district,
                            claimed_total=claimed)
        confidence = verdict.confidence.value
        total = claimed if verdict.verified else None
    else:
        confidence = "insufficient"
        total = None

    citations = [asdict(Citation(label=c, url=fec_committee_url(c)))
                 for c in committees]
    return {"text": final_text, "confidence": confidence, "total": total,
            "citations": citations, "scene": scene}
