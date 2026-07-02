"""Cross-process trajectory determinism: a game played from (scenario, seed)
must not depend on PYTHONHASHSEED.

Two prior bugs of this class: battle dice application followed set-ordered
``_TROOP_TYPES`` (fixed 2026-07-01b), and Tax/Supply/Parley command moves were
emitted in set order (fixed 2026-07-01d), so the random policy's index-based
choice -- and with it the whole trajectory -- varied by process. In-process
tests cannot catch this (the hash seed is fixed per process), so this test
replays the same seeded game in two subprocesses with different hash seeds
and requires identical move-by-move trajectories and final state.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DRIVER = """
import importlib.util, json, random, sys
spec = importlib.util.spec_from_file_location("smoke", "tests/test_full_game_smoke.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from plantagenet import actions, legal_moves
from plantagenet.scenarios import build_initial_state

rng = random.Random(2)
state = build_initial_state("henry_vi", seed=2)
for step in range(250):
    if state.phase == "over":
        break
    moves = legal_moves.legal_moves(state)
    if not moves:
        break
    mv = m._pick(moves, rng)
    if mv.get("type") == "build_plan" and "plan" not in mv:
        mv = m._fill_plan(state, mv)
    elif mv.get("type") == "play_event" and "decisions" not in mv:
        mv = {**mv, "decisions": m.fill_event_decisions(state, mv["card"], mv["side"])}
    print(step, json.dumps(mv, sort_keys=True, default=str))
    actions.apply_action(state, mv)
print("FINAL", state.model_dump_json())
"""


def _run(hashseed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=hashseed,
               PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT)]))
    r = subprocess.run([sys.executable, "-c", DRIVER], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout


def test_seeded_trajectory_is_hashseed_independent():
    assert _run("0") == _run("1")
