"""Battle-modifier card effects: Culverins and Falconets, Leeward Battle Line."""

from __future__ import annotations

import pytest

from plantagenet import battle
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


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
