import os
import pytest
from sqlalchemy import text
from otm_data.db import get_engine, apply_schema

TABLES = ["contributions", "candidate_committee", "committees", "candidates"]


@pytest.fixture()
def db_engine():
    url = os.environ.get("OTM_TEST_DATABASE_URL",
                         "postgresql+psycopg://otm:otm@localhost:5433/otm")
    engine = get_engine(url)
    apply_schema(engine)
    with engine.begin() as conn:
        for t in TABLES:
            conn.execute(text(f"TRUNCATE {t} CASCADE"))
    yield engine
    engine.dispose()
