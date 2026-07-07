from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.runner import run_eval
from otm_eval.gate_thresholds import MIN_ACCURACY, MAX_BRIER

# The build gate: the recorded baseline must clear the accuracy and calibration
# thresholds. A regression past these thresholds fails CI (spec 5.3).


def test_ci_gate_baseline_passes():
    report = run_eval(load_golden(), load_recorded())
    assert report.passes(min_accuracy=MIN_ACCURACY, max_brier=MAX_BRIER), (
        f"accuracy={report.accuracy():.3f} brier={report.brier():.3f}"
    )


def test_shipped_baseline_scores_perfect():
    # The recorded baseline is derived deterministically from ground truth, so
    # the *shipped* golden.jsonl/recorded.json must score exactly 1.0. The gate
    # threshold above only guards >= MIN_ACCURACY; this catches a regenerated
    # baseline whose recorded totals drift out of sync with golden (a mismatch
    # the fixture-based unit tests can't see).
    report = run_eval(load_golden(), load_recorded())
    assert report.accuracy() == 1.0, f"baseline not perfect: accuracy={report.accuracy():.4f}"
