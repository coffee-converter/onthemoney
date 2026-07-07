from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.runner import run_eval, ItemResult, Report
from otm_eval.scoreboard import report_to_dict, report_to_markdown, write_scoreboard
from tests.conftest import FIXTURE_GOLDEN, FIXTURE_RECORDED


def _report():
    return run_eval(load_golden(FIXTURE_GOLDEN), load_recorded(FIXTURE_RECORDED))


def test_report_to_dict_has_metrics():
    d = report_to_dict(_report())
    assert d["accuracy"] == 1.0
    assert d["item_count"] == 5
    assert "brier" in d and "neutrality_accuracy" in d


def test_report_to_markdown_mentions_accuracy():
    md = report_to_markdown(_report())
    assert "Accuracy" in md
    assert "az06-funds" in md


def test_write_scoreboard_creates_files(tmp_path):
    base = tmp_path / "scoreboard"
    write_scoreboard(_report(), str(base))
    assert (tmp_path / "scoreboard.json").exists()
    assert (tmp_path / "scoreboard.md").exists()


def test_report_dict_has_regime_breakdown():
    items = [
        ItemResult(id="a", trajectory_ok=True, answer_ok=True, scene_ok=True,
                   neutral_ok=True, confidence="high", correct=True),
        ItemResult(id="b", trajectory_ok=True, answer_ok=False, scene_ok=True,
                   neutral_ok=True, confidence="high", correct=False),
        ItemResult(id="c", trajectory_ok=True, answer_ok=True, scene_ok=True,
                   neutral_ok=True, confidence="insufficient", correct=True),
    ]
    d = report_to_dict(Report(items=items))
    assert d["by_regime"]["high"] == {"count": 2, "accuracy": 0.5}
    assert d["by_regime"]["insufficient"] == {"count": 1, "accuracy": 1.0}
    # Regime counts partition the full item set.
    assert sum(r["count"] for r in d["by_regime"].values()) == d["item_count"]
