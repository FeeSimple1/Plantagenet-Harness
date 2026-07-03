"""Mutation-survivor killers for scenarios.py (see mutation-results/).

Pins scenario-setup placements and assets, War carry-over, and War deck
composition against surviving mutants.
"""

from __future__ import annotations

from plantagenet import static_data
from plantagenet.scenarios import (
    _apply_lost_heir_influence,
    _recompute_stronghold_markers,
    apply_iiil_setup,
    apply_iiiy_setup,
    apply_natural_causes,
    build_initial_state,
    renew_war,
)
from plantagenet.state import LordStatus, VassalStatus


def _grand(seed=1):
    return build_initial_state("wars_of_the_roses", seed=seed)


def _to_iiy(removed=()):
    s = _grand()
    for lid in removed:
        s.lords[lid].status = LordStatus.REMOVED
    s.victory = {"result": "yorkist"}
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iiy"
    return n


def test_montagu_special_rule_applies_only_in_somersets_return():
    # L93 In->NotIn (+And->Or), L102 In->NotIn, L104 IsNot->Is / In->NotIn,
    # L107 NotIn->In.
    s = build_initial_state("somersets_return", seed=1)
    wk = s.lords["warwick_yorkist"]
    assert "L23" in wk.capabilities
    assert "montagu" in wk.special_vassals
    s2 = build_initial_state("henry_vi", seed=1)     # has Warwick, no Montagu rule
    assert "L23" not in s2.lords["warwick_yorkist"].capabilities
    assert "montagu" not in s2.lords["warwick_yorkist"].special_vassals


def test_bosworth_battle_only_setup_fields():
    # L57 Eq->NotEq (King side acts in a battle-only scenario), L184 int 1->2.
    s = build_initial_state("bosworth")
    assert s.phase == "battle"
    assert s.active_side == "yorkist"                # Richard III's side is King
    assert s.turn_box == 1


def test_end_marker_box_comes_only_from_an_end_calendar_marker():
    # L172 In->NotIn: scenarios without an "end" marker must keep end_box None.
    assert build_initial_state("henry_vi").calendar.end_box is None
    assert build_initial_state("my_kingdom_for_a_horse").calendar.end_box == 10


def test_vassals_all_except_mode_offmaps_only_the_excepted():
    # L270 And->Or.
    s = build_initial_state("warwicks_rebellion", seed=1)
    assert s.vassals["devon"].status == VassalStatus.OFF_MAP
    assert s.vassals["oxford"].status == VassalStatus.OFF_MAP
    assert s.vassals["beaumont"].status == VassalStatus.AT_SEAT


def test_on_map_lords_are_not_marked_calendar_exile():
    # L219 const False->True.
    s = build_initial_state("henry_vi", seed=1)
    assert s.lords["york"].calendar_exile is False
    assert s.lords["henry_vi"].calendar_exile is False


def test_grand_scenario_decks_are_the_full_scenario_ia_decks():
    # L306 NotIn->In: the in-play filter must keep, not drop, the deck.
    s = _grand()
    for side in ("lancastrian", "yorkist"):
        assert set(s.decks[side]["draw"]) == set(
            static_data.scenario_card_deck("henry_vi", side))


def test_renewed_war_deck_is_own_side_no_rose_cards():
    # L327 Eq->NotEq (side) / int 0->1 (rose); also pins the IIL King token.
    s = _grand()
    s.victory = {"result": "lancastrian"}
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iil"
    assert n.lords["henry_vi"].status == LordStatus.MUSTERED
    assert n.lords["henry_vi"].location == "london"  # KING token: highest Heir
    cards = static_data.load_cards()
    draw = n.decks["lancastrian"]["draw"]
    assert all(cards[c]["side"] == "lancastrian" for c in draw)
    assert "L2" in draw                              # a plain no-rose card is dealt in


def test_lost_heir_penalty_is_8_per_heir_and_heirs_only():
    # L375 int 0->1, L384 And->Or, L386 int 8->9 (and succession is_global_heir).
    s = _grand()
    assert _apply_lost_heir_influence(s, {"henry_vi"}) == 8
    track = s.influence["track"]
    assert track.marker_side == "yorkist" and track.marker_at == 8
    s2 = _grand()
    assert _apply_lost_heir_influence(s2, {"buckingham"}) == 0   # not a Heir
    track2 = s2.influence["track"]
    assert track2.marker_side == "lancastrian" and track2.marker_at == 0


