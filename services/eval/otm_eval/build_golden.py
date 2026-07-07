"""Select golden cases from whatever DB is loaded and derive their expectations
from the oracle, so the golden set is reproducible ground truth rather than
hand-typed numbers. Ranks districts by their leading candidate's itemized
individual receipts — summed from `contributions` (memo transactions excluded),
exactly the way oracle.state_field / resolve_candidate rank them. There is no
precomputed itemized column; `candidate_totals` holds only official
receipts/individual_total, not the itemized subset.
"""
from otm_eval.golden import GoldenItem
from otm_eval.system import derive_expected
from sqlalchemy import text

# Every House district's leading candidate and its itemized total, in one query.
# DISTINCT ON keeps the top candidate per district; memo_cd='X' is excluded to
# match the oracle's definition of itemized receipts. District is normalized
# with LPAD to 2 chars so at-large seats stored as both "0" and "00" collapse
# into a single district instead of double-counting.
_LEADERS_SQL = text(
    "SELECT DISTINCT ON (st, di) st, di, itemized FROM ("
    "  SELECT c.office_state AS st, LPAD(c.district, 2, '0') AS di, c.cand_id AS cid, "
    "    COALESCE(SUM(ct.amount), 0) AS itemized "
    "  FROM candidates c "
    "  LEFT JOIN candidate_committee cc "
    "    ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
    "  LEFT JOIN contributions ct "
    "    ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
    "  WHERE c.office = 'H' AND c.election_yr = :yr "
    "  GROUP BY c.office_state, LPAD(c.district, 2, '0'), c.cand_id) s "
    "ORDER BY st, di, itemized DESC"
)


def _leader_districts(engine) -> list[tuple[str, str, float]]:
    """(state, district, leader_itemized) for every House district."""
    with engine.connect() as conn:
        rows = conn.execute(_LEADERS_SQL, {"yr": 2024}).all()
    return [(r.st, str(r.di).zfill(2), float(r.itemized)) for r in rows]


def _case(engine, state: str, district: str, label: str) -> dict:
    item = GoldenItem(
        id=f"{state.lower()}{district}-funds",
        query=f"Who funds the representative in {state}-{district}?",
        state=state, district=district,
        expected_tools=["resolve_entity", "funding_summary", "emit_scene"],
        expected_committees=[], expected_total=None, expected_scene=None,
        calibration_label=label,
    )
    # derive_expected grounds committees / total / scene against the oracle; use
    # its scene verbatim so the golden and recorded baselines cannot drift.
    exp = derive_expected(engine, item)
    return {
        "id": item.id, "query": item.query, "state": state, "district": district,
        "expected_tools": item.expected_tools, "expected_committees": exp.committees,
        "expected_total": exp.total, "expected_scene": exp.scene,
        "calibration_label": label,
    }


def select_cases(engine, *, n_high: int = 16, n_partial: int = 4) -> list[dict]:
    leaders = _leader_districts(engine)
    highs = sorted((d for d in leaders if d[2] > 0), key=lambda d: d[2],
                   reverse=True)[:n_high]
    partials = [d for d in leaders if d[2] == 0][:n_partial]
    cases: list[dict] = []
    for st, di, _ in highs:
        cases.append(_case(engine, st, di, "high"))
    for st, di, _ in partials:
        cases.append(_case(engine, st, di, "partial"))
    # Synthesized insufficient cases: districts that cannot exist.
    for st in ("AZ", "TX", "CA", "NY"):
        cases.append({
            "id": f"{st.lower()}99-none",
            "query": f"Who funds the representative in {st}-99?",
            "state": st, "district": "99", "expected_tools": ["resolve_entity"],
            "expected_committees": [], "expected_total": None, "expected_scene": None,
            "calibration_label": "insufficient",
        })
    # Fail loudly if district normalization ever lets a real seat double-count.
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), f"duplicate golden ids: {ids}"
    return cases
