from decimal import Decimal
from otm_data.load import (
    load_candidates, load_committees, load_linkages,
    load_contributions, linked_committee_ids,
)
from otm_data.oracle import (
    resolve_candidate, committees_for_candidate, total_raised, top_donors,
)


def _lines(name):
    with open(f"tests/fixtures/{name}") as f:
        return f.read().splitlines()


def _seed(engine):
    load_candidates(engine, _lines("cn_sample.txt"))
    load_committees(engine, _lines("cm_sample.txt"))
    load_linkages(engine, _lines("ccl_sample.txt"))
    load_contributions(engine, _lines("itcont_sample.txt"),
                       cmte_ids=linked_committee_ids(engine))


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


def test_top_donors_excludes_memo_and_orders(db_engine):
    _seed(db_engine)
    donors = top_donors(db_engine, "H2AZ06099", n=5)
    assert len(donors) == 1
    assert donors[0].name == "DOE, JOHN"
    assert donors[0].amount == Decimal("500.00")
