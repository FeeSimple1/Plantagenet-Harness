# ChatGPT plays the Plantagenet Harness — bug-hunt setup

Zip this repo, upload it to a ChatGPT **Project**, and let ChatGPT (GPT-5.x)
play the harness in its own Python sandbox — no API key, no network — while a
baked-in instrumentation layer auto-captures every engine anomaly (illegal
action, crash, stall, broken board invariant). A different model walking
different trajectories is what surfaces bugs the scripted sweeps miss.

This is the harness-agnostic "ChatGPT-plays-your-engine" pattern (the same one
Nevsky used), already **ported and wired** for Plantagenet. The wiring lives in
`scripts/chatgpt_play_helper.py`; this guide explains the contract, the
Plantagenet-specific notes, and the project instructions to paste.

## The model in one paragraph

ChatGPT itself is the player. It runs the harness in its sandbox, calls
`nv.show()` to see the active side's briefing plus a numbered list of legal
actions, decides, calls `nv.apply(N)`, and loops. The helper validates every
offered action against the real executor on a throwaway deep copy, so the model
is never shown an illegal move, and any filtered move is logged as a bug. At the
end, `nv.findings_report()` prints the triage queue you collect. There is no API
driver and no self-play script — ChatGPT is the decision-maker.

## What the harness exposes (the contract — already wired)

The adapter block at the top of `scripts/chatgpt_play_helper.py` maps the
generic contract onto this engine. For the record, the wiring is:

- **scenarios** → `static_data.list_scenario_ids()`.
- **load** → `scenarios.build_initial_state(scenario_id, seed)` (deterministic
  from the seed; fully sets the board, so `setup_actions` is empty).
- **briefing** → `render.render_summary(state)` plus an active-side/phase header.
  The player controls **both** sides, so the full-board summary is correct;
  Plantagenet has no per-side hidden *board* state (drawn-card hands are omitted).
- **legal actions** → `legal_moves.legal_moves(state)`. The engine decides the
  active side itself and each move is a **flat dict** carrying its own `side`
  (e.g. `{"type":"parley","side":"yorkist","by_lord":"york","target":"lynn"}`),
  so the adapter ignores the `side` argument and returns the engine's moves.
- **apply** → `actions.apply_action(state, action)` (mutates in place; raises
  `errors.IllegalAction` on an illegal move — a normal rejection, not a crash).
- **terminal / winner** → `state.phase == "over"` / `state.victory`.
- **deep copy** → `state.model_copy(deep=True)`.
- **invariants** → `invariants.board_invariant_violations(state)` (co-location,
  influence-cap, lord-status, card-zone), stringified.

### The 4.1 Plan (`build_plan`) is a free construction

`build_plan` is the one *templated* action: the player freely chooses which
Mustered Lords to activate. The adapter expands the template into one concrete,
ready-to-apply **default** plan (activate all of that side's Mustered Lords,
padded with Pass to the required card count) so `nv.apply(N)` always works and
is validated. To choose a different plan, the player submits a **raw action
dict**, e.g.

```python
nv.apply({"type":"build_plan","side":"yorkist",
          "plan":[{"lord":"york"}, {"lord":"march"}, {"pass":True}, {"pass":True}]})
```

The number of plan entries must equal the `cards_required` shown on the move
(the `// ...` note on the menu line spells this out, including the side's
Mustered Lord ids).

## §RNG — why the validated palette is safe here

The validated palette deep-copies the state, applies a candidate, and discards
the copy. That is only safe if the RNG can't leak from copy to original.
Plantagenet stores the RNG **in the state** (`seed` + `rng_state`, each roll a
pure function reconstructed via `state.dice()`), so `state.model_copy(deep=True)`
isolates it perfectly. `VALIDATE = True` is correct — leave it on.

## §Invariants

`invariants.board_invariant_violations` runs after every applied action and is
already the engine's full always-on set: the canonical L&C **co-location** check
(no two opposing Mustered Lords share a Locale outside a Stronghold, exempting a
pending Approach), plus influence-marker bounds, lord status/position
consistency, and card-zone uniqueness. Nothing to add.

## Scenarios

`henry_vi`, `towton`, `somersets_return`, `warwicks_rebellion`,
`my_kingdom_for_a_horse`, `bosworth`, `wars_of_the_roses`.

- **Start with `henry_vi`** (the intro War, fewest decisions per turn).
- `wars_of_the_roses` is the **grand** scenario: long, and a decisive War
  victory auto-continues into the next War (the helper calls `renew_war` for
  you and prints a transition line). Good for a deep soak run, not a first run.
