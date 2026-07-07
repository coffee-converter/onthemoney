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


from datetime import datetime, timezone
from otm_agent.demo_guard import DemoConfig, rate_limited

_CFG = DemoConfig(enabled=True, daily_usd=5.0, max_query_chars=500,
                  rate_per_min=3, rate_per_day=5, max_tokens=1024, admin_secret=None)


def test_rate_limit_trips_after_per_minute_cap(seeded_engine):
    now = datetime(2026, 7, 7, 14, 3, 0, tzinfo=timezone.utc)
    results = [rate_limited(seeded_engine, _CFG, "1.1.1.1", now) for _ in range(4)]
    assert results == [False, False, False, True]  # 4th within the minute trips


def test_rate_limit_isolated_per_ip(seeded_engine):
    now = datetime(2026, 7, 7, 15, 0, 0, tzinfo=timezone.utc)
    for _ in range(3):
        rate_limited(seeded_engine, _CFG, "2.2.2.2", now)
    assert rate_limited(seeded_engine, _CFG, "3.3.3.3", now) is False  # different IP


from datetime import date
from otm_agent.demo_guard import budget_exceeded, bill


def test_budget_not_exceeded_when_empty(seeded_engine):
    assert budget_exceeded(seeded_engine, _CFG, date(2026, 7, 7)) is False


def test_bill_accumulates_and_trips(seeded_engine):
    day = date(2026, 7, 8)
    bill(seeded_engine, day, 2.5)
    bill(seeded_engine, day, 3.0)  # total 5.5 >= 5.0 cap
    assert budget_exceeded(seeded_engine, _CFG, day) is True
