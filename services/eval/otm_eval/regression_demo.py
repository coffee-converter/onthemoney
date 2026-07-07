"""Show the gate catching a real regression. Simulate a units/rounding bug in the
funding tool that drifts every high-confidence total by 10% while each answer is
still reported at high confidence — the shape of a real tool/model regression a
naive smoke test would miss. Prove the gate flips from pass to fail, with the
accuracy drop and Brier spike a fleet of confidently-wrong answers produces.
Writes data/regression.json for the surface.
"""
import copy
import json
from dataclasses import replace
from pathlib import Path
from otm_eval.golden import load_golden
from otm_eval.runner import run_eval
from otm_eval.system import SystemOutput
from otm_eval.gate_thresholds import MIN_ACCURACY, MAX_BRIER

_ARTIFACT = Path(__file__).with_name("data") / "regression.json"


def _first_high_case(golden) -> str:
    for item in golden:
        if item.calibration_label == "high" and item.expected_total not in (None, "0.00"):
            return item.id
    raise RuntimeError("no high-confidence case to perturb")


def inject_regression(recorded: dict[str, SystemOutput],
                      golden=None) -> dict[str, SystemOutput]:
    """Return a copy simulating a systematic regression: a units/rounding bug in
    the funding tool drifts EVERY high-confidence total by 10%, each still reported
    at high confidence. One perturbed case would not cross the gate thresholds on a
    ~24-case set; a real shared-tool regression hits every case that tool feeds, and
    that is what the gate must catch.

    `golden` is the case set to perturb against; it defaults to the on-disk golden
    but callers should pass the same golden they grade with so the two can't drift."""
    items = golden if golden is not None else load_golden()
    golden = {item.id: item for item in items}
    broken = copy.deepcopy(recorded)
    for cid, out in broken.items():
        item = golden.get(cid)
        if item and item.calibration_label == "high" and out.total not in (None, "0.00"):
            broken[cid] = replace(out, total=f"{float(out.total) * 0.9:.2f}")
    return broken


def run_regression_demo(golden, recorded) -> dict:
    representative = _first_high_case(golden)
    if representative not in recorded:
        raise RuntimeError(
            f"golden case {representative!r} is missing from the recorded baseline; "
            "regenerate the baseline so golden and recorded stay in sync")
    before = run_eval(golden, recorded)
    broken = inject_regression(recorded, golden)
    after = run_eval(golden, broken)
    affected = sum(1 for cid, out in broken.items()
                   if recorded[cid].total != out.total)
    demo = {
        "case": representative,
        "cases_affected": affected,
        "clean_total": recorded[representative].total,
        "broken_total": broken[representative].total,
        "before": {"accuracy": round(before.accuracy(), 3),
                   "brier": round(before.brier(), 3),
                   "passes": before.passes(min_accuracy=MIN_ACCURACY, max_brier=MAX_BRIER)},
        "after": {"accuracy": round(after.accuracy(), 3),
                  "brier": round(after.brier(), 3),
                  "passes": after.passes(min_accuracy=MIN_ACCURACY, max_brier=MAX_BRIER)},
        "delta": {"accuracy": round(before.accuracy() - after.accuracy(), 3),
                  "brier": round(after.brier() - before.brier(), 3)},
        "thresholds": {"min_accuracy": MIN_ACCURACY, "max_brier": MAX_BRIER},
    }
    return demo


def main() -> None:
    from otm_eval.system import load_recorded
    demo = run_regression_demo(load_golden(), load_recorded())
    _ARTIFACT.write_text(json.dumps(demo, indent=2))
    status = "FAIL" if not demo["after"]["passes"] else "PASS"
    print(f"[regression-demo] systematic bug across {demo['cases_affected']} high cases "
          f"(e.g. {demo['case']}: {demo['clean_total']} -> {demo['broken_total']}); "
          f"gate now {status}; "
          f"accuracy {demo['before']['accuracy']} -> {demo['after']['accuracy']}, "
          f"brier {demo['before']['brier']} -> {demo['after']['brier']}")


if __name__ == "__main__":
    main()
