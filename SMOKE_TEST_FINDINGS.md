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
