import os
from pathlib import Path
from sqlalchemy import Engine, create_engine, text

_SCHEMA = Path(__file__).with_name("schema.sql")


def get_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("OTM_DATABASE_URL", "postgresql+psycopg://otm:otm@localhost:5433/otm")
    return create_engine(url, future=True)


def apply_schema(engine: Engine) -> None:
    sql = _SCHEMA.read_text()
    with engine.begin() as conn:
        for statement in sql.split(";"):
            if statement.strip():
                conn.execute(text(statement))
