"""Ground-truth replay: the recorded 347-action grand-scenario self-play
(seed 181, three Wars, two Battles) must replay exactly on the current engine.

This is the dice/draw-path regression the unit suite cannot give: every Arts
of War draw, battle outcome (winner/deaths/disbands), Levy Lord roll, Pay
result, Tides of War tally, and War victory in the log is compared against
the engine's live results while the recorded actions are applied.

Two steps are waived as recorded-run bugs, both confirmed against the
scenario specs and both impossible in the current engine (the old
levy-capability enumerator ignored the War deck's composition):
  - step 117: L4 HERALDS levied in War IIL ("all no-rose EXCEPT L4")
  - step 279: L37 (rose 3) levied in War IIIL (deck adds only L25/L34/L36)
The harness asserts these actions are still NOT offered.

One vintage accommodation: the recording's engine auto-fired the Culverins
Capability for every holder in a Battle; the current engine makes firing an
explicit decision (4.4.1 "may"), so the replay attaches it (--auto-culverins).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_recorded_grand_selfplay_replays_exactly():
    r = subprocess.run(
        [sys.executable, "scripts/replay_log.py",
         "tests/data/grand_selfplay_seed181_log.md",
         "--waive", "117,279", "--auto-culverins"],
        cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "replayed 347 actions, 0 divergences" in r.stdout