- **`bosworth` is battle-only and is NOT playable through this interface yet.**
  The enumerator has no Battle-phase branch — battles are resolved internally by
  command handlers (March/Approach → `battle.resolve_battle`), not offered as
  enumerated actions. Driven through `legal_moves`, Bosworth stalls immediately
  with a `no_legal_moves` finding after `end_muster`. That finding is *correct*
  (it documents the gap); just don't pick Bosworth for a play session. Adding an
  enumerated Battle action is the natural follow-up if you want it playable here.

## Dependencies

The helper's import chain needs only **pydantic** (already present in ChatGPT's
sandbox). `typer` (the CLI dep) is not imported by the helper, so a sandbox
without it is fine. If the sandbox lacks pydantic, `pip install pydantic` in the
tool first.

## Local smoke test (no ChatGPT needed)

Proves the wiring runs end to end and exercises the validator:

```python
import sys; sys.path.insert(0, "src"); sys.path.insert(0, "scripts")
import chatgpt_play_helper as nv
nv.start("henry_vi", seed=1)
for _ in range(200):
    acts = nv.auto()          # fast-forward forced turns, return the next menu
    if not acts: break
    nv.apply(0)               # greedy stand-in for the model
nv.findings_report()
```

A 6-scenario × 3-seed sweep through this helper (every standalone scenario plus
the grand scenario's War transitions) currently comes back with **zero** notable
findings — `bosworth` aside, which stalls as described above.

---

# ChatGPT Project instructions (paste into the Project's custom instructions)

> You are playtesting GMT's *Plantagenet: Cousins' War* (a Levy & Command
> wargame) via a Python rules engine in this project, working in your Python
> tool. Unzip the uploaded repo if needed, then run:
>
> ```python
> import sys; sys.path.insert(0, "src"); sys.path.insert(0, "scripts")
> import chatgpt_play_helper as nv
> nv.start("henry_vi", seed=1)
> ```
>
> Play turn by turn. `nv.show()` prints the active side's briefing and a
> NUMBERED list of legal actions. You control BOTH sides — play each turn to win
> for whichever side is active. Decide, then `nv.apply(N)` to play action number
> N. For a custom March/Campaign Plan, pass a raw dict instead:
> `nv.apply({"type":"build_plan","side":"<side>","plan":[{"lord":"<id>"}, {"pass":true}, ...]})`
> with exactly `cards_required` entries (the menu's `//` note lists the side's
> Mustered Lord ids).
>
> `nv.auto()` fast-forwards purely-forced turns (single legal action) and returns
> the next real menu — call it between decisions to skip boilerplate. `nv.save("game.json")`
> checkpoints; `nv.load("game.json")` restores after a sandbox reset.
>
> Play to win: advance on objectives, Levy troops and capabilities, March,
> Tax/Parley for coin and Favour, keep your Lords supplied, and use special
> capabilities; pass only when it is genuinely the best move. Do NOT pick the
> `bosworth` scenario — it is battle-only and not playable through this
> interface.
>
> The harness auto-records any engine anomaly. Periodically and at the end, run
> `nv.findings_report()` and paste its output back to the maintainer — that list
> is the goal of the exercise.

---

## What you get back

`nv.findings_report()` prints `N total, M notable`. Each notable entry is a real
engine defect to triage:

- `over_enum_filtered` / `illegal_action` — the menu offered a move the executor
  rejects (enumerator/handler asymmetry — the dominant bug class).
- `exception` / `exception_in_probe` — applying an offered move crashed (worse
  than an illegal: a real engine bug).
- `no_legal_moves` — a stall/deadlock (the active side had no legal action).
- `invariant` / `invariant_crash` — an illegal board state slipped through
  (e.g. co-located enemies).

For each, fix the **root** (don't just rely on the validator hiding it) and add
a negative test: assert the enumerator does not *offer* the bad move, not only
that the handler rejects it — matching the round-trip discipline in
`CROSS_PROJECT_LESSONS.md`.

## Tips

- Start with `henry_vi`; even a partial game finds bugs.
- Vary the seed and re-run; try more than one model — different decision policies
  walk different trajectories.
- The sandbox is ephemeral. If it resets, re-run the setup cell or `nv.load()`
  from a checkpoint.
- Long games run slower with validation on (a deep copy per candidate per turn).
  That is fine for interactive play; for a fast headless over-enum sweep, use the
  existing `scripts/roundtrip_sweep.py` / `tests/test_full_game_smoke.py` with
  the board invariants active.
