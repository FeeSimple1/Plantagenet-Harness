"""Property-based conservation tests (Hypothesis).

These drive random legal play from Hypothesis-chosen (scenario, seed, depth) and
assert engine invariants that must hold in EVERY reachable state, letting
Hypothesis search and shrink the trajectory space rather than relying on a fixed
seed list.

Conservation laws asserted:

* **Physical one-zone law.** An Arts of War card occupies at most one *physical*
  location at a time: a deck pile (draw/discard/held/set_aside), a Lord's mat
  (a deployed Capability), or the pending-resolution slot. (``active_events`` is
  an effect-marker layer, NOT a physical zone -- ``events.expire_scope``
  deliberately tolerates an active card already sitting in discard -- so it is
  excluded.) This is the law the Y20 succession-duplication bug broke; checked
  here continuously over the whole reachable state space.
* **Board invariants.** ``invariants.board_invariant_violations`` stays empty.
* **No negative troops.** Every force count on every Lord mat is a non-negative
  integer (no arithmetic underflow drains a unit below zero).
"""

from __future__ import annotations

import random
from collections import defaultdict

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from plantagenet import actions, invariants, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war
from tests._helpers import fill_event_decisions

_SCENARIOS = static_data.list_scenario_ids()
_FLOW = {"end_muster", "end_activation", "end_campaign", "pass", "react"}


def _mustered(state, side):
    return [lid for lid, v in state.lords.items()
            if v.side == side and v.status == "mustered"]


def _physical_card_locations(state):
    """(side, card) -> list of physical zone labels it currently occupies."""
    loc: dict[tuple[str, str], list[str]] = defaultdict(list)
    for side, deck in state.decks.items():
        for pile in ("draw", "discard", "held", "set_aside"):
            for c in deck.get(pile, []):
                loc[(side, c)].append(f"deck:{pile}")
    for lid, ls in state.lords.items():
        for c in ls.capabilities:
            loc[(ls.side, c)].append(f"mat:{lid}")
    for e in state.pending_events:
        if e.get("card"):
            loc[(e.get("side"), e["card"])].append("pending_event")
    return loc


def _assert_conservation(state):
    dup = {k: v for k, v in _physical_card_locations(state).items() if len(v) > 1}
    assert not dup, f"card in two physical zones: {dup}"
    assert invariants.board_invariant_violations(state) == []
    for lid, ls in state.lords.items():
        for unit, n in ls.forces.items():
            assert isinstance(n, int) and n >= 0, f"{lid} {unit} count {n!r}"


def _one_random_step(state, rng):
    moves = legal_moves.legal_moves(state)
    if not moves:
        return False
    enders = [m for m in moves if m["type"] in _FLOW]
    others = [m for m in moves if m["type"] not in _FLOW]
    mv = (rng.choice(enders) if enders and (not others or rng.random() < 0.55)
          else rng.choice(others or enders))
    if mv.get("type") == "build_plan" and "plan" not in mv:
        n = mv["cards_required"]
        lords = _mustered(state, mv["side"])
        plan = [{"lord": x} for x in lords][:n] + [{"pass": True}] * max(0, n - len(lords))
        mv = {"type": "build_plan", "side": mv["side"], "plan": plan[:n]}
    elif mv.get("type") == "play_event" and "decisions" not in mv:
        mv = {**mv, "decisions": fill_event_decisions(state, mv["card"], mv["side"])}
    try:
        actions.apply_action(state, mv)
    except IllegalAction:
        return False
    return True


@settings(max_examples=120, deadline=None,
          suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large])
@given(sid=st.sampled_from(_SCENARIOS),
       seed=st.integers(min_value=0, max_value=2**31 - 1),
       depth=st.integers(min_value=0, max_value=200))
def test_conservation_holds_over_random_play(sid, seed, depth):
    rng = random.Random(seed)
    state = build_initial_state(sid, seed=seed)
    _assert_conservation(state)
    for _ in range(depth):
        if state.phase == "over":
            if state.grand_scenario and (state.victory or {}).get("result") in (
                    "lancastrian", "yorkist"):
                try:
                    state = renew_war(state)
                except IllegalAction:
                    break
            else:
                break
        elif not _one_random_step(state, rng):
            break
        _assert_conservation(state)


@settings(max_examples=50, deadline=None)
@given(sid=st.sampled_from(_SCENARIOS),
       seed=st.integers(min_value=0, max_value=2**31 - 1))
def test_initial_state_is_conserved_for_every_scenario(sid, seed):
    _assert_conservation(build_initial_state(sid, seed=seed))
