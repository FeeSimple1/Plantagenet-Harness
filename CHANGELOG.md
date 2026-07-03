# Changelog

All notable changes to the Plantagenet harness are recorded here. Dates are the
date of the change; the project is not formally released, so versions are
internal milestones.

## [Unreleased]

### Added
- Mutation sweep of the eight large modules (2,535 sites): all 777 surviving
  mutants triaged (mutation-results/*.triage.md), 565 killed by 138 new tests;
  89 proven equivalent, 69 low-value, 54 classified open. Suite 658 -> 796.
- Ground-truth replay: `scripts/replay_log.py` replays a recorded playthrough
  log against the current engine, comparing every dice/draw-dependent result;
  the 347-action seed-181 grand-scenario recording replays with 0 divergences
  (two waived vintage bugs, documented) and is pinned as a test.
- CI `typecheck` job: the codebase is now `mypy --strict` clean (626
  annotation errors -> 0; annotation-only edits, behavioral equivalence
  verified by byte-identical full-game final states vs the pre-annotation
  tree under pinned hash seeds).
- Forward traceability: `scripts/extract_clause_index.py` extracts the
  authoritative clause index from the Rules of Play PDF into
  `source/plantagenet_clause_index.tsv` (101 clauses); the traceability matrix
  now lists rulebook clauses with no code citation (9/101, all triaged benign
  in `SMOKE_TEST_FINDINGS.md`), shows each cited clause's rulebook title, and
  flags cited clause numbers absent from the rulebook (annotation typos).
- Deterministic tests for the niche battle branches (Regroup recovery,
  Patrick+Leeward, Norfolk is Late, Swift Maneuver, Warden, Talbot, Vanguard)
  and the general Succession rule; suite 639 -> 656.

### Fixed
- 6.2.2 REPLACE no longer counts as Heir removal (D-007): a living card swap
  (March -> Edward IV) kept the -8 penalty and dropped the Heir slot at third-
  War setup; dead Heirs now also persist across Wars via a ledger even when
  absent from a roster (York dead pre-IIY could be resurrected by IIIY), and
  non-Heir deaths no longer carry (they may return, 6.2.2 NOTE).
- The -8 lost-Heir Influence charge now applies once, at third-War setup
  (IIIY/IIIL Influence Tracks), not at every War transition.
- Command-move enumeration no longer depends on `PYTHONHASHSEED`: Tax,
  ship-borne Supply, and campaign Parley targets were emitted in set order,
  so seeded game trajectories varied across processes. Emission sites now
  sorted; `(scenario, seed)` fully determines a game across processes
  (regression-tested in two subprocesses with different hash seeds).
- General Succession (6.2) no longer skips in-play Heirs: the Heir role passes
  to the next-ranked living Heir, and a new Lord enters play only if that Heir
  is not already in the game (War I: Margaret's removal wrongly instantiated
  Somerset (2) while Somerset (1) was Mustered).
- Battle dice application no longer depends on `PYTHONHASHSEED`: `_TROOP_TYPES`
  is now an ordered tuple, making the Regroup recovery loop (4.4.2) and the
  Aftermath Loss rolls (4.4.3) reproducible across processes (save/replay and
  future ground-truth replays).
- Corrected the false claim (in the traceability generator, matrix, and
  findings log) that the repo's Rules PDF was the Seljuk rulebook -- it is the
  Plantagenet Rules of Play (Levy & Campaign Series Vol. IV).

## [0.3.0] - 2026-06-21

Marks the engine as feature-complete: Levy, full Campaign, Combat (4.x), all 74
Arts of War cards (both faces), Succession (6.2), and the Wars of the Roses grand
scenario all play end-to-end through the agent-facing interface.

### Added
- `scripts/sweep_harness.py` — multi-policy full-game sweeper with per-step board
  invariant checks (bug-finding gauntlet).
- `scripts/battle_fuzz.py` — battle decision-payload fuzzer that resolves each
  fuzzed battle on a fork (sound crash / invariant oracle).
- Property-based conservation tests (`tests/test_property_conservation.py`).
- Mutation-testing harnesses (`scripts/mutation_probe.py` and the coverage-
  guided `scripts/mutation_cov.py`); sweeps on
  `influence.py` killed 31/32 mutants (the 1 survivor is an equivalent mutant)
  and surfaced an Influence-check branch-coverage gap, now closed...
- GitHub Actions CI (ruff + pytest on a Python 3.10–3.12 matrix).
- `CHANGELOG.md`.

### Fixed
- `battle.resolve_battle` no longer crashes with a raw `TypeError` on a malformed
  `regroup` decision; it raises `IllegalAction("bad_regroup")`.
- `succession._deck_has` now recognises a card deployed as a Capability on a
  Lord's mat, so a while_king / count-threshold deck ADD can no longer clone it
  into the draw pile (`card_in_deck_and_on_mat`).

### Changed
- `requires-python` corrected to `>=3.10` (the engine runs on 3.10; the prior
  `>=3.11` pin was inaccurate). ruff/mypy targets aligned to py310.
- README Status section rewritten to reflect the feature-complete engine.

## [0.1.0] - earlier

Initial harness: data model, Levy Muster, Campaign backbone, movement/economy,
and the bulk of the rules audit (see `SMOKE_TEST_FINDINGS.md` for the full log).
