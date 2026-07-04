import json
from dataclasses import dataclass
from pathlib import Path
from otm_eval.golden import GoldenItem
from otm_agent.tools import resolve_entity, funding_summary
from otm_agent.answer import compose_answer

_DEFAULT = Path(__file__).with_name("data") / "recorded.json"


@dataclass
class SystemOutput:
    id: str
    tools_called: list[str]
    committees: list[str]
    total: str | None
    confidence: str
    scene: dict | None
    text: str


@dataclass
class Expected:
    tools: list[str]
    committees: list[str]
    total: str | None
    scene: dict | None
    confidence: str


def load_recorded(path: str | None = None) -> dict[str, SystemOutput]:
    src = Path(path) if path else _DEFAULT
    raw = json.loads(src.read_text())
    return {k: SystemOutput(**v) for k, v in raw.items()}


def derive_expected(engine, item: GoldenItem) -> Expected:
    res = resolve_entity(engine, state=item.state, district=item.district)
    ans = compose_answer(engine, state=item.state, district=item.district)
    if res is None:
        return Expected(tools=item.expected_tools, committees=[], total=None,
                        scene=None, confidence="insufficient")
    fs = funding_summary(engine, res.candidate.cand_id)
    total = fs.total if fs.total != "0.00" else None
    return Expected(tools=item.expected_tools, committees=res.committees,
                    total=total, scene=ans.scene, confidence=ans.confidence.value)
