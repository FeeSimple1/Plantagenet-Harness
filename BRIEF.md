# Plantagenet Harness — Project Specification

## Goal

A Python harness for *Plantagenet: Cousins' War* (GMT Games, Levy &
Command series). The harness holds full game state, validates and
executes all rules-defined actions, runs Battle engagements
automatically, rolls all dice, and exposes a structured interface
designed to be consumed by an LLM (Claude or ChatGPT) playing one or
both sides.

The user supplies strategic judgment via the LLM. The user adjudicates
rules ambiguities surfaced during development. The harness supplies
everything else: state, rules enforcement, mechanical resolution.

This is a private project. Code quality should be good enough for the
user to maintain, not for external readers.

> **This harness is for Plantagenet only.** The Nevsky-Harness was used
> as a structural template for how to shape the project. No Nevsky rules,
> data, card text, or map content are carried into this harness. Where a
> ported document references Nevsky, the reference is illustrative of an
> engineering pattern, not an input to Plantagenet's rules.

## Authoritative Sources (Priority Order)

1. **Rules of Play** (`source/Plantagenet_Rules_Final_web.pdf`) and the
   **Errata & Clarification** (`reference/Plantagenet Errata &
   Clarification.txt`, also `source/plantagenet_errata&clarification.pdf`).
   Where the Rules of Play or the Errata & Clarification contradict any
   other input, they trump it. The Errata is verified equivalent between
   its `.txt` and PDF forms (the `.txt` spells out two red-strikethrough
   deletions as "[Deleted from original]" and transcribes the Action
   Requirements Summary table that is a graphic in the PDF).
2. The curated **reference `.txt` files** in `reference/` (Arts of War
   Reference, Lords and Vassals, Map, Scenario, Forces info). These are
   designer-clarified distillations and are the FIRST stop for any
   question about card text, capability mechanics, or rule
   interpretation. The Tips paragraphs in the Arts of War Reference are
   designer-clarified text and resolve most apparent ambiguities.
3. **Background Book** (`source/Plantagenet_Bkgnd-Book_Final_web.pdf`) —
   Quickstart, examples of play, and the Arts of War notes the AoW
   Reference is drawn from. Examples are not a rules source on their own;
   useful for clarifying examples.

PDFs in the repo's `source/` directory ARE readable; treat them as
ordinary inputs.

When sources conflict, higher priority wins. For Q-NNN consultation, the
FIRST step is always the relevant `.txt` reference's section. Skipping
that step is a process bug.

## Scope of Inquiry — Hard Constraint

This is a software project to encode a board game's rules. It is NOT a
historical research project. The game's setting in the 15th-century Wars
of the Roses is theme, not subject matter.

### Sources you may consult

- The repo's reference `.txt` files.
- The repo's PDFs (Rules of Play, Background Book, Errata).
- Standard Python / library documentation needed to write the code.
- Files the user has placed in the repo.

### Sources you may NOT consult without explicit user instruction

- Wikipedia, encyclopedias, or any general-knowledge history of the
  period, persons (Plantagenet, Neville, Tudor, Beaufort…), places, or
  battles (Towton, Bosworth, Tewkesbury…).
- Academic or popular history sources, even when the rulebook references
  them.
- Other GMT games or board-game databases (BoardGameGeek, ConsimWorld)
  for comparative rules interpretation. **This includes Nevsky** — the
  template harness — for anything beyond engineering patterns.
- Your own pre-existing knowledge of the Wars of the Roses or of these
  game titles. If you find yourself "remembering" a fact, treat it as if
  it doesn't exist; consult the repo files instead.
- Web searches of any kind related to the game's subject matter.

### Why this matters

Proper names (Henry VI, Warwick, March, Fauconberg, Harlech, Calais) are
tokens the rules use to identify specific game pieces with specific game
stats. Their historical referents are irrelevant. Encoding any historical
"fact" as game logic is a bug, not a feature.

Use proper names exactly as the rules use them, for state tracking, code
identifiers, file names, and displays. Do not gloss them with historical
context.

