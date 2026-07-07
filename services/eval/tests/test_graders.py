from otm_eval.golden import load_golden
from otm_eval.system import load_recorded
from otm_eval.graders import grade_trajectory, grade_answer, grade_scene
from tests.conftest import FIXTURE_GOLDEN, FIXTURE_RECORDED

GOLDEN = {i.id: i for i in load_golden(FIXTURE_GOLDEN)}
REC = load_recorded(FIXTURE_RECORDED)


def test_trajectory_pass_on_baseline():
    assert grade_trajectory(GOLDEN["az06-funds"], REC["az06-funds"]) is True
    assert grade_trajectory(GOLDEN["az99-none"], REC["az99-none"]) is True


def test_trajectory_fails_on_wrong_committee():
    out = REC["az06-funds"]
    bad = out.__class__(**{**out.__dict__, "committees": ["C99999999"]})
    assert grade_trajectory(GOLDEN["az06-funds"], bad) is False


def test_answer_numeric_exact():
    assert grade_answer(GOLDEN["az06-funds"], REC["az06-funds"]) is True
    out = REC["az06-funds"]
    off = out.__class__(**{**out.__dict__, "total": "500.01"})
    assert grade_answer(GOLDEN["az06-funds"], off) is False


def test_answer_negative_case_requires_none():
    assert grade_answer(GOLDEN["az99-none"], REC["az99-none"]) is True


def test_scene_structural_match_and_absence():
    assert grade_scene(GOLDEN["az06-funds"], REC["az06-funds"]) is True
    assert grade_scene(GOLDEN["az99-none"], REC["az99-none"]) is True
    out = REC["az06-funds"]
    moved = out.__class__(**{**out.__dict__,
                            "scene": {"highlight": {"state": "AZ", "district": "07"},
                                      "camera": out.scene["camera"]}})
    assert grade_scene(GOLDEN["az06-funds"], moved) is False
