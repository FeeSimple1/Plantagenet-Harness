"""Rejected reactions must leave accepted action history unchanged."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from tests.test_reactions import _approach_setup


def test_rejected_final_reaction_does_not_mutate_prior_history():
    """Action atomicity: rejected 4.3.5 reaction cannot alter prior accepted passes."""
    state, attacker, _ = _approach_setup()
    state.decks["yorkist"]["held"] = ["Y11"]
    actions.apply_action(
        state,
        {"type": "march", "side": "yorkist", "by_lord": attacker, "to": "lincoln",
         "decisions": {"culverins": [attacker]}},
    )
    # Henry first declines King's Parley. Blocked Ford is still awaiting a
    # response; the accepted result includes the reaction log so far.
    actions.apply_action(state, {"type": "react", "pass": True})
    accepted = state.history[-1]
    before = state.to_json()
    assert len(accepted["result"]["resolved"]) == 1
    # Declining the last offer resumes Battle, whose invalid Culverins choice
    # rejects the reaction. No record of that failed attempt may leak backward.
    with pytest.raises(IllegalAction, match="no_culverins"):
        actions.apply_action(state, {"type": "react", "pass": True})
    assert state.to_json() == before
    assert state.history[-1] is accepted
    assert len(accepted["result"]["resolved"]) == 1
    assert state.pending[0]["idx"] == 1
