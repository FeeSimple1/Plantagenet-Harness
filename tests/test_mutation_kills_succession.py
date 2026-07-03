"""Mutation-survivor killers for succession.py (see mutation-results/).

Pins the successor Calendar box, the global-Heir list used for the -8
carry-over penalty, and the setup-only recompute guard.
"""

from __future__ import annotations

from plantagenet import succession
from plantagenet.scenarios import apply_iiil_setup, build_initial_state
from plantagenet.state import LordState, LordStatus


def test_scripted_successor_enters_the_next_calendar_box():
    # L438 bin Add->Sub / int 1->2: an AVAILABLE scripted successor goes to
    # turn_box + 1 exactly (War I: Somerset (1)'s removal adds Somerset (2)).
    s = build_initial_state("wars_of_the_roses", seed=1)
    s.turn_box = 4
    s.lords["somerset_2"] = LordState(lord_id="somerset_2", side="lancastrian",
                                      status=LordStatus.AVAILABLE)
    s.lords["somerset_1"].status = LordStatus.REMOVED
    r = succession.on_heir_removed(s, "somerset_1")
    assert r["succession"] == "somerset_2"
    assert s.lords["somerset_2"].status == LordStatus.CALENDAR
    assert s.lords["somerset_2"].calendar_box == 5


def test_global_heir_list_membership():
    # L72 In->NotIn: the 6.2.1 list drives the cross-War -8 penalty.
    assert succession.is_global_heir("yorkist", "york") is True
    assert succession.is_global_heir("lancastrian", "henry_tudor") is True
    assert succession.is_global_heir("lancastrian", "buckingham") is False
    assert succession.is_global_heir("yorkist", "norfolk") is False


def test_setup_only_war_setup_does_not_fire_count_triggers():
    # L145 And->Or / L146 Or->And: War IIIL is setup_only, so apply_setup must
    # NOT run the heir-count recompute (which would add Y16 for a sole Heir).
    s = build_initial_state("wars_of_the_roses", seed=1)
    s.grand_scenario["current_war"] = "war_iiil"
    apply_iiil_setup(s, removed={"march", "rutland", "gloucester_1"})
    s.decks["yorkist"] = {"draw": [], "discard": [], "held": [], "set_aside": []}
    succession.apply_setup(s)
    assert "Y16" not in s.decks["yorkist"]["draw"]
