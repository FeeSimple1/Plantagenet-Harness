"""Wave F: Succession (6.2-6.3) general mechanic for the grand scenario."""

from __future__ import annotations

from plantagenet import battle, succession
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def test_heir_rank_lookup():
    s = build_initial_state("wars_of_the_roses")
    assert succession.heir_rank(s, "lancastrian", "henry_vi") == 1
    assert succession.heir_rank(s, "lancastrian", "margaret") == 2
    assert succession.heir_rank(s, "yorkist", "york") == 1
    assert succession.heir_rank(s, "lancastrian", "exeter_1") is None   # not an Heir


def test_removing_top_heir_adds_next_to_calendar():
    s = build_initial_state("wars_of_the_roses")
    r = succession.on_heir_removed(s, "henry_vi")
    assert r["succession"] == "margaret"
    assert s.lords["margaret"].status == LordStatus.CALENDAR
    assert s.lords["margaret"].calendar_box == s.turn_box + 1


def test_succession_only_in_grand_scenario():
    s = build_initial_state("henry_vi")            # standalone, not grand
    assert succession.on_heir_removed(s, "henry_vi") is None


def test_kill_lord_triggers_succession_in_grand_scenario():
    s = build_initial_state("wars_of_the_roses")
    battle._kill_lord(s, "henry_vi")
    assert s.lords["henry_vi"].status == LordStatus.REMOVED
    assert "margaret" in s.lords and s.lords["margaret"].status == LordStatus.CALENDAR


def test_dead_heir_does_not_return():
    s = build_initial_state("wars_of_the_roses")
    # Somerset (1) is rank 3; remove it -> Somerset (2) (rank 4) enters.
    r = succession.on_heir_removed(s, "somerset_1")
    assert r["succession"] == "somerset_2"
