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
