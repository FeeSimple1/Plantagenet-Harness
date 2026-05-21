"""Command-line interface for the Plantagenet harness.

Phase 0 wires up the command skeleton and the data-inspection commands
that work without game logic. Commands that require the state model and
rules engine (``new``, ``state``, ``legal-moves``, ``do``, ``pending``,
``history``) are present as stubs so the grammar is fixed early; they
raise a clear "not yet implemented" message until their phase lands.

The action grammar for ``do`` is documented in ACTIONS.md as it grows.
"""

from __future__ import annotations

import json

import typer

from plantagenet import __version__, static_data

app = typer.Typer(
    add_completion=False,
    help="Harness for GMT's Plantagenet: Cousins' War.",
    no_args_is_help=True,
)

_NOT_YET = "not yet implemented — arrives in a later phase (see BRIEF.md)"


@app.command()
def version() -> None:
    """Print the harness version."""
    typer.echo(f"plantagenet-harness {__version__}")


@app.command()
def scenarios() -> None:
    """List the scenario ids that can be passed to ``new``."""
    for sid in static_data.list_scenario_ids():
        scn = static_data.load_scenario(sid)
        typer.echo(f"{sid:24s} {scn.get('title', '')}")


@app.command("data-check")
def data_check() -> None:
    """Load and cross-validate all static data; report a summary.

    Phase 0 sanity command: confirms the reference data files parse and
    that cross-references (Seats -> Locales, Ways endpoints, scenario
    Lords) resolve. The same checks are asserted in the test suite.
    """
    from plantagenet import data_integrity

    report = data_integrity.check_all()
    typer.echo(json.dumps(report, indent=2))
    if report["errors"]:
        raise typer.Exit(code=1)


# --- game-logic command stubs (grammar fixed now, behavior later) ---


@app.command()
def new(scenario: str, seed: int = 1, out: str = "game.state.json") -> None:
    """Initialize a state file from a scenario."""
    from plantagenet import scenarios
    from plantagenet.errors import DataError

    valid = static_data.list_scenario_ids()
    if scenario not in valid:
        typer.echo(f"unknown scenario {scenario!r}; choose from: {', '.join(valid)}")
        raise typer.Exit(code=1)
    try:
        state = scenarios.build_initial_state(scenario, seed=seed)
    except DataError as e:
        typer.echo(f"failed to build scenario: {e}")
        raise typer.Exit(code=1) from e
    state.save(out)
    typer.echo(f"Initialized {scenario!r} (seed {seed}) -> {out}")


@app.command()
def state(file: str, mode: str = "summary", focus: str | None = None) -> None:
    """Render current state: summary | verbose | focused.

    Use ``--mode focused --focus <lord_id|locale_id|calendar|influence>``
    for a focused view.
    """
    from plantagenet import render
    from plantagenet.state import GameState

    gs = GameState.load(file)
    if mode == "summary":
        typer.echo(render.render_summary(gs))
    elif mode == "verbose":
        typer.echo(render.render_verbose(gs))
    elif mode == "focused":
        if not focus:
            typer.echo("--focus is required for focused mode "
                       "(a lord id, locale id, 'calendar', or 'influence')")
            raise typer.Exit(code=1)
        typer.echo(render.render_focused(gs, focus))
    else:
        typer.echo(f"unknown mode {mode!r}; use summary | verbose | focused")
        raise typer.Exit(code=1)


@app.command("legal-moves")
def legal_moves(file: str, side: str | None = None) -> None:
    """Enumerate legal actions for the active player. (Phase 2+)"""
    raise typer.Exit(_stub("legal-moves"))


@app.command()
def do(file: str, action: str) -> None:
    """Execute a submitted JSON action. (Phase 2+)"""
    raise typer.Exit(_stub("do"))


@app.command()
def pending(file: str) -> None:
    """Show pending sub-decisions and who owes a response. (Phase 3b+)"""
    raise typer.Exit(_stub("pending"))


@app.command()
def history(file: str, n: int = 10) -> None:
    """Show the last N actions and results. (Phase 1+)"""
    raise typer.Exit(_stub("history"))


def _stub(name: str) -> str:
    return f"`{name}` is {_NOT_YET}"


if __name__ == "__main__":
    app()
