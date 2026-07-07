from sqlalchemy import text


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
