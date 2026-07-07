import pytest

import otm_agent.config as config
from otm_agent.config import get_settings


def test_default_model(monkeypatch):
    monkeypatch.delenv("OTM_AGENT_MODEL", raising=False)
    assert get_settings().model == "claude-sonnet-5"


def test_model_override(monkeypatch):
    monkeypatch.setenv("OTM_AGENT_MODEL", "claude-opus-4-8")
    assert get_settings().model == "claude-opus-4-8"


def test_seeded_engine_has_candidate(seeded_engine):
    from sqlalchemy import text
    with seeded_engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM candidates")).scalar()
    assert n == 1


from otm_agent.config import estimate_cost


def test_estimate_cost_uses_per_million_pricing():
    # 1M input + 1M output at a known rate; exact value depends on the price map,
    # so assert it is positive and scales with tokens rather than a magic number.
    a = estimate_cost("claude-sonnet-5", 1_000_000, 0)
    b = estimate_cost("claude-sonnet-5", 2_000_000, 0)
    assert a > 0
    assert b == pytest.approx(2 * a)


def test_estimate_cost_unknown_model_falls_back():
    assert estimate_cost("some-unlisted-model", 1000, 1000) > 0


def test_estimate_cost_matches_dated_and_tagged_model_ids():
    # A deploy id may carry a snapshot date and/or a context-window tag; all
    # forms of the same family must price identically, not hit the fallback.
    base = estimate_cost("claude-opus-4-8", 1_000_000, 1_000_000)
    assert estimate_cost("claude-opus-4-8-20260101", 1_000_000, 1_000_000) == base
    assert estimate_cost("claude-opus-4-8[1m]", 1_000_000, 1_000_000) == base
    # Opus is far pricier than the mid-tier fallback, so a fallback miss would
    # roughly quarter this figure — guard against that regression explicitly.
    assert base > estimate_cost("some-unlisted-model", 1_000_000, 1_000_000)
