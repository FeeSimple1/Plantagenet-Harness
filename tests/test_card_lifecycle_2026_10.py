"""Regressions from the seed-20261011 complete grand-campaign playtest."""

from __future__ import annotations

from copy import deepcopy

import pytest

from plantagenet import actions, invariants, legal_moves, scenarios
from plantagenet.errors import IllegalAction
from plantagenet.state import CampaignState, GameState


def reject_unchanged(state: GameState, move: dict, code: str) -> None:
    old = state.model_dump(mode="json")
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, move)
    assert error.value.code == code
    assert state.model_dump(mode="json") == old


def later_levy_state(side: str = "lancastrian") -> GameState:
    """Small, controlled later-Levy Arts of War position."""
    scenario = "warwicks_rebellion" if side == "lancastrian" else "henry_vi"
    state = scenarios.build_initial_state(scenario, seed=20261011)
    state.phase = "levy"
    state.levy_step = "arts_of_war"
    state.turn_box = (state.calendar.first_box or 1) + 1
    state.active_side = side
    deck = state.decks[side]
    if side == "lancastrian":
        deck["draw"] = ["L1", "L11"]
        deck["discard"] = ["L12", "L13", "L2", "L28"]
    else:
        deck["draw"] = ["Y1", "Y11"]
        deck["discard"] = ["Y12", "Y13", "Y2", "Y8"]
    deck["held"] = []
    deck["set_aside"] = []
    state.active_events = []
    state.pending_events = []
    state.rng_state = None
    return state


def campaign_reset_state() -> GameState:
    """Controlled Campaign-end position with Held Events on both sides."""
    state = scenarios.build_initial_state("henry_vi", seed=17)
    state.phase = "campaign"
    state.levy_step = "done"
    state.campaign = CampaignState(step="end")
    for side, cards in {
        "lancastrian": ["L1", "L11", "L13"],
        "yorkist": ["Y1", "Y11", "Y13"],
    }.items():
        deck = state.decks[side]
        for card in cards:
            for pile in ("draw", "discard", "set_aside"):
                if card in deck.get(pile, []):
                    deck[pile].remove(card)
        deck["held"] = list(cards)
    return state


# R1: every later Levy rebuilds and shuffles the unused Event deck (3.1.1).
def test_later_levy_draw_rejoins_discard_and_consumes_shuffle_rng() -> None:
    state = later_levy_state()
    old_rng = deepcopy(state.rng_state)
    assert len(state.decks["lancastrian"]["discard"]) == 4
    result = actions.apply_action(state, {"type": "draw", "side": "lancastrian"})
    assert len(result["drawn"]) == 2
    assert state.rng_state != old_rng
    assert state.decks["lancastrian"]["discard"] == []


def test_later_levy_pair_depends_on_rng_state() -> None:
    pairs = set()
    for seed in range(32):
        state = later_levy_state()
        state.seed = seed
        state.rng_state = None
        result = actions.apply_action(state, {"type": "draw", "side": "lancastrian"})
        pairs.add(tuple(result["drawn"]))
    assert len(pairs) > 1


def test_empty_draw_still_draws_from_unused_discard_pool() -> None:
    state = later_levy_state()
    deck = state.decks["lancastrian"]
    deck["discard"] += deck["draw"]
    deck["draw"] = []
    result = actions.apply_action(state, {"type": "draw", "side": "lancastrian"})
    assert len(result["drawn"]) == 2
    assert deck["discard"] == []


@pytest.mark.parametrize("side", ["lancastrian", "yorkist"])
def test_shuffle_excludes_held_attached_active_and_pending_cards(side: str) -> None:
    state = later_levy_state(side)
    prefix = "L" if side == "lancastrian" else "Y"
    deck = state.decks[side]
    held, attached, active, pending = (f"{prefix}{n}" for n in (3, 4, 5, 6))
    for card in (held, attached, active, pending):
        for pile in ("draw", "discard", "set_aside"):
            if card in deck.get(pile, []):
                deck[pile].remove(card)
    deck["held"] = [held]
    lord = next(lord for lord in state.lords.values() if lord.side == side
                and lord.status == "mustered")
    lord.capabilities = [attached]
    state.active_events = [{"card": active, "side": side, "scope": "this_levy"}]
    state.pending_events = [{"card": pending, "side": side}]
    forbidden = {held, attached, active, pending}
    # Pending events normally block Draw; this directly tests the pool builder.
    from plantagenet.arts_of_war import _shuffle_unused
    _shuffle_unused(state, side)
    assert not forbidden.intersection(deck["draw"])
    assert invariants.board_invariant_violations(state) == []


