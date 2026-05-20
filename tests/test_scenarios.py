"""Scenario setup data fidelity (Scenario Reference)."""

from __future__ import annotations

import pytest

from plantagenet import static_data

STANDALONE = ["henry_vi", "towton", "somersets_return",
              "warwicks_rebellion", "my_kingdom_for_a_horse", "bosworth"]


def test_index_lists_all_scenarios():
    ids = static_data.list_scenario_ids()
    assert ids == STANDALONE + ["wars_of_the_roses"]


@pytest.mark.parametrize("sid", STANDALONE)
def test_standalone_scenarios_load_and_reference_real_lords(sid, lords):
    scn = static_data.load_scenario(sid)
    assert scn["id"] == sid
    for side in ("lancastrian", "yorkist"):
        block = scn["sides"][side]
        assert block["role"] in ("king", "rebel")
        for lord_id in block["lord_cards"]:
            assert lord_id in lords, (sid, side, lord_id)
        # Mustered Lords must be among the scenario's Lord cards.
        for lord_id in block["mustered"]:
            assert lord_id in block["lord_cards"], (sid, side, lord_id)


def test_each_scenario_has_exactly_one_king():
    for sid in STANDALONE:
        scn = static_data.load_scenario(sid)
        roles = {s: scn["sides"][s]["role"] for s in ("lancastrian", "yorkist")}
        assert sorted(roles.values()) == ["king", "rebel"], (sid, roles)


def test_bosworth_is_battle_only():
    scn = static_data.load_scenario("bosworth")
    assert scn.get("battle_only") is True


def test_grand_scenario_has_five_wars():
    scn = static_data.load_scenario("wars_of_the_roses")
    assert scn["is_grand_scenario"] is True
    war_ids = [w["war_id"] for w in scn["wars"]]
    assert war_ids == ["war_i", "war_iiy", "war_iil", "war_iiiy", "war_iiil"]


def test_grand_scenario_heirs_reference_real_lords(lords):
    scn = static_data.load_scenario("wars_of_the_roses")
    for side in ("yorkist", "lancastrian"):
        for entry in scn["heirs"][side]:
            for lid in entry["lord_ids"]:
                assert lid in lords, (side, lid)
