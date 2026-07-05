from dataclasses import asdict, dataclass
from typing import Callable
from sqlalchemy import Engine
from otm_agent.tools import resolve_entity, funding_summary
from otm_agent.geo import district_centroid, resolve_place, all_district_keys
from otm_agent.scene import build_scene
from otm_agent.config import get_settings
from otm_data.oracle import (
    contributions_by_state, industry_breakdown, top_employers, state_field,
    state_totals,
)


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


def _state_field(engine: Engine, args: dict) -> dict:
    entries = state_field(engine, args["state"].upper())
    return {"state": args["state"].upper(), "candidates": [
        {"district": e.district, "cand_id": e.cand_id, "name": e.name,
         "party": e.party, "itemized": f"{e.itemized:.2f}"} for e in entries]}


def _fit_camera(pts: list[dict]) -> dict:
    if not pts:
        return {"type": "flyTo", "lon": -96.0, "lat": 38.0, "zoom": 4}
    lons = [p["lng"] for p in pts]
    lats = [p["lat"] for p in pts]
    return {"type": "flyTo", "lon": sum(lons) / len(lons),
            "lat": sum(lats) / len(lats), "zoom": 5}


def _norm_district(place) -> str | None:
    if isinstance(place, str) and "-" in place:
        st, di = place.split("-", 1)
        key = f"{st.strip().upper()}-{di.strip().zfill(2)}"
        return key if district_centroid(*key.split("-")) is not None else None
    return None


def _render_map(engine: Engine, args: dict) -> dict:
    # Ground each semantic place to real geometry - the agent picks what and how
    # to draw; it never supplies raw coordinates.
    pts: list[dict] = []
    fit: list[dict] = []
    for p in args.get("points", []):
        coord = resolve_place(p.get("place"))
        if coord is None:
            continue
        pt = {"lng": coord[0], "lat": coord[1], "value": float(p.get("value") or 0),
              "color": p.get("color"), "label": p.get("label"),
              "tooltip": [str(t) for t in (p.get("tooltip") or [])]}
        pts.append(pt)
        fit.append(pt)
    regions: list[dict] = []
    for r in args.get("regions", []):
        key = _norm_district(r.get("place"))
        if key is None:
            continue
        centroid = district_centroid(*key.split("-"))
        regions.append({"place": key, "value": float(r.get("value") or 0),
                        "color": r.get("color"), "label": r.get("label"),
                        "tooltip": [str(t) for t in (r.get("tooltip") or [])]})
        fit.append({"lng": centroid[0], "lat": centroid[1]})
    overlays: list[dict] = []
    if pts:
        overlays.append({"type": "points", "points": pts})
    if regions:
        overlays.append({"type": "regions", "regions": regions})
    return {"camera": _fit_camera(fit), "flows": [], "overlays": overlays,
            "title": args.get("title", "")}


def _highlight_district(engine: Engine, args: dict) -> dict:
    state, district = args["state"].upper(), args["district"]
    centroid = district_centroid(state, district)
    if centroid is None:
        return {"insufficient": True}
    lon, lat = centroid
    return {"camera": {"type": "flyTo", "lon": lon, "lat": lat, "zoom": 7},
            "highlight": {"state": state, "district": district}, "flows": []}


_PARTY_HEX = {"D": "#2166ac", "R": "#b2182b", "I": "#7b3fa0", "L": "#d99a2b", "G": "#43b26a"}
_PARTY_LETTER = {"DEM": "D", "DFL": "D", "DNL": "D", "REP": "R", "GOP": "R",
                 "IND": "I", "NPA": "I", "NON": "I", "UN": "I", "LIB": "L",
                 "GRE": "G", "CON": "C"}


def _short_money(amt: float) -> str:
    if amt >= 1_000_000:
        return f"${amt / 1_000_000:.1f}M"
    if amt >= 1_000:
        return f"${amt / 1_000:.0f}k"
    return f"${amt:.0f}"


def _map_state(engine: Engine, args: dict) -> dict:
    # Build a whole-state map server-side so the agent never hand-transcribes a
    # long list (which it sometimes gets wrong). The agent just picks encoding.
    state = args["state"].upper()
    entries = state_field(engine, state)
    color_by = args.get("color_by", "party")
    shape = "points" if args.get("shape") == "points" else "regions"
    label_mode = str(args.get("label", "district")).lower()  # district|total|name|none
    items: list[dict] = []
    for e in entries:
        if district_centroid(state, e.district) is None:
            continue
        pl = _PARTY_LETTER.get((e.party or "").upper())
        item = {"place": f"{state}-{e.district}", "value": float(e.itemized),
                "tooltip": [e.name, pl or e.party, f"${float(e.itemized):,.0f}"]}
        if color_by == "party" and pl in _PARTY_HEX:
            item["color"] = _PARTY_HEX[pl]
        if label_mode == "district":
            item["label"] = e.district
        elif label_mode == "total":
            item["label"] = _short_money(float(e.itemized))
        elif label_mode == "name":
            item["label"] = e.name.split(",")[0].title()
        items.append(item)
    field = "points" if shape == "points" else "regions"
    return _render_map(engine, {field: items, "title": f"{state} House districts"})


