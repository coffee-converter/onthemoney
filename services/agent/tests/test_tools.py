from otm_agent.tools import resolve_entity, funding_summary


def test_resolve_entity_hit(seeded_engine):
    res = resolve_entity(seeded_engine, state="AZ", district="06")
    assert res is not None
    assert res.candidate.cand_id == "H2AZ06099"
    assert res.committees == ["C00770886"]


def test_resolve_entity_miss(seeded_engine):
    assert resolve_entity(seeded_engine, state="AZ", district="99") is None


def test_funding_summary_excludes_memo(seeded_engine):
    fs = funding_summary(seeded_engine, "H2AZ06099", top_n=5)
    assert fs.total == "500.00"
    assert len(fs.donors) == 1
    assert fs.donors[0].name == "DOE, JOHN"
    assert fs.donors[0].amount == "500.00"
