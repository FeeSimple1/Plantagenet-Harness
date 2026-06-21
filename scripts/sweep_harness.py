"""Mass game-sweep + decision-payload fuzz harness (bug-finding gauntlet).

Drives full games through the agent-facing interface (legal_moves ->
apply_action), resolving grand-scenario War transitions. Policies
(random / survival / aggressor / fuzz) reach trajectories random play alone
rarely walks -- late turns, threshold victories, and decision-rich battles.

Bug oracle (sound): every enumerated move WITHOUT extra payload must apply
(round-trip discipline), so an IllegalAction on a *plain* enumerated move, on a
required templated fill, or any non-IllegalAction exception, or a board-invariant
break after a successful apply, is a BUG. An IllegalAction provoked by a *fuzzed*
optional decision payload is NOT a bug -- we fall back to the minimal legal form.

Probing on model_copy(deep=True) is exact: the RNG lives in the state, so the
copy rolls the same dice as the real apply.
"""

from __future__ import annotations

import argparse
import random
import traceback
from dataclasses import dataclass, field
from typing import Any

from plantagenet import actions, invariants, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war

_FLOW_ENDERS = {"end_muster", "end_activation", "end_campaign", "pass", "react"}
_FEED = {"forage", "supply", "tax", "pay"}
_BATTLE_TRIGGERING = {"march", "approach", "sail", "intercept"}


@dataclass
class Bug:
    kind: str
    sid: str
    seed: int
    policy: str
    step: int
    move: dict[str, Any]
    detail: str


@dataclass
class Stats:
    games: int = 0
    steps: int = 0
    completed: int = 0
    transitions: int = 0
    battles: int = 0
    max_turn_box: int = 0
    bugs_file: str | None = None
    bugs: list[Bug] = field(default_factory=list)


def _mustered(state, side):
    return [lid for lid, v in state.lords.items()
            if v.side == side and v.status == "mustered"]


def _minimal_plan(state, mv):
    side, n = mv["side"], mv["cards_required"]
    plan = [{"lord": lid} for lid in _mustered(state, side)][:n]
    while len(plan) < n:
        plan.append({"pass": True})
    return {"type": "build_plan", "side": side, "plan": plan}


def _fuzzed_plan(state, mv, rng):
    side, n = mv["side"], mv["cards_required"]
    lords = _mustered(state, side)
    rng.shuffle(lords)
    k = rng.randint(0, min(len(lords), n))
    plan = [{"lord": lid} for lid in lords[:k]]
    while len(plan) < n:
        plan.append({"pass": True})
    return {"type": "build_plan", "side": side, "plan": plan}


def _fuzz_battle_decisions(state, mv, rng):
    side = mv["side"]
    own = _mustered(state, side)
    enemy = _mustered(state, actions.other_side(side))
    d: dict[str, Any] = {}
    if rng.random() < 0.5:
        d["valour"] = rng.random() < 0.5
    if own and rng.random() < 0.3:
        d["flee"] = rng.sample(own, k=rng.randint(0, min(2, len(own))))
    if own and rng.random() < 0.2:
        d["vanguard"] = rng.choice(own)
    if rng.random() < 0.2:
        d["swift_maneuver"] = rng.choice([side, actions.other_side(side)])
    if own and rng.random() < 0.2:
        d["culverins"] = rng.sample(own, k=rng.randint(0, min(2, len(own))))
    if own and rng.random() < 0.2:
        d["yeomen"] = rng.sample(own, k=rng.randint(0, min(2, len(own))))
    if enemy and rng.random() < 0.2:
        d["spoils_to"] = rng.choice(["pool", "self"])
    return {**mv, "decisions": d} if d else mv


def _event_fill(state, mv):
    from tests._helpers import fill_event_decisions
    return {**mv, "decisions": fill_event_decisions(state, mv["card"], mv["side"])}


def _enrich(state, mv, rng, policy):
    t = mv.get("type")
    if t == "build_plan" and "plan" not in mv:
        if policy == "fuzz" and rng.random() < 0.7:
            return _fuzzed_plan(state, mv, rng), True
        return _minimal_plan(state, mv), False
    if t == "play_event" and "decisions" not in mv:
        return _event_fill(state, mv), False
    # NOTE: battle `decisions` are NOT fuzzed here -- capability-dependent keys
    # (vanguard/swift/culverins/spoils) are validated at reaction-resolution, a
    # later step, so a one-step probe cannot soundly accept/reject them. Battle
    # decision fuzzing lives in scripts/battle_fuzz.py, which resolves the whole
    # battle on a fork (any IllegalAction anywhere -> discard as an illegal combo).
    return mv, False


def _minimal(state, mv):
    t = mv.get("type")
    if t == "build_plan" and "plan" not in mv:
        return _minimal_plan(state, mv)
    if t == "play_event" and "decisions" not in mv:
        return _event_fill(state, mv)
    return mv


