"""Nationwide bulk ingest from FEC bulk zip files.

Expects these in --data-dir (download from
https://www.fec.gov/data/browse-data/?tab=bulk-data):
  cn24.zip, cm24.zip, ccl24.zip, weball24.zip, indiv24.zip

Loads the full House slice: every House candidate, their committees, official
totals, and all itemized individual contributions.
"""
import argparse
from pathlib import Path
from sqlalchemy import Engine, text
from otm_data.db import get_engine, apply_schema
from otm_data.load import (
    load_candidates, load_committees, load_linkages, load_candidate_totals,
    house_committee_ids,
)
from otm_data.bulk import zip_lines, bulk_load_contributions, weball_total_line

_TABLES = ["contributions", "candidate_committee", "committees", "candidates",
           "candidate_totals"]


def run_bulk_ingest(engine: Engine, *, data_dir: Path, cycle: int = 2024) -> dict:
    apply_schema(engine)
    with engine.begin() as conn:
        for t in _TABLES:
            conn.execute(text(f"TRUNCATE {t} CASCADE"))

    cands = load_candidates(engine, zip_lines(data_dir / "cn24.zip", "cn"),
                            election_yr=cycle)
    cmtes = load_committees(engine, zip_lines(data_dir / "cm24.zip", "cm"))
    links = load_linkages(engine, zip_lines(data_dir / "ccl24.zip", "ccl"),
                          election_yr=cycle)
    cmte_ids = house_committee_ids(engine, election_yr=cycle)
    contribs = bulk_load_contributions(engine, data_dir / "indiv24.zip",
                                       cmte_ids=cmte_ids)
    totals = load_candidate_totals(engine, [
        weball_total_line(line, cycle)
        for line in zip_lines(data_dir / "weball24.zip", "weball") if line.strip()
    ])
    return {"candidates": cands, "committees": cmtes, "linkages": links,
            "house_committees": len(cmte_ids), "contributions": contribs,
            "totals": totals}


def main() -> None:
    ap = argparse.ArgumentParser(description="Nationwide FEC bulk ingest.")
    ap.add_argument("--data-dir", type=Path, default=Path("./_bulk"))
    ap.add_argument("--cycle", type=int, default=2024)
    args = ap.parse_args()
    counts = run_bulk_ingest(get_engine(), data_dir=args.data_dir, cycle=args.cycle)
    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
