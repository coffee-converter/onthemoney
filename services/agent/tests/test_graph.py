from otm_agent.graph import supervise, parse_claimed_total
from otm_agent.answer import Confidence


def test_parse_claimed_total():
    assert parse_claimed_total("reported 500.00 in receipts") == "500.00"
    assert parse_claimed_total("no figure here") is None


def test_parse_claimed_total_handles_currency_and_commas():
    assert parse_claimed_total("Total: $38,820.00 for 2024") == "38820.00"


def test_supervise_match_keeps_high(seeded_engine):
    v = supervise(seeded_engine, state="AZ", district="06", claimed_total="500.00")
    assert v.verified is True
    assert v.truth_total == "500.00"
    assert v.confidence is Confidence.HIGH


def test_supervise_mismatch_downgrades(seeded_engine):
    v = supervise(seeded_engine, state="AZ", district="06", claimed_total="999.00")
    assert v.verified is False
    assert v.confidence is Confidence.INSUFFICIENT
