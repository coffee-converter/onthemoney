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
    payload = spec.handler(seeded_engine, {"metric": "itemized", "order": "asc", "limit": 5})
    assert payload["metric"] == "itemized"
    assert payload["order"] == "asc"
    assert payload["insufficient"] is False
    rows = payload["districts"]
    assert rows
    # Each row carries the pieces needed to then highlight_district that seat.
    top = rows[0]
    assert set(top) >= {"district", "state", "district_num", "cand_id", "name",
                        "party", "value"}
    assert top["district"] == f"{top['state']}-{top['district_num']}"
    assert [r["value"] for r in rows] == sorted(r["value"] for r in rows)


def test_rank_districts_handler_defaults_to_receipts(seeded_engine):
    spec = get_spec("rank_districts")
    payload = spec.handler(seeded_engine, {"order": "desc"})
    assert payload["metric"] == "receipts"


def test_compare_candidates_handler(seeded_engine):
    spec = get_spec("compare_candidates")
    payload = spec.handler(seeded_engine, {"cand_ids": ["H2AZ06099"]})
    row = payload["candidates"][0]
    assert row["cand_id"] == "H2AZ06099"
    assert row["district"] == "AZ-06"
    assert "out_of_state_pct" in row and "small_dollar_share_pct" in row


def test_top_by_industry_handler(seeded_engine):
    spec = get_spec("top_by_industry")
    bad = spec.handler(seeded_engine, {"industry": "Crypto"})
    assert bad["insufficient"] is True and "valid_industries" in bad
    ok = spec.handler(seeded_engine, {"industry": "Technology", "limit": 5})
    assert ok["industry"] == "Technology"
    assert "itemized" in ok["note"]


def test_map_districts_handler(seeded_engine):
    spec = get_spec("map_districts")
    scene = spec.handler(seeded_engine, {"order": "desc", "metric": "itemized", "limit": 10})
    assert "House districts" in scene["title"]
    kinds = {o["type"] for o in scene.get("overlays", [])}
    assert "regions" in kinds


def test_emit_scene_handler(seeded_engine):
    spec = get_spec("emit_scene")
    payload = spec.handler(seeded_engine, {"state": "AZ", "district": "06"})
    assert payload["highlight"] == {"state": "AZ", "district": "06"}
    assert payload["camera"]["zoom"] == 7


def test_emit_scene_handler_insufficient(seeded_engine):
    spec = get_spec("emit_scene")
    payload = spec.handler(seeded_engine, {"state": "AZ", "district": "99"})
    assert payload == {"insufficient": True}
