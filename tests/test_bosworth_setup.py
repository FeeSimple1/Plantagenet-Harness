"""Bosworth's mandatory, player-selected Capability setup and full Fronts."""
from __future__ import annotations

import copy
import json

import pytest

from plantagenet import actions, invariants, legal_moves, render, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState


def complete_setup(state: GameState) -> None:
    """Deterministic test choices only; the engine supplies no strategy policy."""
    for _ in range(10):  # four cards plus an Array for each player
        moves = legal_moves.legal_moves(state)
        assert moves and moves[0]["type"] != "resolve_battle"
        actions.apply_action(state, moves[0])
    assert state.battle_setup and state.battle_setup.complete


def assert_rejected(state, action, code=None):
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, action)
    if code:
        assert error.value.code == code
    assert state.model_dump_json() == before


def choose_four(state):
    for _ in range(4):
        move = legal_moves.legal_moves(state)[0]
        assert move["type"] == "choose_battle_capability"
        actions.apply_action(state, move)


def test_setup_starts_with_full_decks_and_no_automatic_choices():
    state = build_initial_state("bosworth", seed=42)
    for side in ("yorkist", "lancastrian"):
        assert len(state.decks[side]["draw"]) == 19
        assert state.decks[side]["draw"] == static_data.scenario_card_deck("bosworth", side)
    assert all(not lord.capabilities for lord in state.lords.values())
    assert {m["type"] for m in legal_moves.legal_moves(state)} == {"choose_battle_capability"}
    assert_rejected(state, {"type": "resolve_battle"}, "battle_setup_incomplete")


def test_setup_menu_roundtrips_without_mutation_and_then_battle_completes():
    state = build_initial_state("bosworth", seed=3)
    rng = copy.deepcopy(state.rng_state)
    for _ in range(10):
        before = state.model_dump_json()
        moves = legal_moves.legal_moves(state)
        assert state.model_dump_json() == before
        for move in moves:
            trial = state.model_copy(deep=True)
            actions.apply_action(trial, move)
            assert not invariants.board_invariant_violations(trial)
        actions.apply_action(state, moves[0])
        assert state.rng_state == rng
        assert not state.influence
        assert all(lord.lordship_spent == 0 for lord in state.lords.values())
    assert legal_moves.legal_moves(state) == [{"type": "resolve_battle"}]
    for side in ("yorkist", "lancastrian"):
        assert sum(len(lord.capabilities) for lord in state.lords.values()
                   if lord.side == side) == 4
    result = actions.apply_action(state, {"type": "resolve_battle"})
    assert state.phase == "over"
    assert result["winner"] in ("yorkist", "lancastrian", None)
    assert not invariants.board_invariant_violations(state)


def test_opponents_capabilities_and_arrays_are_not_revealed_early():
    state = build_initial_state("bosworth")
    choose_four(state)
    y_cards = [c for cards in state.battle_setup.capabilities["yorkist"].values() for c in cards]
    actions.apply_action(state, legal_moves.legal_moves(state)[0])
    assert state.active_side == "lancastrian"
    assert all(not lord.capabilities and not lord.special_vassals
               for lord in state.lords.values())
    text = render.render_summary(state)
    assert all(c not in text for c in y_cards)
    assert "hidden setup" in text
    assert_rejected(state, {"type": "resolve_battle"}, "battle_setup_incomplete")
    # Serialization retains unrevealed choices for both players.
    restored = GameState.model_validate_json(state.model_dump_json())
    assert restored == state
    assert legal_moves.legal_moves(restored) == legal_moves.legal_moves(state)


@pytest.mark.parametrize("action,code", [
    ({"type": "choose_battle_capability", "side": "lancastrian",
      "by_lord": "henry_tudor", "card": "L1"}, "not_active_side"),
    ({"type": "choose_battle_capability", "side": "yorkist",
      "by_lord": "henry_tudor", "card": "Y1"}, "wrong_side_lord"),
    ({"type": "choose_battle_capability", "side": "yorkist",
      "by_lord": "richard_iii", "card": "L1"}, "unknown_card"),
    ({"type": "choose_battle_capability", "side": "yorkist",
      "by_lord": "richard_iii", "card": "Y18"}, "card_not_in_scenario"),
    ({"type": "choose_battle_capability", "side": "yorkist",
      "by_lord": "norfolk", "card": "Y33"}, "ineligible_lord"),
    ({"type": "array_battle", "side": "yorkist",
      "front": ["norfolk", "richard_iii", "northumberland_2"]}, "battle_setup_incomplete"),
    ({"type": "end_muster", "side": "yorkist"}, "battle_setup_only"),
    ({"type": "begin_campaign"}, "battle_setup_only"),
])
def test_invalid_setup_actions_reject_atomically(action, code):
    assert_rejected(build_initial_state("bosworth"), action, code)


