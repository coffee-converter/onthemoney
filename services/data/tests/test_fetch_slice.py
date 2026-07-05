from decimal import Decimal
from otm_data.fetch_slice import build_slice, write_slice
from otm_data.parse import (
    parse_candidate, parse_committee, parse_linkage, parse_contribution,
)


class FakeClient:
    def candidates(self, state, district, cycle):
        return [{
            "candidate_id": "H2AZ06099", "name": "CISCOMANI, JUAN", "party": "REP",
            "state": state, "office": "H", "district": district,
        }]

    def committees(self, candidate_id, cycle):
        return [{"committee_id": "C00770886", "name": "CISCOMANI FOR CONGRESS"}]

    def schedule_a(self, committee_id, cycle, limit):
        return [
            {"contributor_name": "DOE, JOHN", "contributor_city": "TUCSON",
             "contributor_state": "AZ", "contributor_zip": "85701",
             "contributor_employer": "ACME CORP", "contributor_occupation": "ENGINEER",
             "contribution_receipt_date": "2024-06-15T00:00:00",
             "contribution_receipt_amount": 500.0, "memo_code": None, "sub_id": "SUBA"},
        ]


def test_build_slice_counts():
    slice_ = build_slice(FakeClient(), [("AZ", "06")], cycle=2024)
    assert len(slice_["cn"]) == 1
    assert len(slice_["cm"]) == 1
    assert len(slice_["ccl"]) == 1
    assert len(slice_["itcont"]) == 1


def test_emitted_lines_parse_correctly():
    slice_ = build_slice(FakeClient(), [("AZ", "06")], cycle=2024)

    cand = parse_candidate(slice_["cn"][0])
    assert cand.cand_id == "H2AZ06099"
    assert cand.office == "H"
    assert cand.district == "06"
    assert cand.election_yr == 2024
    assert cand.pcc_cmte_id == "C00770886"

    cmte = parse_committee(slice_["cm"][0])
    assert cmte.cmte_id == "C00770886"
    assert cmte.cand_id == "H2AZ06099"

    link = parse_linkage(slice_["ccl"][0])
    assert link.cand_id == "H2AZ06099"
    assert link.cmte_id == "C00770886"
    assert link.election_yr == 2024

    contrib = parse_contribution(slice_["itcont"][0])
    assert contrib.cmte_id == "C00770886"
    assert contrib.entity_type == "IND"
    assert contrib.name == "DOE, JOHN"
    assert contrib.amount == Decimal("500.00")
    assert contrib.memo_cd == ""
    assert contrib.sub_id == "SUBA"


class NullFieldClient(FakeClient):
    def schedule_a(self, committee_id, cycle, limit):
        # Real FEC rows often have null employer/occupation/city.
        return [
            {"contributor_name": "DOE, JOHN", "contributor_city": None,
             "contributor_state": "AZ", "contributor_zip": None,
             "contributor_employer": None, "contributor_occupation": None,
             "contribution_receipt_date": "2024-06-15T00:00:00",
             "contribution_receipt_amount": 250.0, "memo_code": None, "sub_id": "SUBX"},
        ]


def test_null_contribution_fields_do_not_crash():
    slice_ = build_slice(NullFieldClient(), [("AZ", "06")], cycle=2024)
    contrib = parse_contribution(slice_["itcont"][0])
    assert contrib.entity_type == "IND"
    assert contrib.employer == ""
    assert contrib.amount == Decimal("250.00")
    assert contrib.sub_id == "SUBX"


def test_write_slice_creates_bulk_files(tmp_path):
    slice_ = build_slice(FakeClient(), [("AZ", "06")], cycle=2024)
    write_slice(slice_, tmp_path)
    for name in ["cn", "cm", "ccl", "itcont"]:
        assert (tmp_path / f"{name}.txt").exists()
