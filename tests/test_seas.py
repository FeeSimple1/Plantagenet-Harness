"""Sea-zone data fidelity (RULES_DECISIONS.md D-001; Rules 4.6.1 / FAQ #1)."""

from __future__ import annotations

from plantagenet import static_data


def test_three_zones_with_expected_members():
    seas = static_data.load_seas()
    zones = seas["zones"]
    assert set(zones) == {"irish_sea", "english_channel", "north_sea"}
    assert set(zones["irish_sea"]["ports"]) == {"bristol", "pembroke", "harlech"}
    assert zones["irish_sea"]["exile_boxes"] == ["ireland"]
    assert "scotland" in zones["north_sea"]["exile_boxes"]
    assert {"france", "burgundy"} == set(zones["english_channel"]["exile_boxes"])


def test_every_port_in_exactly_one_zone(locales):
    seas = static_data.load_seas()
    members = [p for z in seas["zones"].values() for p in z["ports"]]
    ports = {lid for lid, loc in locales.items() if loc.get("port")}
    assert sorted(members) == sorted(ports)
    assert len(members) == len(set(members)) == 16


def test_adjacency_is_irish_channel_north_chain():
    seas = static_data.load_seas()
    adj = {frozenset(pair) for pair in seas["adjacency"]}
    assert frozenset({"irish_sea", "english_channel"}) in adj
    assert frozenset({"english_channel", "north_sea"}) in adj
    # Irish Sea and North Sea are NOT directly adjacent.
    assert frozenset({"irish_sea", "north_sea"}) not in adj


def test_exile_boxes_have_sea_zone_and_act_as_port():
    boxes = static_data.load_exile_boxes()
    expected = {"scotland": "north_sea", "france": "english_channel",
                "ireland": "irish_sea", "burgundy": "english_channel"}
    for box, zone in expected.items():
        assert boxes[box]["sea_zone"] == zone
        assert boxes[box]["acts_as_port"] is True
