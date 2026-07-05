from otm_agent.geo import district_centroid, resolve_place


def test_centroid_hit():
    c = district_centroid("IL", "05")
    assert c is not None
    assert len(c) == 2


def test_centroid_miss():
    assert district_centroid("AZ", "99") is None


def test_resolve_place():
    assert resolve_place("IL-05") is not None       # district id
    assert resolve_place("AZ") is not None           # state centroid
    assert resolve_place([-88.0, 42.0]) == (-88.0, 42.0)  # explicit coords
    assert resolve_place("ZZ-99") is None            # unknown
