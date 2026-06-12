"""Regressions from full grand-scenario playthroughs (2026-06-11).

1. Scenario End tie-break: Errata & Clarification FAQ #5 -- a scenario Tied
   (Influence at 0) at the final Victory check goes to the King's side, not a
   draw. Before the fix a tied War I/II also dead-ended the whole grand
   scenario (renew_war needs a decisive result).
2. Surrender (6.1.1) must END the conceded War immediately: phase -> "over",
   no further legal moves, straight into Renewed War (6.1.2).
"""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war


def _to_final_box_tied(state):
    state.turn_box = state.calendar.last_box
    t = state.influence["track"]
    t.marker_at = 0                      # Influence marker at 0 == tied (FAQ #5)
    return state


# ---------------------------------------------------- FAQ #5 tie-break (5.3)
def test_5_3_tie_goes_to_the_king_standalone():
    s = _to_final_box_tied(build_initial_state("henry_vi", seed=1))
    res = campaign._victory_check(s)
    assert res is not None and res["rule"] == "5.3"
    king = next(side for side, role in s.roles.items() if role == "king")
    assert res["result"] == king == "lancastrian"


def test_5_3_untied_still_goes_to_the_influence_leader():
    s = _to_final_box_tied(build_initial_state("henry_vi", seed=1))
    t = s.influence["track"]
    t.marker_side, t.marker_at = "yorkist", 3
    assert campaign._victory_check(s) == {"result": "yorkist", "rule": "5.3"}


def test_5_3_tie_in_grand_war_i_transitions_to_the_kings_war():
    s = _to_final_box_tied(build_initial_state("wars_of_the_roses", seed=1))
    res = campaign._victory_check(s)
    assert res["result"] == "lancastrian"          # King's side in War I
    s.phase, s.victory = "over", res
    nxt = renew_war(s)                             # must NOT dead-end on a tie
    assert nxt.grand_scenario["current_war"] == "war_iil"
    assert nxt.phase == "levy" and nxt.victory is None


# ------------------------------------------------- Surrender ends the War
def test_concede_ends_the_war_immediately():
    s = build_initial_state("wars_of_the_roses", seed=2)   # War I
    actions.apply_action(s, {"type": "concede", "side": "lancastrian"})
    assert s.phase == "over"
    assert s.victory == {"result": "yorkist", "rule": "6.1.1 Surrender",
                         "conceded_by": "lancastrian"}
    assert legal_moves.legal_moves(s) == []                # no play after surrender
    nxt = renew_war(s)                                     # straight to Renewed War
    assert nxt.grand_scenario["current_war"] == "war_iiy"


def test_concede_still_rejected_in_the_third_war():
    s = build_initial_state("wars_of_the_roses", seed=2)
    s.grand_scenario["current_war"] = "war_iiiy"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "concede", "side": "yorkist"})
    assert e.value.code == "no_surrender"
