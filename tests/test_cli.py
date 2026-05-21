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


def test_game_command_stub_is_not_yet_implemented():
    result = runner.invoke(app, ["do", "game.state.json", "{}"])
    assert result.exit_code != 0
    assert "not yet implemented" in result.stdout


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
