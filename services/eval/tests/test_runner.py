from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.runner import run_eval
from tests.conftest import FIXTURE_GOLDEN, FIXTURE_RECORDED


def test_baseline_scores_perfect():
    report = run_eval(load_golden(FIXTURE_GOLDEN), load_recorded(FIXTURE_RECORDED))
    assert report.accuracy() == 1.0
    assert report.trajectory_accuracy() == 1.0
    assert report.scene_accuracy() == 1.0
    assert report.neutrality_accuracy() == 1.0
    # high cases contribute (0.9-1)^2=0.01 each; the partial case (0.5-1)^2=0.25.
    assert report.brier() < 0.1


def test_regression_is_detected():
    golden = load_golden(FIXTURE_GOLDEN)
    rec = load_recorded(FIXTURE_RECORDED)
    broken = dict(rec)
    az06 = broken["az06-funds"]
    broken["az06-funds"] = az06.__class__(**{**az06.__dict__, "total": "999.00"})
    report = run_eval(golden, broken)
    assert report.accuracy() < 1.0
    assert report.passes(min_accuracy=0.9, max_brier=0.2) is False
