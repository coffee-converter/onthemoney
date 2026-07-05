from decimal import Decimal
from otm_data.load import (
    load_candidates, load_committees, load_linkages,
    load_contributions, linked_committee_ids,
)
from otm_data.oracle import (
    resolve_candidate, committees_for_candidate, total_raised, top_donors,
    candidate_finance, contributions_by_state, district_candidates,
    classify_industry, industry_breakdown, top_employers, state_field,
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
