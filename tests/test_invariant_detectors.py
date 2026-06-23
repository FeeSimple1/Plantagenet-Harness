"""Verify the board-invariant DETECTORS actually fire on violating states.

The whole testing strategy (sweeps, fuzz, property tests) asserts
``board_invariant_violations(state) == []``. Coverage-guided gap hunting showed
the violation-REPORTING branches were never executed -- so the safety net was
itself unverified. These tests hand-build each violation and assert the right
detector flags it (and the clean baseline stays empty).
"""

from __future__ import annotations

from plantagenet import invariants
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _s():
    return build_initial_state("wars_of_the_roses", seed=1)


def _kinds(viols):
    return {v["kind"] for v in viols}


def test_clean_initial_state_has_no_violations():
    assert invariants.board_invariant_violations(_s()) == []


def test_influence_marker_out_of_bounds_detected():
    s = _s()
    s.influence["track"].marker_at = 999
    assert "influence_marker_oob" in _kinds(invariants.influence_violations(s))


def test_calendar_lord_without_box_detected():
    s = _s()
    lid = next(i for i, v in s.lords.items() if v.status == LordStatus.CALENDAR)
    s.lords[lid].calendar_box = None
    assert "calendar_no_box" in _kinds(invariants.lord_status_violations(s))


def test_captured_lord_without_holder_detected():
    s = _s()
    lid = next(iter(s.lords))
    ls = s.lords[lid]
    ls.status = LordStatus.CAPTURED
    ls.location = ls.exile_box = ls.at_sea = ls.calendar_box = None
    ls.captured_by = None
    assert "captured_no_holder" in _kinds(invariants.lord_status_violations(s))


def test_incompatible_dual_position_detected():
    s = _s()
    lid = next(i for i, v in s.lords.items() if v.location is not None)
    s.lords[lid].at_sea = "irish_sea"        # location AND at_sea -> impossible
    assert "incompatible_position" in _kinds(invariants.lord_status_violations(s))


def test_location_not_a_locale_detected():
    s = _s()
    lid = next(i for i, v in s.lords.items() if v.location is not None)
    s.lords[lid].location = "ireland"        # a Sea/Exile box id, not a Locale
    assert "location_not_a_locale" in _kinds(invariants.lord_status_violations(s))


def test_vassal_book_mismatch_detected():
    s = _s()
    lid = next(iter(s.lords))
    s.lords[lid].vassals = ["this_vassal_does_not_belong_here"]
    assert "vassal_book_mismatch" in _kinds(invariants.vassal_book_violations(s))