def _pick(moves, rng, policy):
    enders = [m for m in moves if m["type"] in _FLOW_ENDERS]
    others = [m for m in moves if m["type"] not in _FLOW_ENDERS]
    if policy == "survival":
        feed = [m for m in others if m["type"] in _FEED]
        if feed and rng.random() < 0.7:
            return rng.choice(feed)
        if enders and rng.random() < 0.5:
            return rng.choice(enders)
        return rng.choice(others or enders)
    if policy == "aggressor":
        fight = [m for m in others if m["type"] in _BATTLE_TRIGGERING]
        if fight and rng.random() < 0.7:
            return rng.choice(fight)
        if others and rng.random() < 0.7:
            return rng.choice(others)
        return rng.choice(enders or others)
    if enders and (not others or rng.random() < 0.55):
        return rng.choice(enders)
    return rng.choice(others or enders)


def _record(stats, bug):
    stats.bugs.append(bug)
    if stats.bugs_file is not None:
        with open(stats.bugs_file, "a") as fh:
            fh.write(f"[{bug.kind}] {bug.sid} seed={bug.seed} policy={bug.policy} "
                     f"step={bug.step}\n  move: {bug.move}\n  detail: {bug.detail}\n")


def _apply_direct(state, candidate, mv, step, sid, seed, policy, fuzzed, stats):
    """Apply a plain (non-fuzzed) enumerated move straight to the real state.
    A raise or invariant break here is a real bug (round-trip discipline)."""
    try:
        actions.apply_action(state, candidate)
    except IllegalAction as e:
        _record(stats, Bug("over_enumeration", sid, seed, policy, step, candidate,
                           f"{e.code}: {e.message}"))
        return None
    except Exception:
        _record(stats, Bug("crash", sid, seed, policy, step, candidate,
                           traceback.format_exc().splitlines()[-1]))
        return None
    bad = invariants.board_invariant_violations(state)
    if bad:
        _record(stats, Bug("invariant", sid, seed, policy, step, candidate, str(bad)))
        return None
    return candidate


def _commit(state, candidate, mv, step, sid, seed, policy, fuzzed, stats):
    if not fuzzed:
        return _apply_direct(state, candidate, mv, step, sid, seed, policy, fuzzed, stats)
    # Fuzzed optional payload: probe on a copy so an illegal choice can be
    # discarded without corrupting the real game (RNG is copied -> exact).
    probe = state.model_copy(deep=True)
    try:
        actions.apply_action(probe, candidate)
    except IllegalAction:
        candidate = _minimal(state, mv)        # fuzz legally rejected -> fall back
        return _apply_direct(state, candidate, mv, step, sid, seed, policy, False, stats)
    except Exception:
        _record(stats, Bug("crash", sid, seed, policy, step, candidate,
                           traceback.format_exc().splitlines()[-1]))
        return None
    bad = invariants.board_invariant_violations(probe)
    if bad:
        _record(stats, Bug("invariant", sid, seed, policy, step, candidate, str(bad)))
        return None
    actions.apply_action(state, candidate)     # probe clean -> commit identical outcome
    return candidate


def play_game(sid, seed, policy, stats, budget=12000):
    rng = random.Random((seed << 8) ^ (hash(policy) & 0xFFFF))
    state = build_initial_state(sid, seed=seed)
    stats.games += 1
    for step in range(budget):
        if getattr(state, "turn_box", 0):
            stats.max_turn_box = max(stats.max_turn_box, state.turn_box)
        if state.phase == "over":
            if state.grand_scenario and (state.victory or {}).get("result") in (
                    "lancastrian", "yorkist"):
                try:
                    state = renew_war(state)
                    stats.transitions += 1
                    continue
                except IllegalAction:
                    stats.completed += 1
                    return state
            stats.completed += 1
            return state
        moves = legal_moves.legal_moves(state)
        if not moves:
            return state
        mv = _pick(moves, rng, policy)
        if mv.get("type") in _BATTLE_TRIGGERING and mv.get("to") and \
                actions.enemy_lord_at(state, mv.get("to"), mv["side"]):
            stats.battles += 1
        candidate, fuzzed = _enrich(state, mv, rng, policy)
        applied = _commit(state, candidate, mv, step, sid, seed, policy, fuzzed, stats)
        stats.steps += 1
        if applied is None:
            return state          # bug recorded; stop this game (state may be corrupt)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="wars_of_the_roses")
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--policies", default="random,survival,aggressor,fuzz")
    ap.add_argument("--bugs-file", default=None)
    args = ap.parse_args()
    policies = args.policies.split(",")
    stats = Stats(bugs_file=args.bugs_file)
    for seed in range(args.start, args.start + args.seeds):
        for pol in policies:
            play_game(args.scenario, seed, pol, stats)
    print(f"scenario={args.scenario} games={stats.games} steps={stats.steps} "
          f"completed={stats.completed} war_transitions={stats.transitions} "
          f"battles_entered={stats.battles} max_turn_box={stats.max_turn_box}")
    if stats.bugs:
        print(f"\n!!! {len(stats.bugs)} BUG(S):")
        seen = set()
        for b in stats.bugs:
            key = (b.kind, b.detail, b.move.get("type"))
            if key in seen:
                continue
            seen.add(key)
            print(f"\n[{b.kind}] {b.sid} seed={b.seed} policy={b.policy} step={b.step}")
            print(f"  move: {b.move}")
            print(f"  detail: {b.detail}")
        print(f"\n(unique signatures: {len(seen)}; total: {len(stats.bugs)})")
    else:
        print("\nNo bugs found.")
    return stats


if __name__ == "__main__":
    main()
