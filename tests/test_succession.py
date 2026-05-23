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


# ------------------- Phase 5b: structured per-War Succession (War I) -------------------
def _deck(s, side):
    d = s.decks[side]
    return set(d["draw"]) | set(d["discard"]) | set(d["held"])


def test_war_i_setup_registers_while_remains_sources():
    s = build_initial_state("wars_of_the_roses")
    assert s.grand_scenario["deck_sources"]["lancastrian"]["L15"] == ["henry_vi"]
    assert {"L15", "L17"} <= _deck(s, "lancastrian")


def test_removing_henry_vi_swaps_cards_and_calendars_margaret():
    from plantagenet import succession
    s = build_initial_state("wars_of_the_roses")
    r = succession.on_heir_removed(s, "henry_vi")
    assert r["succession"] == "margaret"
    assert s.lords["margaret"].status == LordStatus.CALENDAR
    deck = _deck(s, "lancastrian")
    assert "L15" not in deck and "L17" not in deck      # while_remains sources dropped
    assert "L27" in deck and "L31" in deck              # added on removal


def test_muster_of_margaret_assigns_l26_set_aside():
    from plantagenet import succession
    s = build_initial_state("wars_of_the_roses")
    succession.on_heir_removed(s, "henry_vi")           # Margaret -> Calendar
    s.lords["margaret"].status = LordStatus.MUSTERED.value
    succession.on_muster_lord(s, "margaret")
    assert "L26" in s.lords["margaret"].capabilities
    assert "L26" in s.grand_scenario["set_aside_on_disband"]["margaret"]


def test_margaret_disband_sets_l26_aside_not_discarded():
    from plantagenet import campaign, succession
    s = build_initial_state("wars_of_the_roses")
    succession.on_heir_removed(s, "henry_vi")
    s.lords["margaret"].status = LordStatus.MUSTERED.value
    succession.on_muster_lord(s, "margaret")
    campaign._disband_lord(s, s.lords["margaret"])
    assert "L26" in s.decks["lancastrian"]["set_aside"]
    assert "L26" not in s.decks["lancastrian"].get("discard", [])


def test_henry_released_suppressed_when_l26_assigned():
    import pytest

    from plantagenet import actions, succession
    from plantagenet.errors import IllegalAction
    s = build_initial_state("wars_of_the_roses")
    succession.on_heir_removed(s, "henry_vi")
    s.lords["margaret"].status = LordStatus.MUSTERED.value
    succession.on_muster_lord(s, "margaret")            # L26 leaves the deck
    for pile in ("draw", "discard", "held"):
        assert "L26" not in s.decks["lancastrian"][pile]
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_event", "card": "L26", "side": "lancastrian"})
    assert e.value.code == "event_suppressed"


def test_removing_somerset_one_calendars_somerset_two():
    from plantagenet import succession
    s = build_initial_state("wars_of_the_roses")
    r = succession.on_heir_removed(s, "somerset_1")
    assert r["succession"] == "somerset_2"


def test_automatic_war_victory_on_henry_and_somerset_removed():
    from plantagenet import battle
    s = build_initial_state("wars_of_the_roses")
    battle._kill_lord(s, "henry_vi")
    assert s.victory is None or s.phase != "over"        # not yet
    battle._kill_lord(s, "somerset_1")
    assert s.phase == "over" and s.victory["result"] == "yorkist"
