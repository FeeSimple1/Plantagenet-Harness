"""6.2 general Succession rule: the Heir role passes to the next-ranked LIVING
Heir; a new Lord enters play only if that Heir is not already in the game.

Regression for a rules bug found 2026-07-01: ``_general_next_heir`` SKIPPED
next-ranked Heirs already in play (status not AVAILABLE) and instantiated the
first lower-ranked ABSENT Heir instead. In War I, Margaret's removal with
Somerset (1) Mustered wrongly created Somerset (2) on the Calendar -- the War I
sheet adds Somerset (2) only upon Somerset (1)'s own removal ("Removal of
Somerset (1) adds Somerset (2) to the next Calendar box"), and scripts nothing
for Margaret's removal.
"""

from __future__ import annotations

from plantagenet import succession
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordState, LordStatus


def _after_henry(seed=2):
    """War I with Henry VI dead: Margaret entered by the scripted trigger."""
    s = build_initial_state("wars_of_the_roses", seed=seed)
    s.lords["henry_vi"].status = LordStatus.REMOVED.value
    succession.on_heir_removed(s, "henry_vi")
    return s


def test_margaret_death_adds_nobody_while_somerset1_in_play():
    s = _after_henry()
    assert s.lords["somerset_1"].status == LordStatus.MUSTERED
    before = set(s.lords)
    s.lords["margaret"].status = LordStatus.REMOVED.value
    r = succession.on_heir_removed(s, "margaret")
    assert "succession" not in r                     # nobody enters play
    assert set(s.lords) == before                    # Somerset (2) NOT instantiated
    assert "somerset_2" not in s.lords
    assert r["recompute"]["king"] == "somerset_1"    # Heir role passes to him


def test_margaret_death_adds_nobody_when_next_heir_on_calendar():
    s = _after_henry()
    s.lords["somerset_1"].status = LordStatus.REMOVED.value
    succession.on_heir_removed(s, "somerset_1")      # scripted: Somerset (2) -> Calendar
    assert s.lords["somerset_2"].status == LordStatus.CALENDAR
    before = set(s.lords)
    s.lords["margaret"].status = LordStatus.REMOVED.value
    r = succession.on_heir_removed(s, "margaret")    # rank 3 dead; rank 4 on Calendar
    assert "succession" not in r
    assert set(s.lords) == before
    assert r["recompute"]["king"] == "somerset_2"


def test_general_rule_instantiates_absent_next_heir():
    # Somerset (1) dead WITHOUT the scripted trigger having run (unit-level):
    # Margaret's removal must fall to rank 4 and instantiate Somerset (2).
    s = _after_henry()
    s.lords["somerset_1"].status = LordStatus.REMOVED.value
    assert "somerset_2" not in s.lords
    s.lords["margaret"].status = LordStatus.REMOVED.value
    r = succession.on_heir_removed(s, "margaret")
    assert r["succession"] == "somerset_2" and r["added"] is True
    assert s.lords["somerset_2"].status == LordStatus.CALENDAR
    assert s.lords["somerset_2"].calendar_box == s.turn_box + 1


def test_general_rule_calendars_an_available_next_heir():
    # The next Heir exists but is off-map AVAILABLE: he goes to the next
    # Calendar box (no "added" flag -- his LordState already existed).
    s = _after_henry()
    s.lords["somerset_1"].status = LordStatus.REMOVED.value
    s.lords["somerset_2"] = LordState(lord_id="somerset_2", side="lancastrian",
                                      status=LordStatus.AVAILABLE)
    s.lords["margaret"].status = LordStatus.REMOVED.value
    r = succession.on_heir_removed(s, "margaret")
    assert r["succession"] == "somerset_2" and "added" not in r
    assert s.lords["somerset_2"].status == LordStatus.CALENDAR
    assert s.lords["somerset_2"].calendar_box == s.turn_box + 1


def test_york_death_adds_no_yorkist_in_war_i():
    # War I sheet: "Do not replace or add any Yorkists."
    s = build_initial_state("wars_of_the_roses", seed=2)
    before = set(s.lords)
    s.lords["york"].status = LordStatus.REMOVED.value
    r = succession.on_heir_removed(s, "york")
    assert "succession" not in r
    assert set(s.lords) == before and "edward_iv" not in s.lords
    assert r["recompute"]["king"] == "march"


def test_non_heir_removal_is_a_noop():
    s = build_initial_state("wars_of_the_roses", seed=2)
    s.lords["warwick_yorkist"].status = LordStatus.REMOVED.value
    assert succession.on_heir_removed(s, "warwick_yorkist") is None


def test_third_war_only_heir_skipped_outside_third_war():
    # Global 6.2.1 table fallback (no War roster): Warwick is an Heir "in the
    # third War only"; outside it the rank-6 entry is skipped and the table
    # exhausts to None.
    s = build_initial_state("wars_of_the_roses", seed=2)
    s.grand_scenario["current_war"] = "war_ix_nonexistent"    # -> global table
    for lid in ("henry_vi", "somerset_1"):
        s.lords[lid].status = LordStatus.REMOVED.value
    for lid in ("margaret", "henry_tudor"):                   # never instantiated
        s.lords[lid] = LordState(lord_id=lid, side="lancastrian",
                                 status=LordStatus.REMOVED)
    assert succession._general_next_heir(s, "lancastrian", "somerset_2") is None
    # And with Warwick dead too, the table exhausts to None.
    s.lords["warwick_yorkist"].status = LordStatus.REMOVED.value
    assert succession._general_next_heir(s, "lancastrian", "somerset_2") is None
