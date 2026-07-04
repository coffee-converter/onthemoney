import pytest
from otm_eval.graders import brier_score, grade_neutrality


def test_brier_perfect_high_confidence():
    # all high-confidence and correct -> (0.9 - 1)^2 = 0.01
    assert brier_score([("high", True), ("high", True)]) == pytest.approx(0.01)


def test_brier_penalizes_confident_and_wrong():
    # high-confidence but wrong -> (0.9 - 0)^2 = 0.81
    assert brier_score([("high", False)]) == pytest.approx(0.81)


def test_brier_empty_is_zero():
    assert brier_score([]) == 0.0


def test_neutrality_passes_descriptive_text():
    assert grade_neutrality("AZ-06 reported 500.00 in itemized receipts for 2024.") is True


def test_neutrality_flags_editorializing():
    assert grade_neutrality("This corrupt incumbent is the best candidate; vote for them.") is False
