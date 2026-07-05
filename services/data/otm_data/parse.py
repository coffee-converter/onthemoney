from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class Candidate:
    cand_id: str
    name: str
    party: str
    election_yr: int | None
    office_state: str
    office: str
    district: str
    pcc_cmte_id: str


@dataclass
class Committee:
    cmte_id: str
    name: str
    cand_id: str


@dataclass
class Linkage:
    cand_id: str
    cmte_id: str
    cmte_type: str
    cmte_desig: str
    election_yr: int | None


@dataclass
class CandidateTotal:
    cand_id: str
    cycle: int | None
    receipts: Decimal
    individual_total: Decimal


@dataclass
class Contribution:
    sub_id: str
    cmte_id: str
    name: str
    city: str
    state: str
    zip_code: str
    employer: str
    occupation: str
    transaction_dt: date | None
    amount: Decimal
    entity_type: str
    memo_cd: str


def _int(v: str) -> int | None:
    return int(v) if v.strip().isdigit() else None


def _fec_date(v: str) -> date | None:
    v = v.strip()
    if len(v) != 8:
        return None
    try:
        return datetime.strptime(v, "%m%d%Y").date()
    except ValueError:
        return None


def parse_candidate(line: str) -> Candidate:
    f = line.rstrip("\n").split("|")
    return Candidate(
        cand_id=f[0], name=f[1], party=f[2], election_yr=_int(f[3]),
        office_state=f[4], office=f[5], district=f[6], pcc_cmte_id=f[9],
    )


def parse_committee(line: str) -> Committee:
    f = line.rstrip("\n").split("|")
    return Committee(cmte_id=f[0], name=f[1], cand_id=f[14])


def parse_linkage(line: str) -> Linkage:
    f = line.rstrip("\n").split("|")
    return Linkage(
        cand_id=f[0], cmte_id=f[3], cmte_type=f[4], cmte_desig=f[5],
        election_yr=_int(f[2]),
    )


def parse_candidate_total(line: str) -> CandidateTotal:
    # cand_id|cycle|receipts|individual_total
    f = line.rstrip("\n").split("|")
    return CandidateTotal(
        cand_id=f[0], cycle=_int(f[1]),
        receipts=Decimal(f[2] or "0"), individual_total=Decimal(f[3] or "0"),
    )


def parse_contribution(line: str) -> Contribution:
    f = line.rstrip("\n").split("|")
    return Contribution(
        cmte_id=f[0], entity_type=f[6], name=f[7], city=f[8], state=f[9],
        zip_code=f[10], employer=f[11], occupation=f[12],
        transaction_dt=_fec_date(f[13]), amount=Decimal(f[14] or "0"),
        memo_cd=f[18], sub_id=f[20],
    )
