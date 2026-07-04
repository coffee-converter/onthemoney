from otm_agent.geo import district_centroid


def test_centroid_hit():
    assert district_centroid("AZ", "06") == (-110.5, 32.0)


def test_centroid_miss():
    assert district_centroid("AZ", "99") is None