# R2: first-Levy Capability allocation is a player choice evaluated jointly (3.1.2).
def test_first_draw_menu_exposes_all_maximum_card_allocations() -> None:
    state = scenarios.build_initial_state("wars_of_the_roses", seed=20261011)
    moves = legal_moves.legal_moves(state)
    assert moves and {move["type"] for move in moves} == {"draw"}
    assignments = [move["assignments"] for move in moves]
    assert {assignment["Y11"] for assignment in assignments} >= {"york", "march"}
    assert {assignment["Y7"] for assignment in assignments} >= {"york", "march"}
    assert all(sum(lid is not None for lid in assignment.values()) == 2
               for assignment in assignments)


def test_explicit_initial_assignment_can_choose_somerset() -> None:
    state = scenarios.build_initial_state("wars_of_the_roses", seed=9)
    state.active_side = "lancastrian"
    deck = state.decks["lancastrian"]
    deck["draw"] = ["L21"]
    deck["discard"] = deck["held"] = deck["set_aside"] = []
    move = next(move for move in legal_moves.legal_moves(state)
                if move["assignments"].get("L21") == "somerset_1")
    result = actions.apply_action(state, move)
    assert "L21" in state.lords["somerset_1"].capabilities
    assert result["deployed"] == [{"card": "L21", "lord": "somerset_1"}]


def joint_assignment_state() -> GameState:
    state = scenarios.build_initial_state("wars_of_the_roses", seed=20261011)
    deck = state.decks["yorkist"]
    deck["draw"] = ["Y11", "Y7"]
    deck["discard"] = deck["held"] = deck["set_aside"] = []
    # Leave York only one open slot; March can take the other card.
    state.lords["york"].capabilities = ["Y3"]
    return state


def test_joint_assignment_preserves_both_cards_when_one_lord_has_one_slot() -> None:
    state = joint_assignment_state()
    result = actions.apply_action(state, {"type": "draw", "side": "yorkist",
                                          "assignments": {"Y11": "york", "Y7": "march"}})
    assert result["discarded"] == []
    assert "Y11" in state.lords["york"].capabilities
    assert "Y7" in state.lords["march"].capabilities


def test_cannot_discard_card_when_a_joint_assignment_preserves_both() -> None:
    state = joint_assignment_state()
    reject_unchanged(state, {"type": "draw", "side": "yorkist",
                             "assignments": {"Y11": "york", "Y7": None}},
                     "illegal_capability_assignment")


# R3: Campaign Reset permits selective Held-Event return (4.8.6).
def test_end_campaign_menu_advertises_held_reset_choices() -> None:
    state = campaign_reset_state()
    assert legal_moves.legal_moves(state) == [{"type": "end_campaign",
                                               "discard_held_options": {
        "lancastrian": ["L1", "L11", "L13"],
        "yorkist": ["Y1", "Y11", "Y13"],
    }}]


@pytest.mark.parametrize("side,cid", [("yorkist", "Y11"), ("lancastrian", "L11")])
def test_reset_can_discard_one_held_event_and_keep_the_others(side: str, cid: str) -> None:
    state = campaign_reset_state()
    held = deepcopy(state.decks[side]["held"])
    result = actions.apply_action(state, {"type": "end_campaign",
                                          "decisions": {"discard_held": {side: [cid]}}})
    assert result["discarded_held"] == {side: [cid]}
    assert cid not in state.decks[side]["held"]
    assert cid in state.decks[side]["discard"]
    assert all(card in state.decks[side]["held"] for card in held if card != cid)


def test_reset_without_selection_keeps_every_held_event() -> None:
    state = campaign_reset_state()
    held = {side: deepcopy(state.decks[side]["held"])
            for side in ("lancastrian", "yorkist")}
    result = actions.apply_action(state, {"type": "end_campaign"})
    assert result["discarded_held"] == {}
    assert all(state.decks[side]["held"] == cards for side, cards in held.items())


def test_illegal_held_discard_rejects_entire_end_campaign_atomically() -> None:
    state = campaign_reset_state()
    reject_unchanged(state, {"type": "end_campaign", "decisions": {
        "discard_held": {"yorkist": ["L11"]}}}, "card_not_held")


def test_returned_held_event_rejoins_next_levy_shuffle() -> None:
    state = campaign_reset_state()
    actions.apply_action(state, {"type": "end_campaign", "decisions": {
        "discard_held": {"yorkist": ["Y11"]}}})
    assert state.phase == "levy" and state.levy_step == "arts_of_war"
    assert state.active_side == "yorkist"
    assert "Y11" in state.decks["yorkist"]["discard"]
    result = actions.apply_action(state, {"type": "draw", "side": "yorkist"})
    assert state.decks["yorkist"]["discard"] == []
    live = set(result["drawn"]) | set(state.decks["yorkist"]["draw"])
    live |= set(state.decks["yorkist"]["held"])
    live |= {e["card"] for e in state.pending_events}
    live |= {e["card"] for e in state.active_events if e.get("side") == "yorkist"}
    assert "Y11" in live
