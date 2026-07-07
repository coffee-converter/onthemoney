from otm_eval.golden import load_golden
from otm_eval.system import load_recorded, derive_expected, SystemOutput
from tests.conftest import FIXTURE_GOLDEN, FIXTURE_RECORDED


def test_load_recorded_keyed_by_id():
    rec = load_recorded(FIXTURE_RECORDED)
    assert set(rec) >= {"az06-funds", "ca22-funds", "az99-none"}
    assert isinstance(rec["az06-funds"], SystemOutput)
    assert rec["az06-funds"].total == "500.00"
    assert rec["az99-none"].total is None


def test_derive_expected_matches_golden_for_seeded_district(seeded_engine):
    az06 = next(i for i in load_golden(FIXTURE_GOLDEN) if i.id == "az06-funds")
    exp = derive_expected(seeded_engine, az06)
    assert exp.committees == az06.expected_committees
    assert exp.total == az06.expected_total
    assert exp.confidence == az06.calibration_label
    assert exp.scene["highlight"] == az06.expected_scene["highlight"]


def test_derive_expected_negative_case(seeded_engine):
    neg = next(i for i in load_golden(FIXTURE_GOLDEN) if i.id == "az99-none")
    exp = derive_expected(seeded_engine, neg)
    assert exp.total is None
    assert exp.scene is None
    assert exp.confidence == "insufficient"
