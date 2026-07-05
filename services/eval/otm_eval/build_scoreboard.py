"""Build the scoreboard JSON the BFF serves: eval results + dataset coverage."""
import argparse
import json
from pathlib import Path
from otm_data.db import get_engine
from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.runner import run_eval
from otm_eval.scoreboard import report_to_dict
from otm_eval.coverage import coverage_stats


def build(engine=None) -> dict:
    d = report_to_dict(run_eval(load_golden(), load_recorded()))
    d["coverage"] = coverage_stats(engine or get_engine())
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the scoreboard JSON.")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.write_text(json.dumps(build(), indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
