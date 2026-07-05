import json
from pathlib import Path

_TABLE = json.loads(Path(__file__).with_name("districts.json").read_text())


def district_centroid(state: str, district: str) -> tuple[float, float] | None:
    key = f"{state}-{district}"
    coords = _TABLE.get(key)
    if coords is None:
        return None
    return (coords[0], coords[1])


def _state_centroids() -> dict[str, tuple[float, float]]:
    acc: dict[str, list[tuple[float, float]]] = {}
    for key, (lng, lat) in _TABLE.items():
        acc.setdefault(key.split("-")[0], []).append((lng, lat))
    return {
        st: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v))
        for st, v in acc.items()
    }


_STATE_CENTROIDS = _state_centroids()


def resolve_place(place) -> tuple[float, float] | None:
    """Ground a semantic place reference to a lng/lat, so the agent never hands
    the map raw coordinates: a district id ('AZ-01'), a state code ('AZ'), or an
    explicit [lng, lat] pair."""
    if isinstance(place, (list, tuple)) and len(place) == 2:
        try:
            return (float(place[0]), float(place[1]))
        except (TypeError, ValueError):
            return None
    if isinstance(place, str):
        p = place.strip().upper()
        if "-" in p:
            st, di = p.split("-", 1)
            return district_centroid(st, di.zfill(2))
        if len(p) == 2:
            return _STATE_CENTROIDS.get(p)
    return None
