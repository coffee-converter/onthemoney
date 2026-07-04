from dataclasses import dataclass
from otm_eval.golden import GoldenItem
from otm_eval.system import SystemOutput
from otm_eval.graders import (
    grade_trajectory, grade_answer, grade_scene, grade_neutrality, brier_score,
)


@dataclass
class ItemResult:
    id: str
    trajectory_ok: bool
    answer_ok: bool
    scene_ok: bool
    neutral_ok: bool
    confidence: str
    correct: bool


def _fraction(flags: list[bool]) -> float:
    return sum(1 for f in flags if f) / len(flags) if flags else 0.0


@dataclass
class Report:
    items: list[ItemResult]

    def accuracy(self) -> float:
        return _fraction([r.correct for r in self.items])

    def trajectory_accuracy(self) -> float:
        return _fraction([r.trajectory_ok for r in self.items])

    def scene_accuracy(self) -> float:
        return _fraction([r.scene_ok for r in self.items])

    def neutrality_accuracy(self) -> float:
        return _fraction([r.neutral_ok for r in self.items])

    def brier(self) -> float:
        return brier_score([(r.confidence, r.correct) for r in self.items])

    def passes(self, *, min_accuracy: float, max_brier: float) -> bool:
        return self.accuracy() >= min_accuracy and self.brier() <= max_brier


_MISSING = SystemOutput(id="", tools_called=[], committees=[], total=None,
                        confidence="insufficient", scene=None, text="")


def run_eval(golden: list[GoldenItem],
             outputs: dict[str, SystemOutput]) -> Report:
    results = []
    for item in golden:
        out = outputs.get(item.id, _MISSING)
        results.append(ItemResult(
            id=item.id,
            trajectory_ok=grade_trajectory(item, out),
            answer_ok=grade_answer(item, out),
            scene_ok=grade_scene(item, out),
            neutral_ok=grade_neutrality(out.text),
            confidence=out.confidence,
            correct=grade_answer(item, out),
        ))
    return Report(items=results)
