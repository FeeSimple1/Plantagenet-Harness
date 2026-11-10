"""Immediate Arts of War Event resolution integrated into the draw flow (3.1.3).

A 2nd-or-later Levy draws Events; immediate ones are queued on
``state.pending_events`` and resolved by ``play_event`` (with any decisions)
before the Levy advances. Each resolved card returns to the deck (3.1.3), and an
Event whose precondition is unmet has no effect rather than being rejected.
"""

from __future__ import annotations

import pytest

from plantagenet import actions, invariants, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus
from tests._helpers import resolve_pending_events


def _later_levy_with_top(scenario, seed, side_imm):
    """Build a later-Levy state whose complete unused pool is two immediates.

    Rule 3.1.1 now shuffles the whole unused pool before every later draw, so a
    test cannot force cards merely by moving them to the old draw-pile top.
    """
    s = build_initial_state(scenario, seed=seed)
    s.turn_box = 2
    side = s.active_side
    cards = side_imm[side]
    s.decks[side]["draw"] = list(cards)
    s.decks[side]["discard"] = []
    s.seed = 0                  # Random(0).shuffle preserves this two-card order
    s.rng_state = None
    return s, side, cards


def test_draw_queues_immediates_and_blocks_advance():
    s, side, cards = _later_levy_with_top(
        "warwicks_rebellion", 1, {"lancastrian": ["L30", "L26"]})
    r = actions.apply_action(s, {"type": "draw", "side": side})
    assert r["next"] == "resolve_events"
    assert [pe["card"] for pe in s.pending_events] == cards
    # The Levy does not advance: active side unchanged, still arts_of_war.
    assert s.active_side == side and s.levy_step == "arts_of_war"
    assert invariants.board_invariant_violations(s) == []


def test_only_play_event_legal_while_pending():
    s, side, _ = _later_levy_with_top(
        "warwicks_rebellion", 1, {"lancastrian": ["L30", "L26"]})
    actions.apply_action(s, {"type": "draw", "side": side})
    moves = legal_moves.legal_moves(s)
    assert {m["type"] for m in moves} == {"play_event"}
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "draw", "side": side})
    assert e.value.code == "events_pending"


def test_resolution_returns_card_to_deck_and_advances():
    s, side, cards = _later_levy_with_top(
        "warwicks_rebellion", 1, {"lancastrian": ["L30", "L26"]})
    actions.apply_action(s, {"type": "draw", "side": side})
    resolve_pending_events(s)
    assert s.pending_events == []
    # Each immediate card is back in the deck exactly once (3.1.3, no duplication).
    for c in cards:
        piles = sum(s.decks[side][p].count(c) for p in ("draw", "discard", "held"))
        assert piles == 1, (c, piles)
    assert invariants.board_invariant_violations(s) == []
    # Rebel finished -> King draws next.
    assert s.active_side != side and s.levy_step == "arts_of_war"


def test_precondition_unmet_event_has_no_effect_not_rejected():
    # Tudor Banners (L32) has no effect unless Henry Tudor is at a Friendly
    # Stronghold; drawing it without him must resolve to no effect, not raise.
    s = build_initial_state("warwicks_rebellion", seed=1)
    s.turn_box = 2
    # Resolve as a pending event directly through play_event in a forced context.
    s.pending_events.append({"card": "L32", "side": "lancastrian"})
    s.active_side = "lancastrian"
    r = actions.apply_action(s, {"type": "play_event", "card": "L32",
                                 "side": "lancastrian"})
    assert "no_effect" in r
    assert invariants.board_invariant_violations(s) == []


def _welsh_rebellion_draw():
    state, side, _ = _later_levy_with_top(
        "warwicks_rebellion", 19, {"lancastrian": ["L25", "L30"]},
    )
    actions.apply_action(state, {"type": "draw", "side": side})
    return state


