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
                 "donor_geography", "find_candidate", "funding_timeline",
                 "donor_size_breakdown", "top_candidates", "race_summary",
                 "rank_districts", "compare_candidates", "top_by_industry",
                 "render_map", "map_state", "map_nation", "map_candidates",
                 "map_districts", "highlight_district"}
    # A tool that raised is recovered into an {"error": ...} payload upstream so
    # the request can finish; it must NOT count as grounding, or a crashed
    # analytical tool would still yield a confident "high" answer with no data.
    grounded = any(
        step["type"] == "tool_result" and step["name"] in _GROUNDED
        and not step["payload"].get("insufficient", False)
        and "error" not in step["payload"]
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

    # Never surface a blank answer: if the model rendered a map but wrote no
    # prose, give the user something rather than an empty card.
    if not final_text.strip():
        final_text = (
            "The map above is drawn from the underlying FEC data. Ask a follow-up "
            "if you'd like the specific figures called out."
            if scene or grounded
            else "I could not find enough data to answer that."
        )

    citations = [asdict(Citation(label=c, url=fec_committee_url(c)))
                 for c in committees]
    return {"text": final_text, "confidence": confidence, "total": total,
            "receipts": receipts, "individual_total": individual_total,
            "citations": citations, "scene": scene}
