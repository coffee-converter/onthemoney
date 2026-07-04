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
