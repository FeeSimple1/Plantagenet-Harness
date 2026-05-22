"""Wave C2: phase-dependent Armour, Melee-Strike, round-control, and Death
Capabilities/Events (1.9.1) -- Barded Horse, Chevaliers, Piquiers, Yeomen of
the Crown, Final Charge, Bloody Thou Art, Vanguard, Swift Maneuver, Captain."""

from __future__ import annotations

import pytest

from plantagenet import battle, commands
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


class _StubDice:
    """Deterministic dice yielding a fixed sequence of d6 values."""

    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0

    def d6(self):
        v = self.seq[self.i % len(self.seq)]
        self.i += 1
        return v


def _force(state, lord_id, location="cambridge", caps=None):
    ls = state.lords[lord_id]
    ls.status = LordStatus.MUSTERED.value
    ls.location = location
    ls.capabilities = list(caps or [])
    return battle._Force(state, lord_id)


def test_chevaliers_missile_armour_minus_one_and_melee_double():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", caps=["L36"])
    f.count["men_at_arms"] = 2
    f.routed.setdefault("men_at_arms", 0)
    base_melee = f.raw_hits("melee")
    battle._apply_phase_caps(s, {"york": f}, {})
    assert f.prof["men_at_arms"]["prot_missile"] == [1, 2]      # base [1,3] -1
    assert f.melee_mult["men_at_arms"] == 2
    assert f.raw_hits("melee") == base_melee + f.count["men_at_arms"] * 1  # MaA melee doubled


def test_barded_horse_phase_protection():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", caps=["L27"])
    battle._apply_phase_caps(s, {"york": f}, {})
    assert f.prot_range("retinue", "missile") == [1, 3]
    assert f.prot_range("retinue", "melee") == [1, 5]


def test_piquiers_armour_until_three_rout():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", caps=["L34"])
    f.count["men_at_arms"] = 3
    f.count["militia"] = 1
    f.routed.update({"men_at_arms": 0, "militia": 0})
    battle._apply_phase_caps(s, {"york": f}, {})
    assert f.prot_range("men_at_arms", "melee") == [1, 4]       # < 3 Routed
    f.routed["men_at_arms"] = 3
    assert f.prot_range("men_at_arms", "melee") == [1, 3]       # 3 Routed -> base


def test_yeomen_redirects_failed_retinue_save_to_men_at_arms():
    s = build_initial_state("warwicks_rebellion")
    f = _force(s, "margaret", caps=["L31"])
    f.count["men_at_arms"] = 1
    f.routed.setdefault("men_at_arms", 0)
    battle._apply_phase_caps(s, {"margaret": f}, {"yeomen": ["margaret"]})
    assert f.yeomen
    # One Melee Hit; dice always fails the save (roll 6 > prot hi). Valour off.
    log = []
    battle._absorb_side([f], 1, _StubDice([6]), battle._ABSORB_DEFAULT, False, log, "melee")
    assert f.routed["men_at_arms"] == 1            # Men-at-Arms routed instead
    assert f.routed["retinue"] == 0                # Retinue spared


def test_captain_makes_lord_a_marshal_when_no_rival():
    s = build_initial_state("henry_vi")
    s.lords["salisbury"].status = LordStatus.MUSTERED.value
    s.lords["salisbury"].location = "york"
    s.lords["salisbury"].capabilities = ["Y30"]    # CAPTAIN
    assert commands._effective_title(s, "salisbury") == "marshal"
    # A Friendly Marshal co-located removes the Captain promotion.
    s.lords["warwick_yorkist"].status = LordStatus.MUSTERED.value
    s.lords["warwick_yorkist"].location = "york"   # Warwick (Yorkist) is a Lieutenant
    assert commands._effective_title(s, "salisbury") != "marshal"


def test_bloody_thou_art_kills_all_routed_losers():
    s = build_initial_state("my_kingdom_for_a_horse")   # Influence track + Richard III
    rid = "richard_iii"
    s.lords[rid].status = LordStatus.MUSTERED.value
    s.lords[rid].location = "leicester"
    s.lords[rid].capabilities = ["Y33"]             # BLOODY THOU ART
    foe = next(lo for lo, ls in s.lords.items() if ls.side == "lancastrian")
    s.lords[foe].status = LordStatus.MUSTERED.value
    s.lords[foe].location = "leicester"
    forces = {rid: battle._Force(s, rid), foe: battle._Force(s, foe)}
    forces[foe].lord_routed = True                  # loser already Routed
    res = battle._ending(s, s.lords[rid].location, forces, [rid], [foe], [], [])
    assert foe in res["deaths"]                     # certain Death, no Disband roll
    assert foe not in res.get("disbands", [])


def test_swift_maneuver_requires_held_event():
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"swift_maneuver": "yorkist"})
    assert e.value.code == "no_swift"


def test_vanguard_requires_capability():
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"vanguard": "york"})
    assert e.value.code == "no_vanguard"


def _round1_melee_atk(result):
    eng = result["rounds"][0]["engagements"][0]
    m = next(st for st in eng["strikes"] if st["phase"] == "melee")
    return m["attacker_hits"]


def test_final_charge_adds_three_melee_hits():
    def setup():
        s = build_initial_state("my_kingdom_for_a_horse")
        rid = "richard_iii"
        s.lords[rid].status = LordStatus.MUSTERED.value
        s.lords[rid].location = "leicester"
        s.lords[rid].capabilities = ["Y32"]         # FINAL CHARGE
        foe = next(lo for lo, ls in s.lords.items() if ls.side == "lancastrian")
        s.lords[foe].status = LordStatus.MUSTERED.value
        s.lords[foe].location = "leicester"
        return s, rid, foe
    s, rid, foe = setup()
    base = _round1_melee_atk(battle.resolve_battle(s, "leicester", rid, foe, {}))
    s2, rid2, foe2 = setup()
    r = battle.resolve_battle(s2, "leicester", rid2, foe2, {"final_charge": [rid2]})
    assert _round1_melee_atk(r) >= base + 3
