from otm_agent.answer import compose_answer, Confidence, fec_committee_url


def test_committee_url():
    assert fec_committee_url("C00770886") == \
        "https://www.fec.gov/data/committee/C00770886/"


def test_compose_answer_high_confidence(seeded_engine):
    ans = compose_answer(seeded_engine, state="AZ", district="06")
    assert ans.confidence is Confidence.HIGH
    assert "500.00" in ans.narration
    assert ans.scene is not None
    assert ans.scene["highlight"] == {"state": "AZ", "district": "06"}
    assert any(c.url.endswith("/C00770886/") for c in ans.citations)


def test_compose_answer_insufficient_when_no_candidate(seeded_engine):
    ans = compose_answer(seeded_engine, state="AZ", district="99")
    assert ans.confidence is Confidence.INSUFFICIENT
    assert ans.scene is None
    assert ans.citations == []
