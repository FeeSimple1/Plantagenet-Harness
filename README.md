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

**Feature-complete engine.** The harness plays *Plantagenet* end-to-end through
the agent-facing interface (`legal_moves` -> `apply_action`), rolling all dice
from a seeded RNG:

- **Levy (3.x):** Arts of War draw with immediate/Held Event resolution, Pay
  (3.2), and the full Muster (Parley, Lord, Vassal, Transport, Troops,
  Capability).
- **Campaign (4.x):** Plan (4.1), alternating Activation (4.2), and every
  Command — March (4.3, incl. Group March, Approach/Intercept into enemy
  contact), Sail (4.6.1), Supply (4.5), Tax (4.6.3), Forage (4.6.2),
  Parley (4.6.4), Pass — plus Feed (4.7) and End-Campaign (4.8): Tides of War
  scoring, Victory check, Grow, Waste, Turn advance.
- **Combat (4.3.5 / 4.4):** the multi-Lord Battle engine with Approach/Exile,
  battle-reaction timing windows, and the Capability/Held-Event/Valour decision
  payload.
- **All 74 Arts of War cards** (both the Event and Capability faces) are coded.
- **Succession (6.2)** and the three-War **Wars of the Roses grand scenario**
  resolve through all Renewed-War transitions, alongside the standalone and
  battle-only (Bosworth) scenarios.

Verification: 586 passing tests (`pytest`), ruff clean, continuous board-invariant
checks, and two reusable bug-finding harnesses (`scripts/sweep_harness.py`,
`scripts/battle_fuzz.py`). See [`SMOKE_TEST_FINDINGS.md`](SMOKE_TEST_FINDINGS.md)
for the full audit/bug log and [`CHANGELOG.md`](CHANGELOG.md) for milestones.

Known gaps (not bugs): the engine has not yet been validated move-by-move against
an external recorded game (the highest-value test still outstanding); a few rules
calls were adjudicated rather than designer-confirmed (see
[`RULES_DECISIONS.md`](RULES_DECISIONS.md) / [`RULES_QUESTIONS.md`](RULES_QUESTIONS.md));
and `mypy --strict` is configured but not yet clean.

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
  - `campaign.py` — Campaign flow, Forage/Feed/Pillage/Disband, End-Campaign
    (Tides of War, Grow, Waste, Victory, Turn advance).
  - `commands.py` — March, Sail, Supply, Tax, campaign Parley (4.3, 4.5, 4.6.1-.4).
  - `pay.py` — Levy Pay step: Pay Troops/Lords/Vassals (3.2).
  - `battle.py` — Approach/Exile (4.3.5) and the multi-Lord Battle engine (4.4).
  - `cli.py` — the CLI: `new`, `state`, `legal-moves` (with `--validated`),
    `do`, `pending`, `history`, and the data commands.
  - `data/static/` — `forces.json`, `locales.json`, `ways.json`,
    `lords.json`, `vassals.json`, `exile_boxes.json`.
  - `data/scenarios/` — one file per scenario plus `index.json`.
  - `data/schema/` — `state.schema.json` (state-file schema stub).
  - `llm/` — LLM-consumer interface.
- `reference/` — curated `.txt` references (Arts of War, Lords & Vassals,
  Map, Scenario, Errata) — the FIRST stop for rules questions.
- `source/` — Rules of Play, Background Book, and Errata PDFs.
- `scripts/` — data builders (`build_map_data.py`, `build_scenarios.py`,
  `build_grand_scenario.py`) and bug-finding sweeps (`sweep_harness.py`,
  `battle_fuzz.py`).
- `tests/` — pytest suite (586 tests) covering the full engine, plus
  property-based conservation tests and the fuzz-finding regressions.

## How to run things

```
pip install -e ".[dev]"   # Python 3.10+
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
- [`CHATGPT_PLAY_PORTING_GUIDE.md`](CHATGPT_PLAY_PORTING_GUIDE.md) — how to
  let ChatGPT play the harness in its sandbox for a bug hunt.
- [`STRATEGY.md`](STRATEGY.md) — gameplay strategy notes from AI
  playthroughs (impressions, not doctrine; grounded in the victory rules).
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
