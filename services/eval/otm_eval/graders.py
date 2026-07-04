from otm_eval.golden import GoldenItem
from otm_eval.system import SystemOutput


def grade_trajectory(item: GoldenItem, out: SystemOutput) -> bool:
    tools_ok = set(item.expected_tools) <= set(out.tools_called)
    ids_ok = set(item.expected_committees) == set(out.committees)
    return tools_ok and ids_ok


def grade_answer(item: GoldenItem, out: SystemOutput) -> bool:
    return item.expected_total == out.total


def grade_scene(item: GoldenItem, out: SystemOutput) -> bool:
    if item.expected_scene is None:
        return out.scene is None
    if out.scene is None:
        return False
    return (out.scene.get("highlight") == item.expected_scene.get("highlight")
            and out.scene.get("camera") == item.expected_scene.get("camera"))


CONF_PROB = {"high": 0.9, "partial": 0.5}


def brier_score(pairs: list[tuple[str, bool]]) -> float:
    scored = [(CONF_PROB[label], 1.0 if correct else 0.0)
              for label, correct in pairs if label in CONF_PROB]
    if not scored:
        return 0.0
    return sum((p - actual) ** 2 for p, actual in scored) / len(scored)


BANNED_TERMS = [
    "corrupt", "crooked", "should vote", "vote for", "best candidate",
    "worst candidate", "evil", "hero", "disgraceful", "endorse",
]


def grade_neutrality(text: str) -> bool:
    low = (text or "").lower()
    return not any(term in low for term in BANNED_TERMS)
