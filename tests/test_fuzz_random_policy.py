"""Random-policy fuzz (cross-harness advisory §5): walk Levy trajectories the
first-legal round-trip sweep never reaches, asserting after every step that the
agent-facing palette offers no handler-rejected move and no board invariant
breaks. Seeded for determinism."""

from __future__ import annotations

import random

import pytest

from plantagenet import actions, invariants, legal_moves, static_data
from plantagenet.errors import IllegalAction

_SCENARIOS = [s for s in static_data.list_scenario_ids() if s != "bosworth"]


@pytest.mark.parametrize("sid", _SCENARIOS)
@pytest.mark.parametrize("seed", [1, 7, 42])
def test_random_levy_fuzz_keeps_invariants_and_clean_palette(sid, seed):
    rng = random.Random(seed)
    state = static_data and None  # placeholder to keep ruff quiet about imports
    from plantagenet.scenarios import build_initial_state
    state = build_initial_state(sid, seed=seed)
    if state.phase != "levy":
        return
    steps = 0
    # Drive the whole Levy (Arts of War draw -> Pay -> Muster) by random choice.
    while state.phase == "levy" and state.levy_step != "done" and steps < 400:
        if state.levy_step == "arts_of_war":
            actions.apply_action(state, {"type": "draw", "side": state.active_side})
            steps += 1
            continue
        if state.levy_step == "pay":
            actions.apply_action(state, {"type": "pay", "side": state.active_side})
            steps += 1
            continue
        # Muster step: validated palette must be clean, invariants must hold.
        palette = legal_moves.validated_legal_moves(state)
        assert palette["rejected"] == [], \
            f"{sid} seed {seed}: over-enumeration {palette['rejected']}"
        bad = invariants.board_invariant_violations(state)
        assert bad == [], f"{sid} seed {seed}: invariant broke {bad}"
        moves = palette["moves"]
        if not moves:
            break
        mv = rng.choice(moves)
        try:
            actions.apply_action(state, mv)
        except IllegalAction as e:                # palette said legal -> must apply
            pytest.fail(f"{sid} seed {seed}: validated move {mv} rejected -> {e.code}")
        steps += 1
    assert invariants.board_invariant_violations(state) == []
