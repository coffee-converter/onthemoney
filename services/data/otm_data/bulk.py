"""Nationwide bulk ingest.

Streams FEC's full individual-contributions file (indiv24.zip, ~4 GB compressed)
without unzipping it to disk, filters to House-linked committees, and COPYs the
rows into Postgres. Also loads candidate financial summaries (weball) for the
official totals.
"""
import io
import zipfile
from decimal import Decimal
from pathlib import Path
from sqlalchemy import Engine
from otm_data.parse import parse_contribution


def zip_lines(zip_path: str | Path, hint: str):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        name = next((n for n in names if hint in n.lower()), names[0])
        with zf.open(name) as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8", errors="replace"):
                yield line


def bulk_load_contributions(engine: Engine, zip_path: str | Path, *,
                            cmte_ids: set[str]) -> int:
    """COPY individual (IND) contributions for the given committees into the
    contributions table. The table should be empty first (COPY does not upsert).
    """
    raw = engine.raw_connection()
    n = 0
    try:
        pg = raw.driver_connection  # the underlying psycopg 3 connection
        with pg.cursor() as cur:
            with cur.copy(
                "COPY contributions (sub_id, cmte_id, name, city, state, zip_code, "
                "employer, occupation, transaction_dt, amount, entity_type, memo_cd) "
                "FROM STDIN"
            ) as copy:
                for line in zip_lines(zip_path, "itcont"):
                    if not line.strip():
                        continue
                    r = parse_contribution(line)
                    if r.entity_type != "IND" or r.cmte_id not in cmte_ids:
                        continue
                    copy.write_row((
                        r.sub_id, r.cmte_id, r.name, r.city, r.state, r.zip_code,
                        r.employer, r.occupation, r.transaction_dt,
                        str(r.amount), r.entity_type, r.memo_cd,
                    ))
                    n += 1
        raw.commit()
    finally:
        raw.close()
    return n


def weball_total_line(line: str, cycle: int) -> str:
    # weball columns: CAND_ID=0, TTL_RECEIPTS=5, TTL_INDIV_CONTRIB=17
    f = line.rstrip("\n").split("|")
    receipts = f[5] if len(f) > 5 and f[5] else "0"
    individual = f[17] if len(f) > 17 and f[17] else "0"
    return f"{f[0]}|{cycle}|{receipts}|{individual}"
