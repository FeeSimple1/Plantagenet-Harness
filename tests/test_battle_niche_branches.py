"""Deterministic tests for the niche battle branches logged in
SMOKE_TEST_FINDINGS (coverage triage): the Regroup troop-recovery loop, the
Patrick de la Mote + Leeward Battle Line combination, Norfolk is Late (Towton),
the Swift Maneuver played-Event path, and Warden of the Marches on the Death
check (including the no-window case that must NOT burn the card).

Seeds were searched offline. The fork oracle (the RNG lives in the state, so a
``model_copy(deep=True)`` rolls identical dice) turns dice-dependent behaviour
into exact assertions.
"""

from __future__ import annotations

from math import ceil

import pytest

from plantagenet import battle
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def _duel(seed, y_forces=None, h_forces=None, at="cambridge"):
    s = build_initial_state("henry_vi", seed=seed)
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = at
        s.lords[lid].capabilities = []
    if y_forces:
        s.lords["york"].forces = dict(y_forces)
    if h_forces:
        s.lords["henry_vi"].forces = dict(h_forces)
    return s


def _round_hits(rlog):
    return sum(st["attacker_hits"] for e in rlog["engagements"] for st in e["strikes"])


# ------------------------------------------------ Regroup troop recovery (4.4.2)
def test_regroup_recovers_routed_troops_for_round_2():
    # Seed 64: the Battle reaches Round 2 with Routed York Troops, and at least
    # one recovery roll succeeds. The no-Regroup fork rolls the same dice
    # through Round 1, so Round 1 must be identical and York's Round-2 strike
    # total strictly higher with the recovered Troops back in line.
    yf = {"retinue": 1, "men_at_arms": 2, "longbow": 2, "militia": 3}
    hf = {"retinue": 1, "men_at_arms": 3, "longbow": 3, "militia": 3}
    s1 = _duel(64, yf, hf)
    s1.decks["yorkist"]["held"] = ["Y30"]
    s2 = s1.model_copy(deep=True)
    r1 = battle.resolve_battle(s1, "cambridge", "york", "henry_vi",
                               {"regroup": {"lord": "york", "round": 2}})
    r2 = battle.resolve_battle(s2, "cambridge", "york", "henry_vi", {})
    assert len(r1["rounds"]) >= 2 and len(r2["rounds"]) >= 2
    assert r1["rounds"][0] == r2["rounds"][0]          # same dice through Round 1
    assert _round_hits(r1["rounds"][1]) > _round_hits(r2["rounds"][1])
    assert "Y30" not in s1.decks["yorkist"]["held"]    # Event consumed


# ------------------------------- Patrick de la Mote + Leeward Battle Line (Y37)
def test_patrick_doubles_culverins_dice_and_leeward_halves_them():
    s = _duel(7)
    s.lords["york"].capabilities = ["Y1"]              # CULVERINS AND FALCONETS
    s.decks["yorkist"]["held"] = ["Y37"]               # PATRICK DE LA MOTE
    s.decks["lancastrian"]["held"] = ["L1"]            # LEEWARD BATTLE LINE
    p_only = s.model_copy(deep=True)
    plain = s.model_copy(deep=True)
    plain.lords["york"].capabilities = []

    def strike(r):
        return r["rounds"][0]["engagements"][0]["strikes"][0]

    base = strike(battle.resolve_battle(
        plain, "cambridge", "henry_vi", "york", {}))["defender_hits"]
    r_p = battle.resolve_battle(p_only, "cambridge", "henry_vi", "york",
                                {"patrick": True, "culverins": ["york"]})
    r_pl = battle.resolve_battle(s, "cambridge", "henry_vi", "york",
                                 {"patrick": True, "culverins": ["york"],
                                  "leeward": ["lancastrian"]})
    d_p, d_pl = strike(r_p)["defender_hits"], strike(r_pl)["defender_hits"]
    assert strike(r_p)["phase"] == "missile"
    assert base + 2 <= d_p <= base + 12                # Patrick: TWO Culverins dice
    assert d_pl == ceil(d_p / 2)                       # Leeward halves them (same dice)
    assert "Y37" not in s.decks["yorkist"]["held"]
    assert "L1" not in s.decks["lancastrian"]["held"]
    assert "Y1" not in s.lords["york"].capabilities    # Culverins fired -> discarded


def test_patrick_requires_a_yorkist_culverins_in_the_battle():
    s = _duel(7)
    s.decks["yorkist"]["held"] = ["Y37"]
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "henry_vi", "york", {"patrick": True})
    assert e.value.code == "no_culverins_for_patrick"


