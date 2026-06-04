"""Regression: own-timing Held Events (1.9.1, play_held_event) were accepted by
the engine but never advertised by legal_moves, and L28/L33 could be played at
an illegal time (no preceding qualifying Move). These tests cover enumeration,
round-trip acceptance, the March/Sail->Port timing window, and its lifecycle."""

from __future__ import annotations

import pytest

from plantagenet import actions, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster
from tests.test_command_enumeration import _activate, _into_activation
from tests.test_sail_cross_sea import _sailor_at


def _round_trip(state, move):
    probe = state.model_copy(deep=True)
    actions.apply_action(probe, move)            # must not raise IllegalAction
    return probe


def _held(moves, card):
    return [m for m in moves if m["type"] == "play_held_event" and m["card"] == card]


# --------------------------------------------------- Sail -> Port opens window
def test_sail_to_port_opens_window_and_enumerates_l28_l33():
    s, lid = _sailor_at("bristol")
    s.decks["lancastrian"]["held"] = ["L28", "L33"]
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lid, "to": "pembroke"})   # both Irish Sea Ports
    assert s.hold_window is not None
    assert s.hold_window["action"] == "sail"
    assert s.hold_window["dest"] == "pembroke" and lid in s.hold_window["lords"]
    moves = legal_moves.legal_moves(s)
    l28, l33 = _held(moves, "L28"), _held(moves, "L33")
    assert l28 and l33, "L28/L33 not offered while the Sail window is open"
    assert l28[0]["decisions"]["lords"] == [lid]
    _round_trip(s, l28[0])
    _round_trip(s, l33[0])


def test_next_action_closes_the_window():
    s, lid = _sailor_at("bristol")
    s.decks["lancastrian"]["held"] = ["L28", "L33"]
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lid, "to": "pembroke"})
    assert s.hold_window is not None
    actions.apply_action(s, {"type": "end_activation", "side": "lancastrian"})
    assert s.hold_window is None
    moves = legal_moves.legal_moves(s)
    assert not _held(moves, "L28") and not _held(moves, "L33")


# ----------------------------------------------- L33 only after a Sail (not March)
def test_l33_not_offered_after_march_only_window():
    s, lid = _sailor_at("bristol")
    s.lords[lid].location = "pembroke"
    s.decks["lancastrian"]["held"] = ["L28", "L33"]
    s.hold_window = {"action": "march", "side": "lancastrian",
                     "lords": [lid], "dest": "pembroke"}
    moves = legal_moves.legal_moves(s)
    assert _held(moves, "L28"), "L28 should be offered after a March to a Port"
    assert not _held(moves, "L33"), "L33 is Sail-only and must not be offered after a March"


def test_l33_rejected_without_a_sail_window():
    s, lid = _sailor_at("bristol")
    s.lords[lid].location = "pembroke"
    s.hold_window = None
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_held_event", "card": "L33",
                                 "side": "lancastrian"})
    assert e.value.code in ("not_held", "no_sail_window")  # not_held guard first
    s.decks["lancastrian"]["held"] = ["L33"]
    s.hold_window = {"action": "march", "side": "lancastrian",
                     "lords": [lid], "dest": "pembroke"}
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_held_event", "card": "L33",
                                 "side": "lancastrian"})
    assert e.value.code == "no_sail_window"


def test_l28_rejected_without_window_and_for_non_mover():
    s, lid = _sailor_at("bristol")
    s.lords[lid].location = "pembroke"
    s.decks["lancastrian"]["held"] = ["L28"]
    s.hold_window = None
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_held_event", "card": "L28",
                                 "side": "lancastrian", "decisions": {"lords": [lid]}})
    assert e.value.code == "no_move_window"
    # Window open, but naming a Lord who did not move is rejected.
    s.hold_window = {"action": "sail", "side": "lancastrian",
                     "lords": ["somebody_else"], "dest": "pembroke"}
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_held_event", "card": "L28",
                                 "side": "lancastrian", "decisions": {"lords": [lid]}})
    assert e.value.code == "not_mover"


