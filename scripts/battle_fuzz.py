"""Dedicated battle decision-payload fuzzer (least-verified surface).

The mass sweep (sweep_harness.py) cannot soundly fuzz battle ``decisions``:
capability-dependent keys (vanguard/swift/culverins/spoils/...) are validated at
reaction-resolution, a *later* step, so a one-step probe can't accept/reject
them. This harness instead resolves each fuzzed battle FULLY on a fork: apply the
combat-triggering move with a random (type-correct, value-wild) decisions
payload, then drive the whole reaction sequence off legal_moves until it settles.

Sound oracle: an IllegalAction ANYWHERE in the forked resolution means the
decision combo was illegal -> discard (not a bug). A non-IllegalAction exception
(crash) or a board-invariant break after the battle fully resolves IS a bug --
a robust engine must reject bad choices gracefully, never crash or corrupt state.
The real game advances with the plain move (default decisions) to reach the next
battle; only the forks see fuzz, so the run stays on a legal trajectory.
"""

from __future__ import annotations

import argparse
import random
import traceback
from typing import Any

from plantagenet import actions, invariants, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war

_BATTLE_TRIGGERING = {"march", "approach", "sail", "intercept"}
_FLOW_ENDERS = {"end_muster", "end_activation", "end_campaign", "pass", "react"}


def _mustered(state, side):
    return [lid for lid, v in state.lords.items()
            if v.side == side and v.status == "mustered"]


def _rand_decisions(state, side, rng):
    own = _mustered(state, side)
    opp = _mustered(state, actions.other_side(side))
    both = own + opp
    sides = [side, actions.other_side(side)]
    d: dict[str, Any] = {}

    def maybe(p, key, val):
        if rng.random() < p:
            d[key] = val

    def sub(pool, lo=0, hi=2):
        if not pool:
            return []
        return rng.sample(pool, k=rng.randint(lo, min(hi, len(pool))))

    maybe(0.5, "valour", rng.random() < 0.5)
    maybe(0.5, "swift_maneuver_end", rng.random() < 0.5)
    maybe(0.3, "flee", sub(own))
    maybe(0.2, "flee_rounds", {lid: rng.randint(1, 3) for lid in sub(own)})
    maybe(0.2, "absorb_order", rng.sample(both, k=len(both)) if both else [])
    maybe(0.2, "absorb_lords", sub(own))
    maybe(0.2, "engagement_order", sub(both, 0, 3))
    maybe(0.2, "culverins", sub(own))
    maybe(0.2, "leeward", sub(sides, 0, 2))
    maybe(0.2, "caltrops", sub(sides, 0, 2))
    maybe(0.15, "vanguard", rng.choice(own) if own else None)
    maybe(0.15, "swift_maneuver", rng.choice(sides))
    maybe(0.15, "ravine", rng.choice(opp) if opp else None)
    maybe(0.15, "regroup", rng.choice(own) if own else None)
    maybe(0.15, "final_charge", sub(own))
    maybe(0.15, "spoils_to", rng.choice(own) if own else "pool")
    maybe(0.1, "patrick", True)
    maybe(0.1, "warden", True)
    maybe(0.1, "talbot", True)
    maybe(0.1, "escape_ship", sub(own))
    maybe(0.1, "flank_attack", rng.random() < 0.5)
    maybe(0.1, "intercept_group", sub(own))
    return d


def _resolve_fork(fork, rng, guard=120):
    """Drive a forked state's reaction sequence to settlement off legal_moves.
    Randomly play or decline offered reactions (extra coverage). Raises whatever
    apply_action raises (caller classifies)."""
    n = 0
    while fork.pending and n < guard:
        rmoves = legal_moves.legal_moves(fork)
        if not rmoves:
            break
        actions.apply_action(fork, rng.choice(rmoves))
        n += 1


class Stats:
    def __init__(self, bugs_file=None):
        self.games = self.battles = self.trials = self.illegal = 0
        self.bugs: list[str] = []
        self.bugs_file = bugs_file

    def bug(self, msg):
        self.bugs.append(msg)
        if self.bugs_file:
            with open(self.bugs_file, "a") as fh:
                fh.write(msg + "\n")


def _fuzz_battle(state, mv, rng, stats, trials):
    side = mv["side"]
    stats.battles += 1
    for _ in range(trials):
        stats.trials += 1
        fork = state.model_copy(deep=True)
        dec = _rand_decisions(fork, side, rng)
        cand = {**mv, "decisions": dec}
        try:
            actions.apply_action(fork, cand)
            _resolve_fork(fork, rng)
        except IllegalAction:
            stats.illegal += 1
            continue
        except Exception:
            stats.bug(f"[CRASH] move={mv} decisions={dec}\n  "
                      + traceback.format_exc().splitlines()[-1])
            continue
        bad = invariants.board_invariant_violations(fork)
        if bad:
            stats.bug(f"[INVARIANT] move={mv} decisions={dec}\n  {bad}")


def play_and_fuzz(sid, seed, stats, trials, budget=12000):
    rng = random.Random(seed * 2654435761 & 0xFFFFFFFF)
    state = build_initial_state(sid, seed=seed)
    stats.games += 1
    for _ in range(budget):
        if state.phase == "over":
            if state.grand_scenario and (state.victory or {}).get("result") in (
                    "lancastrian", "yorkist"):
                try:
                    state = renew_war(state)
                    continue
                except IllegalAction:
                    return
            return
        moves = legal_moves.legal_moves(state)
        if not moves:
            return
        # Prefer combat-triggering marches into enemy contact (aggressor drive).
        battle_moves = [m for m in moves if m.get("type") in _BATTLE_TRIGGERING
                        and m.get("to") and actions.enemy_lord_at(state, m["to"], m["side"])]
        if battle_moves and rng.random() < 0.85:
            mv = rng.choice(battle_moves)
            _fuzz_battle(state, mv, rng, stats, trials)
            # advance real game with the plain move (default decisions)
            try:
                actions.apply_action(state, mv)
                _resolve_fork(state, rng)
            except IllegalAction:
                return
            continue
        # otherwise normal progress
        enders = [m for m in moves if m["type"] in _FLOW_ENDERS]
        others = [m for m in moves if m["type"] not in _FLOW_ENDERS]
        mv = (rng.choice(enders) if enders and (not others or rng.random() < 0.5)
              else rng.choice(others or enders))
        if mv.get("type") == "build_plan" and "plan" not in mv:
            n = mv["cards_required"]
            lords = _mustered(state, mv["side"])
            plan = [{"lord": x} for x in lords][:n] + [{"pass": True}] * max(0, n - len(lords))
            mv = {"type": "build_plan", "side": mv["side"], "plan": plan[:n]}
        elif mv.get("type") == "play_event" and "decisions" not in mv:
            from tests._helpers import fill_event_decisions
            mv = {**mv, "decisions": fill_event_decisions(state, mv["card"], mv["side"])}
        try:
            actions.apply_action(state, mv)
        except IllegalAction:
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="wars_of_the_roses")
    ap.add_argument("--seeds", type=int, default=40)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--bugs-file", default=None)
    args = ap.parse_args()
    stats = Stats(bugs_file=args.bugs_file)
    for seed in range(args.start, args.start + args.seeds):
        play_and_fuzz(args.scenario, seed, stats, args.trials)
    print(f"games={stats.games} battles={stats.battles} trials={stats.trials} "
          f"illegal_combos={stats.illegal} bugs={len(stats.bugs)}")
    for b in stats.bugs[:20]:
        print("\n" + b)


if __name__ == "__main__":
    main()
