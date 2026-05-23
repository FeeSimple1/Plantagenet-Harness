"""Command-line interface for the Plantagenet harness.

Inspection commands (``version``, ``scenarios``, ``data-check``) work on the
static data; the game-logic commands (``new``, ``state``, ``legal-moves``,
``do``, ``pending``, ``history``) drive and inspect a saved state file.

The action grammar for ``do`` is documented in ACTIONS.md.
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


# --- game-logic commands ---


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
def legal_moves(file: str, validated: bool = False) -> None:
    """Enumerate legal actions for the active player. With ``--validated``, probe
    each move and drop any the handler rejects (logging the over-enumeration)."""
    from plantagenet import legal_moves as lm
    from plantagenet.state import GameState

    gs = GameState.load(file)
    if validated:
        typer.echo(json.dumps(lm.validated_legal_moves(gs), indent=2))
        return
    moves = lm.legal_moves(gs)
    typer.echo(json.dumps({"active_side": gs.active_side, "levy_step": gs.levy_step,
                           "count": len(moves), "moves": moves}, indent=2))


@app.command()
def do(file: str, action: str) -> None:
    """Execute a submitted JSON action and save the updated state."""
    from plantagenet import actions
    from plantagenet.errors import IllegalAction
    from plantagenet.state import GameState

    try:
        parsed = json.loads(action)
    except json.JSONDecodeError as e:
        typer.echo(f"action is not valid JSON: {e}")
        raise typer.Exit(code=1) from e
    gs = GameState.load(file)
    try:
        result = actions.apply_action(gs, parsed)
    except IllegalAction as e:
        typer.echo(json.dumps({"error": {"code": e.code, "message": e.message}}, indent=2))
        raise typer.Exit(code=1) from e
    gs.save(file)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def pending(file: str) -> None:
    """Show any pending reaction(s) and who owes the next response (Q-004)."""
    from plantagenet.state import GameState

    gs = GameState.load(file)
    out: dict = {"pending": gs.pending}
    if gs.pending:
        inter = gs.pending[0]
        offers = inter.get("offers", [])
        idx = inter.get("idx", 0)
        out["trigger"] = inter.get("trigger")
        if idx < len(offers):
            out["awaiting"] = offers[idx]          # the next reactor who owes a `react`
    typer.echo(json.dumps(out, indent=2))


@app.command()
def history(file: str, n: int = 10) -> None:
    """Show the last N actions and their results."""
    from plantagenet.state import GameState

    gs = GameState.load(file)
    shown = gs.history[-n:] if n > 0 else gs.history
    typer.echo(json.dumps({"total": len(gs.history), "shown": len(shown),
                           "history": shown}, indent=2))


if __name__ == "__main__":
    app()