def test_welsh_rebellion_removes_chosen_troops_from_each_lord_atomically():
    state = _welsh_rebellion_draw()
    edward, pembroke = state.lords["edward_iv"], state.lords["pembroke"]
    edward.location = "ludlow"
    edward.forces = {"retinue": 1, "militia": 1}
    move, = legal_moves.legal_moves(state)
    assert move["event_choices"] == {"troops": {
        "edward_iv": {"available": {"militia": 1}, "remove": 1},
        "pembroke": {"available": {"men_at_arms": 1, "longbow": 3, "militia": 2}, "remove": 2},
    }}
    choices = {"pembroke": ["militia", "militia"], "edward_iv": ["militia"]}
    before = state.model_dump_json()
    for decisions, code in (
        ({"troops": {**choices, "edward_iv": ["retinue"]}}, "bad_event_target"),
        ({"troops": {**choices, "pembroke": ["men_at_arms", "men_at_arms"]}}, "bad_event_target"),
        ({"troops": {"pembroke": ["militia", "militia"]}}, "bad_event_target"),
        ({"troops": {**choices, "pembroke": ["militia"]}}, "bad_count"),
        ({"strongholds": ["pembroke", "ludlow"]}, "bad_event_decisions"),
    ):
        with pytest.raises(IllegalAction) as error:
            actions.apply_action(state, {**move, "decisions": decisions})
        assert error.value.code == code
        assert state.model_dump_json() == before

    action = {**move, "decisions": {"troops": choices}}
    loaded = GameState.model_validate_json(before)
    result = actions.apply_action(state, action)
    assert actions.apply_action(loaded, action) == result
    assert loaded.model_dump_json() == state.model_dump_json()
    assert result["troops_removed"] == {"edward_iv": 1, "pembroke": 2}
    assert result["disbanded"] == ["edward_iv"] and edward.status == LordStatus.CALENDAR
    assert pembroke.forces == {"retinue": 1, "men_at_arms": 1, "longbow": 3, "militia": 0}
    assert state.locales["ludlow"].favour == "yorkist"
    assert state.pending_events == [{"side": "lancastrian", "card": "L30"}]
    assert state.decks["lancastrian"]["draw"].count("L25") == 1
    assert invariants.board_invariant_violations(state) == []


@pytest.mark.parametrize("targets", [[], ["hereford"], ["hereford", "ludlow"]])
def test_welsh_rebellion_removes_exact_chosen_favour(targets):
    state = _welsh_rebellion_draw()
    state.lords["pembroke"].location = "london"
    available = set(targets)
    if len(targets) == 2:
        available.add("pembroke")
    for loc in ("hereford", "ludlow", "pembroke"):
        state.locales[loc].favour = "yorkist" if loc in available else "neutral"
    move, = legal_moves.legal_moves(state)
    assert move["event_choices"] == {"strongholds": {
        "available": dict.fromkeys(available, 1), "remove": len(targets),
    }}
    if len(targets) == 2:
        before = state.model_dump_json()
        for bad in (["ludlow", "ludlow"], ["ludlow", "london"]):
            with pytest.raises(IllegalAction, match="bad_event_target"):
                actions.apply_action(state, {**move, "decisions": {"strongholds": bad}})
            assert state.model_dump_json() == before
    result = actions.apply_action(state, {**move, "decisions": {"strongholds": targets}})
    assert result["favour_removed"] == len(targets)
    for loc in available:
        assert state.locales[loc].favour == ("neutral" if loc in targets else "yorkist")
    assert state.locales["london"].favour == "yorkist"
    assert invariants.board_invariant_violations(state) == []


def test_welsh_rebellion_default_does_not_depend_on_force_dictionary_order():
    state = _welsh_rebellion_draw()
    reordered = state.model_copy(deep=True)
    forces = reordered.lords["pembroke"].forces
    reordered.lords["pembroke"].forces = dict(reversed(list(forces.items())))
    for position in (state, reordered):
        move, = legal_moves.legal_moves(position)
        actions.apply_action(position, move)
    assert state.lords["pembroke"].forces == reordered.lords["pembroke"].forces


def test_warwicks_propaganda_sizes_to_available():
    # Only 2 Yorkist Strongholds exist -> Warwick's Propaganda selects 2, not 3.
    s = build_initial_state("warwicks_rebellion", seed=1)
    for _loc, ls in s.locales.items():
        if ls.favour == "yorkist":
            ls.favour = "neutral"
    picks = list(s.locales)[:2]
    for loc in picks:
        s.locales[loc].favour = "yorkist"
    s.turn_box = (s.calendar.first_box or s.turn_box) + 1
    s.decks["lancastrian"]["draw"].remove("L23")
    s.pending_events.append({"card": "L23", "side": "lancastrian"})
    s.active_side = "lancastrian"
    # Supplying 3 is now wrong (only 2 available); supplying 2 is correct.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_event", "card": "L23",
                                 "side": "lancastrian", "decisions": {
                                     "strongholds": list(s.locales)[:3]}})
    assert e.value.code == "bad_count"
    actions.apply_action(s, {"type": "play_event", "card": "L23",
                             "side": "lancastrian", "decisions": {
                                 "strongholds": picks}})
    assert all(s.locales[loc].favour == "yorkist" for loc in picks)
    resolve_pending_events(s)
    assert all(s.locales[loc].favour == "neutral" for loc in picks)
