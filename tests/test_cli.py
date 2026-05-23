"""CLI structure smoke tests (Phase 0)."""

from __future__ import annotations

from typer.testing import CliRunner

from plantagenet.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "plantagenet-harness" in result.stdout


def test_scenarios_lists_all():
    result = runner.invoke(app, ["scenarios"])
    assert result.exit_code == 0
    for sid in ("henry_vi", "bosworth", "wars_of_the_roses"):
        assert sid in result.stdout


def test_data_check_passes():
    result = runner.invoke(app, ["data-check"])
    assert result.exit_code == 0
    assert '"errors": []' in result.stdout


def test_pending_shows_empty_when_no_reaction(tmp_path):
    out = tmp_path / "g.state.json"
    runner.invoke(app, ["new", "henry_vi", "--out", str(out)])
    result = runner.invoke(app, ["pending", str(out)])
    assert result.exit_code == 0
    assert '"pending": []' in result.stdout


def test_history_shows_recent_actions(tmp_path):
    import json as _json
    out = tmp_path / "g.state.json"
    runner.invoke(app, ["new", "henry_vi", "--out", str(out)])
    # An Arts of War draw is a recordable action.
    runner.invoke(app, ["do", str(out), _json.dumps({"type": "draw", "side": "yorkist"})])
    result = runner.invoke(app, ["history", str(out), "--n", "5"])
    assert result.exit_code == 0
    data = _json.loads(result.stdout)
    assert data["total"] >= 1 and data["history"][-1]["action"]["type"] == "draw"


def test_new_and_state_summary(tmp_path):
    out = tmp_path / "g.state.json"
    r1 = runner.invoke(app, ["new", "henry_vi", "--out", str(out)])
    assert r1.exit_code == 0, r1.stdout
    assert out.exists()
    r2 = runner.invoke(app, ["state", str(out)])
    assert r2.exit_code == 0
    assert "Henry VI" in r2.stdout


def test_new_rejects_unknown_scenario(tmp_path):
    r = runner.invoke(app, ["new", "not_a_scenario", "--out", str(tmp_path / "x.json")])
    assert r.exit_code == 1
    assert "unknown scenario" in r.stdout


def test_state_focused_requires_focus(tmp_path):
    out = tmp_path / "g.state.json"
    runner.invoke(app, ["new", "towton", "--out", str(out)])
    r = runner.invoke(app, ["state", str(out), "--mode", "focused"])
    assert r.exit_code == 1
    assert "--focus is required" in r.stdout
