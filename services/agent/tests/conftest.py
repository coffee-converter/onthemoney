import os
import pytest
from sqlalchemy import text
from otm_data.db import get_engine, apply_schema
from otm_data.load import (
    load_candidates, load_committees, load_linkages,
    load_contributions, linked_committee_ids,
)

TABLES = ["contributions", "candidate_committee", "committees", "candidates",
          "candidate_totals"]

# Standard AZ-06 seed (mirrors the data package fixtures; kept inline so the agent
# package tests do not reach into the data package's test tree).
CN = ["H2AZ06099|CISCOMANI, JUAN|REP|2024|AZ|H|06|I|C|C00770886|123 MAIN ST||TUCSON|AZ|85701"]
CM = ["C00770886|CISCOMANI FOR CONGRESS|SMITH, JANE|PO BOX 1||TUCSON|AZ|85701|P|H|REP|Q|||H2AZ06099"]
CCL = ["H2AZ06099|2024|2024|C00770886|H|P|LNK123"]
ITCONT = [
    "C00770886|N|Q2|P|202400000|15|IND|DOE, JOHN|TUCSON|AZ|85701|ACME CORP|ENGINEER|06152024|500.00||T1|1|||SUBA",
    "C00770886|N|Q2|P|202400001|15|IND|ROE, JANE|MESA|AZ|85201|SELF|CONSULTANT|06162024|1000.00||T2|1|X|MEMO|SUBB",
]


@pytest.fixture()
def db_engine():
    url = os.environ.get("OTM_TEST_DATABASE_URL",
                         "postgresql+psycopg://otm:otm@localhost:5433/otm_test")
    engine = get_engine(url)
    apply_schema(engine)
    with engine.begin() as conn:
        for t in TABLES:
            conn.execute(text(f"TRUNCATE {t} CASCADE"))
    yield engine
    engine.dispose()


@pytest.fixture()
def seeded_engine(db_engine):
    load_candidates(db_engine, CN)
    load_committees(db_engine, CM)
    load_linkages(db_engine, CCL)
    load_contributions(db_engine, ITCONT, cmte_ids=linked_committee_ids(db_engine))
    return db_engine
