from otm_agent.registry import tool_specs, get_spec


def test_registry_lists_all_tools():
    names = {s.name for s in tool_specs()}
    assert {"resolve_entity", "funding_summary", "emit_scene",
            "industry_breakdown", "top_employers"} <= names


def test_each_spec_has_object_schema():
    for spec in tool_specs():
        assert spec.input_schema["type"] == "object"
        assert "properties" in spec.input_schema


def test_resolve_entity_handler(seeded_engine):
    spec = get_spec("resolve_entity")
    payload = spec.handler(seeded_engine, {"state": "AZ", "district": "06"})
    assert payload["found"] is True
    assert payload["candidate"]["cand_id"] == "H2AZ06099"
    assert payload["committees"] == ["C00770886"]


def test_funding_summary_handler(seeded_engine):
    spec = get_spec("funding_summary")
    payload = spec.handler(seeded_engine, {"cand_id": "H2AZ06099"})
    assert payload["total"] == "500.00"
    assert payload["donors"][0]["name"] == "DOE, JOHN"


def test_rank_districts_handler(seeded_engine):
    spec = get_spec("rank_districts")
    payload = spec.handler(seeded_engine, {"order": "asc", "limit": 5})
    assert payload["order"] == "asc"
    assert payload["insufficient"] is False
    rows = payload["districts"]
    assert rows
    # Each row carries the pieces needed to then highlight_district that seat.
    top = rows[0]
    assert set(top) >= {"district", "state", "district_num", "cand_id", "name",
                        "party", "itemized"}
    assert top["district"] == f"{top['state']}-{top['district_num']}"
    assert [r["itemized"] for r in rows] == sorted(r["itemized"] for r in rows)


def test_emit_scene_handler(seeded_engine):
    spec = get_spec("emit_scene")
    payload = spec.handler(seeded_engine, {"state": "AZ", "district": "06"})
    assert payload["highlight"] == {"state": "AZ", "district": "06"}
    assert payload["camera"]["zoom"] == 7


def test_emit_scene_handler_insufficient(seeded_engine):
    spec = get_spec("emit_scene")
    payload = spec.handler(seeded_engine, {"state": "AZ", "district": "99"})
    assert payload == {"insufficient": True}
