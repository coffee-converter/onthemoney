from otm_data.oracle import StateTotal

DISTRICT_ZOOM = 7


def build_scene(*, state: str, district: str, centroid: tuple[float, float],
                state_flows: list[StateTotal]) -> dict:
    # Flows are itemized receipts aggregated by contributor state: one weighted
    # flow per state, so the map shows the full geographic funding pattern.
    lon, lat = centroid
    return {
        "camera": {"type": "flyTo", "lon": lon, "lat": lat, "zoom": DISTRICT_ZOOM},
        "highlight": {"state": state, "district": district},
        "flows": [
            {"state": s.state, "total": f"{s.amount:.2f}", "count": s.count}
            for s in state_flows
        ],
    }
