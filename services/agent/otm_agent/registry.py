from dataclasses import asdict, dataclass
from typing import Callable
from sqlalchemy import Engine
from otm_agent.tools import resolve_entity, funding_summary
from otm_agent.geo import district_centroid
from otm_agent.scene import build_scene
from otm_agent.config import get_settings
from otm_data.oracle import contributions_by_state, industry_breakdown, top_employers


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[Engine, dict], dict]


def _resolve_entity(engine: Engine, args: dict) -> dict:
    res = resolve_entity(engine, state=args["state"], district=args["district"],
                         cycle=int(args.get("cycle", 2024)))
    if res is None:
        return {"found": False}
    return {"found": True, "candidate": asdict(res.candidate),
            "committees": res.committees}


def _funding_summary(engine: Engine, args: dict) -> dict:
    fs = funding_summary(engine, args["cand_id"], cycle=int(args.get("cycle", 2024)),
                         top_n=int(args.get("top_n", get_settings().top_n)))
    return {"total": fs.total, "receipts": fs.receipts,
            "individual_total": fs.individual_total,
            "donors": [asdict(d) for d in fs.donors]}


def _industry_breakdown(engine: Engine, args: dict) -> dict:
    inds = industry_breakdown(engine, args["cand_id"],
                              election_yr=int(args.get("cycle", 2024)))
    return {"industries": [
        {"industry": i.industry, "amount": f"{i.amount:.2f}", "count": i.count}
        for i in inds
    ]}


def _top_employers(engine: Engine, args: dict) -> dict:
    emps = top_employers(engine, args["cand_id"],
                         election_yr=int(args.get("cycle", 2024)),
                         n=int(args.get("n", 10)))
    return {"employers": [
        {"employer": e.employer, "amount": f"{e.amount:.2f}", "count": e.count}
        for e in emps
    ]}


def _emit_scene(engine: Engine, args: dict) -> dict:
    state, district = args["state"], args["district"]
    res = resolve_entity(engine, state=state, district=district)
    centroid = district_centroid(state, district)
    if res is None or centroid is None:
        return {"insufficient": True}
    by_state = contributions_by_state(engine, res.candidate.cand_id)
    return build_scene(state=state, district=district, centroid=centroid,
                       state_flows=by_state)


_STATE_DISTRICT = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "description": "Two-letter state code, e.g. AZ"},
        "district": {"type": "string", "description": "Zero-padded district, e.g. 06"},
    },
    "required": ["state", "district"],
}

_SPECS = [
    ToolSpec(
        name="resolve_entity",
        description="Resolve a U.S. House district to its 2024 candidate and committees",
        input_schema=_STATE_DISTRICT,
        handler=_resolve_entity,
    ),
    ToolSpec(
        name="funding_summary",
        description="Total itemized individual receipts and top donors for a candidate id",
        input_schema={
            "type": "object",
            "properties": {
                "cand_id": {"type": "string", "description": "FEC candidate id"},
            },
            "required": ["cand_id"],
        },
        handler=_funding_summary,
    ),
    ToolSpec(
        name="industry_breakdown",
        description="Break a candidate's itemized individual donations into industry "
                    "buckets (from donor employers), ranked by dollars. Use to answer "
                    "what kinds of money fund a candidate (grassroots vs corporate, etc).",
        input_schema={
            "type": "object",
            "properties": {"cand_id": {"type": "string", "description": "FEC candidate id"}},
            "required": ["cand_id"],
        },
        handler=_industry_breakdown,
    ),
    ToolSpec(
        name="top_employers",
        description="Rank the employers whose people give a candidate the most itemized "
                    "money. Use for 'which companies / who funds X'.",
        input_schema={
            "type": "object",
            "properties": {
                "cand_id": {"type": "string", "description": "FEC candidate id"},
                "n": {"type": "integer", "description": "How many to return (default 10)"},
            },
            "required": ["cand_id"],
        },
        handler=_top_employers,
    ),
    ToolSpec(
        name="emit_scene",
        description="Build MapLibre scene commands for a district's funding view",
        input_schema=_STATE_DISTRICT,
        handler=_emit_scene,
    ),
]


def tool_specs() -> list[ToolSpec]:
    return list(_SPECS)


def get_spec(name: str) -> ToolSpec:
    for spec in _SPECS:
        if spec.name == name:
            return spec
    raise KeyError(name)
