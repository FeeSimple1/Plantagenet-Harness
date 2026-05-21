# Plantagenet Harness

Python harness for GMT's *Plantagenet: Cousins' War* (Levy & Command
series). Holds full game state, validates and resolves every rules-defined
action, runs Battle engagements automatically, rolls all dice from a
seeded RNG, and exposes a structured interface designed to be consumed by
an LLM playing one or both sides.

The detailed project specification is in [`BRIEF.md`](BRIEF.md). This file
is an operator's guide to the codebase as it stands.

> Scope note: this harness is for **Plantagenet only**. The Nevsky-Harness
> was a structural template; no Nevsky rules or data are included here.

## Status

**Phase 2 (done): Levy Muster mechanics.** The harness now enforces the
Levy Muster segment (3.4): `parley`, `levy_lord`, `levy_vassal`,
`levy_transport`, and `levy_troops`, each gated by the Influence check (1.4.2) and Lordship,
with `legal-moves` enumerating the active side's options and `do` executing
actions. Turn order is "Rebel then King's" (3.1-3.4). Two Muster actions are
(`levy_troops` uses the Strongholds table, D-004, and Depletes/Exhausts the
Locale.) The one remaining deferred Muster action is `levy_capability`
(Arts of War cards, Phase 4).

**Phase 3a-i (current): Campaign backbone.** The Campaign turn now runs:
`begin_campaign` -> Plan (4.1, season-sized) -> Activation (4.2, Rebel/King
alternating) with the `forage` (4.6.2) and `pass` (4.6.5) Commands and Feed
(4.7) -> `end_campaign` (4.8): Tides of War scoring (4.8.1), Victory check
(4.8.3/5.x), Grow (4.8.4), Waste (4.8.5), and advance to the next Turn's
Levy. Deferred to 3a-ii: the movement/route Commands `march`/`sail`/
`supply`/`tax`/campaign-`parley`, and Pay (3.2) on Turn rollover; combat is
Phase 3b. See the phasing plan in `BRIEF.md`.

## Where things are

- `src/plantagenet/` — the harness package.
  - `static_data.py` — loaders for the JSON reference data (cached).
  - `data_integrity.py` — cross-reference validation of the static data.
  - `rng.py` — the seeded dice (`DiceRoller`).
  - `errors.py` — `IllegalAction` (carries a stable `code`) and friends.
  - `state.py` — the Pydantic `GameState` model (save/load, dice wiring).
  - `scenarios.py` — `build_initial_state(scenario_id, seed)` loader.
  - `render.py` — summary / verbose / focused renderings.
  - `influence.py` — Influence points and the Influence check (1.4.x).
  - `actions.py` — Levy Muster action handlers + dispatcher (3.4).
  - `legal_moves.py` — phase-aware enumerator (Levy Muster + Campaign).
  - `campaign.py` — Campaign flow, Forage/Feed, and End-Campaign (Tides of
    War, Grow, Waste, Victory, Turn advance).
  - `cli.py` — the CLI. `new`, `state`, `legal-moves`, `do`, and the data
    commands work; `pending`/`history` are stubs until their phase.
  - `data/static/` — `forces.json`, `locales.json`, `ways.json`,
    `lords.json`, `vassals.json`, `exile_boxes.json`.
  - `data/scenarios/` — one file per scenario plus `index.json`.
  - `data/schema/` — `state.schema.json` (state-file schema stub).
  - `llm/` — LLM-consumer interface (populated in later phases).
- `reference/` — curated `.txt` references (Arts of War, Lords & Vassals,
  Map, Scenario, Errata) — the FIRST stop for rules questions.
- `source/` — Rules of Play, Background Book, and Errata PDFs.
- `scripts/` — data builders (`build_map_data.py`, `build_scenarios.py`,
  `build_grand_scenario.py`); agents and sweeps arrive in later phases.
- `tests/` — pytest suite; Phase 0 covers data integrity and the CLI.

## How to run things

```
pip install -e ".[dev]"
PYTHONPATH=src pytest -q
```

Inspect the static data without game logic:

```
PYTHONPATH=src python -m plantagenet.cli scenarios     # list scenarios
PYTHONPATH=src python -m plantagenet.cli data-check     # validate data
```

Start a game and inspect it:

```
PYTHONPATH=src python -m plantagenet.cli new henry_vi --seed 1 --out game.state.json
PYTHONPATH=src python -m plantagenet.cli state game.state.json                       # summary
PYTHONPATH=src python -m plantagenet.cli state game.state.json --mode verbose         # full JSON
PYTHONPATH=src python -m plantagenet.cli state game.state.json --mode focused --focus calendar
```

Regenerate the data files from the references (if a reference changes):

```
PYTHONPATH=src python scripts/build_map_data.py
PYTHONPATH=src python scripts/build_scenarios.py
PYTHONPATH=src python scripts/build_grand_scenario.py
```

## Documentation map

- [`BRIEF.md`](BRIEF.md) — project specification, sources priority,
  ambiguity policy, phasing.
- [`ACTIONS.md`](ACTIONS.md) — the JSON action grammar (grows per phase).
- [`RULES_DECISIONS.md`](RULES_DECISIONS.md) — adjudicated rules calls
  (permanent).
- [`RULES_QUESTIONS.md`](RULES_QUESTIONS.md) — open rules questions.
- [`SMOKE_TEST_FINDINGS.md`](SMOKE_TEST_FINDINGS.md) — append-only bug log.
- [`CROSS_PROJECT_LESSONS.md`](CROSS_PROJECT_LESSONS.md) /
  [`FUTURE_PROJECTS_LESSONS.md`](FUTURE_PROJECTS_LESSONS.md) — audit-pattern
  catalogs ported from the Nevsky project (engineering patterns only; the
  Nevsky-specific examples are marked as illustrative).

## Authoritative sources

Per `BRIEF.md`: the Rules of Play and the Errata & Clarification trump any
other input; then the curated `.txt` references (esp. the Arts of War
Reference Tips); then the Background Book (examples, not a standalone rules
source). Stay strictly within the repo files; the game's history is theme,
not subject matter.
