"""Full-game smoke run (readiness gap 2): drive complete games through the
agent-facing interface (legal_moves -> apply_action), resolving reactions and
War transitions, asserting that no enumerated move is rejected and no board
invariant breaks at any step. This exercises the Campaign/Battle/End/transition
trajectories the Levy fuzz never reaches."""

from __future__ import annotations

import random

import pytest

from plantagenet import actions, invariants, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war
from tests._helpers import fill_event_decisions

_FLOW_ENDERS = {"end_muster", "end_activation", "end_campaign", "pass", "react"}


def _fill_plan(state, mv):
    """Construct a minimal legal Plan (4.1) for a build_plan template: activate
    this side's Mustered Lords, padding with Pass to the required card count."""
    side, n = mv["side"], mv["cards_required"]
    lords = [lid for lid, v in state.lords.items()
             if v.side == side and v.status == "mustered"]
    plan = [{"lord": lid} for lid in lords][:n]
    while len(plan) < n:
        plan.append({"pass": True})
    return {"type": "build_plan", "side": side, "plan": plan}


def _pick(moves, rng):
    """Progress-biased policy: usually advance the sequence, else exercise a
    random substantive move -- enough variety to be a smoke test, enough drive
    to terminate."""
    enders = [m for m in moves if m["type"] in _FLOW_ENDERS]
    others = [m for m in moves if m["type"] not in _FLOW_ENDERS]
    if enders and (not others or rng.random() < 0.6):
        return rng.choice(enders)
    return rng.choice(others or enders)


def _play_to_end(sid, seed, budget=8000):
    rng = random.Random(seed)
    state = build_initial_state(sid, seed=seed)
    transitions = 0
    for _ in range(budget):
        if state.phase == "over":
            # Grand scenario: a decisive War victory continues to the next War.
            if state.grand_scenario and (state.victory or {}).get("result") in (
                    "lancastrian", "yorkist"):
                try:
                    state = renew_war(state)
                    transitions += 1
                    continue
                except IllegalAction:
                    break          # final War concluded -> whole game over
            break                  # standalone scenario over (or a draw)
        moves = legal_moves.legal_moves(state)
        if not moves:
            break
        mv = _pick(moves, rng)
        if mv.get("type") == "build_plan" and "plan" not in mv:
            mv = _fill_plan(state, mv)
        elif mv.get("type") == "play_event" and "decisions" not in mv:
            mv = {**mv, "decisions": fill_event_decisions(state, mv["card"], mv["side"])}
        try:
            actions.apply_action(state, mv)
        except IllegalAction as e:                 # the menu must never offer an illegal move
            pytest.fail(f"{sid} seed {seed}: enumerated {mv} rejected -> {e.code}")
        bad = invariants.board_invariant_violations(state)
        assert bad == [], f"{sid} seed {seed}: invariant broke after {mv}: {bad}"
    return state, transitions


@pytest.mark.parametrize("sid", [s for s in static_data.list_scenario_ids()
                                 if s not in ("bosworth", "wars_of_the_roses")])
@pytest.mark.parametrize("seed", [1, 5, 7])
def test_standalone_scenario_plays_to_completion(sid, seed):
    state, _ = _play_to_end(sid, seed)
    assert state.phase == "over"                   # reached a scenario end (5.x / special)
    assert invariants.board_invariant_violations(state) == []


@pytest.mark.parametrize("seed", [1, 2, 7])
def test_grand_scenario_plays_through_war_transitions(seed):
    # Seeds chosen to reach a decisive War (with correct flat thresholds some seeds
    # legitimately end a War in a draw, which does not trigger a Renewed War).
    state, transitions = _play_to_end("wars_of_the_roses", seed)
    assert transitions >= 1                         # advanced through >= 1 Renewed War
    assert invariants.board_invariant_violations(state) == []
