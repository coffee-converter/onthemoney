import json
from pathlib import Path

_TABLE = json.loads(Path(__file__).with_name("districts.json").read_text())


def district_centroid(state: str, district: str) -> tuple[float, float] | None:
    key = f"{state}-{district}"
    coords = _TABLE.get(key)
    if coords is None:
        return None
    return (coords[0], coords[1])
