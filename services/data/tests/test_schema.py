from sqlalchemy import text


def test_schema_creates_all_tables(db_engine):
    with db_engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        )).scalars().all()
    assert {"candidates", "committees", "candidate_committee", "contributions",
            "candidate_totals"} <= set(rows)
