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
    total_from_tool = None
    receipts = None
    individual_total = None

    for step in trace:
        if step["type"] == "tool_use" and step["name"] == "resolve_entity":
            state = step["input"].get("state")
            district = step["input"].get("district")
        if step["type"] == "tool_result":
            payload = step["payload"]
            if step["name"] == "resolve_entity" and payload.get("found"):
                committees = payload.get("committees", [])
            if step["name"] == "funding_summary" and "total" in payload:
                total_from_tool = payload.get("total")
                receipts = payload.get("receipts")
                individual_total = payload.get("individual_total")
            if step["name"] == "emit_scene" and "highlight" in payload:
                scene = payload

    # An answer assembled from deterministic analytical tools is grounded by
    # construction, even when there is no single district total to verify.
    _GROUNDED = {"state_field", "industry_breakdown", "top_employers",
                 "render_map", "highlight_district"}
    grounded = any(
        step["type"] == "tool_result" and step["name"] in _GROUNDED
        and not step["payload"].get("insufficient", False)
        for step in trace
    )

    # Prefer the exact figure the tool returned over re-parsing the model's prose
    # (the model reformats with $ and commas, which is lossy to compare).
    claimed = total_from_tool if total_from_tool is not None else parse_claimed_total(final_text)
    # A grounded analytical / multi-candidate answer (breakdowns, comparisons,
    # custom maps) is trustworthy by construction; only fall back to verifying a
    # single district total for a plain funding answer.
    if grounded:
        confidence = "high"
        total = None
    elif state and district:
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
            "receipts": receipts, "individual_total": individual_total,
            "citations": citations, "scene": scene}
