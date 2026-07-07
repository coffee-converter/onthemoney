"""Write golden.jsonl + recorded.json from the loaded DB. Deterministic, no key.

Prefer `make regenerate` from the repo root: it runs this and then rebuilds the
regression-demo artifact the /how-it-works page imports, so the downstream copy
can't drift. Running this module alone refreshes only the baseline.
    uv run python -m otm_eval.regenerate
"""
import json
from pathlib import Path
from otm_data.db import get_engine
from otm_eval.golden import GoldenItem
from otm_eval.build_golden import select_cases
from otm_eval.build_recorded import recorded_from_golden

_DATA = Path(__file__).with_name("data")


def main() -> None:
    engine = get_engine()
    cases = select_cases(engine)
    (_DATA / "golden.jsonl").write_text(
        "\n".join(json.dumps(c) for c in cases) + "\n")
    items = [GoldenItem(**c) for c in cases]
    rec = recorded_from_golden(engine, items)
    (_DATA / "recorded.json").write_text(json.dumps(rec, indent=2))
    print(f"wrote {len(cases)} golden cases and recorded baseline")


if __name__ == "__main__":
    main()
