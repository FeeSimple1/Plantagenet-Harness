"""Regressions from the October 2026 interactive playtest on 76353e6.

Fixtures are unaltered pre-action game positions with history omitted.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from plantagenet.actions import apply_action
from plantagenet.errors import IllegalAction
from plantagenet.legal_moves import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus

DATA = Path(__file__).resolve().parent / "fixtures" / "playtest_2026_10"


def load_state(name: str) -> GameState:
    return GameState.model_validate_json((DATA / name).read_text())


def run_rochester(*, starved: bool = False):
    state = load_state("defender-battle-before.json")
    if starved:
        # Controlled variant, NOT the natural game position:
        # neither combatant carries food, and the battlefield cannot be Pillaged.
        state.lords["york"].assets["provender"] = 0
        state.lords["warwick_lancastrian"].assets["provender"] = 0
        state.locales["rochester"].depletion = "exhausted"
    seq = json.loads((DATA / "defender-battle-actions.json").read_text())
    for action in seq[:-1]:
        apply_action(state, copy.deepcopy(action))
    before_feed = state.model_copy(deep=True)
    result = apply_action(state, copy.deepcopy(seq[-1]))
    return before_feed, state, result


def test_stationary_defender_must_feed_after_battle():
    before, after, result = run_rochester()
    lord = before.lords["york"]
    assert lord.status == LordStatus.MUSTERED
    assert sum(n for kind, n in lord.forces.items() if kind != "retinue") == 5
    assert after.lords["york"].assets["provender"] == lord.assets["provender"] - 1
    assert any(x.get("lord") == "york" and x.get("fed") == 1
               for x in result["feed"]["yorkist"]["fed"])


def test_starving_stationary_defender_must_disband():
    _, after, result = run_rochester(starved=True)
    assert after.lords["york"].status != LordStatus.MUSTERED
    assert "york" in result["feed"]["yorkist"]["disbanded"]


@pytest.mark.parametrize("card", ["L5", "L11"])
def test_held_event_cannot_be_offered_as_capability(card: str):
    state = load_state("held-capability-before.json")
    assert card in state.decks["lancastrian"]["held"]
    illegal = {"type": "levy_capability", "side": "lancastrian",
               "by_lord": "clarence", "card": card}
    assert illegal not in legal_moves(state)


@pytest.mark.parametrize("card", ["L5", "L11"])
def test_held_event_cannot_be_executed_as_capability(card: str):
    state = load_state("held-capability-before.json")
    before = state.model_dump_json()
    with pytest.raises(IllegalAction):
        apply_action(state, {"type": "levy_capability", "side": "lancastrian",
                             "by_lord": "clarence", "card": card})
    assert state.model_dump_json() == before


def parliament_options():
    """Apply each advertised London Parley to an independent pre-action copy."""
    base = load_state("parliament-before.json")
    outcomes = []
    for action in legal_moves(base):
        if (action.get("type") == "parley"
                and action.get("by_lord") == "henry_vi"
                and action.get("target") == "london"):
            trial = base.model_copy(deep=True)
            result = apply_action(trial, copy.deepcopy(action))
            event = next(e for e in trial.active_events if e["card"] == "L18")
            outcomes.append((base, trial, result,
                             event.get("used", {}).get("henry_vi", 0)))
    return outcomes


def test_parliament_allows_reserving_the_once_per_lord_bonus():
    outcomes = parliament_options()
    assert outcomes, "No London Parley choices were offered"
    assert any(used == 0 for _, _, _, used in outcomes), (
        "Every offered Parley consumes Parliament Votes; no normal Parley "
        "preserving the bonus for a later target is available."
    )


def test_automatic_parliament_parley_does_not_roll():
    automatic = [o for o in parliament_options() if o[3] == 1]
    assert automatic, "The automatic-success choice should be reachable"
    before, after, result, _ = automatic[0]
    assert result["success"] is True
    assert result.get("roll") is None
    assert before.rng_state == after.rng_state


def test_bosworth_cannot_resolve_without_required_capability_selection():
    state = build_initial_state("bosworth", seed=20261010)
    counts = {side: sum(len(lord.capabilities) for lord in state.lords.values()
                        if lord.side == side)
              for side in ("yorkist", "lancastrian")}
    # Initial setup may legitimately be pending, but resolution must not bypass it.
    assert counts == {"yorkist": 0, "lancastrian": 0}
    with pytest.raises(IllegalAction):
        apply_action(state, {"type": "resolve_battle"})


def test_parliament_can_be_reserved_then_used_on_a_later_target():
    state = load_state("parliament-before.json")
    event = next(e for e in state.active_events if e["card"] == "L18")
    before_rng = copy.deepcopy(state.rng_state)
    first = apply_action(state, {"type": "parley", "side": "lancastrian",
                                "by_lord": "henry_vi", "target": "london",
                                "use_parliament_votes": False})
    assert first["roll"] in range(1, 7)
    assert first["spent"] == 1
    assert state.rng_state != before_rng
    assert event.get("used", {}).get("henry_vi", 0) == 0
    # The first ordinary Parley succeeds with this checkpoint's fixed seed.
    assert first["success"]
    later = next(m for m in legal_moves(state) if m.get("type") == "parley"
                 and m.get("by_lord") == "henry_vi" and m.get("target") != "london"
                 and "use_parliament_votes" not in m)
    before_rng = copy.deepcopy(state.rng_state)
    result = apply_action(state, later)
    assert result["success"] and result["roll"] is None
    assert result["spent"] == result["way_cost"]  # one-point discount, not all route cost
    assert event["used"]["henry_vi"] == 1
    assert state.rng_state == before_rng
    assert not any("use_parliament_votes" in m for m in legal_moves(state)
                   if m.get("by_lord") == "henry_vi")


def test_parliament_enumeration_is_completely_read_only():
    state = load_state("parliament-before.json")
    before = state.model_dump_json()
    legal_moves(state)
    legal_moves(state)
    assert state.model_dump_json() == before


@pytest.mark.parametrize("choice", ["false", 0, None, [], {}])
def test_invalid_parliament_choice_rejects_atomically(choice):
    state = load_state("parliament-before.json")
    before = state.model_dump_json()
    with pytest.raises(IllegalAction, match="use_parliament_votes"):
        apply_action(state, {"type": "parley", "side": "lancastrian",
                             "by_lord": "henry_vi", "target": "london",
                             "use_parliament_votes": choice})
    assert state.model_dump_json() == before


def test_succession_automatic_parley_does_not_roll_either():
    state = build_initial_state("henry_vi", seed=51)
    state.levy_step = "muster"
    state.active_events.append({"card": "Y18", "side": "yorkist", "scope": "this_levy"})
    before_rng = copy.deepcopy(state.rng_state)
    result = apply_action(state, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "lynn"})
    assert result["success"] is True and result["roll"] is None
    assert result["spent"] == 1
    assert before_rng == state.rng_state


@pytest.mark.parametrize("effect", ["L32", "L37"])
def test_automatic_vassal_levy_keeps_influence_cost_without_rolling(effect):
    state = build_initial_state("my_kingdom_for_a_horse", seed=22)
    state.levy_step = "muster"
    state.active_side = "lancastrian"
    lord = state.lords["henry_tudor"]
    lord.status = LordStatus.MUSTERED
    lord.calendar_box = None
    lord.exile_box = None
    lord.location = "london"
    state.locales["london"].favour = "lancastrian"
    state.locales["leicester"].favour = "lancastrian"  # Dudley's Seat
    for enemy in state.lords.values():
        if enemy.side == "yorkist" and enemy.location == "leicester":
            enemy.location = "york"
    if effect == "L32":
        lord.capabilities.append(effect)  # Two Roses
    else:
        state.active_events.append({"card": effect, "side": "lancastrian"})
    before_rng = copy.deepcopy(state.rng_state)
    result = apply_action(state, {"type": "levy_vassal", "side": "lancastrian",
                                 "by_lord": "henry_tudor", "target": "dudley"})
    assert result["success"] and result["roll"] is None
    assert result["spent"] == 1 and lord.lordship_spent == 1
    assert "dudley" in lord.vassals
    assert state.rng_state == before_rng


def test_great_ships_levy_parley_is_enumerated_across_seas():
    state = build_initial_state("henry_vi", seed=71)
    state.levy_step = "muster"
    lord = state.lords["york"]
    lord.location = "lynn"
    lord.capabilities.append("Y6")
    state.locales["lynn"].favour = "yorkist"
    move = {"type": "parley", "side": "yorkist", "by_lord": "york", "target": "dover"}
    assert move in legal_moves(state)
    result = apply_action(state, move)
    assert result["way_cost"] == 1
