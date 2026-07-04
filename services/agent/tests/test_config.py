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
