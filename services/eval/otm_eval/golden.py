import json
from dataclasses import dataclass
from pathlib import Path

_DEFAULT = Path(__file__).with_name("data") / "golden.jsonl"


@dataclass
class GoldenItem:
    id: str
    query: str
    state: str
    district: str
    expected_tools: list[str]
    expected_committees: list[str]
    expected_total: str | None
    expected_scene: dict | None
    calibration_label: str


def load_golden(path: str | None = None) -> list[GoldenItem]:
    src = Path(path) if path else _DEFAULT
    items = []
    for line in src.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        items.append(GoldenItem(**d))
    return items
