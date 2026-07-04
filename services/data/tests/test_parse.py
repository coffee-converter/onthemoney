from decimal import Decimal
from datetime import date
from otm_data.parse import (
    parse_candidate, parse_committee, parse_linkage, parse_contribution,
)


def _first_line(name):
    with open(f"tests/fixtures/{name}") as f:
        return f.readline().rstrip("\n")


def test_parse_candidate():
    c = parse_candidate(_first_line("cn_sample.txt"))
    assert c.cand_id == "H2AZ06099"
    assert c.name == "CISCOMANI, JUAN"
    assert c.office == "H"
    assert c.office_state == "AZ"
    assert c.district == "06"
    assert c.election_yr == 2024
    assert c.pcc_cmte_id == "C00770886"


def test_parse_committee():
    c = parse_committee(_first_line("cm_sample.txt"))
    assert c.cmte_id == "C00770886"
    assert c.name == "CISCOMANI FOR CONGRESS"
    assert c.cand_id == "H2AZ06099"


def test_parse_linkage():
    lk = parse_linkage(_first_line("ccl_sample.txt"))
    assert lk.cand_id == "H2AZ06099"
    assert lk.cmte_id == "C00770886"
    assert lk.election_yr == 2024


def test_parse_contribution_individual():
    row = parse_contribution(_first_line("itcont_sample.txt"))
    assert row.cmte_id == "C00770886"
    assert row.name == "DOE, JOHN"
    assert row.amount == Decimal("500.00")
    assert row.entity_type == "IND"
    assert row.transaction_dt == date(2024, 6, 15)
    assert row.memo_cd == ""
    assert row.sub_id == "SUBA"


def test_parse_contribution_memo_flag():
    lines = open("tests/fixtures/itcont_sample.txt").read().splitlines()
    memo = parse_contribution(lines[1])
    assert memo.memo_cd == "X"
    assert memo.amount == Decimal("1000.00")
