import json
from pathlib import Path
from otm_eval.runner import Report


def _by_regime(report: Report) -> dict:
    out: dict[str, dict] = {}
    for label in ("high", "partial", "insufficient"):
        group = [r for r in report.items if r.confidence == label]
        if not group:
            continue
        acc = sum(1 for r in group if r.correct) / len(group)
        out[label] = {"count": len(group), "accuracy": round(acc, 3)}
    return out


def report_to_dict(report: Report) -> dict:
    return {
        "item_count": len(report.items),
        "accuracy": report.accuracy(),
        "trajectory_accuracy": report.trajectory_accuracy(),
        "scene_accuracy": report.scene_accuracy(),
        "neutrality_accuracy": report.neutrality_accuracy(),
        "brier": report.brier(),
        "answer_accuracy": report.accuracy(),
        "by_regime": _by_regime(report),
        "items": [
            {"id": r.id, "correct": r.correct, "trajectory_ok": r.trajectory_ok,
             "scene_ok": r.scene_ok, "neutral_ok": r.neutral_ok,
             "confidence": r.confidence}
            for r in report.items
        ],
    }


def report_to_markdown(report: Report) -> str:
    lines = [
        "# On The Money eval scoreboard",
        "",
        f"- Accuracy: {report.accuracy():.3f}",
        f"- Trajectory accuracy: {report.trajectory_accuracy():.3f}",
        f"- Scene accuracy: {report.scene_accuracy():.3f}",
        f"- Neutrality accuracy: {report.neutrality_accuracy():.3f}",
        f"- Brier score (calibration): {report.brier():.3f}",
        "",
        "| Item | Correct | Trajectory | Scene | Neutral | Confidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in report.items:
        lines.append(
            f"| {r.id} | {r.correct} | {r.trajectory_ok} | {r.scene_ok} "
            f"| {r.neutral_ok} | {r.confidence} |"
        )
    return "\n".join(lines) + "\n"


def write_scoreboard(report: Report, path: str) -> None:
    Path(f"{path}.json").write_text(json.dumps(report_to_dict(report), indent=2))
    Path(f"{path}.md").write_text(report_to_markdown(report))
