"""Natural Causes (E4/E5): aging-Heir removal after a won second War (IIY/IIL).
Henry VI & York roll 2d6 (removed if the sum < the last Turn box played);
Edward IV rolls 1d6 in IIY only (removed on a 6). D-006 residue (c)."""

from __future__ import annotations

from plantagenet import influence
from plantagenet.scenarios import apply_natural_causes, build_initial_state, renew_war
from plantagenet.state import LordState, LordStatus


def _iiy_state(seed=1, turn_box=15, war="war_iiy"):
    s = build_initial_state("wars_of_the_roses", seed=seed)
    s.grand_scenario["current_war"] = war
    s.turn_box = turn_box
    for lid in ("henry_vi", "york"):
        s.lords[lid].status = LordStatus.MUSTERED
    s.lords["edward_iv"] = LordState(lord_id="edward_iv", side="yorkist",
                                     status=LordStatus.MUSTERED, location="london")
    return s


def test_henry_vi_and_york_always_die_when_war_runs_to_the_end():
    # last Turn box 15; 2d6 sum maxes at 12 < 15 -> both removed for any seed.
    for seed in range(1, 6):
        s = _iiy_state(seed=seed, turn_box=15)
        log = apply_natural_causes(s)
        assert log["applied"] and "henry_vi" in log["removed"] and "york" in log["removed"]
        assert s.lords["henry_vi"].status == LordStatus.REMOVED
        assert s.lords["york"].status == LordStatus.REMOVED


def test_no_natural_death_when_war_ends_at_box_two():
    # last Turn box 2; a 2d6 sum (min 2) is never < 2 -> nobody removed.
    s = _iiy_state(turn_box=2)
    log = apply_natural_causes(s)
    assert "henry_vi" not in log["removed"] and "york" not in log["removed"]
    assert s.lords["henry_vi"].status == LordStatus.MUSTERED


def test_edward_iv_uses_a_single_die_in_iiy():
    saw6 = sawkeep = False
    for seed in range(1, 40):
        s = _iiy_state(seed=seed, turn_box=15)
        log = apply_natural_causes(s)
        ed = next(r for r in log["rolls"] if r["lord"] == "edward_iv")
        assert 1 <= ed["roll"] <= 6                       # one die, not two
        if ed["roll"] == 6:
            saw6 = True
            assert ed["removed"] and s.lords["edward_iv"].status == LordStatus.REMOVED
        else:
            sawkeep = True
            assert not ed["removed"] and s.lords["edward_iv"].status == LordStatus.MUSTERED
        if saw6 and sawkeep:
            break
    assert saw6 and sawkeep


def test_iil_has_no_edward_iv_roll():
    s = _iiy_state(turn_box=15, war="war_iil")
    log = apply_natural_causes(s)
    assert {r["lord"] for r in log["rolls"]} == {"henry_vi", "york"}   # no Edward IV


def test_already_removed_heir_is_not_rerolled():
    s = _iiy_state(turn_box=15)
    s.lords["york"].status = LordStatus.REMOVED            # already out
    log = apply_natural_causes(s)
    assert "york" not in {r["lord"] for r in log["rolls"]}


def test_renew_charges_minus_eight_for_a_natural_death_global_heir():
    # IIY -> IIIY at box 15: Henry VI dies of Natural Causes. He is a 6.2.1
    # global Heir though absent from IIIY's per-War list, so the Lancastrian -8
    # must still apply (and via the static-side fallback, since Henry VI does
    # not appear on the IIIY roster). York is held out of play here so the net
    # Influence track isolates the Lancastrian penalty.
    s = _iiy_state(turn_box=15)
    del s.lords["edward_iv"]
    s.lords["york"].status = LordStatus.AVAILABLE          # not present -> not rolled, no -8
    s.victory = {"result": "yorkist"}
    lanc_before = influence._net_lanc(s.influence["track"])
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iiiy"
    assert s.lords["henry_vi"].status == LordStatus.REMOVED   # died of Natural Causes
    assert "henry_vi" not in n.lords                          # absent from the IIIY roster
    lanc_after = influence._net_lanc(n.influence["track"])
    assert lanc_before - lanc_after == 8                      # Henry VI -8 (global Heir, 6.2.1)
