"""Enumerator/handler round-trip sweep for the Levy Muster segment.

For every move the enumerator emits in a reachable state, replay it
through `apply_action` on a deep-copied snapshot and assert it is NOT
rejected with IllegalAction. This is the round-trip discipline from
CROSS_PROJECT_LESSONS: the enumerator and handlers must agree, so the
consumer never sees a phantom-legal move.

Then advance one move under a first-listed policy and repeat, across all
scenarios with Levy play, until the Levy completes.
"""

from __future__ import annotations

import sys

from plantagenet import actions, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def sweep_scenario(scenario_id: str, seed: int = 1) -> list[str]:
    findings: list[str] = []
    state = build_initial_state(scenario_id, seed=seed)
    if state.phase != "levy":
        return findings
    steps = 0
    while state.levy_step == "muster" and steps < 500:
        moves = legal_moves.legal_moves(state)
        for mv in moves:
            snap = state.model_copy(deep=True)
            try:
                actions.apply_action(snap, mv)
            except IllegalAction as e:
                findings.append(f"{scenario_id}: enumerator emitted illegal {mv['type']} "
                                f"-> {e.code} ({mv})")
        # advance under a simple policy: take the first non-end move, else end.
        nxt = next((m for m in moves if m["type"] != "end_muster"), moves[-1])
        actions.apply_action(state, nxt)
        steps += 1
    return findings


def main() -> int:
    all_findings: list[str] = []
    for sid in static_data.list_scenario_ids():
        if sid == "bosworth":
            continue  # battle-only, no Levy
        for seed in (1, 2, 3):
            all_findings.extend(sweep_scenario(sid, seed))
    if all_findings:
        print(f"{len(all_findings)} round-trip findings:")
        for f in all_findings:
            print("  ", f)
        return 1
    print("Round-trip sweep clean: every enumerated Levy move applied without IllegalAction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
