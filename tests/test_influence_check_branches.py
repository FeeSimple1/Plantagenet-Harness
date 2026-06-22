"""Influence check (1.4.2) branch coverage -- closes mutation-testing survivors.

The pre-existing success-formula test exercised only rating 5, where the crit
(roll==1), fumble (roll==6) and the `and` in `roll != 6 and roll <= rating` are
all masked (every non-6 roll is <= 5 anyway, and roll 1 succeeds via the rating
clause). Mutation testing (`scripts/mutation_probe.py` on `influence.py`) left
those branches plus the spend formula and the _RATING_BONUS map as survivors.
These tests pin each branch at the ratings that actually distinguish them, with
the d6 forced to a chosen value.
"""

from __future__ import annotations

import pytest

from plantagenet import influence, ratings
from plantagenet.errors import IllegalAction
from plantagenet.rng import DiceRoller
from plantagenet.scenarios import build_initial_state


@pytest.fixture
def force_d6(monkeypatch):
    def _force(value):
        monkeypatch.setattr(DiceRoller, "d6", lambda self: value)
    return _force


def _base_rating(state):
    return ratings.rating(state, "york", "influence", action=None)


# ------------------------------------------------------------- success rule
def test_roll_one_always_succeeds_even_at_rating_zero(force_d6):
    """Crit: roll==1 succeeds regardless of rating (kills roll==1 -> roll==2)."""
    s = build_initial_state("henry_vi")
    force_d6(1)
    r = influence.check_influence(s, "york", "yorkist",
                                  loyalty_mod=-_base_rating(s))   # rating == 0
    assert r["rating"] == 0
    assert r["success"] is True


def test_roll_six_always_fails_even_at_high_rating(force_d6):
    """Fumble: roll==6 fails regardless of rating (kills roll!=6 -> roll!=7 and
    the `and` -> `or` in the success expression)."""
    s = build_initial_state("henry_vi")
    force_d6(6)
    r = influence.check_influence(s, "york", "yorkist", loyalty_mod=+5)  # rating high
    assert r["rating"] >= 6
    assert r["success"] is False


def test_mid_roll_compares_against_rating(force_d6):
    """2..5: success iff roll <= rating (kills the `and`->`or` and the <= bound)."""
    s = build_initial_state("henry_vi")
    force_d6(4)
    # rating 3 -> 4 > 3 -> fail
    r = influence.check_influence(s, "york", "yorkist", loyalty_mod=3 - _base_rating(s))
    assert r["rating"] == 3 and r["success"] is False
    s2 = build_initial_state("henry_vi")
    force_d6(3)
    # rating 3 -> 3 <= 3 -> success (boundary)
    r2 = influence.check_influence(s2, "york", "yorkist", loyalty_mod=3 - _base_rating(s2))
    assert r2["rating"] == 3 and r2["success"] is True


# ------------------------------------------------------------- spend formula
@pytest.mark.parametrize("extra,way,disc,expected", [
    (0, 0, 0, 1),     # base only
    (1, 0, 0, 2),     # +extra
    (0, 2, 0, 3),     # +way cost
    (1, 2, 1, 3),     # 1 + 1 + 2 - 1
    (0, 0, 10, 0),    # discount drives spend to the 0 floor (clamp)
])
def test_spend_formula(force_d6, extra, way, disc, expected):
    s = build_initial_state("henry_vi")
    force_d6(3)
    r = influence.check_influence(s, "york", "yorkist",
                                  extra_spend=extra, way_cost=way, discount=disc)
    assert r["spent"] == expected


# ------------------------------------------------------------- rating bonus map
@pytest.mark.parametrize("extra,bonus", [(0, 0), (1, 1), (3, 2)])
def test_extra_spend_rating_bonus(force_d6, extra, bonus):
    s = build_initial_state("henry_vi")
    force_d6(3)
    base = _base_rating(s)
    r = influence.check_influence(s, "york", "yorkist", extra_spend=extra)
    assert r["rating"] == base + bonus


def test_invalid_extra_spend_rejected():
    s = build_initial_state("henry_vi")
    with pytest.raises(IllegalAction) as e:
        influence.check_influence(s, "york", "yorkist", extra_spend=2)
    assert e.value.code == "bad_extra_spend"