## Rules Accuracy Trumps Simplification — HARD CONSTRAINT

Where the rules are clear, the harness MUST implement them faithfully.
Simplifications, approximations, "Phase N+ deferrals", and convenience
shortcuts are NOT acceptable when the rules are explicit.

The only acceptable reasons to depart from the rules are:
1. The rules are ambiguous (→ Ambiguity Policy / Q-NNN below).
2. The user has explicitly adjudicated a deviation (recorded in
   `RULES_DECISIONS.md` as `[HOUSE RULE]`).

Not acceptable: "easier this way", "Phase N is just a stub", "most games
won't hit this", "the simplification is conservative".

Code comments that say "simplified", "approximated", "deferred", or
similar are flags for audit. Each must trace to a Q-NNN, a `[HOUSE RULE]`,
or a future-phase commitment with an explicit tracking item.

## Completeness — HARD CONSTRAINT

Every rule and aspect of the game covered in the source and reference
documents must be **completely** covered — not just the common cases.
Partial or "good enough" coverage is a defect. Drive coverage from the
reference documents exhaustively (every card, every Command, every Event,
every Capability, every Phase, every scenario), not from whatever an
agent happens to exercise during self-play.

## Ambiguity Policy

Every rule encoded in code must trace to a source. The user is the sole
authority on rules interpretation when sources are silent or unclear.

### Consultation Chain — REQUIRED before logging any question

1. **Curated reference file.** Read the relevant `.txt` section IN FULL
   (Arts of War Reference for card/capability text, Map Reference for
   adjacency, Scenario Reference for setup, etc.). If the answer is
   there, the consultation ends — do not log a question.
2. **Rules of Play, primary section.** Read the cited section in the PDF,
   plus sub-sections.
3. **Rules of Play, related sections.** Follow cross-references.
4. **Background Book examples.** Worked examples often resolve apparent
   ambiguity; they are not rules.
5. **Errata & Clarification.** Check whether the case is addressed.

Only after all five steps are performed and documented should a question
be logged. If the consultation resolves it, encode the answer with a
citation comment and proceed.

### Question Format — REQUIRED fields

Append to `RULES_QUESTIONS.md`: Question ID (Q-NNN), Context, Consultation
log (what was checked at each step, with section numbers/quotes; confirm
no external/historical sources were consulted), What is ambiguous,
Options (≥2 concrete possibilities each with a rules argument), Affects
(files/functions/tests/scenarios), Blocking?.

### Decision Log

When the user answers, MOVE the entry from `RULES_QUESTIONS.md` to
`RULES_DECISIONS.md`, appending the adjudication, any citation, and the
commit hash where it is encoded. Decisions are permanent. `[HOUSE RULE]`
decisions (rules silent) are authoritative and cited like any rule.

## No Agent in the Harness — Hard Constraint

The harness encodes the rules and exposes state. It MUST NOT make
strategic decisions for the consumer. The harness's job:

- Maintain authoritative game state.
- Enforce rules: actions succeed and mutate state or raise
  `IllegalAction` with a code.
- Surface state in forms the consumer can read efficiently.
- Enumerate legal moves with their mechanical effects.
- Compute previews / forecasts on request.

It MUST NOT recommend actions, editorialise about trade-offs, pick
decisions for the consumer, or run an internal action-selecting agent.
Prescriptive language ("use when…", "should", "prefer") in `src/` is a
bug; replace it with a description of the mechanical effect.

Self-play / test driver policies under `tests/` and `scripts/` ARE agents
(necessarily, to stress the engine) but are NOT part of the shipped
harness.

## Game-Specific Notes (Plantagenet)

- **Sides:** Lancastrian (red) and Yorkist (white). Each scenario names
  which side is King and which is Rebel.
- **Forces:** Retinue, Vassal, Men-at-Arms, Longbowman, Militia,
  Mercenaries, Handgunners — each with a Strike profile (melee / archery /
  gun, counts may be fractional) and an Armour protection range. See
  `data/static/forces.json`.