def _map_nation(engine: Engine, args: dict) -> dict:
    # Nationwide funding map. 'regions' colors every district by its state's
    # total (a state-level choropleth built from district polygons); 'points'
    # drops one bubble per state at its centroid.
    shape = "points" if args.get("shape") == "points" else "regions"
    totals = {t.state: float(t.total) for t in state_totals(engine)}
    counts: dict[str, int] = {}
    for key in all_district_keys():
        st = key.split("-")[0]
        counts[st] = counts.get(st, 0) + 1
    # Compact per-state summary so the model can rank and normalize (e.g. per
    # district) instead of parsing every rendered region.
    summary = sorted(
        [{"state": st, "total": round(total), "districts": counts.get(st, 0),
          "per_district": round(total / counts[st]) if counts.get(st) else 0}
         for st, total in totals.items()],
        key=lambda r: -r["total"],
    )
    if shape == "points":
        items = [{"place": st, "value": total,
                  "tooltip": [st, f"${total:,.0f} raised statewide"]}
                 for st, total in sorted(totals.items(), key=lambda kv: -kv[1])]
        scene = _render_map(engine, {"points": items, "title": "House funding by state"})
    else:
        regions = [{"place": key, "value": totals.get(key.split("-")[0], 0.0),
                    "tooltip": [key.split("-")[0],
                                f"${totals.get(key.split('-')[0], 0.0):,.0f} raised statewide"]}
                   for key in all_district_keys()]
        scene = _render_map(engine, {"regions": regions, "title": "House funding by state"})
    scene["summary"] = summary
    return scene


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
        name="highlight_district",
        description="Just locate and highlight a district on the map (outline and "
                    "label, no money flows). Use for 'where is <district>' questions.",
        input_schema=_STATE_DISTRICT,
        handler=_highlight_district,
    ),
    ToolSpec(
        name="state_field",
        description="Every district's leading candidate across a state (district, "
                    "cand_id, name, party, itemized total). Data for a whole-state map.",
        input_schema={
            "type": "object",
            "properties": {"state": {"type": "string", "description": "Two-letter state code"}},
            "required": ["state"],
        },
        handler=_state_field,
    ),
    ToolSpec(
        name="render_map",
        description="Draw a custom map. Provide 'points' (sized/colored markers) "
                    "and/or 'regions' (a choropleth heat map shading district polygons "
                    "by value). Each item's 'place' is a district id like 'AZ-01' "
                    "(regions must be districts; points may also use a state code). "
                    "'value' sizes markers or colors regions; 'tooltip' is hover text "
                    "lines; points also take 'color' and 'label'. Use 'regions' for "
                    "choropleth / heat-map requests, 'points' for markers. Values must "
                    "come from tool results - never invent numbers.",
        input_schema={
            "type": "object",
            "properties": {
                "points": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "place": {"type": "string", "description": "District id (AZ-01) or state code (AZ)"},
                        "value": {"type": "number", "description": "Sizes the marker"},
                        "color": {"type": "string", "description": "Hex color, e.g. #4a90e2"},
                        "label": {"type": "string"},
                        "tooltip": {"type": "array", "items": {"type": "string"},
                                    "description": "Hover text lines"},
                    },
                    "required": ["place"],
                }},
                "regions": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "place": {"type": "string", "description": "District id like AZ-01"},
                        "value": {"type": "number", "description": "Shades the district (heat map)"},
                        "color": {"type": "string", "description": "Explicit hex color, e.g. to color by party"},
                        "label": {"type": "string", "description": "Text drawn on the district, e.g. its number"},
                        "tooltip": {"type": "array", "items": {"type": "string"},
                                    "description": "Hover text lines"},
                    },
                    "required": ["place"],
                }},
                "title": {"type": "string"},
            },
        },
        handler=_render_map,
    ),
    ToolSpec(
        name="map_state",
        description="Build a whole-state House map in one call (reliable - prefer "
                    "this over hand-building render_map for 'show/map a state'). "
                    "Params: state (two-letter), color_by ('party' or 'money'), shape "
                    "('regions' choropleth or 'points' bubbles), label (true to draw "
                    "district numbers). Tooltips (candidate, party, total) are added.",
        input_schema={
            "type": "object",
            "properties": {
                "state": {"type": "string", "description": "Two-letter state code"},
                "color_by": {"type": "string", "enum": ["party", "money", "value"],
                             "description": "Color by party, or shade by money"},
                "shape": {"type": "string", "enum": ["regions", "points"],
                          "description": "Choropleth polygons or bubbles"},
                "label": {"type": "string", "enum": ["district", "total", "name", "none"],
                          "description": "Label each district with its number, total, candidate name, or nothing"},
            },
            "required": ["state"],
        },
        handler=_map_state,
    ),
    ToolSpec(
        name="map_nation",
        description="Map the whole country's House funding at once. 'regions' "
                    "(default) shades every district by its state's total raised - a "
                    "nationwide state-level heat map; 'points' drops one bubble per "
                    "state. Use for 'all states', 'nationwide', 'which states raise "
                    "the most' questions. Totals are summed server-side.",
        input_schema={
            "type": "object",
            "properties": {
                "shape": {"type": "string", "enum": ["regions", "points"],
                          "description": "State heat map (regions) or per-state bubbles"},
            },
        },
        handler=_map_nation,
    ),
    ToolSpec(
        name="emit_scene",
        description="Build MapLibre scene commands for a district's funding view "
                    "(district plus money flows). Use for 'who funds <district>'.",
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
