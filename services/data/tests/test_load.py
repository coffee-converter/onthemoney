from sqlalchemy import text
from otm_data.load import (
    load_candidates, load_committees, load_linkages,
    load_contributions, linked_committee_ids,
)


def _lines(name):
    with open(f"tests/fixtures/{name}") as f:
        return f.read().splitlines()


def test_load_candidates_filters_to_house(db_engine):
    lines = _lines("cn_sample.txt") + [
        "S4AZ00099|SENATOR, SAM|DEM|2024|AZ|S|00|C|C|C00999999|||PHOENIX|AZ|85001",
    ]
    n = load_candidates(db_engine, lines, office="H", election_yr=2024)
    assert n == 1
    with db_engine.connect() as conn:
        offices = conn.execute(text("SELECT office FROM candidates")).scalars().all()
    assert offices == ["H"]


def test_load_pipeline_and_contribution_filter(db_engine):
    load_candidates(db_engine, _lines("cn_sample.txt"))
    load_committees(db_engine, _lines("cm_sample.txt"))
    load_linkages(db_engine, _lines("ccl_sample.txt"))
    cmte_ids = linked_committee_ids(db_engine, election_yr=2024)
    assert cmte_ids == {"C00770886"}

    n = load_contributions(db_engine, _lines("itcont_sample.txt"), cmte_ids=cmte_ids)
    assert n == 2  # both IND rows kept (memo filtering happens at query time)
    with db_engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM contributions")).scalar()
    assert total == 2


def test_load_contributions_excludes_unlinked_committees(db_engine):
    n = load_contributions(db_engine, _lines("itcont_sample.txt"), cmte_ids=set())
    assert n == 0
