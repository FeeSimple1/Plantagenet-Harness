"""Influence points and the Influence check (Rules 1.4.1, 1.4.2)."""

from __future__ import annotations

import pytest

from plantagenet import influence
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def _set_track(state, side, at):
    t = state.influence["track"]
    t.marker_side, t.marker_at = side, at


def test_spending_moves_toward_opponent_per_example():
    # 1.4.1 example: marker at Yorkist 3, Yorkists spend 4 -> Lancastrian 1.
    s = build_initial_state("henry_vi")
    _set_track(s, "yorkist", 3)
    influence.spend_influence(s, "yorkist", 4)
    t = s.influence["track"]
    assert (t.marker_side, t.marker_at) == ("lancastrian", 1)


def test_trailing_side_spending_pushes_opponent_higher():
    # 1.4.1 NOTE: the trailing side spending pushes the opponent's total up.
    s = build_initial_state("henry_vi")
    _set_track(s, "yorkist", 3)
    influence.spend_influence(s, "lancastrian", 2)  # trailing side spends
    t = s.influence["track"]
    assert (t.marker_side, t.marker_at) == ("yorkist", 5)


def test_influence_cap_45():
    s = build_initial_state("henry_vi")
    _set_track(s, "yorkist", 44)
    influence.gain_influence(s, "yorkist", 10)
    assert s.influence["track"].marker_at == 45


def test_check_influence_success_formula_and_spend():
    # roll==1 always succeeds; roll==6 always fails; else roll<=rating (1.4.2).
    s = build_initial_state("henry_vi")
    york_rating = influence.lord_influence_rating("york")  # 5
    for _ in range(60):
        before = s.influence["track"]
        net_before = (before.marker_at if before.marker_side == "lancastrian"
                      else -before.marker_at)
        r = influence.check_influence(s, "york", "yorkist")
        assert r["spent"] == 1  # 1 base point, no extras, no ways
        expected = r["roll"] == 1 or (r["roll"] != 6 and r["roll"] <= york_rating)
        assert r["success"] == expected
        net_after = (s.influence["track"].marker_at if s.influence["track"].marker_side
                     == "lancastrian" else -s.influence["track"].marker_at)
        # Yorkist spending moves the net toward Lancastrian (+1 in lanc terms).
        assert net_after == min(45, net_before + 1)


def test_extra_spend_must_be_0_1_or_3():
    s = build_initial_state("henry_vi")
    with pytest.raises(IllegalAction):
        influence.check_influence(s, "york", "yorkist", extra_spend=2)