# ------------------------------------------------ Aspielles: any moment, when held
def test_aspielles_offered_whenever_held():
    s = _activate(_into_activation(), _a_yorkist_lord())
    s.decks["yorkist"]["held"] = ["Y13"]
    moves = legal_moves.legal_moves(s)
    assert _held(moves, "Y13"), "Aspielles (Y13) not offered while held"
    _round_trip(s, _held(moves, "Y13")[0])


# ------------------------------------------- Yorkist Parade: London Friendly + Lord
def test_yorkist_parade_offered_when_london_friendly_with_york():
    s = _activate(_into_activation(), _a_yorkist_lord())
    parader = next(p for p in ("york", "warwick_yorkist") if p in s.lords)
    s.locales["london"].favour = "yorkist"
    s.lords[parader].status = LordStatus.MUSTERED
    s.lords[parader].location = "london"
    s.decks["yorkist"]["held"] = ["Y20"]
    moves = legal_moves.legal_moves(s)
    assert _held(moves, "Y20"), "Yorkist Parade (Y20) not offered"
    _round_trip(s, _held(moves, "Y20")[0])
    # Not offered when London is not Friendly.
    s.locales["london"].favour = "lancastrian"
    assert not _held(legal_moves.legal_moves(s), "Y20")


# --------------------------------------------- Sun in Splendour: a Levy Muster play
def test_sun_in_splendour_offered_in_levy_with_target():
    s = build_initial_state("warwicks_rebellion")
    to_muster(s)
    while s.active_side != "yorkist":
        actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    s.lords["edward_iv"].status = LordStatus.CALENDAR
    s.lords["edward_iv"].calendar_box = 5
    s.locales["london"].favour = "yorkist"
    s.decks["yorkist"]["held"] = ["Y24"]
    moves = legal_moves.legal_moves(s)
    y24 = _held(moves, "Y24")
    assert y24, "Sun in Splendour (Y24) not offered in the Levy"
    assert any(m["decisions"]["target"] == "london" for m in y24)
    _round_trip(s, next(m for m in y24 if m["decisions"]["target"] == "london"))


def _a_yorkist_lord():
    s = _into_activation()
    return next(lid for lid, v in s.lords.items()
                if v.side == "yorkist" and v.status == "mustered" and v.location)


# --------- Pre-existing set-aside bug found while fuzzing the held-event work ---
def test_remustered_lord_capability_not_left_in_set_aside_pile():
    """A mandatory Succession Capability (L26 EDWARD PRINCE OF WALES -> Margaret)
    set aside on Disband (6.2) must leave the set_aside pile when the Lord
    re-Musters -- otherwise it is counted both in a deck pile and on the mat."""
    from plantagenet import campaign, invariants, succession
    from plantagenet.state import LordState
    s = build_initial_state("wars_of_the_roses")
    # Margaret enters in a later War of the grand scenario; inject her so the
    # 'on: muster' Succession trigger (assign L26, set-aside-on-disband) fires.
    here = next(lid for lid, v in s.locales.items() if v.favour == "lancastrian")
    s.lords["margaret"] = LordState(lord_id="margaret", side="lancastrian",
                                    status=LordStatus.MUSTERED, location=here)
    succession.on_muster_lord(s, "margaret")
    assert "L26" in s.lords["margaret"].capabilities
    # Disband her: L26 goes to the set_aside pile, off the mat.
    campaign._disband_lord(s, s.lords["margaret"])
    assert "L26" in s.decks["lancastrian"]["set_aside"]
    assert "L26" not in s.lords["margaret"].capabilities
    # Re-Muster: L26 returns to the mat AND leaves the set_aside pile.
    s.lords["margaret"].status = LordStatus.MUSTERED
    s.lords["margaret"].location = here
    succession.on_muster_lord(s, "margaret")
    assert "L26" in s.lords["margaret"].capabilities
    assert "L26" not in s.decks["lancastrian"]["set_aside"]
    assert invariants.board_invariant_violations(s) == []
