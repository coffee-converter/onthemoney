from otm_eval.golden import GoldenItem
from otm_eval.build_recorded import recorded_from_golden


def test_recorded_baseline_matches_oracle(seeded_engine):
    item = GoldenItem(
        id="az06-funds", query="Who funds the representative in AZ-06?",
        state="AZ", district="06",
        expected_tools=["resolve_entity", "funding_summary", "emit_scene"],
        expected_committees=["C00770886"], expected_total="500.00",
        expected_scene={"highlight": {"state": "AZ", "district": "06"},
                        "camera": {"type": "flyTo", "lon": -110.5, "lat": 32.0, "zoom": 7}},
        calibration_label="high",
    )
    rec = recorded_from_golden(seeded_engine, [item])
    out = rec["az06-funds"]
    # The deterministic baseline reproduces ground truth for a correct system.
    assert out["total"] == "500.00"
    assert out["committees"] == ["C00770886"]
    assert out["confidence"] == "high"
    assert out["tools_called"] == ["resolve_entity", "funding_summary", "emit_scene"]
