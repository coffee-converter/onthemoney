import argparse
from pathlib import Path
from sqlalchemy import Engine
from otm_data.db import get_engine, apply_schema
from otm_data.load import (
    load_candidates, load_committees, load_linkages,
    load_contributions, linked_committee_ids,
)


def _lines(path: Path) -> list[str]:
    return path.read_text(errors="replace").splitlines()


def run_ingest(engine: Engine, *, data_dir: Path, cycle: int = 2024) -> dict[str, int]:
    apply_schema(engine)
    cands = load_candidates(engine, _lines(data_dir / "cn.txt"), election_yr=cycle)
    cmtes = load_committees(engine, _lines(data_dir / "cm.txt"))
    links = load_linkages(engine, _lines(data_dir / "ccl.txt"), election_yr=cycle)
    contribs = load_contributions(
        engine, _lines(data_dir / "itcont.txt"),
        cmte_ids=linked_committee_ids(engine, election_yr=cycle),
    )
    return {"candidates": cands, "committees": cmtes,
            "linkages": links, "contributions": contribs}


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest an FEC bulk-data slice.")
    ap.add_argument("--cycle", type=int, default=2024)
    ap.add_argument("--data-dir", type=Path, required=True)
    args = ap.parse_args()
    counts = run_ingest(get_engine(), data_dir=args.data_dir, cycle=args.cycle)
    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
