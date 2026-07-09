from decimal import Decimal
from otm_data.load import (
    load_candidates, load_committees, load_linkages,
    load_contributions, linked_committee_ids,
)
from otm_data.oracle import (
    resolve_candidate, committees_for_candidate, total_raised, top_donors,
    candidate_finance, contributions_by_state, district_candidates,
    classify_industry, industry_breakdown, top_employers, state_field,
    search_candidates, funding_timeline, donor_size_breakdown, top_candidates,
    rank_districts,
)
from otm_data.load import load_candidate_totals


def _lines(name):
    with open(f"tests/fixtures/{name}") as f:
        return f.read().splitlines()


def _seed(engine):
    load_candidates(engine, _lines("cn_sample.txt"))
    load_committees(engine, _lines("cm_sample.txt"))
    load_linkages(engine, _lines("ccl_sample.txt"))
    load_contributions(engine, _lines("itcont_sample.txt"),
                       cmte_ids=linked_committee_ids(engine))


def test_state_field(db_engine):
    _seed(db_engine)
    field = state_field(db_engine, "AZ")
    assert field
    az06 = [e for e in field if e.district == "06"]
    assert az06 and az06[0].cand_id == "H2AZ06099"


def test_rank_districts_orders_and_dedupes(db_engine):
    _seed(db_engine)
    desc = rank_districts(db_engine, order="desc", limit=25)
    asc = rank_districts(db_engine, order="asc", limit=25)
    assert desc and asc
    # One row per district (the leading candidate), no duplicate seats.
    keys = [(d.state, d.district) for d in desc]
    assert len(keys) == len(set(keys))
    # Ranked correctly in each direction.
    assert [d.value for d in desc] == sorted((d.value for d in desc), reverse=True)
    assert [d.value for d in asc] == sorted(d.value for d in asc)
    # Least-funded <= best-funded, and both surface the same district set.
    assert asc[0].value <= desc[0].value
    assert set(keys) == {(d.state, d.district) for d in asc}


def test_rank_districts_respects_limit(db_engine):
    _seed(db_engine)
    assert len(rank_districts(db_engine, order="asc", limit=1)) == 1


def test_classify_industry():
    assert classify_industry("GOOGLE LLC") == "Technology"
    assert classify_industry("GOLDMAN SACHS") == "Finance"
    assert classify_industry("RETIRED") == "Retired / Not employed"
    assert classify_industry("") == "Unlisted"
    assert classify_industry("ACME WIDGETS") == "Other"


def test_industry_breakdown_reconciles(db_engine):
    _seed(db_engine)
    cand = resolve_candidate(db_engine, state="AZ", district="06")
    inds = industry_breakdown(db_engine, cand.cand_id)
    assert inds
    assert sum(i.amount for i in inds) == total_raised(db_engine, cand.cand_id)
    emps = top_employers(db_engine, cand.cand_id, n=5)
    assert emps and emps[0].amount > 0


def test_district_candidates_ranked(db_engine):
    _seed(db_engine)
    cands = district_candidates(db_engine, state="AZ", district="06")
    assert len(cands) >= 1
    assert cands[0].cand_id == "H2AZ06099"
    assert cands[0].itemized > 0
    amounts = [c.itemized for c in cands]
    assert amounts == sorted(amounts, reverse=True)  # ranked by itemized desc


def test_resolve_candidate_hit(db_engine):
    _seed(db_engine)
    c = resolve_candidate(db_engine, state="AZ", district="06")
    assert c is not None
    assert c.cand_id == "H2AZ06099"
    assert c.name == "CISCOMANI, JUAN"


def test_resolve_candidate_miss_returns_none(db_engine):
    _seed(db_engine)
    assert resolve_candidate(db_engine, state="AZ", district="99") is None


