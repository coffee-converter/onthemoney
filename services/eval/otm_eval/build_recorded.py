"""Deterministic recorded baseline: execute each golden case's expected tool
trajectory against the DB (ground truth) and assemble the SystemOutput a correct
system would produce. No LLM and no API key — this is the reference replay the CI
gate grades against. The live model's job (choosing the trajectory) is measured
separately by run_live.
"""
from otm_eval.golden import GoldenItem
from otm_eval.system import derive_expected


def recorded_from_golden(engine, items: list[GoldenItem]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for item in items:
        exp = derive_expected(engine, item)
        text = _reference_text(item, exp)
        out[item.id] = {
            "id": item.id,
            "tools_called": list(item.expected_tools),
            "committees": exp.committees,
            "total": exp.total,
            "confidence": exp.confidence,
            "scene": exp.scene,
            "text": text,
        }
    return out


def _reference_text(item: GoldenItem, exp) -> str:
    if exp.confidence == "insufficient":
        return (f"No U.S. House candidate for {item.state}-{item.district} is on "
                f"file for the 2024 cycle in this dataset.")
    if exp.total is None:
        return (f"The {item.state}-{item.district} representative has no itemized "
                f"individual receipts recorded for 2024 in this dataset.")
    return (f"The {item.state}-{item.district} representative reported {exp.total} "
            f"in itemized individual receipts for 2024.")
