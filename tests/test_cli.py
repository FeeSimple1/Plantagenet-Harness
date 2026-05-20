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
