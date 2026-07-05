from otm_agent.geo import district_centroid


def test_centroid_hit():
    c = district_centroid("IL", "05")
    assert c is not None
    assert len(c) == 2


def test_centroid_miss():
    assert district_centroid("AZ", "99") is None
