from otm_eval.golden import GoldenItem
from otm_eval.build_golden import select_cases


def test_select_cases_from_seeded_engine(seeded_engine):
    # The eval fixture seeds one high district (AZ-06, itemized 500). Partial
    # districts (a leader with zero itemized) do not exist in this fixture — that
    # regime is exercised at the real-DB regeneration step, where they do exist.
    cases = select_cases(seeded_engine, n_high=1, n_partial=1)
    labels = {c["calibration_label"] for c in cases}
    assert "high" in labels
    assert "insufficient" in labels  # synthesized XX-99 cases
    # The high case carries a derived, non-null total from ground truth.
    highs = [c for c in cases if c["calibration_label"] == "high"]
    assert highs and all(c["expected_total"] not in (None, "0.00") for c in highs)
    # AZ-06 resolves to its real seeded committee and total.
    az = next(c for c in cases if c["state"] == "AZ" and c["district"] == "06")
    assert az["expected_committees"] == ["C00770886"]
    assert az["expected_total"] == "500.00"
    # Ids are unique (guards the district-normalization dedup).
    assert len(cases) == len({c["id"] for c in cases})
    # Every case is constructible as a GoldenItem (exact field set).
    for c in cases:
        GoldenItem(**c)
        assert {"id", "query", "state", "district", "expected_tools",
                "expected_committees", "expected_total", "expected_scene",
                "calibration_label"} == set(c)
