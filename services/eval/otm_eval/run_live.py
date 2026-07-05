"""Live eval: run the real agent against the golden set over the real DB and
write a scoreboard with true model accuracy (not the recorded replay).

Usage:
    ANTHROPIC_API_KEY=... uv run python -m otm_eval.run_live \\
        --out ../../apps/api/src/scoreboard/scoreboard.json
"""
import argparse
import json
import os
from pathlib import Path
from typing import Callable

from otm_data.db import get_engine
from otm_eval.golden import GoldenItem, load_golden
from otm_eval.system import SystemOutput
from otm_eval.runner import run_eval
from otm_eval.scoreboard import report_to_dict
from otm_eval.coverage import coverage_stats


def run(engine, produce: Callable[[object, GoldenItem], SystemOutput]) -> dict:
    """Grade the golden set with `produce(engine, item)` and build the scoreboard
    dict (results + dataset coverage). `produce` is injected so this wiring is
    testable without a live client."""
    golden = load_golden()
    outputs = {item.id: produce(engine, item) for item in golden}
    d = report_to_dict(run_eval(golden, outputs))
    d["coverage"] = coverage_stats(engine)
    return d


def main() -> None:
    ap = argparse.ArgumentParser(description="Live eval run against the real DB.")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is required for a live eval run.")

    # Imported lazily so the module (and its test) load without the SDK/key.
    from anthropic import Anthropic
    from otm_eval.live import system_output_from_live

    client = Anthropic()
    engine = get_engine()

    def produce(eng, item: GoldenItem) -> SystemOutput:
        out = system_output_from_live(eng, item, client)
        print(f"  {item.id}: correct={out.total is not None} confidence={out.confidence}")
        return out

    d = run(engine, produce)
    args.out.write_text(json.dumps(d, indent=2))
    print(f"accuracy={d['accuracy']:.2f} brier={d['brier']:.3f} -> wrote {args.out}")


if __name__ == "__main__":
    main()
