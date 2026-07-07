from sqlalchemy import text

from otm_agent.demo_guard import load_demo_config, query_hash


def test_demo_tables_exist(seeded_engine):
    with seeded_engine.connect() as conn:
        found = {
            r[0]
            for r in conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name LIKE 'demo_%'"
            ))
        }
    assert {"demo_rate_limit", "demo_budget_ledger", "demo_answer_cache"} <= found


def test_config_defaults_off(monkeypatch):
    monkeypatch.delenv("OTM_DEMO_ENABLED", raising=False)
    cfg = load_demo_config()
    assert cfg.enabled is False
    assert cfg.daily_usd == 5.0
    assert cfg.max_query_chars == 500


def test_config_enabled_and_overrides(monkeypatch):
    monkeypatch.setenv("OTM_DEMO_ENABLED", "1")
    monkeypatch.setenv("OTM_DEMO_DAILY_USD", "12.5")
    cfg = load_demo_config()
    assert cfg.enabled is True
    assert cfg.daily_usd == 12.5


def test_query_hash_normalizes():
    assert query_hash("Where is IL-04?") == query_hash("  where is  il-04  ")
    assert query_hash("Who funds AOC?") != query_hash("Who funds MTG?")
