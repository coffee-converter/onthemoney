from dataclasses import dataclass
from sqlalchemy import Engine
from otm_data.oracle import (
    CandidateRef, resolve_candidate, committees_for_candidate,
    total_raised, top_donors, candidate_finance,
)


@dataclass
class EntityResolution:
    candidate: CandidateRef
    committees: list[str]


@dataclass
class DonorLine:
    name: str
    employer: str
    amount: str
    state: str = ""


@dataclass
class FundingSummary:
    cand_id: str
    total: str                        # itemized individual receipts we tallied
    donors: list[DonorLine]
    receipts: str | None = None       # official FEC total raised (all sources)
    individual_total: str | None = None  # official individual contributions


def resolve_entity(engine: Engine, *, state: str, district: str,
                   cycle: int = 2024) -> EntityResolution | None:
    cand = resolve_candidate(engine, state=state, district=district, election_yr=cycle)
    if cand is None:
        return None
    cmtes = committees_for_candidate(engine, cand.cand_id, election_yr=cycle)
    return EntityResolution(candidate=cand, committees=cmtes)


def funding_summary(engine: Engine, cand_id: str, *, cycle: int = 2024,
                    top_n: int = 10) -> FundingSummary:
    total = total_raised(engine, cand_id, election_yr=cycle)
    donors = top_donors(engine, cand_id, election_yr=cycle, n=top_n)
    fin = candidate_finance(engine, cand_id, election_yr=cycle)
    return FundingSummary(
        cand_id=cand_id,
        total=f"{total:.2f}",
        receipts=(f"{fin.receipts:.2f}" if fin else None),
        individual_total=(f"{fin.individual_total:.2f}" if fin else None),
        donors=[DonorLine(name=d.name, employer=d.employer,
                          amount=f"{d.amount:.2f}", state=d.state)
                for d in donors],
    )
