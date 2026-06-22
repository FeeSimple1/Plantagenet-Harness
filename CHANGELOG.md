# Changelog

All notable changes to the Plantagenet harness are recorded here. Dates are the
date of the change; the project is not formally released, so versions are
internal milestones.

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
