"""Battle-modifier card effects: Culverins and Falconets, Leeward Battle Line."""

from __future__ import annotations

import pytest

from plantagenet import battle
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _duel(seed=5):
    s = build_initial_state("henry_vi", seed=seed)
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []          # clean mats for the test
    return s


def _round1_missile(result):
    eng = result["rounds"][0]["engagements"][0]
    m = next(st for st in eng["strikes"] if st["phase"] == "missile")
    return m["attacker_hits"], m["defender_hits"]


def test_culverins_adds_missile_hits_round_one_and_discards():
    base = _round1_missile(battle.resolve_battle(_duel(), "cambridge", "york", "henry_vi", {}))
    s = _duel()
    s.lords["york"].capabilities = ["Y1"]        # York holds Culverins (Y1 Capability)
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"culverins": ["york"]})
    a_hits, _ = _round1_missile(r)
    assert a_hits > base[0]                       # +1 d6 added to York's Missile Hits
    assert "Y1" not in s.lords["york"].capabilities          # discarded on use
    assert "Y1" in s.decks["yorkist"]["discard"]


def test_leeward_halves_incoming_missile_hits():
    base = _round1_missile(battle.resolve_battle(_duel(), "cambridge", "york", "henry_vi", {}))
    s = _duel()
    s.decks["lancastrian"]["held"] = ["L1"]      # Defender holds Leeward (L1 Event)
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"leeward": ["lancastrian"]})
    a_hits, _ = _round1_missile(r)
    assert a_hits == -(-base[0] // 2)             # halved, round up (Defender receives a_hits)
    assert "L1" not in s.decks["lancastrian"]["held"]        # Hold Event used


def test_both_leeward_cancels():
    base = _round1_missile(battle.resolve_battle(_duel(), "cambridge", "york", "henry_vi", {}))
    s = _duel()
    s.decks["lancastrian"]["held"] = ["L1"]
    s.decks["yorkist"]["held"] = ["Y1"]
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"leeward": ["lancastrian", "yorkist"]})
    a_hits, d_hits = _round1_missile(r)
    assert a_hits == base[0] and d_hits == base[1]   # neither side's Missile Hits halved


def test_invalid_card_plays_rejected():
    s = _duel()
    with pytest.raises(IllegalAction) as e:       # York has no Culverins Capability
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"culverins": ["york"]})
    assert e.value.code == "no_culverins"
    s2 = _duel()
    with pytest.raises(IllegalAction) as e:       # Lancastrians hold no Leeward Event
        battle.resolve_battle(s2, "cambridge", "york", "henry_vi", {"leeward": ["lancastrian"]})
    assert e.value.code == "no_leeward"


def _round_melee(result, rnd, key="attacker_hits"):
    eng = result["rounds"][rnd]["engagements"][0]
    return next(st for st in eng["strikes"] if st["phase"] == "melee")[key]


def test_caltrops_adds_two_melee_each_round():
    base = _round_melee(battle.resolve_battle(_duel(), "cambridge", "york", "henry_vi", {}), 0)
    s = _duel()
    s.decks["yorkist"]["held"] = ["Y19"]          # Yorkist holds Caltrops
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"caltrops": ["yorkist"]})
    assert _round_melee(r, 0) == base + 2
    assert "Y19" not in s.decks["yorkist"]["held"]   # Hold Event consumed


def test_barricades_buffs_armour_at_friendly_stronghold():
    s = _duel()
    s.locales["cambridge"].favour = "yorkist"
    s.lords["york"].capabilities = ["Y9"]         # Barricades
    forces = {lid: battle._Force(s, lid) for lid in ("york", "henry_vi")}
    battle._apply_barricades(s, forces, "cambridge")
    assert forces["york"].prof["men_at_arms"]["prot"] == [1, 4]
    assert forces["york"].prof["longbow"]["prot"] == [1, 2]
    assert forces["york"].prof["militia"]["prot"] == [1, 2]
    # Not at a Friendly Stronghold -> no buff.
    s2 = _duel()
    s2.locales["cambridge"].favour = "neutral"
    s2.lords["york"].capabilities = ["Y9"]
    f2 = {lid: battle._Force(s2, lid) for lid in ("york", "henry_vi")}
    battle._apply_barricades(s2, f2, "cambridge")
    assert f2["york"].prof["men_at_arms"]["prot"] == [1, 3]


def test_ravine_ignores_enemy_lord_round_one():
    s = _duel()
    s.decks["lancastrian"]["held"] = ["L12"]      # Lancastrians hold Ravine
    # Play Ravine on York (the only Attacker) -> Round 1 has no Engagement.
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"ravine": "york"})
    assert r["rounds"][0]["engagements"] == []
    assert "L12" not in s.decks["lancastrian"]["held"]


def test_blocked_ford_forbids_exile():
    s = _duel()
    s.decks["yorkist"]["held"] = ["Y11"]          # Blocked Ford
    r = battle.approach(s, "cambridge", ["york"],
                        {"responses": {"henry_vi": "exile"}, "blocked_ford": ["yorkist"]})
    assert r["blocked_ford"] is True
    assert r["exiles"] == [] and r["battle"] is not None   # Exile forbidden -> Battle


def test_invalid_combat_card_plays_rejected():
    s = _duel()
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"caltrops": ["yorkist"]})
    assert e.value.code == "no_caltrops"
    s2 = _duel()
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s2, "cambridge", "york", "henry_vi", {"ravine": "york"})
    assert e.value.code == "no_ravine"


def test_regroup_consumes_held_event_and_validates():
    s = _duel()
    s.decks["yorkist"]["held"] = ["Y30"]          # Regroup
    battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                          {"regroup": {"lord": "york", "round": 2}})
    assert "Y30" not in s.decks["yorkist"]["held"]   # consumed on play
    s2 = _duel()                                      # no Regroup held -> rejected
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s2, "cambridge", "york", "henry_vi",
                              {"regroup": {"lord": "york"}})
    assert e.value.code == "no_regroup"


def test_escape_ship_exiles_routed_lord_instead_of_death():
    s = _duel()
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "ipswich"            # a Port
    s.locales["ipswich"].favour = "yorkist"          # Friendly Port for York
    s.decks["yorkist"]["held"] = ["Y3"]              # Escape Ship
    r = battle.resolve_battle(s, "ipswich", "york", "henry_vi",
                              {"flee": ["york"], "escape_ship": ["york"]})
    assert "york" in r["exiles"]                      # Exiled, not Death-rolled
    assert s.lords["york"].status == LordStatus.CALENDAR
    assert s.lords["york"].calendar_exile is True
    assert "york" not in r["deaths"]


def test_escape_ship_needs_route_to_friendly_port():
    s = _duel()                                       # Cambridge is not a Port
    s.decks["yorkist"]["held"] = ["Y3"]
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"flee": ["york"], "escape_ship": ["york"]})
    assert "york" not in r.get("exiles", [])          # no Friendly Port route -> no Escape
