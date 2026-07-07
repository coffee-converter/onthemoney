from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.runner import run_eval
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
