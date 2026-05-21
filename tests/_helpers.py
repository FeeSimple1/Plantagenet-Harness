"""Shared test helpers for advancing the Levy flow past the Arts of War draw."""

from __future__ import annotations

from plantagenet import actions


def to_muster(state):
    """Advance through the Arts of War draw (3.1, Rebel then King) to Muster."""
    while state.phase == "levy" and state.levy_step == "arts_of_war":
        actions.apply_action(state, {"type": "draw", "side": state.active_side})
    return state
