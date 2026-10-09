"""Historical seed-181 replay preserves its valid prefix and rejects its Pay bug.

The original 347-action recording remains unchanged. Steps 1-68 still match the
current engine's recorded oracle fields. At step 69 (Pay, rule 3.2.1), Henry VI
owns one Coin but needs three; Somerset owns none and needs one. Both are at
exhausted London. Henry must spend his Coin on his own Troops even partially,
leaving no surplus to Share, so both must Disband. The old engine incorrectly
spent Henry's Coin on Somerset; its step-73 Somerset action is consequently
illegal under the corrected rules.

This defect is neither waived nor reproduced through an engine accommodation.
The full historical recording must be rejected. Current full-game smoke tests
provide end-to-end validation of games played under the corrected rules.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _replay(*args):
    return subprocess.run(
        [sys.executable, "scripts/replay_log.py",
         "tests/data/grand_selfplay_seed181_log.md", *args],
        cwd=ROOT, capture_output=True, text=True, timeout=120)


def test_recorded_grand_selfplay_valid_prefix_replays_exactly():
    """Rules 3.1-4.8: every recorded oracle before corrected Pay still matches."""
    result = _replay("--through", "68")
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert "replayed 68 actions, 0 divergences" in result.stdout
    assert "WAIVED" not in result.stdout
    assert "step 69" not in result.stdout


def test_full_historical_recording_rejected_at_corrected_pay():
    """Rule 3.2.1: own-mat partial Pay makes the old step-69 outcome impossible."""
    result = _replay()
    assert result.returncode == 2, result.stdout[-2000:] + result.stderr[-2000:]
    assert ("step 69: DIVERGE unpaid_disbanded ['henry_vi', 'somerset_1'] "
            "!= ['henry_vi']") in result.stdout
    assert "step 73: NO MATCH" in result.stdout
    assert "WAIVED" not in result.stdout
    assert "replayed 347 actions, 0 divergences" not in result.stdout
