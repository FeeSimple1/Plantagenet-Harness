"""Mutation-testing kill suite for src/plantagenet/battle.py.

Each test pins exact rules behaviour that a surviving mutant (see
mutation-results/battle.py.triage.md) would change: death-roll thresholds
and the Flee -2 (4.4.3), Losses rolls, Spoils/Exile asset arithmetic,
Culverins dice counts, Caltrops splitting, decision plumbing, and the
positional Array/Reposition/Engagement rules (4.4.1-4.4.2).

Dice are controlled either with an exact-sequence stub (monkeypatched onto
``GameState.dice``) or by peeking the state-held roller on a deep copy.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from plantagenet import battle, influence
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus, VassalState, VassalStatus


class _SeqDice:
    """Deterministic d6 stream: exact sequence, optionally cycling."""

    def __init__(self, seq, cycle=False):
        self.seq = list(seq)
        self.i = 0
        self.cycle = cycle

    def d6(self):
        if self.i >= len(self.seq):
            if not self.cycle:
                raise AssertionError("unexpected extra d6 roll")
            self.i = 0
        v = self.seq[self.i]
        self.i += 1
        return v


def _patch_dice(monkeypatch, seq, cycle=False):
    stub = _SeqDice(seq, cycle)
    monkeypatch.setattr(GameState, "dice", lambda self: stub)
    monkeypatch.setattr(GameState, "store_dice", lambda self, roller: None)
    return stub


def _duel(seed=1, a="york", d="henry_vi", at="cambridge"):
    s = build_initial_state("henry_vi", seed=seed)
    for lid in (a, d):
        s.lords[lid].location = at
        s.lords[lid].capabilities = []
    return s


def _net(state):
    return influence._net_lanc(state.influence["track"])


def _melee(result, eng=0):
    strikes = result["rounds"][0]["engagements"][eng]["strikes"]
    return next(st for st in strikes if st["phase"] == "melee")


def _missile(result, eng=0):
    strikes = result["rounds"][0]["engagements"][eng]["strikes"]
    return next(st for st in strikes if st["phase"] == "missile")


# --------------------------------------------------------------- FLEE (4.4.2)
def test_flee_rounds_accepts_round_one():
    s = _duel(seed=2)
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"flee_rounds": {"york": 1}})
    assert r["rounds"][0]["fled"] == ["york"]
    assert r["winner_side"] == "lancastrian"


def test_both_sides_fleeing_is_a_draw():
    s = _duel(seed=2)
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"flee": ["york", "henry_vi"]})
    assert r["winner_side"] is None            # both sides lose (4.4.3)
    assert len(r["rounds"]) == 1
    assert r["rounds"][0]["engagements"] == []
    assert "influence_award" not in r
    assert "for_trust_not_him" not in r


# ----------------------------------------------------- winner Influence (4.4.3)
def test_influence_awards_and_capture_of_the_king():
    s = _duel(seed=2)
    s.lords["york"].vassals = ["devon"]        # printed 5 + 1 Vassal = 6
    net0 = _net(s)
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"flee": ["york"]})
    assert r["influence_award"] == {"lancastrian": 6}
    assert _net(s) - net0 == 6
    # Capture of the King (Scenario Ia): exactly +10 Influence, no Death roll.
    s2 = _duel(seed=2)
    net0 = _net(s2)
    r2 = battle.resolve_battle(s2, "cambridge", "york", "henry_vi",
                               {"flee": ["henry_vi"]})
    assert r2["captured"] == [{"lord": "henry_vi", "by": "york"}]
    assert r2["deaths"] == [] and r2["disbands"] == []
    assert net0 - _net(s2) == r2["influence_award"]["yorkist"] + 10


# ------------------------------------------------------- Escape Ship (4.4.3)
def test_escape_ship_rules():
    # At a Friendly Port: Exile, the card is burned, Influence 5+1 is paid.
    s = _duel(seed=2, at="ipswich")
    s.locales["ipswich"].favour = "yorkist"
    s.lords["york"].vassals = ["devon"]
    s.decks["yorkist"]["held"] = ["Y3"]        # ESCAPE SHIP
    net0 = _net(s)
    r = battle.resolve_battle(s, "ipswich", "york", "henry_vi",
                              {"flee": ["york"], "escape_ship": ["york"]})
    assert r["exiles"] == ["york"] and r["deaths"] == [] and r["disbands"] == []
    assert "Y3" not in s.decks["yorkist"]["held"]
    assert _net(s) - net0 == 12                # win award 5+1, plus Exile 5+1
    # An overland Friendly Route to a Friendly Port (ely -> lynn) also works.
    s2 = _duel(seed=2, at="ely")
    s2.locales["lynn"].favour = "yorkist"
    s2.decks["yorkist"]["held"] = ["Y3"]
    r2 = battle.resolve_battle(s2, "ely", "york", "henry_vi",
                               {"flee": ["york"], "escape_ship": ["york"]})
    assert "york" in r2["exiles"]
    # No traceable Route to the only Friendly Port -> no Escape Ship.
    s3 = _duel(seed=2, at="cambridge")
    for meta in s3.locales.values():
        meta.favour = "lancastrian"
    s3.locales["newcastle"].favour = "yorkist"     # friendly port, unreachable
    s3.decks["yorkist"]["held"] = ["Y3"]
    r3 = battle.resolve_battle(s3, "cambridge", "york", "henry_vi",
                               {"flee": ["york"], "escape_ship": ["york"]})
    assert r3["exiles"] == []
    # Naming an Unrouted Lord must not burn the card.
    s4 = _duel(seed=2, at="lynn")
    s4.locales["lynn"].favour = "lancastrian"
    s4.decks["lancastrian"]["held"] = ["L3"]
    r4 = battle.resolve_battle(s4, "lynn", "york", "henry_vi",
                               {"flee": ["york"], "escape_ship": ["henry_vi"]})
    assert r4["exiles"] == []
    assert "L3" in s4.decks["lancastrian"]["held"]


# -------------------------------------------------------- Death check (4.4.3)
def _routed_loser_ending(s, fled=False):
    forces = {lid: battle._Force(s, lid) for lid in ("york", "somerset_1")}
    forces["somerset_1"].lord_routed = True
    forces["somerset_1"].fled = fled
    return battle._ending(s, "cambridge", forces, ["york"], ["somerset_1"], [], [])


def test_death_roll_threshold_and_flee_modifier(monkeypatch):
    s = _duel(seed=1, d="somerset_1")
    s.lords["york"].vassals = ["devon"]        # a Routed Vassal of the winner
    s.vassals["devon"] = VassalState(vassal_id="devon",
                                     status=VassalStatus.MUSTERED,
                                     on_lord="york")
    _patch_dice(monkeypatch, [3])              # 3 >= 3 -> dies
    forces = {lid: battle._Force(s, lid) for lid in ("york", "somerset_1")}
    forces["somerset_1"].lord_routed = True
    forces["york"].routed["vassal"] = 1
    r = battle._ending(s, "cambridge", forces, ["york"], ["somerset_1"], [], [])
    assert r["deaths"] == ["somerset_1"] and r["disbands"] == []
    assert r["vassal_disbands"] == ["devon"]   # 4.4.3: Disbands, leaves the mat
    assert "devon" not in s.lords["york"].vassals
    # The Flee -2 modifier straddles the threshold.
    s2 = _duel(seed=1, d="somerset_1")
    _patch_dice(monkeypatch, [5])              # 5 - 2 = 3 -> dies
    r2 = _routed_loser_ending(s2, fled=True)
    assert r2["deaths"] == ["somerset_1"]
    s3 = _duel(seed=1, d="somerset_1")
    _patch_dice(monkeypatch, [4])              # 4 - 2 = 2 -> Disbands
    r3 = _routed_loser_ending(s3, fled=True)
    assert r3["disbands"] == ["somerset_1"] and r3["deaths"] == []


def test_flee_modifier_and_no_default_talbot_end_to_end():
    # Seed 7: the first stored d6 is 3, so the fleeing Lord rolls 3-2=1: Disband.
    s = _duel(seed=7)
    assert s.model_copy(deep=True).dice().d6() == 3
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"flee": ["york"]})
    assert r["disbands"] == ["york"] and r["deaths"] == []
    # Seed 4: Somerset Routs and dies; no implicit Talbot/Warden may save him.
    s2 = _duel(seed=4, d="somerset_1")
    r2 = battle.resolve_battle(s2, "cambridge", "york", "somerset_1", {})
    assert r2["deaths"] == ["somerset_1"]


# ------------------------------------------------------------ Losses (4.4.3)
def test_losses_rolls():
    s = _duel(seed=1)
    f = battle._Force(s, "york")               # militia 2 on the mat
    f.routed["militia"] = 2
    res = {}
    battle._losses(s, f, _SeqDice([1, 6]), res)     # militia Protection is 1-1
    assert res["losses"]["york"] == {"recovered": 1, "lost": 1}
    assert s.lords["york"].forces["militia"] == 1
    s2 = _duel(seed=1)
    s2.lords["york"].forces = {"retinue": 1, "militia": 1, "men_at_arms": 1}
    f2 = battle._Force(s2, "york")
    f2.routed["militia"] = 1
    battle._losses(s2, f2, _SeqDice([6]), {})
    assert s2.lords["york"].forces["militia"] == 0  # 1 - 1, floor is 0 not 1
    # Battle-local additions never take Loss rolls.
    s3 = _duel(seed=1)
    f3 = battle._Force(s3, "york")
    f3.count["mercenaries"] = 2                # battle-local: not on the mat
    f3.routed["mercenaries"] = 2
    res3 = {}
    battle._losses(s3, f3, _SeqDice([]), res3)      # any roll would raise
    assert res3["losses"]["york"] == {"recovered": 0, "lost": 0}


# ------------------------------------------------------------ Spoils (4.4.3)
def test_spoils_rules():
    s = _duel(seed=1)
    s.locales["cambridge"].favour = "lancastrian"
    s.lords["york"].assets["cart"] = 2
    s.lords["march"].assets["cart"] = 1
    hv0 = s.lords["henry_vi"].assets["cart"]
    battle._spoils(s, "cambridge", [battle._Force(s, "henry_vi")],
                   ["york", "march"], {})
    assert s.lords["york"].assets["cart"] == 0
    assert s.lords["march"].assets["cart"] == 0
    assert s.lords["henry_vi"].assets["cart"] == hv0 + 3
    # Losers without a cart entry yield nothing (no phantom "1").
    s2 = _duel(seed=1)
    s2.locales["cambridge"].favour = "lancastrian"
    s2.lords["york"].assets.pop("cart")
    s2.lords["march"].assets.pop("cart")
    hv0 = s2.lords["henry_vi"].assets["cart"]
    res2 = {}
    battle._spoils(s2, "cambridge", [battle._Force(s2, "henry_vi")],
                   ["york", "march"], res2)
    assert res2["spoils"]["cart"] == 0
    assert s2.lords["henry_vi"].assets["cart"] == hv0
    # Neutral: halved total is drawn down across losers, keyless loser gives 0.
    s3 = _duel(seed=1)
    s3.lords["york"].assets.pop("cart")
    s3.lords["march"].assets["cart"] = 2
    battle._spoils(s3, "cambridge", [battle._Force(s3, "henry_vi")],
                   ["york", "march"], {})
    assert s3.lords["york"].assets["cart"] == 0
    assert s3.lords["march"].assets["cart"] == 1
    # spoils_to distribution with sparse asset dicts.
    s4 = _duel(seed=1)
    s4.locales["cambridge"].favour = "lancastrian"
    s4.lords["york"].assets["cart"] = 2
    s4.lords["york"].assets.pop("provender")
    s4.lords["somerset_1"].assets.pop("cart")
    s4.lords["somerset_1"].assets.pop("provender")
    winners = [battle._Force(s4, "henry_vi"), battle._Force(s4, "somerset_1")]
    battle._spoils(s4, "cambridge", winners, ["york"], {},
                   spoils_to={"somerset_1": {"cart": 2}})
    assert s4.lords["somerset_1"].assets["cart"] == 2
    assert s4.lords["somerset_1"].assets.get("provender", 0) == 0


# ---------------------------------------------------- Approach/Exile (4.3.5)
def test_exile_asset_transfer_fractions():
    # Locale favours the exiling Lord's side: the attacker takes nothing.
    s = _duel(seed=1)
    s.locales["cambridge"].favour = "lancastrian"
    battle._exile(s, "cambridge", "henry_vi", "york")
    assert s.lords["york"].assets["cart"] == 2
    assert s.lords["york"].assets["provender"] == 2
    # Neutral: half rounded up; keyless entries stay zero; cost is 5+1 Vassal.
    s2 = _duel(seed=1)
    s2.lords["henry_vi"].assets["cart"] = 3
    s2.lords["henry_vi"].assets.pop("provender")
    s2.lords["henry_vi"].vassals = ["devon"]
    s2.lords["york"].assets.pop("cart")
    net0 = _net(s2)
    battle._exile(s2, "cambridge", "henry_vi", "york")
    assert s2.lords["york"].assets["cart"] == 2          # ceil(3 * 0.5)
    assert s2.lords["york"].assets["provender"] == 2     # unchanged
    assert net0 - _net(s2) == 6                          # spend toward yorkist


# --------------------------------------------- Culverins and Patrick (4.4.1)
def test_culverins_add_exactly_one_die_without_patrick():
    s = _duel(seed=5)
    s.lords["york"].capabilities = ["Y1"]
    peek = s.model_copy(deep=True).dice()
    d1, d2 = peek.d6(), peek.d6()
    base = battle.resolve_battle(s.model_copy(deep=True), "cambridge",
                                 "york", "henry_vi", {})
    s_b = s.model_copy(deep=True)
    cul = battle.resolve_battle(s_b, "cambridge", "york", "henry_vi",
                                {"culverins": ["york"]})
    assert (_missile(cul)["attacker_hits"]
            == _missile(base)["attacker_hits"] + d1)
    assert "Y1" not in s_b.lords["york"].capabilities    # Capability discarded
    assert s_b.decks["yorkist"]["discard"].count("Y1") == 1  # exactly once
    # Patrick de la Mote: exactly two dice for a Yorkist Culverins.
    s_c = s.model_copy(deep=True)
    s_c.decks["yorkist"]["held"] = ["Y37"]
    pat = battle.resolve_battle(s_c, "cambridge", "york", "henry_vi",
                                {"culverins": ["york"], "patrick": True})
    assert (_missile(pat)["attacker_hits"]
            == _missile(base)["attacker_hits"] + d1 + d2)


def test_culverins_defender_dice_counts():
    s = _duel(seed=5)
    s.lords["henry_vi"].capabilities = ["L1"]
    s.lords["york"].capabilities = ["Y1"]      # idle: satisfies Patrick's check
    peek = s.model_copy(deep=True).dice()
    d1 = peek.d6()
    base = battle.resolve_battle(s.model_copy(deep=True), "cambridge",
                                 "york", "henry_vi", {})
    cul = battle.resolve_battle(s.model_copy(deep=True), "cambridge", "york",
                                "henry_vi", {"culverins": ["henry_vi"]})
    assert (_missile(cul)["defender_hits"]
            == _missile(base)["defender_hits"] + d1)
    # Patrick never boosts a LANCASTRIAN defender's Culverins.
    s_b = s.model_copy(deep=True)
    s_b.decks["yorkist"]["held"] = ["Y37"]
    pat = battle.resolve_battle(s_b, "cambridge", "york", "henry_vi",
                                {"culverins": ["henry_vi"], "patrick": True})
    assert (_missile(pat)["defender_hits"]
            == _missile(base)["defender_hits"] + d1)
    # ... but adds exactly one extra die for a YORKIST defender's Culverins.
    s2 = _duel(seed=5)
    s2.lords["york"].capabilities = ["Y1"]
    peek2 = s2.model_copy(deep=True).dice()
    e1, e2 = peek2.d6(), peek2.d6()
    base2 = battle.resolve_battle(s2.model_copy(deep=True), "cambridge",
                                  "henry_vi", "york", {})
    s2.decks["yorkist"]["held"] = ["Y37"]
    pat2 = battle.resolve_battle(s2, "cambridge", "henry_vi", "york",
                                 {"culverins": ["york"], "patrick": True})
    assert (_missile(pat2)["defender_hits"]
            == _missile(base2)["defender_hits"] + e1 + e2)


# ------------------------------------------------------ Hit absorption (4.4.2)
def test_absorb_side_priority_plan_and_legacy_valour_flag():
    s = _duel(seed=1)
    f = battle._Force(s, "york")               # valour 2
    log = []
    battle._absorb_side([f], 1, _SeqDice([6, 6]), battle._ABSORB_DEFAULT,
                        False, log)            # legacy False = nobody rerolls
    assert "valour_reroll" not in log[0]
    assert f.routed["militia"] == 1
    # A unit type missing from absorb_order is still appended as a target.
    f2 = battle._Force(s, "york")
    f2.count = {"retinue": 1, "militia": 1, "men_at_arms": 1}
    f2.routed = {t: 0 for t in f2.count}
    f2.valour = 0
    battle._absorb_side([f2], 2, _SeqDice([6, 6]), ["militia"], set(), [])
    assert f2.routed["militia"] == 1 and f2.routed["retinue"] == 1
    # A plan naming an exhausted unit falls through to the default priority.
    f3 = battle._Force(s, "york")
    f3.count = {"retinue": 1, "men_at_arms": 1}
    f3.routed = {"retinue": 0, "men_at_arms": 1}
    f3.valour = 0
    battle._absorb_side([f3], 1, _SeqDice([6]), battle._ABSORB_DEFAULT,
                        set(), [], "melee", None, [{"unit": "men_at_arms"}])
    assert f3.routed["men_at_arms"] == 1       # NOT Routed beyond its count
    assert f3.routed["retinue"] == 1


def test_yeomen_rules_and_capability_gates():
    s = _duel(seed=1)
    f = battle._Force(s, "york")
    f.yeomen = True
    f.valour = 0
    log = []
    battle._absorb_side([f], 1, _SeqDice([6]), battle._ABSORB_DEFAULT,
                        set(), log, "melee", None, [{"unit": "retinue"}])
    assert f.routed["men_at_arms"] == 1 and f.routed["retinue"] == 0
    assert log[0]["yeomen_redirect"] == "men_at_arms"
    g = battle._Force(s, "york")               # no Yeomen: Retinue Routs
    g.valour = 0
    battle._absorb_side([g], 1, _SeqDice([6]), battle._ABSORB_DEFAULT,
                        set(), [], "melee", None, [{"unit": "retinue"}])
    assert g.routed["retinue"] == 1 and g.routed["men_at_arms"] == 0
    # Opt-in forms, and the Church Blessing capability gate.
    s.lords["york"].capabilities = ["L31"]     # YEOMEN OF THE CROWN
    fy, fh = battle._Force(s, "york"), battle._Force(s, "henry_vi")
    battle._apply_phase_caps(s, {"york": fy, "henry_vi": fh}, {"yeomen": [True]})
    assert fy.yeomen is True                   # blanket opt-in, has the card
    assert fh.yeomen is False                  # no Capability -> never
    fy2 = battle._Force(s, "york")
    battle._apply_phase_caps(s, {"york": fy2}, {"yeomen": ["henry_vi"]})
    assert fy2.yeomen is False                 # not opted in
    fz = battle._Force(s, "henry_vi")          # no CHURCH BLESSING
    battle._apply_armour_caps(s, {"henry_vi": fz})
    assert fz.prof["men_at_arms"]["prot"] == [1, 3]


def test_piquiers_rout_count_and_battle_troop_additions():
    s = _duel(seed=1)
    f = battle._Force(s, "york")
    f.piquiers = True
    f.routed["men_at_arms"], f.routed["militia"] = 2, 1    # 3 Routed: expires
    assert f.prot_range("men_at_arms", "melee") == [1, 3]
    f2 = battle._Force(s, "york")
    f2.piquiers = True
    f2.count = {"retinue": 1, "militia": 3}
    f2.routed = {"retinue": 0, "militia": 2}               # no MaA entry: 2 < 3
    assert f2.prot_range("militia", "melee") == [1, 4]
    f3 = battle._Force(s, "york")
    f3.piquiers = True
    f3.count = {"retinue": 1, "men_at_arms": 3}
    f3.routed = {"retinue": 0, "men_at_arms": 2}           # no Militia entry
    assert f3.prot_range("men_at_arms", "missile") == [1, 4]
    # Special Vassals without an Armour modifier leave the Retinue as is.
    s3 = _duel(seed=1)
    s3.lords["york"].special_vassals = ["hastings"]
    f5 = battle._Force(s3, "york")
    battle._apply_special_vassal_armour(s3, {"york": f5})
    assert f5.prof["retinue"]["prot"] == [1, 4]
    s3.lords["york"].special_vassals = ["montagu"]      # Montagu: Armour 1-5
    f6 = battle._Force(s3, "york")
    battle._apply_special_vassal_armour(s3, {"york": f6})
    assert f6.prof["retinue"]["prot"] == [1, 5]
    # Y25 adds exactly 2 battle-local Longbowmen, none of them Routed.
    s2 = _duel(seed=1)
    s2.lords["york"].capabilities = ["Y25"]
    s2.lords["york"].forces = {"retinue": 1, "men_at_arms": 2}
    f4 = battle._Force(s2, "york")
    battle._apply_battle_troop_caps(s2, {"york": f4}, "cardiff")
    assert f4.count["longbow"] == 2
    assert f4.routed["longbow"] == 0


def test_battle_troop_capability_conditions():
    # Y37: needs a Route to Friendly Carlisle (hexham is adjacent).
    s = _duel(seed=1)
    s.lords["york"].capabilities = ["Y37"]
    s.locales["carlisle"].favour = "yorkist"
    f = battle._Force(s, "york")
    battle._apply_battle_troop_caps(s, {"york": f}, "hexham")
    assert f.count["men_at_arms"] == 4                     # 2 + 2
    s.locales["carlisle"].favour = "lancastrian"           # no Route now
    f2 = battle._Force(s, "york")
    battle._apply_battle_troop_caps(s, {"york": f2}, "hexham")
    assert f2.count["men_at_arms"] == 2
    # L33: a Friendly locale far from the Channel does NOT qualify.
    s2 = _duel(seed=1)
    s2.lords["henry_vi"].capabilities = ["L33"]
    s2.locales["york"].favour = "lancastrian"
    f3 = battle._Force(s2, "henry_vi")
    battle._apply_battle_troop_caps(s2, {"henry_vi": f3}, "york")
    assert f3.count["men_at_arms"] == 2


# ------------------------------------------------- Array and Engage (4.4.1-2)
def test_array_and_engagement_choices():
    pos, res = battle._initial_array(["a1", "a2"], ["d1"], {})
    assert pos["attacker"] == {1: "a1"}        # opposite the occupied center
    assert res["attacker"] == ["a2"]
    _, res2 = battle._initial_array(["a1"], ["d1", "d2", "d3", "d4"], {})
    assert res2["defender"] == ["d4"]
    _, res3 = battle._initial_array(["a1", "a2"], ["d1"],
                                    {"attacker_positions": {1: "a1"}})
    assert res3["attacker"] == ["a2"]

    # Flanking choice rules (4.4.2).
    def forces(*lids):
        return {lid: SimpleNamespace(lord_routed=False) for lid in lids}

    # A unique nearest target may NOT be overridden by a flank choice.
    engs = battle._engagements(
        {"attacker": {0: "a1", 2: "a2"}, "defender": {1: "d1", 2: "d2"}},
        forces("a1", "a2", "d1", "d2"), {"a1": 2})
    assert len(engs) == 2
    # In a genuine tie an integer choice picks that column.
    positions = {"attacker": {0: "a2", 1: "a1", 2: "a3"},
                 "defender": {0: "d1", 2: "d2"}}
    engs2 = battle._engagements(positions, forces("a1", "a2", "a3", "d1", "d2"),
                                {"a1": 2})
    grp = next(e for e in engs2 if "a1" in e["attacker"])
    assert grp["defender"] == ["d2"]
    # An out-of-range integer falls back to the default (nearest, ties left).
    engs3 = battle._engagements(positions, forces("a1", "a2", "a3", "d1", "d2"),
                                {"a1": 7})
    grp3 = next(e for e in engs3 if "a1" in e["attacker"])
    assert grp3["defender"] == ["d1"]


def test_reposition_rout_removal_held_reserves_and_center_fill():
    def forces(**routed):
        return {lid: SimpleNamespace(lord_routed=r) for lid, r in routed.items()}

    # Routed front Lords leave the Array and a reserve advances.
    positions = {"defender": {1: "d1"}, "attacker": {}}
    reserves = {"defender": ["d2"], "attacker": []}
    battle._reposition(positions, reserves, forces(d1=True, d2=False))
    assert positions["defender"] == {1: "d2"}
    # A held reserve (Norfolk is Late) may not be advanced by choice either.
    positions = {"attacker": {1: "a1"}, "defender": {}}
    reserves = {"attacker": ["a2"], "defender": []}
    battle._reposition(positions, reserves, forces(a1=False, a2=False),
                       held=frozenset({"a2"}),
                       repo={"attacker": {"advance": {0: "a2"}}})
    assert reserves["attacker"] == ["a2"]
    assert positions["attacker"] == {1: "a1"}
    # Center fill: the default also reaches a lone RIGHT wing ...
    positions = {"attacker": {2: "a2"}, "defender": {}}
    battle._reposition(positions, {"attacker": [], "defender": []},
                       forces(a2=False))
    assert positions["attacker"] == {1: "a2"}
    # ... and takes the LEFT wing first when both are options ...
    positions = {"attacker": {0: "a1"}, "defender": {}}
    battle._reposition(positions, {"attacker": [], "defender": []},
                       forces(a1=False))
    assert positions["attacker"] == {1: "a1"}
    # ... an empty chosen wing falls back to [left, right] ...
    positions = {"attacker": {0: "a1"}, "defender": {}}
    battle._reposition(positions, {"attacker": [], "defender": []},
                       forces(a1=False), repo={"attacker": {"center_from": 2}})
    assert positions["attacker"] == {1: "a1"}
    # ... and choosing the RIGHT wing moves that Lord when it is occupied.
    positions = {"attacker": {0: "a1", 2: "a2"}, "defender": {}}
    battle._reposition(positions, {"attacker": [], "defender": []},
                       forces(a1=False, a2=False),
                       repo={"attacker": {"center_from": 2}})
    assert positions["attacker"] == {0: "a1", 1: "a2"}


# ------------------------------------------------- multi-Lord Round control
def _two_on_two(seed=1):
    s = build_initial_state("henry_vi", seed=seed)
    for lid, n in (("york", 2), ("march", 2), ("henry_vi", 0), ("somerset_1", 2)):
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
        forces = {"retinue": 1}
        if n:
            forces["men_at_arms"] = n          # no Missile strikes: no dice
        s.lords[lid].forces = forces
    return s


def test_swift_maneuver_ends_the_round_only_when_played(monkeypatch):
    s = _two_on_two()
    s.decks["yorkist"]["held"] = ["Y36"]
    _patch_dice(monkeypatch, [6, 1, 1, 1], cycle=True)   # Henry's Retinue Routs
    r = battle.resolve_battle(s, "cambridge", ["york", "march"],
                              ["henry_vi", "somerset_1"],
                              {"swift_maneuver": "yorkist", "valour": False})
    assert len(r["rounds"][0]["engagements"]) == 1       # Round ended early
    s2 = _two_on_two()
    _patch_dice(monkeypatch, [6, 1, 1, 1], cycle=True)
    r2 = battle.resolve_battle(s2, "cambridge", ["york", "march"],
                               ["henry_vi", "somerset_1"], {"valour": False})
    assert len(r2["rounds"][0]["engagements"]) == 2      # no Swift: full Round


def test_caltrops_split_between_engagements():
    def hits(decisions, seed=3):
        s = _two_on_two(seed=seed)
        s.decks["yorkist"]["held"] = ["Y19"]
        r = battle.resolve_battle(s, "cambridge", ["york", "march"],
                                  ["henry_vi", "somerset_1"], decisions)
        return [_melee(r, 0)["attacker_hits"], _melee(r, 1)["attacker_hits"]]

    base = {"caltrops": ["yorkist"]}
    assert hits({**base, "caltrops_split": {1: {"yorkist": [1, 0]}}}) == [6, 5]
    assert hits({**base, "caltrops_split": {1: {"yorkist": [1, 1]}}}) == [6, 6]
    # A short split list: the remainder defaults to the leftover budget.
    assert hits({**base, "caltrops_split": {1: {"yorkist": [1]}}}) == [6, 6]


def test_vanguard_restricts_round_one_only(monkeypatch):
    s = _two_on_two()
    s.lords["york"].capabilities = ["Y36"]     # VANGUARD
    _patch_dice(monkeypatch, [1], cycle=True)  # everything saves: no Routs
    r = battle.resolve_battle(s, "cambridge", ["york", "march"],
                              ["henry_vi", "somerset_1"], {"vanguard": "york"})
    assert len(r["rounds"][0]["engagements"]) == 1
    assert "york" in r["rounds"][0]["engagements"][0]["attacker"]
    assert len(r["rounds"][1]["engagements"]) == 2       # Round 2: all engage
    assert len(r["rounds"]) == 60              # the emergency Round cap (4.4.2)


def test_ravine_ignores_a_lord_in_round_one_only(monkeypatch):
    s = _two_on_two()
    s.decks["lancastrian"]["held"] = ["L12"]   # RAVINE, played against york
    _patch_dice(monkeypatch, [1], cycle=True)  # everything saves: no Routs
    r = battle.resolve_battle(s, "cambridge", ["york", "march"],
                              ["henry_vi", "somerset_1"], {"ravine": "york"})
    r1 = r["rounds"][0]["engagements"]
    assert len(r1) == 1                        # york's Engagement is skipped
    assert r1[0]["attacker"] == ["march"] and r1[0]["defender"] == ["somerset_1"]
    assert any("york" in e["attacker"]
               for e in r["rounds"][1]["engagements"])   # back in Round 2


def test_final_charge_math_and_retinue_self_hit(monkeypatch):
    def setup():
        s = build_initial_state("my_kingdom_for_a_horse")
        s.lords["richard_iii"].status = LordStatus.MUSTERED
        s.lords["richard_iii"].location = "leicester"
        s.lords["richard_iii"].capabilities = ["Y32"]
        s.lords["richard_iii"].forces = {"retinue": 1, "men_at_arms": 2}
        s.lords["henry_tudor"].location = "leicester"
        s.lords["henry_tudor"].forces = {"retinue": 1}
        return s

    fc = {"final_charge": ["richard_iii"], "valour": False}
    # Self-hit fails (5 vs Armour 1-4): Richard Routs alongside his victim.
    _patch_dice(monkeypatch, [5, 6, 1, 1, 1, 1, 1])
    r = battle.resolve_battle(setup(), "leicester", "richard_iii",
                              "henry_tudor", fc)
    assert _melee(r)["attacker_hits"] == 8               # ceil(3+2) + exactly 3
    assert r["winner_side"] is None
    # Boundary saves: rolls of exactly 4 (hi) and 1 (lo) both save.
    for die in (4, 1):
        _patch_dice(monkeypatch, [die, 6, 1, 1, 1, 1])
        r2 = battle.resolve_battle(setup(), "leicester", "richard_iii",
                                   "henry_tudor", fc)
        assert r2["winner_side"] == "yorkist"
    # A failed self-hit may be Valour-rerolled; the reroll saves on 4.
    _patch_dice(monkeypatch, [5, 4, 6, 6, 1, 1, 1, 1])
    r3 = battle.resolve_battle(setup(), "leicester", "richard_iii",
                               "henry_tudor", {"final_charge": ["richard_iii"]})
    assert r3["winner_side"] == "yorkist"


# ---------------------------------------------------- Norfolk is Late (Towton)
def test_norfolk_is_late_needs_another_yorkist_and_returns(monkeypatch):
    t = build_initial_state("towton", seed=1)
    for lid in ("norfolk", "somerset_1", "march"):
        t.lords[lid].location = "york"
    r = battle.resolve_battle(t, "york", ["norfolk"], ["somerset_1"], {})
    assert r["rounds"][0]["engagements"] != []           # alone: NOT late
    assert not t.flags.get("norfolk_is_late_used")
    t2 = build_initial_state("towton", seed=1)
    for lid in ("norfolk", "somerset_1", "march"):
        t2.lords[lid].location = "york"
    _patch_dice(monkeypatch, [1], cycle=True)            # no Routs: reach Round 2
    r2 = battle.resolve_battle(t2, "york", ["norfolk", "march"],
                               ["somerset_1"], {})
    assert t2.flags.get("norfolk_is_late_used") is True
    assert all("norfolk" not in e["attacker"]
               for e in r2["rounds"][0]["engagements"])
    assert any("norfolk" in e["attacker"]
               for e in r2["rounds"][1]["engagements"])  # advances in Round 2
    # Test of Arms: only a Battle AT York flips York's Favour to the winner.
    t3 = build_initial_state("towton", seed=1)
    for lid in ("march", "somerset_1"):
        t3.lords[lid].location = "york"
    r3 = battle.resolve_battle(t3, "york", ["march"], ["somerset_1"],
                               {"flee": ["somerset_1"]})
    assert r3["test_of_arms"] == "yorkist"
    assert t3.locales["york"].favour == "yorkist"
    t4 = build_initial_state("towton", seed=1)
    for lid in ("march", "somerset_1"):
        t4.lords[lid].location = "cambridge"
    battle.resolve_battle(t4, "cambridge", ["march"], ["somerset_1"],
                          {"flee": ["somerset_1"]})
    assert t4.locales["york"].favour == "neutral"


# -------------------------------------------- For Trust Not Him (L7, 3.4.3)
def test_for_trust_moves_the_vassal_and_its_battle_unit(monkeypatch):
    assert battle._vassal_loyalty_mod("devon", "lancastrian") == 1
    assert battle._vassal_loyalty_mod("devon", "yorkist") == -1

    def run(vassals):
        s = _duel(seed=1)
        s.lords["henry_vi"].vassals = list(vassals)
        s.vassals["devon"] = VassalState(vassal_id="devon",
                                         status=VassalStatus.MUSTERED,
                                         on_lord="henry_vi")
        s.decks["yorkist"]["held"] = ["L7"]
        forces = {lid: battle._Force(s, lid) for lid in ("york", "henry_vi")}
        _patch_dice(monkeypatch, [1])                    # check always succeeds
        res = battle._resolve_for_trust(
            s, ["york"], ["henry_vi"], forces,
            {"for_trust_not_him": {"by": "york", "target": "devon"}})
        assert res["success"] is True
        return s, forces

    s, forces = run(["devon", "shrewsbury"])
    assert forces["henry_vi"].count["vassal"] == 1       # 2 - 1
    assert forces["york"].count["vassal"] == 1
    assert forces["york"].routed["vassal"] == 0          # arrives Unrouted
    assert "devon" in s.lords["york"].vassals
    s2, forces2 = run(["devon"])
    assert forces2["henry_vi"].count["vassal"] == 0      # 1 - 1, floor 0


# ---------------------------------------------------------- validation guards
def test_validation_guards_and_north_stronghold():
    s = _duel(seed=1)
    for loc in ("scarborough", "newcastle", "appleby", "hexham", "bamburgh"):
        s.locales[loc].favour = "yorkist"
    s.locales["carlisle"].favour = "lancastrian"
    assert battle._friendly_north_stronghold(s) == "carlisle"
    # Approach requires a Mustered attacker AT the locale.
    s2 = _duel(seed=1)
    s2.lords["york"].location = "london"
    with pytest.raises(IllegalAction) as e:
        battle.approach(s2, "cambridge", ["york"])
    assert e.value.code == "no_attacker"
    # Suspicion must name a target IN the battle.
    s3 = _duel(seed=1)
    with pytest.raises(IllegalAction) as e3:
        battle.resolve_battle(s3, "cambridge", "york", "henry_vi",
                              {"suspicion": {"by": "york", "target": "buckingham"}})
    assert e3.value.code == "bad_suspicion"
    # Final Charge is Richard III only (Y32).
    s5 = _duel(seed=1)
    with pytest.raises(IllegalAction) as e5:
        battle.resolve_battle(s5, "cambridge", "york", "henry_vi",
                              {"final_charge": ["york"]})
    assert e5.value.code == "no_final_charge"
    # Blocked Ford must be an IllegalAction without the Held Event.
    s4 = _duel(seed=1)
    with pytest.raises(IllegalAction) as e4:
        battle.approach(s4, "cambridge", ["york"], {"blocked_ford": ["yorkist"]})
    assert e4.value.code == "no_blocked_ford"


# ------------------------------------------- decision plumbing (4.4.2 "or []")
def _muster_line(seed=1, lords=("york", "march", "henry_vi", "somerset_1")):
    """Mustered Lords at Cambridge with Retinue + 2 Men-at-Arms (no Missiles)."""
    s = build_initial_state("henry_vi", seed=seed)
    for lid in lords:
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
        s.lords[lid].forces = {"retinue": 1, "men_at_arms": 2}
    return s


def test_engagement_order_decision_reorders_engagements():
    # 4.4.2: the Attacker declares the order Engagements resolve in. Fork
    # oracle: the same state with and without a supplied order.
    s = _muster_line()
    base = battle.resolve_battle(s.model_copy(deep=True), "cambridge",
                                 ["york", "march"], ["henry_vi", "somerset_1"], {})
    assert base["rounds"][0]["engagements"][0]["attacker"] == ["york"]
    ordered = battle.resolve_battle(s.model_copy(deep=True), "cambridge",
                                    ["york", "march"], ["henry_vi", "somerset_1"],
                                    {"engagement_order": ["march"]})
    assert ordered["rounds"][0]["engagements"][0]["attacker"] == ["march"]


def test_absorb_lords_decision_changes_which_lord_absorbs_first():
    # 4.4.2: in a 1v2 Engagement the owner picks which Lord absorbs first.
    s = _muster_line(lords=("york", "henry_vi", "somerset_1"))
    base = battle.resolve_battle(s.model_copy(deep=True), "cambridge", "york",
                                 ["henry_vi", "somerset_1"], {})
    assert len(base["rounds"][0]["engagements"]) == 1
    assert _melee(base)["defender_rolls"][0]["lord"] == "henry_vi"
    picked = battle.resolve_battle(s.model_copy(deep=True), "cambridge", "york",
                                   ["henry_vi", "somerset_1"],
                                   {"absorb_lords": ["somerset_1"]})
    assert _melee(picked)["defender_rolls"][0]["lord"] == "somerset_1"


def test_absorb_plan_decision_directs_hits_unit_by_unit():
    # 4.4.2 "Hit by Hit": the plan redirects the first Hit onto the Retinue.
    s = _muster_line(lords=("york", "henry_vi"))
    base = battle.resolve_battle(s.model_copy(deep=True), "cambridge", "york",
                                 "henry_vi", {})
    assert _melee(base)["defender_rolls"][0]["unit"] == "men_at_arms"
    planned = battle.resolve_battle(
        s.model_copy(deep=True), "cambridge", "york", "henry_vi",
        {"absorb_plan": {"defender": [{"unit": "retinue"}]}})
    assert _melee(planned)["defender_rolls"][0]["unit"] == "retinue"


def test_reposition_decision_is_honoured_with_int_round_keys():
    # 4.4.2 REPOSITION: with wings-only Arrays the default center fill (from
    # the left) keeps two column-on-column Engagements; the attacker choosing
    # center_from=2 skews the line into ONE merged Engagement. The int Round
    # key must be honoured as-is, without needing the str-key fallback.
    s = _muster_line()
    pos = {"attacker_positions": {0: "york", 2: "march"},
           "defender_positions": {0: "henry_vi", 2: "somerset_1"}}
    base = battle.resolve_battle(s.model_copy(deep=True), "cambridge",
                                 ["york", "march"], ["henry_vi", "somerset_1"],
                                 dict(pos))
    assert len(base["rounds"][0]["engagements"]) == 2
    skew = battle.resolve_battle(
        s.model_copy(deep=True), "cambridge", ["york", "march"],
        ["henry_vi", "somerset_1"],
        {**pos, "reposition": {1: {"attacker": {"center_from": 2}}}})
    assert len(skew["rounds"][0]["engagements"]) == 1


# -------------------------------------------------------------- Regroup (Y30)
def test_regroup_defaults_to_round_two_and_recovers_singly(monkeypatch):
    # Omitting "round" defaults to Round 2 (4.4.2); the recovery counter starts
    # at 0, a roll of exactly hi (Militia Protection 1-1, roll 1) recovers, and
    # each success recovers exactly ONE Troop: [1, 6] on 2 Routed Militia.
    s = _duel(seed=1)
    s.lords["york"].forces = {"retinue": 1, "militia": 3}
    s.lords["henry_vi"].forces = {"retinue": 1}
    s.decks["yorkist"]["held"] = ["Y30"]       # REGROUP
    # R1 missile: Henry saves 2 Hits [1,1]; melee: Henry saves 5 [1x5], York's
    # Militia roll [6,6,1] and two Rout. R2 Regroup [1,6] recovers one; missile
    # [1]; melee: Henry's Retinue fails [6] (no reroll) and Routs; York saves
    # [1,1,1]. Ending: the King is Captured (no Death roll); the Losses roll
    # [6] for York's one still-Routed Militia loses it.
    stub = _patch_dice(monkeypatch, [1, 1, 1, 1, 1, 1, 1, 6, 6, 1,
                                     1, 6, 1, 6, 1, 1, 1, 6])
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"regroup": {"lord": "york"}, "valour": False})
    assert len(r["rounds"]) == 2 and r["winner_side"] == "yorkist"
    assert r["losses"]["york"] == {"recovered": 0, "lost": 1}
    assert s.lords["york"].forces["militia"] == 2
    assert stub.i == len(stub.seq)             # every die accounted for


def test_regroup_recovery_fires_on_its_round_only(monkeypatch):
    # Recovery rolls happen at the START of the named Round only: a Militia
    # Routed again in Round 2 stays Routed through Round 3 and comes back via
    # the Losses roll [1], not via a phantom Round-3 Regroup.
    s = _duel(seed=1)
    s.lords["york"].forces = {"retinue": 1, "militia": 2}
    s.lords["henry_vi"].forces = {"retinue": 1}
    s.decks["yorkist"]["held"] = ["Y30"]
    stub = _patch_dice(monkeypatch, [1, 1, 1, 1, 1, 6, 1, 1,
                                     1, 1, 1, 1, 1, 1, 6, 1, 1,
                                     1, 6, 1, 1, 1, 1])
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"regroup": {"lord": "york", "round": 2},
                               "valour": False})
    assert len(r["rounds"]) == 3 and r["winner_side"] == "yorkist"
    assert r["losses"]["york"] == {"recovered": 1, "lost": 0}
    assert s.lords["york"].forces["militia"] == 2
    assert stub.i == len(stub.seq)


# --------------------------------------------- Final Charge Valour gate (Y32)
def _kingdom(forces_r3, forces_tudor):
    s = build_initial_state("my_kingdom_for_a_horse")
    s.lords["richard_iii"].status = LordStatus.MUSTERED
    s.lords["richard_iii"].location = "leicester"
    s.lords["richard_iii"].capabilities = ["Y32"]
    s.lords["richard_iii"].forces = dict(forces_r3)
    s.lords["henry_tudor"].location = "leicester"
    s.lords["henry_tudor"].forces = dict(forces_tudor)
    return s


def test_final_charge_valour_gate_is_strictly_positive(monkeypatch):
    # Richard (Valour 2) burns both points on Missile-phase rerolls [6,6/6,1];
    # his failed Final Charge self-Hit [5] then gets NO reroll at Valour 0: the
    # Retinue Routs and the Battle is a mutual loss.
    s = _kingdom({"retinue": 1, "men_at_arms": 2}, {"retinue": 1, "longbow": 1})
    stub = _patch_dice(monkeypatch, [6, 6, 6, 1, 5, 6, 6, 6, 6, 1, 1])
    r = battle.resolve_battle(s, "leicester", "richard_iii", "henry_tudor",
                              {"final_charge": ["richard_iii"]})
    assert r["winner_side"] is None            # both Retinues Routed in Round 1
    assert sorted(r["disbands"]) == ["henry_tudor", "richard_iii"]
    assert stub.i == len(stub.seq)


def test_final_charge_reroll_burns_exactly_one_valour(monkeypatch):
    # Final Charge in Rounds 1 AND 2 with the self-Hit failing [5] each Round:
    # the Round-1 reroll must burn exactly one Valour (2 -> 1) so the Round-2
    # gate (Valour 1 > 0) still allows the reroll into the save [1] and a win.
    s = _kingdom({"retinue": 1}, {"retinue": 1, "militia": 4, "men_at_arms": 1})
    stub = _patch_dice(monkeypatch, [1, 1, 5, 1, 6, 6, 6, 6, 1, 1,
                                     1, 1, 1, 1, 1, 1, 5, 1, 6, 6,
                                     1, 1, 1, 1, 1])
    r = battle.resolve_battle(s, "leicester", "richard_iii", "henry_tudor",
                              {"final_charge": {"richard_iii": [1, 2]},
                               "valour": ["richard_iii"]})
    assert len(r["rounds"]) == 2 and r["winner_side"] == "yorkist"
    assert r["disbands"] == ["henry_tudor"]
    assert stub.i == len(stub.seq)


# ------------------------------------------------------- Swift Maneuver (Y36)
def test_swift_break_needs_a_new_retinue_rout_this_round(monkeypatch):
    # Round 1: the directed Hit Routs Buckingham's Retinue [6] and the Round
    # ends early (1 of 2 Engagements). Round 2: Buckingham is still Routed but
    # that is NOT a Retinue Routed THIS Round, so both Engagements resolve.
    s = build_initial_state("henry_vi", seed=1)
    for lid, forces in (("york", {"retinue": 1, "men_at_arms": 2}),
                        ("march", {"retinue": 1, "men_at_arms": 2}),
                        ("henry_vi", {"retinue": 1, "men_at_arms": 2}),
                        ("somerset_1", {"retinue": 1, "men_at_arms": 2}),
                        ("buckingham", {"retinue": 1})):
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
        s.lords[lid].forces = forces
    s.decks["yorkist"]["held"] = ["Y36"]       # SWIFT MANEUVER
    stub = _patch_dice(monkeypatch, [6] + [1] * 34)
    r = battle.resolve_battle(
        s, "cambridge", ["york", "march"],
        ["henry_vi", "somerset_1", "buckingham"],
        {"swift_maneuver": "yorkist", "valour": False,
         "absorb_plan": {"defender": [{"lord": "buckingham", "unit": "retinue"}]},
         "flee_rounds": {"henry_vi": 3, "somerset_1": 3}})
    assert len(r["rounds"][0]["engagements"]) == 1   # new Rout ends Round 1
    assert len(r["rounds"][1]["engagements"]) == 2   # old Rout: Round 2 runs on
    assert r["winner_side"] == "yorkist"
    assert stub.i == len(stub.seq)


# -------------------------------------------- Foreign Haven (IIY, 4.3.5/4.4.3)
def _rebellion_forces(s):
    return {lid: battle._Force(s, lid)
            for lid in ("edward_iv", "warwick_lancastrian")}


def test_foreign_haven_shifts_only_when_warwick_dies_as_defender(monkeypatch):
    # Warwick dying as DEFENDER shifts Lancastrians to the current Calendar box
    # and Yorkists to the next (Margaret 9 -> 1, Gloucester 9 -> 2) ...
    s = build_initial_state("warwicks_rebellion")
    _patch_dice(monkeypatch, [3])              # Death roll: 3 >= 3 -> dies
    forces = _rebellion_forces(s)
    forces["warwick_lancastrian"].lord_routed = True
    r = battle._ending(s, "london", forces, ["edward_iv"],
                       ["warwick_lancastrian"], [], [])
    assert r["deaths"] == ["warwick_lancastrian"] and r["foreign_haven"] is True
    assert s.lords["margaret"].calendar_box == 1
    assert s.lords["gloucester_1"].calendar_box == 2
    # ... but NOT when he merely Disbands (roll 2 < 3) ...
    s2 = build_initial_state("warwicks_rebellion")
    _patch_dice(monkeypatch, [2])
    forces2 = _rebellion_forces(s2)
    forces2["warwick_lancastrian"].lord_routed = True
    r2 = battle._ending(s2, "london", forces2, ["edward_iv"],
                        ["warwick_lancastrian"], [], [])
    assert r2["disbands"] == ["warwick_lancastrian"]
    assert "foreign_haven" not in r2
    assert s2.lords["margaret"].calendar_box == 9
    # ... and NOT when he dies as the ATTACKER.
    s3 = build_initial_state("warwicks_rebellion")
    _patch_dice(monkeypatch, [3])
    forces3 = _rebellion_forces(s3)
    forces3["warwick_lancastrian"].lord_routed = True
    r3 = battle._ending(s3, "london", forces3, ["warwick_lancastrian"],
                        ["edward_iv"], [], [])
    assert r3["deaths"] == ["warwick_lancastrian"]
    assert "foreign_haven" not in r3
    assert s3.lords["margaret"].calendar_box == 9
    assert s3.lords["gloucester_1"].calendar_box == 9


def test_foreign_haven_approach_exile_needs_warwick_and_the_rule():
    # Warwick choosing Exile on Approach shifts the Calendars (rule active) ...
    s = build_initial_state("warwicks_rebellion")
    s.lords["warwick_lancastrian"].location = "london"
    r = battle.approach(s, "london", ["edward_iv"],
                        {"responses": {"warwick_lancastrian": "exile"}})
    assert r["exiles"] == ["warwick_lancastrian"] and r["foreign_haven"] is True
    assert s.lords["margaret"].calendar_box == 1
    assert s.lords["gloucester_1"].calendar_box == 2
    # ... another Lord's Exile does not ...
    s2 = build_initial_state("warwicks_rebellion")
    s2.lords["edward_iv"].location = "york"
    r2 = battle.approach(s2, "york", ["edward_iv"],
                         {"responses": {"clarence": "exile"}})
    assert r2["exiles"] == ["clarence"] and "foreign_haven" not in r2
    assert s2.lords["margaret"].calendar_box == 9
    # ... nor Warwick's when Foreign Haven is not a rule in force.
    s3 = build_initial_state("warwicks_rebellion")
    s3.scenario = "henry_vi"                   # same board, no Foreign Haven
    s3.lords["warwick_lancastrian"].location = "london"
    r3 = battle.approach(s3, "london", ["edward_iv"],
                         {"responses": {"warwick_lancastrian": "exile"}})
    assert r3["exiles"] == ["warwick_lancastrian"]
    assert "foreign_haven" not in r3
    assert s3.lords["margaret"].calendar_box == 9
