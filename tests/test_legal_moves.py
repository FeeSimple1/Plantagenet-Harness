"""Levy enumerator and the enumerator/handler round-trip property (3.4)."""

from __future__ import annotations

import pytest

from plantagenet import actions, invariants, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster

LEVY_SCENARIOS = [s for s in static_data.list_scenario_ids() if s != "bosworth"]


def test_enumerator_only_for_active_side_during_muster():
    s = build_initial_state("henry_vi")
    to_muster(s)
    moves = legal_moves.legal_moves(s)
    assert moves and all(m["side"] == s.active_side for m in moves)
    # Levy Capability is now enumerated; only Levy Troops-style deferrals are not.
    assert any(m["type"] == "levy_capability" for m in moves)
    assert any(m["type"] == "end_muster" for m in moves)


def test_enumerator_offers_begin_campaign_when_levy_done():
    s = build_initial_state("henry_vi")
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": "yorkist"})
    actions.apply_action(s, {"type": "end_muster", "side": "lancastrian"})
    assert s.levy_step == "done"
    assert legal_moves.legal_moves(s) == [{"type": "begin_campaign"}]


@pytest.mark.parametrize("sid", LEVY_SCENARIOS)
def test_round_trip_every_emitted_move_applies(sid):
    # CROSS_PROJECT_LESSONS round-trip: nothing the enumerator emits should
    # be rejected by the handler.
    for seed in (1, 2):
        state = build_initial_state(sid, seed=seed)
        to_muster(state)
        steps = 0
        while state.levy_step == "muster" and steps < 300:
            moves = legal_moves.legal_moves(state)
            for mv in moves:
                snap = state.model_copy(deep=True)
                try:
                    actions.apply_action(snap, mv)
                except IllegalAction as e:
                    pytest.fail(f"{sid}: enumerator emitted illegal {mv} -> {e.code}")
                # Advisory #2: no enumerated move may produce illegal co-location.
                assert invariants.co_location_violations(snap) == [], \
                    f"{sid}: {mv} produced co-location {invariants.co_location_violations(snap)}"
            nxt = next((m for m in moves if m["type"] != "end_muster"), moves[-1])
            actions.apply_action(state, nxt)
            assert invariants.co_location_violations(state) == []
            steps += 1


def test_roundtrip_sweep_marker_present_in_source():
    # Guard: the round-trip sweep script must stay in the repo (cheap
    # regression insurance per CROSS_PROJECT_LESSONS).
    import inspect

    import plantagenet.legal_moves as lm
    assert "round-trip" in inspect.getsource(lm).lower()
