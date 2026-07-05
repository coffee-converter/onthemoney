from otm_eval.run_live import run
from otm_eval.system import SystemOutput


def test_run_wires_golden_through_grading_and_coverage(seeded_engine):
    # Inject a producer that echoes each item's expectations, so the run scores
    # high and we can assert the wiring (grading + coverage) without a live client.
    def produce(engine, item):
        return SystemOutput(
            id=item.id,
            tools_called=item.expected_tools,
            committees=item.expected_committees,
            total=item.expected_total,
            confidence="high",
            scene=item.expected_scene,
            text="Reported receipts for the 2024 cycle.",
        )

    d = run(seeded_engine, produce)
    assert d["item_count"] >= 1
    assert "accuracy" in d and "brier" in d
    assert d["coverage"]["districts"] == 1  # seeded AZ-06
