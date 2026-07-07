from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.runner import run_eval
from otm_eval.regression_demo import inject_regression, run_regression_demo
from otm_eval.gate_thresholds import MIN_ACCURACY, MAX_BRIER


def test_injected_bug_fails_the_gate():
    golden = load_golden()
    clean = load_recorded()
    assert run_eval(golden, clean).passes(min_accuracy=MIN_ACCURACY, max_brier=MAX_BRIER)
    broken = inject_regression(clean)
    report = run_eval(golden, broken)
    assert not report.passes(min_accuracy=MIN_ACCURACY, max_brier=MAX_BRIER)


def test_demo_artifact_has_before_after_delta():
    demo = run_regression_demo(load_golden(), load_recorded())
    assert demo["before"]["passes"] is True
    assert demo["after"]["passes"] is False
    assert demo["case"]
    assert demo["cases_affected"] >= 1
    assert demo["delta"]["brier"] >= 0