def test_resolve_candidate_returns_top_fundraiser(db_engine):
    _seed(db_engine)  # H2AZ06099 with 500.00 in AZ-06
    # A second AZ-06 candidate whose committee raised more must win resolution.
    load_candidates(db_engine, [
        "H4AZ06222|BIGRAISER, PAT|DEM|2024|AZ|H|06|C|C|C00888888|||PHOENIX|AZ|85001",
    ])
    load_committees(db_engine, [
        "C00888888|BIGRAISER FOR CONGRESS|DOE, X|ADDR||PHOENIX|AZ|85001|P|H|DEM|Q|||H4AZ06222",
    ])
    load_linkages(db_engine, ["H4AZ06222|2024|2024|C00888888|H|P|LNK999"])
    load_contributions(db_engine, [
        "C00888888|N|Q2|P|2|15|IND|WHALE, MOE|PHOENIX|AZ|85001|BIGCO|CEO|06152024|9000.00||T9|1|||SUBZ",
    ], cmte_ids=linked_committee_ids(db_engine))

    c = resolve_candidate(db_engine, state="AZ", district="06")
    assert c is not None
    assert c.cand_id == "H4AZ06222"


def test_committees_for_candidate(db_engine):
    _seed(db_engine)
    assert committees_for_candidate(db_engine, "H2AZ06099") == ["C00770886"]


def test_total_raised_excludes_memo(db_engine):
    _seed(db_engine)
    # $500 real + $1000 memo (X) -> only $500 counts
    assert total_raised(db_engine, "H2AZ06099") == Decimal("500.00")


def test_candidate_finance(db_engine):
    _seed(db_engine)
    load_candidate_totals(db_engine, ["H2AZ06099|2024|1500.00|800.00"])
    fin = candidate_finance(db_engine, "H2AZ06099")
    assert fin is not None
    assert fin.receipts == Decimal("1500.00")
    assert fin.individual_total == Decimal("800.00")


def test_candidate_finance_missing_returns_none(db_engine):
    _seed(db_engine)
    assert candidate_finance(db_engine, "H2AZ06099") is None


def test_contributions_by_state(db_engine):
    _seed(db_engine)
    rows = contributions_by_state(db_engine, "H2AZ06099")
    assert len(rows) == 1
    assert rows[0].state == "AZ"
    assert rows[0].amount == Decimal("500.00")  # memo row excluded
    assert rows[0].count == 1


def test_top_donors_excludes_memo_and_orders(db_engine):
    _seed(db_engine)
    donors = top_donors(db_engine, "H2AZ06099", n=5)
    assert len(donors) == 1
    assert donors[0].name == "DOE, JOHN"
    assert donors[0].amount == Decimal("500.00")
    assert donors[0].state == "AZ"


def test_funding_timeline(db_engine):
    _seed(db_engine)
    rows = funding_timeline(db_engine, "H2AZ06099")
    assert rows
    by_month = {r.month: r for r in rows}
    assert "2024-06" in by_month  # the $500 gift dated 06152024
    assert by_month["2024-06"].amount == Decimal("500.00")  # $1000 memo excluded
    assert by_month["2024-06"].count == 1


def test_donor_size_breakdown(db_engine):
    _seed(db_engine)
    load_candidate_totals(db_engine, ["H2AZ06099|2024|1500.00|800.00"])
    res = donor_size_breakdown(db_engine, "H2AZ06099")
    assert res["individual_total"] == 800.0
    assert res["unitemized_small_dollar"] == 300.0  # 800 individual - 500 itemized
    assert any(b["range"] == "200_to_999" and b["amount"] == 500.0
               for b in res["itemized_buckets"])


def test_top_candidates_ranked(db_engine):
    _seed(db_engine)
    top = top_candidates(db_engine, metric="itemized", limit=25)
    assert top
    vals = [t.value for t in top]
    assert vals == sorted(vals, reverse=True)
    assert any(t.cand_id == "H2AZ06099" for t in top)
    load_candidate_totals(db_engine, ["H2AZ06099|2024|1500.00|800.00"])
    byrec = top_candidates(db_engine, metric="receipts", limit=25)
    assert any(t.cand_id == "H2AZ06099" and t.value == Decimal("1500.00") for t in byrec)


def test_search_candidates_by_name(db_engine):
    _seed(db_engine)
    matches = search_candidates(db_engine, "Ciscomani Juan")
    hit = [m for m in matches if m.cand_id == "H2AZ06099"]
    assert hit and hit[0].state == "AZ" and hit[0].district == "06"