def test_natural_causes_boundary_roll_equal_to_last_turn_survives():
    # L770 Lt->LtE: a roll equal to the last Turn box played is NOT a removal.
    s = _grand(seed=1)                               # Henry VI rolls 8 on seed 1
    s.grand_scenario["current_war"] = "war_iiy"
    s.turn_box = 8
    out = apply_natural_causes(s)
    assert out["applied"] is True
    henry = next(r for r in out["rolls"] if r["lord"] == "henry_vi")
    assert henry["roll"] == 8 and henry["removed"] is False
    assert s.lords["henry_vi"].status == LordStatus.MUSTERED


def test_iiy_pembroke_joins_at_exactly_two_heirs_not_three():
    # L491 LtE->Lt / int 2->3.
    n = _to_iiy(removed=["york", "march"])           # two Heir slots remain
    assert n.lords["pembroke"].status == LordStatus.MUSTERED
    assert n.lords["pembroke"].location == "pembroke"
    n2 = _to_iiy(removed=["york"])                   # three remain: no Pembroke
    assert n2.lords["pembroke"].status not in (LordStatus.MUSTERED, LordStatus.CALENDAR)


def test_iiy_unplaced_margaret_loses_her_exile_marker():
    # L432 const False->True (_unplace_lord must clear calendar_exile).
    n = _to_iiy()                                    # Henry VI survives -> Margaret out
    assert n.lords["margaret"].status == LordStatus.AVAILABLE
    assert n.lords["margaret"].calendar_exile is False


def test_stronghold_marker_tie_defaults_to_yorkist_at_zero():
    # L456 GtE->Gt / int 0->1.
    s = _grand()
    for ls in s.locales.values():
        ls.favour = "neutral"                        # every type ties at 0
    _recompute_stronghold_markers(s)
    for typ in ("city", "town", "fortress"):
        mk = s.influence["track"].stronghold_markers[typ]
        assert mk.side == "yorkist" and mk.at == 0


def test_iiiy_heir_cards_depend_on_who_is_king():
    # L549 Eq->NotEq (Y31 vs Y20), L563 Eq->NotEq (Y28 with Edward IV King).
    s = _grand()
    s.grand_scenario["current_war"] = "war_iiiy"
    apply_iiiy_setup(s, removed={"york"})            # Edward IV King, Rutland Heir
    ds = s.grand_scenario["deck_sources"]["yorkist"]
    assert s.lords["edward_iv"].location == "london"
    assert "rutland" in ds.get("Y31", [])            # Heir to Edward IV
    assert "rutland" not in ds.get("Y20", [])
    s2 = _grand()
    s2.grand_scenario["current_war"] = "war_iiiy"
    apply_iiiy_setup(s2, removed={"york", "rutland"})   # Edward IV King + Gloucester
    ds2 = s2.grand_scenario["deck_sources"]["yorkist"]
    assert "gloucester_1" in ds2.get("Y28", [])      # with Edward IV -> also Y28


def test_gloucester_as_heir_flag_does_not_appear_from_nowhere():
    # L803 const False->True: the Y28 set-aside flag only carries from War 2.
    s = _grand()
    s.victory = {"result": "yorkist"}
    n = renew_war(s)
    assert n.grand_scenario["gloucester_as_heir_played"] is False
    n.victory = {"result": "yorkist"}
    n2 = renew_war(n)
    assert n2.grand_scenario["current_war"] == "war_iiiy"
    assert n2.grand_scenario["gloucester_as_heir_played"] is False


def test_iiil_margaret_king_gets_edward_and_y28_flag_selects_gloucester2():
    # L694 Eq->NotEq (L26 EDWARD), L703 Or->And / L706 In->NotIn (Y28 set-aside).
    s = _grand()
    s.grand_scenario["current_war"] = "war_iiil"
    apply_iiil_setup(s, removed={"henry_vi"})
    assert "L26" in s.lords["margaret"].capabilities
    s2 = _grand()
    s2.grand_scenario["current_war"] = "war_iiil"
    s2.grand_scenario["gloucester_as_heir_played"] = True
    log = apply_iiil_setup(s2, removed=set())
    assert log["yorkist_heirs"] == ["gloucester_2"]  # Y28 played: sole Heir
    assert s2.lords["gloucester_2"].exile_box == "burgundy"
    assert s2.lords["york"].status == LordStatus.AVAILABLE
    assert "gloucester_2" in s2.grand_scenario["deck_sources"]["yorkist"].get("Y35", [])
