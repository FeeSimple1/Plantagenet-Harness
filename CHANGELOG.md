# Changelog

All notable changes to the Plantagenet harness are recorded here. Dates are the
date of the change; the project is not formally released, so versions are
internal milestones.

## [Unreleased]

### Added
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
