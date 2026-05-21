# SMOKE Test Findings — Plantagenet Harness

Append-only log of every SMOKE finding (bug surfaced during development or
auditing), with round-by-round context. Nothing here is ever overwritten;
the SMOKE numbering is the institutional memory of every bug found and how
it was fixed.

Each entry: SMOKE-NNN, round, the pattern (see `FUTURE_PROJECTS_LESSONS.md`),
a description, the fix, and the commit/test that closes it.

---

## Round 0 (Phase 0 — skeleton + static data)

No SMOKEs yet (no game logic implemented). Two map data-integrity
findings were surfaced by the `ways.json` symmetry check during data
encoding and routed to `RULES_QUESTIONS.md` rather than logged as SMOKEs,
because they are source ambiguities, not code bugs:

- Q-001: Sea adjacency between Ports is not enumerated in the references.
- Q-002: Leicester's connections to Peterborough and Nottingham are
  declared from Leicester's line only, not reciprocated.

The symmetry check itself (every Way declared from both endpoints) is the
Phase-0 analogue of the enumerator/handler round-trip discipline described
in `CROSS_PROJECT_LESSONS.md` — it catches transcription divergence in the
static data before any logic depends on it.

## Round 1 (Phase 0 — map corrections)

Applied user-supplied map corrections (resolving Q-001/Q-002, see
`RULES_DECISIONS.md` D-001/D-002/D-003):
- Encoded Sea zones (Irish Sea / English Channel / North Sea) with Port
  and Exile-box membership and zone adjacency (`seas.json`).
- Set Bristol as a Port (Irish Sea); added the two confirmed Leicester
  edges (Peterborough/Road, Nottingham/Highway).

Re-ran the reciprocity discipline two ways and they agree: the
`ways.json` builder symmetry check passes with no pending edges, and an
independent prose parse of the Map Reference (`scripts/reciprocity_sweep.py`)
reports 81 reciprocal pairs and zero one-sided edges or type mismatches.

## Round 2 (Phase 0 cleanup)

Removed `reference/Plantagenet map.rtf` (a duplicate of `Plantagenet Map
Reference.txt`) to eliminate the two-sources-of-truth drift risk flagged
after the map corrections. The `.txt` is now the single canonical map
reference.

## Round 3 (Phase 1 — state model, loader, display)

No game-logic SMOKEs (no rules logic yet). Two issues caught during
development before commit, noted for the record:
- RNG state serialized the Mersenne-Twister internal as a tuple, which a
  JSON round-trip turned into a list, breaking save/load identity. Fixed
  by list-ifying fully in `DiceRoller.get_state` (test:
  `test_save_load_round_trip`).
- The focused Lord view duplicated the status token. Cosmetic; fixed.

Guardrails added: `state.schema.json` is regenerated from the Pydantic
model (`scripts/generate_schema.py`) and a test asserts the committed
schema matches the model so it cannot silently drift. Initial
`active_side` is set to the King's side as a provisional pointer; precise
turn order per the Sequence of Play is a Phase 2 concern (documented in
`scenarios.py`).
