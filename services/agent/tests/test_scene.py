from decimal import Decimal
from otm_data.oracle import StateTotal
from otm_agent.scene import build_scene


def test_build_scene_shape():
    flows = [
        StateTotal(state="AZ", amount=Decimal("500.00"), count=2),
        StateTotal(state="CA", amount=Decimal("250.00"), count=1),
    ]
    scene = build_scene(state="AZ", district="06",
                        centroid=(-110.5, 32.0), state_flows=flows)
    assert scene["camera"] == {"type": "flyTo", "lon": -110.5, "lat": 32.0, "zoom": 7}
    assert scene["highlight"] == {"state": "AZ", "district": "06"}
    assert [f["state"] for f in scene["flows"]] == ["AZ", "CA"]
    assert scene["flows"][0]["total"] == "500.00"
    assert scene["flows"][0]["count"] == 2
