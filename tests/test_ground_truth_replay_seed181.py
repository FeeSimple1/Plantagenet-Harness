"""Historical seed-181 replay stops at its earliest corrected rule violation.

The original 347-action recording is unchanged. Its first 28 recorded actions
match, but the Turn-2 draw of Y22 needs a target before Lancaster can draw at
step 29. The log never recorded that decision. Do not invent a choice to force
an obsolete playthrough through the current engine. A previously identified
step-69 Pay error remains in the historical record too; it is now unreachable.
The current grand-campaign regression supplies all required choices explicitly.
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
    """Rule 3.1: recorded fields match through the draw that now requests Y22."""
    result = _replay("--through", "28")
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    assert "replayed 28 actions, 0 divergences" in result.stdout
    assert "WAIVED" not in result.stdout
    assert "step 29" not in result.stdout


def test_full_historical_recording_rejected_at_missing_event_choice():
    """Y22: the historical log cannot skip a mandatory player selection."""
    result = _replay()
    assert result.returncode == 2, result.stdout[-2000:] + result.stderr[-2000:]
    assert "step 29: NO MATCH 0 candidates" in result.stdout
    assert "'type': 'draw', 'side': 'lancastrian'" in result.stdout
    assert "WAIVED" not in result.stdout
    assert "replayed 347 actions, 0 divergences" not in result.stdout
