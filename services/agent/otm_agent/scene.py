from otm_agent.tools import DonorLine

DISTRICT_ZOOM = 7


def build_scene(*, state: str, district: str, centroid: tuple[float, float],
                donors: list[DonorLine]) -> dict:
    lon, lat = centroid
    return {
        "camera": {"type": "flyTo", "lon": lon, "lat": lat, "zoom": DISTRICT_ZOOM},
        "highlight": {"state": state, "district": district},
        "flows": [
            {"label": d.name, "employer": d.employer, "amount": d.amount,
             "state": d.state}
            for d in donors
        ],
    }
