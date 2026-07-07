from otm_eval.golden import load_golden
from tests.conftest import FIXTURE_GOLDEN


def test_golden_loads_and_includes_negative_case():
    items = load_golden(FIXTURE_GOLDEN)
    ids = {i.id for i in items}
    assert {"az06-funds", "ca22-funds", "az99-none"} <= ids
    neg = next(i for i in items if i.id == "az99-none")
    assert neg.calibration_label == "insufficient"
    assert neg.expected_total is None
    assert neg.expected_scene is None


def test_positive_item_shape():
    az06 = next(i for i in load_golden(FIXTURE_GOLDEN) if i.id == "az06-funds")
    assert az06.expected_committees == ["C00770886"]
    assert az06.expected_total == "500.00"
    assert az06.expected_tools == ["resolve_entity", "funding_summary", "emit_scene"]