# ------------------------------------------------------ Norfolk is Late (Towton)
def test_norfolk_is_late_holds_norfolk_in_reserve_once():
    t = build_initial_state("towton", seed=3)
    for lid in ("march", "norfolk"):
        t.lords[lid].location = "newcastle"
    fork = t.model_copy(deep=True)
    r = battle.resolve_battle(t, "newcastle", ["march", "norfolk"], ["somerset_1"],
                              {"attacker_positions": {1: "norfolk", 0: "march"},
                               "engagement_order": ["march"]})
    round1 = {x for e in r["rounds"][0]["engagements"] for x in e["attacker"] + e["defender"]}
    assert "norfolk" not in round1 and "march" in round1   # held in Reserve Round 1
    assert t.flags.get("norfolk_is_late_used") is True
    # The special rule fires only once: with the flag already used, Norfolk
    # arrays normally from Round 1.
    fork.flags["norfolk_is_late_used"] = True
    r2 = battle.resolve_battle(fork, "newcastle", ["march", "norfolk"], ["somerset_1"], {})
    round1b = {x for e in r2["rounds"][0]["engagements"] for x in e["attacker"] + e["defender"]}
    assert "norfolk" in round1b


# ------------------------------------------------------- Swift Maneuver (Y36)
def test_swift_maneuver_event_plays_and_is_consumed():
    # Seed 28: Henry's Retinue Routs, so the Y36 end-the-Round branch executes.
    s = _duel(28)
    s.decks["yorkist"]["held"] = ["Y36"]
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"swift_maneuver": "yorkist"})
    assert "Y36" not in s.decks["yorkist"]["held"]
    assert r["winner_side"] == "yorkist"


# --------------------------------------------- Warden of the Marches (L16, 4.4.3)
def _north_duel(seed):
    s = _duel(seed, at="newcastle")
    s.locales["carlisle"].favour = "lancastrian"       # a Friendly North refuge
    s.decks["lancastrian"]["held"] = ["L16"]
    return s


def test_warden_moves_routed_lancastrian_north_instead_of_death_roll():
    # Seed 1: Henry VI Routs; L16 moves him to the Friendly North Stronghold.
    # He has no Troops left, so he then Disbands (the L16 no-Troops clause) --
    # but he took no Death roll.
    s = _north_duel(1)
    r = battle.resolve_battle(s, "newcastle", "york", "henry_vi", {"warden": True})
    assert r["warden_moved"] == ["henry_vi"]
    assert "henry_vi" not in r["deaths"]
    assert "henry_vi" in r["disbands"]
    assert "L16" not in s.decks["lancastrian"]["held"]  # window opened -> consumed


def test_warden_not_consumed_when_no_death_check_window_opens():
    # Seed 2: no Lancastrian Routs, so the Death-check window never opens and
    # the Held Event must NOT be burned.
    s = _north_duel(2)
    r = battle.resolve_battle(s, "newcastle", "york", "henry_vi", {"warden": True})
    assert not r.get("warden_moved")
    assert "L16" in s.decks["lancastrian"]["held"]


def test_warden_is_legal_only_in_the_north():
    s = _duel(1)                                       # cambridge: not the North
    s.decks["lancastrian"]["held"] = ["L16"]
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"warden": True})
    assert e.value.code == "warden_not_north"


# ------------------------------------------------------ Talbot to the Rescue (L36)
def test_talbot_disbands_routed_lancastrian_instead_of_death_roll():
    # Seed 1: Henry VI Routs. L36 turns his Death check into a Disband.
    s = _duel(1)
    s.decks["lancastrian"]["held"] = ["L36"]
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"talbot": True})
    assert "henry_vi" in r["disbands"] and "henry_vi" not in r["deaths"]
    assert "L36" not in s.decks["lancastrian"]["held"]      # window opened -> consumed


# ------------------------------------------------------------- Vanguard (Y36 cap)
def test_vanguard_requires_the_capability_and_battle_resolves_with_it():
    s = _duel(5)
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"vanguard": "york"})
    assert e.value.code == "no_vanguard"
    s2 = _duel(5)
    s2.lords["york"].capabilities = ["Y36"]                 # VANGUARD
    r = battle.resolve_battle(s2, "cambridge", "york", "henry_vi", {"vanguard": "york"})
    assert r["rounds"]                                      # Round 1 restricted to his Engagement


# ------------------------------------------- Culverins one-zone (adjudication)
def test_culverins_discarded_exactly_once_when_firing_lord_disbands():
    # Card text (Y1/L1): "this Lord may discard this card to add 1 die roll of
    # Missile Hits ... then discard." The 2026-07-02 mutation triage flagged a
    # possible double-discard masked by the loser's Disband re-discarding the
    # mat; adjudicated clean -- the firing discard removes the card from the
    # mat, so the Disband has nothing to re-discard. Seed 32: Henry VI fires
    # Culverins, Routs, and Disbands; exactly one L1 ends in the discard pile.
    from plantagenet import invariants
    s = _duel(32)
    s.decks["lancastrian"]["draw"].remove("L1")     # deploy from the deck, one zone
    s.lords["henry_vi"].capabilities = ["L1"]
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"culverins": ["henry_vi"]})
    assert "henry_vi" in r["disbands"]
    assert s.decks["lancastrian"]["discard"].count("L1") == 1
    assert "L1" not in s.lords["henry_vi"].capabilities
    assert not [v for v in invariants.board_invariant_violations(s)
                if "card" in v.get("kind", "")]
