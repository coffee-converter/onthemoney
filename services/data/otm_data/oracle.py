from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy import Engine, text


@dataclass
class CandidateRef:
    cand_id: str
    name: str
    party: str
    office_state: str
    district: str


@dataclass
class DonorTotal:
    name: str
    employer: str
    amount: Decimal


def resolve_candidate(engine: Engine, *, state: str, district: str,
                      election_yr: int = 2024) -> CandidateRef | None:
    # A district can have many candidates; resolve to the one with the most
    # itemized individual receipts on file (memo transactions excluded), so
    # "the representative" lands on the leading candidate rather than an
    # arbitrary minor filer.
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT c.cand_id, c.name, c.party, c.office_state, c.district "
            "FROM candidates c "
            "LEFT JOIN candidate_committee cc "
            "  ON cc.cand_id = c.cand_id AND cc.election_yr = c.election_yr "
            "LEFT JOIN contributions ct "
            "  ON ct.cmte_id = cc.cmte_id AND COALESCE(ct.memo_cd, '') <> 'X' "
            "WHERE c.office = 'H' AND c.office_state = :state "
            "  AND c.district = :district AND c.election_yr = :yr "
            "GROUP BY c.cand_id, c.name, c.party, c.office_state, c.district "
            "ORDER BY COALESCE(SUM(ct.amount), 0) DESC, c.cand_id "
            "LIMIT 1"
        ), {"state": state, "district": district, "yr": election_yr}).first()
    return CandidateRef(*row) if row else None


def committees_for_candidate(engine: Engine, cand_id: str, *,
                             election_yr: int = 2024) -> list[str]:
    with engine.connect() as conn:
        return list(conn.execute(text(
            "SELECT cmte_id FROM candidate_committee "
            "WHERE cand_id = :c AND election_yr = :yr ORDER BY cmte_id"
        ), {"c": cand_id, "yr": election_yr}).scalars().all())


def total_raised(engine: Engine, cand_id: str, *, election_yr: int = 2024) -> Decimal:
    with engine.connect() as conn:
        val = conn.execute(text(
            "SELECT COALESCE(SUM(ct.amount), 0) FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X'"
        ), {"c": cand_id, "yr": election_yr}).scalar()
    return Decimal(val)


def top_donors(engine: Engine, cand_id: str, *, election_yr: int = 2024,
               n: int = 10) -> list[DonorTotal]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT ct.name, COALESCE(ct.employer, '') AS employer, SUM(ct.amount) AS amt "
            "FROM contributions ct "
            "JOIN candidate_committee cc ON cc.cmte_id = ct.cmte_id "
            "WHERE cc.cand_id = :c AND cc.election_yr = :yr "
            "AND COALESCE(ct.memo_cd, '') <> 'X' "
            "GROUP BY ct.name, COALESCE(ct.employer, '') "
            "ORDER BY amt DESC, ct.name ASC LIMIT :n"
        ), {"c": cand_id, "yr": election_yr, "n": n}).all()
    return [DonorTotal(name=r[0], employer=r[1], amount=Decimal(r[2])) for r in rows]
