from typing import Iterable
from sqlalchemy import Engine, text
from otm_data.parse import (
    parse_candidate, parse_committee, parse_linkage, parse_contribution,
    parse_candidate_total,
)


def load_candidates(engine: Engine, lines: Iterable[str], *,
                    office: str = "H", election_yr: int = 2024) -> int:
    rows = [parse_candidate(l) for l in lines if l.strip()]
    rows = [r for r in rows if r.office == office and r.election_yr == election_yr]
    stmt = text(
        "INSERT INTO candidates "
        "(cand_id, name, party, election_yr, office_state, office, district, pcc_cmte_id) "
        "VALUES (:cand_id,:name,:party,:election_yr,:office_state,:office,:district,:pcc_cmte_id) "
        "ON CONFLICT (cand_id) DO NOTHING"
    )
    with engine.begin() as conn:
        for r in rows:
            conn.execute(stmt, r.__dict__)
    return len(rows)


def load_committees(engine: Engine, lines: Iterable[str]) -> int:
    rows = [parse_committee(l) for l in lines if l.strip()]
    stmt = text(
        "INSERT INTO committees (cmte_id, name, cand_id) "
        "VALUES (:cmte_id,:name,:cand_id) ON CONFLICT (cmte_id) DO NOTHING"
    )
    with engine.begin() as conn:
        for r in rows:
            conn.execute(stmt, r.__dict__)
    return len(rows)


def load_linkages(engine: Engine, lines: Iterable[str], *, election_yr: int = 2024) -> int:
    rows = [parse_linkage(l) for l in lines if l.strip()]
    rows = [r for r in rows if r.election_yr == election_yr]
    stmt = text(
        "INSERT INTO candidate_committee "
        "(cand_id, cmte_id, cmte_type, cmte_desig, election_yr) "
        "VALUES (:cand_id,:cmte_id,:cmte_type,:cmte_desig,:election_yr) "
        "ON CONFLICT (cand_id, cmte_id, election_yr) DO NOTHING"
    )
    with engine.begin() as conn:
        for r in rows:
            conn.execute(stmt, r.__dict__)
    return len(rows)


def load_candidate_totals(engine: Engine, lines: Iterable[str]) -> int:
    rows = [parse_candidate_total(l) for l in lines if l.strip()]
    stmt = text(
        "INSERT INTO candidate_totals (cand_id, cycle, receipts, individual_total) "
        "VALUES (:cand_id,:cycle,:receipts,:individual_total) "
        "ON CONFLICT (cand_id, cycle) DO NOTHING"
    )
    with engine.begin() as conn:
        for r in rows:
            conn.execute(stmt, r.__dict__)
    return len(rows)


def linked_committee_ids(engine: Engine, *, election_yr: int = 2024) -> set[str]:
    with engine.connect() as conn:
        return set(conn.execute(
            text("SELECT cmte_id FROM candidate_committee WHERE election_yr = :yr"),
            {"yr": election_yr},
        ).scalars().all())


def house_committee_ids(engine: Engine, *, election_yr: int = 2024) -> set[str]:
    # Committees linked to candidates in the candidates table. When that table
    # holds only House candidates, this returns just the House committees.
    with engine.connect() as conn:
        return set(conn.execute(text(
            "SELECT DISTINCT cc.cmte_id FROM candidate_committee cc "
            "JOIN candidates c ON c.cand_id = cc.cand_id "
            "WHERE cc.election_yr = :yr"
        ), {"yr": election_yr}).scalars().all())


def load_contributions(engine: Engine, lines: Iterable[str], *, cmte_ids: set[str]) -> int:
    rows = [parse_contribution(l) for l in lines if l.strip()]
    rows = [r for r in rows if r.entity_type == "IND" and r.cmte_id in cmte_ids]
    stmt = text(
        "INSERT INTO contributions "
        "(sub_id, cmte_id, name, city, state, zip_code, employer, occupation, "
        " transaction_dt, amount, entity_type, memo_cd) "
        "VALUES (:sub_id,:cmte_id,:name,:city,:state,:zip_code,:employer,:occupation,"
        " :transaction_dt,:amount,:entity_type,:memo_cd) "
        "ON CONFLICT (sub_id) DO NOTHING"
    )
    with engine.begin() as conn:
        for r in rows:
            conn.execute(stmt, r.__dict__)
    return len(rows)
