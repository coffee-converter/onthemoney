from otm_agent.tools import DonorLine
from otm_agent.scene import build_scene


def test_build_scene_shape():
    donors = [
        DonorLine(name="DOE, JOHN", employer="ACME CORP", amount="500.00"),
        DonorLine(name="ROE, JANE", employer="SELF", amount="250.00"),
    ]
    scene = build_scene(state="AZ", district="06",
                        centroid=(-110.5, 32.0), donors=donors)
    assert scene["camera"] == {"type": "flyTo", "lon": -110.5, "lat": 32.0, "zoom": 7}
    assert scene["highlight"] == {"state": "AZ", "district": "06"}
    assert [f["label"] for f in scene["flows"]] == ["DOE, JOHN", "ROE, JANE"]
    assert scene["flows"][0]["amount"] == "500.00"
