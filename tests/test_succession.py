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


# ------------------- Phase 5b-ii-a: other Wars' trigger vocabulary -------------------
def _stage_war(war_id, side, present, seed=1):
    """Stage a grand state at ``war_id`` with ``present`` Heir lords Mustered and
    fresh decks, then run Succession setup. Returns the state."""
    from plantagenet import succession
    from plantagenet.state import LordStatus
    s = build_initial_state("wars_of_the_roses", seed=seed)
    gs = s.grand_scenario
    gs["current_war"] = war_id
    gs["deck_sources"] = {}
    gs["set_aside_on_disband"] = {}
    gs["succession_fired"] = []
    gs["current_king"] = {}
    from plantagenet import static_data
    from plantagenet.state import LordState
    statics = static_data.load_lords()
    for _lid, ls in s.lords.items():
        if ls.side == side:
            ls.status = LordStatus.AVAILABLE.value
    for lid in present:
        if lid not in s.lords:
            s.lords[lid] = LordState(lord_id=lid, side=side, status=LordStatus.AVAILABLE.value)
        s.lords[lid].status = LordStatus.MUSTERED.value
        s.lords[lid].location = "london"
    # Ensure replacement targets exist as AVAILABLE so they can enter play.
    for lid in ("edward_iv", "richard_iii", "somerset_2", "pembroke"):
        if lid not in s.lords and lid in statics:
            s.lords[lid] = LordState(lord_id=lid, side=side, status=LordStatus.AVAILABLE.value)
    s.decks[side] = {"draw": [], "discard": [], "held": [], "set_aside": []}
    succession.apply_setup(s)
    return s


def _deck_side(s, side):
    d = s.decks[side]
    return set(d["draw"]) | set(d["discard"]) | set(d["held"])


def _remove(s, lid):
    from plantagenet import succession
    from plantagenet.state import LordStatus
    s.lords[lid].status = LordStatus.REMOVED.value      # _kill_lord sets this first
    return succession.on_heir_removed(s, lid)


def test_iiy_while_remains_york_contributes_cards():
    s = _stage_war("war_iiy", "yorkist", ["york", "march", "rutland", "gloucester_1"])
    assert {"Y14", "Y18", "Y19", "Y20"} <= _deck_side(s, "yorkist")


def test_iiy_replace_march_with_edward_on_becoming_king():
    from plantagenet.state import LordStatus
    s = _stage_war("war_iiy", "yorkist", ["york", "march", "rutland", "gloucester_1"])
    _remove(s, "york")                                  # March becomes highest Heir
    assert s.lords["edward_iv"].status == LordStatus.MUSTERED
    assert s.lords["march"].status == LordStatus.REMOVED
    assert {"Y23", "Y24", "Y28", "Y31"} <= _deck_side(s, "yorkist")


def test_iiy_pembroke_added_when_two_or_fewer_heirs_remain():
    from plantagenet.state import LordStatus
    s = _stage_war("war_iiy", "yorkist", ["york", "march", "rutland", "gloucester_1"])
    _remove(s, "york")                                  # -> edward_iv, rutland, gloucester (3)
    assert "pembroke" not in [lid for lid in s.lords
                              if s.lords[lid].status == LordStatus.CALENDAR]
    _remove(s, "rutland")                               # now 2 heirs -> add Pembroke
    assert s.lords["pembroke"].status == LordStatus.CALENDAR


def test_iil_somerset_one_replaced_in_place_by_two():
    from plantagenet.state import LordStatus
    s = _stage_war("war_iil", "lancastrian", ["henry_vi", "margaret", "somerset_1"])
    _remove(s, "somerset_1")
    # On an in-play removal the replacement enters the Calendar (the dead Lord's
    # board position is gone); position-copy "in place" applies only at setup.
    assert s.lords["somerset_2"].status == LordStatus.CALENDAR
    assert s.lords["somerset_1"].status == LordStatus.REMOVED


def test_iil_while_king_cards_track_the_current_king():
    s = _stage_war("war_iil", "lancastrian", ["henry_vi", "margaret", "somerset_1"])
    assert {"L15", "L17"} <= _deck_side(s, "lancastrian")        # Henry VI is King
    _remove(s, "henry_vi")                              # King becomes Margaret
    deck = _deck_side(s, "lancastrian")
    assert "L15" not in deck and "L17" not in deck       # Henry VI's while_king dropped
    assert {"L27", "L31"} <= deck                        # Margaret's while_king added


def test_setup_only_war_does_not_fire_in_play_removal():
    s = _stage_war("war_iiiy", "yorkist", ["york", "march", "rutland", "gloucester_1"])
    before = _deck_side(s, "yorkist")
    r = _remove(s, "york")
    assert "succession" not in r and "recompute" not in r        # setup_only: no in-play effect
    assert _deck_side(s, "yorkist") == before


# ------------------- Phase 5b-ii-b: Renewed-War setup transition (E1 6.1) -------------------
def test_next_war_selection_by_winner():
    from plantagenet import static_data
    from plantagenet.scenarios import next_war_id
    g = static_data.load_scenario("wars_of_the_roses")
    assert next_war_id(g, "war_i", "lancastrian") == "war_iil"
    assert next_war_id(g, "war_i", "yorkist") == "war_iiy"
    assert next_war_id(g, "war_iil", "yorkist") == "war_iiiy"
    assert next_war_id(g, "war_iiiy", "yorkist") is None     # final War: no Renewed War


def test_war_i_lancastrian_win_transitions_to_iil():
    from plantagenet.scenarios import build_initial_state, renew_war
    s = build_initial_state("wars_of_the_roses")
    s.victory = {"result": "lancastrian", "rule": "5.2"}
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iil"
    assert n.phase == "levy" and n.levy_step == "arts_of_war"
    assert n.lords["henry_vi"].status == LordStatus.MUSTERED   # King at London
    assert n.lords["henry_vi"].location == "london"
    assert n.locales["london"].favour == "lancastrian"
    deck = set(n.decks["lancastrian"]["draw"])
    assert "L4" not in deck and "L18" in deck                  # base deck per arts_of_war_spec
    assert "L15" in deck and "L17" in deck                     # Henry VI while_king (Succession)


def test_renew_carries_removed_heirs_and_minus_eight_influence():
    from plantagenet import influence
    from plantagenet.scenarios import build_initial_state, renew_war
    s = build_initial_state("wars_of_the_roses")
    s.lords["somerset_1"].status = LordStatus.REMOVED.value    # lost in War I
    s.victory = {"result": "lancastrian"}
    before = influence._net_lanc(s.influence["track"])
    n = renew_war(s)
    assert n.lords["somerset_1"].status == LordStatus.REMOVED  # stays out
    after = influence._net_lanc(n.influence["track"])
    assert before - after == 8                                 # -8 Lancastrian Influence


def test_renew_requires_a_decisive_winner():
    import pytest

    from plantagenet.errors import IllegalAction
    from plantagenet.scenarios import build_initial_state, renew_war
    s = build_initial_state("wars_of_the_roses")
    with pytest.raises(IllegalAction) as e:
        renew_war(s)                                           # victory is None
    assert e.value.code == "no_winner"


def test_renew_after_final_war_is_game_over():
    import pytest

    from plantagenet.errors import IllegalAction
    from plantagenet.scenarios import build_initial_state, renew_war
    s = build_initial_state("wars_of_the_roses")
    s.grand_scenario["current_war"] = "war_iiiy"
    s.victory = {"result": "yorkist"}
    with pytest.raises(IllegalAction) as e:
        renew_war(s)
    assert e.value.code == "game_over"