- **Map:** England and Wales. Ways are Road, Highway, and Path (land) plus
  Sea between Ports. Exile boxes: Scotland, France, Ireland, Burgundy
  (Scotland has a one-way land exit to Carlisle/Bamburgh). Calais is a
  Sea-only special stronghold. Regions: South, North, Wales.
- **Influence track** drives Threshold and Scenario-End victory; Campaign
  victory is "no Lords on map". A tie at scenario end goes to the King's
  side (Errata FAQ #5).
- **Scenarios:** Ia Henry VI, Ib Towton, Ic Somerset's Return, II
  Warwick's Rebellion, III My Kingdom for a Horse, III(B) Bosworth
  (battle-only), and the Wars of the Roses grand scenario (Wars I →
  II Y/L → III Y/L) with rank-ordered Heirs and conditional Succession.
- **Special Vassals** (Hastings, Edward Prince of Wales, Montagu,
  Clifford, Thomas Stanley, Trollope) are Mustered via a Capability card,
  not a Levy Vassal action.

## Architecture Requirements

- Python 3.11+.
- A single JSON file holds complete game state; portable across sessions;
  loading fully reconstructs the game.
- Determinism: given a state file and an action, the result is
  deterministic except for dice. Dice use a seeded RNG; the seed/state is
  stored in the state file.
- Two interfaces: a library API and a CLI wrapping it. No graphical
  interface.

## LLM-Consumer Interface — Required Capabilities (target)

`new` (init from scenario), `state` (summary / verbose / focused views),
`legal-moves` (enumerate legal actions for the active player, with
grammar, costs, prerequisites, rule citation), `do` (execute a JSON
action; return a structured result with dice, hits, markers, Influence
changes, and rule citations on errors), `pending` (sub-decisions and who
owes a response), `history`, `save`/`load`. The action grammar is
documented in `ACTIONS.md` as it develops.

## Dice and Mechanical Resolution

The harness rolls all dice; the consumer never does. Every roll is logged
in the action result with context.

## Phasing

Each phase is a separate PR. Do not start the next phase until the
previous PR is merged.

- **Phase 0 (current):** Project skeleton, JSON schema stub for state,
  static reference data (Forces, Locales, Ways, Lords, Vassals, Exile
  boxes), all scenario setup data, basic CLI structure, test framework.
  No game logic; cards are deferred to Phase 4.
- **Phase 1:** State model (Pydantic), scenario loader (all six standalone
  + the Wars of the Roses grand scenario), state display
  (summary/verbose/focused), `state` command.
- **Phase 2:** Levy mechanics — Pay, Disband, Muster, Levy Vassal/Troops/
  Transport/Capability, Parley, Influence checks. `legal-moves` for Levy.
- **Phase 3a:** Campaign simple Commands — March (incl. path), Supply,
  Sail, Forage, Tax, Parley, Pass. Feed/Pay/Disband and the Tides of
  War / Waste cycle. `legal-moves` for these.
- **Phase 3b:** Approach, Avoid Battle, Withdraw, Battle Array and
  resolution (Rounds, missile/melee/gun Strikes, Valour, Flight/Rout).
- **Phase 3c:** Siege-type interactions, Strongholds, and any remaining
  combat edges.
- **Phase 4:** Per-card Arts of War effects (Events and Capabilities) and
  the grand-scenario Succession logic. Until Phase 4, cards are tracked
  as data with effect text; the harness flags when a card in play would
  affect a current action.

## Test Discipline

Every rule encoded in code must have at least one test whose docstring
cites the rule section. A rule without a test does not exist in the
harness. `pytest -v` should read as a list of every rule the harness
claims to implement.

## Commit and PR Workflow

Small, focused commits referencing the rule section or the Q/decision
they resolve. One PR per phase (`phase-N-short-description`). The Cowork
operator has authority to push, pull, commit, open PRs, and merge for
this project (granted by the user, 2026-05-20), mirroring the Nevsky
workflow otherwise.

## Out of Scope

AI opponents / strategy advice, graphical interface, networked play,
distribution. Anything not directly serving "run a Plantagenet game with
state persistence, rules enforcement, and an LLM-friendly interface".
