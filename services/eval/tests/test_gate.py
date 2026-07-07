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