def test_selected_card_cannot_be_reused_and_mat_limit_is_enforced():
    state = build_initial_state("bosworth")
    first = legal_moves.legal_moves(state)[0]
    actions.apply_action(state, first)
    assert_rejected(state, first, "card_in_play")
    second = next(m for m in legal_moves.legal_moves(state) if m["by_lord"] == first["by_lord"])
    actions.apply_action(state, second)
    assert not any(m.get("by_lord") == first["by_lord"] for m in legal_moves.legal_moves(state))
    assert_rejected(state, {**first, "card": "Y11"}, "two_capabilities")


def test_arrays_must_contain_all_three_lords_and_all_six_choices_are_offered():
    state = build_initial_state("bosworth")
    choose_four(state)
    moves = legal_moves.legal_moves(state)
    assert len(moves) == 6
    assert len({tuple(m["front"]) for m in moves}) == 6
    for front in ([], ["richard_iii"] * 3,
                  ["richard_iii", "norfolk", "henry_tudor"], {"left": "richard_iii"}):
        assert_rejected(state, {"type": "array_battle", "side": "yorkist", "front": front},
                        "bad_battle_array")
    assert_rejected(state, {"type": "choose_battle_capability", "side": "yorkist",
                            "by_lord": "norfolk", "card": "Y11"}, "four_capabilities")


def test_completed_arrays_cannot_be_overridden_at_resolution():
    state = build_initial_state("bosworth")
    complete_setup(state)
    assert_rejected(state, {"type": "resolve_battle",
                            "decisions": {"defender_positions": {}}}, "battle_array_locked")
    assert_rejected(state, {"type": "choose_battle_capability", "side": state.active_side,
                            "by_lord": "norfolk", "card": "Y1"}, "battle_setup_closed")


def test_battle_uses_committed_arrays(monkeypatch):
    from plantagenet import battle
    state = build_initial_state("bosworth")
    complete_setup(state)
    observed = {}

    def capture(_state, _locale, _attackers, _defenders, decisions):
        observed.update(decisions)
        return {"winner_side": "lancastrian"}

    monkeypatch.setattr(battle, "resolve_battle", capture)
    actions.apply_action(state, {"type": "resolve_battle"})
    assert observed["attacker_positions"] == dict(
        enumerate(state.battle_setup.arrays["lancastrian"]))
    assert observed["defender_positions"] == dict(enumerate(state.battle_setup.arrays["yorkist"]))
    # These positions survive a real JSON action/state round trip as integers
    # at the engine boundary, rather than introducing unusable string indices.
    assert all(isinstance(i, int) for i in observed["defender_positions"])


def test_setup_special_vassal_is_applied_only_at_reveal():
    state = build_initial_state("bosworth")
    # L35 Thomas Stanley is eligible for Henry Tudor and is in the three-rose deck.
    choose_four(state)
    actions.apply_action(state, legal_moves.legal_moves(state)[0])
    action = {"type": "choose_battle_capability", "side": "lancastrian",
              "by_lord": "henry_tudor", "card": "L35"}
    assert action in legal_moves.legal_moves(state)
    actions.apply_action(state, action)
    assert "thomas_stanley" not in state.lords["henry_tudor"].special_vassals
    for _ in range(3):
        actions.apply_action(state, legal_moves.legal_moves(state)[0])
    actions.apply_action(state, legal_moves.legal_moves(state)[0])
    assert "L35" in state.lords["henry_tudor"].capabilities
    assert "thomas_stanley" in state.lords["henry_tudor"].special_vassals


def test_setup_card_zone_invariant_catches_duplicate():
    state = build_initial_state("bosworth")
    action = legal_moves.legal_moves(state)[0]
    actions.apply_action(state, action)
    assert not invariants.card_zone_violations(state)
    state.decks["yorkist"]["draw"].append(action["card"])
    assert any(x["card"] == action["card"] for x in invariants.card_zone_violations(state))


def test_completed_setup_replay_is_identical():
    state = build_initial_state("bosworth", seed=731)
    complete_setup(state)
    actions.apply_action(state, {"type": "resolve_battle"})
    replay = build_initial_state("bosworth", seed=731)
    for entry in json.loads(state.model_dump_json())["history"]:
        actions.apply_action(replay, entry["action"])
    assert replay == state


def test_same_named_capabilities_cannot_share_a_mat():
    state = build_initial_state("bosworth")
    action = {"type": "choose_battle_capability", "side": "yorkist",
              "by_lord": "richard_iii", "card": "Y1"}
    actions.apply_action(state, action)
    assert_rejected(state, {**action, "card": "Y2"}, "duplicate_capability")
