"""Historical seed-181 replay stops at its earliest corrected rule violation.

The original 347-action recording is unchanged. Its first 27 recorded actions
still match. Step 28 is the first later-Levy draw and was produced before rule
3.1.1's full unused-deck reshuffle was implemented, so the corrected engine
must draw different cards there. Do not rewrite or waive the historical log;
the current full-campaign regression records a complete rules-correct run.
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
    """The pre-fix historical recording remains exact through its first Turn."""
    result = _replay("--through", "27")
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert "replayed 27 actions, 0 divergences" in result.stdout
    assert "WAIVED" not in result.stdout


def test_historical_recording_exposes_old_missing_reshuffle():
    """Rule 3.1.1: the old log diverges at its first later-Levy draw."""
    result = _replay("--through", "28")
    assert result.returncode == 1, result.stdout[-2000:] + result.stderr[-2000:]
    assert "step 28: DIVERGE drawn" in result.stdout
    assert "replayed 28 actions, 1 divergences" in result.stdout


def test_full_historical_recording_cannot_continue_after_correct_draws():
    """The old action stream is invalid once corrected draws change Events."""
    result = _replay()
    assert result.returncode == 2, result.stdout[-2000:] + result.stderr[-2000:]
    assert "step 28: DIVERGE drawn" in result.stdout
    assert "step 30: NO MATCH 0 candidates" in result.stdout
    assert "WAIVED" not in result.stdout
