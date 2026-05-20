# Rules Questions — Plantagenet Harness

Open questions awaiting user adjudication. Each must contain all required
fields (see BRIEF.md "Question Format"). When answered, MOVE the entry to
`RULES_DECISIONS.md`.

---

## Q-001 — Sea adjacency between Ports (and Exile boxes)

**Context.** Encoding the map Ways (`data/static/ways.json`) in Phase 0.
The land Ways (Road / Highway / Path) are fully specified and encoded.

**Consultation log.**
1. `reference/Plantagenet Map Reference.txt` — marks which Locales are
   Ports ("This location is a port") and which Exile boxes exist, but does
   NOT enumerate which Ports are connected to which by Sea, nor the Sea
   adjacency of the Exile boxes (France/Ireland/Burgundy) or Calais.
2. `reference/Plantagenet map.rtf` — identical text to the Map Reference;
   no Sea adjacency listed.
3. Errata & Clarification FAQ #1 states "Sail action does not allow to go
   directly from a port to another port on another sea" — confirming the
   map is partitioned into multiple Seas, but does not enumerate which
   Ports belong to which Sea.
   No external/historical sources were consulted.

**What is ambiguous.** The Sea-zone membership of each Port (and of the
Exile boxes and Calais) is not given in the curated reference text. It is
presumably read off the physical board's Sea areas, which the reference
`.txt` files do not transcribe.

**Options.**
- (a) User provides the Sea-zone groupings (which Ports / Exile boxes
  share each Sea), to be encoded as `type: "sea"` Ways or as Sea-zone
  membership.
- (b) Operator transcribes Sea zones from the Rules of Play / Background
  Book map image — only if a clear, unambiguous map rendering exists
  (reading adjacency off a board scan risks error, so this needs user
  sign-off).

**Affects.** `data/static/ways.json`, `data/static/exile_boxes.json`,
future Sail (4.6.1) and Sea-Parley/adjacency logic. Not blocking for
Phase 0 (land Ways suffice for the skeleton and data-integrity).

**Blocking?** No for Phase 0. Yes for Phase 3a (Sail) and any Sea movement.

---

## Q-002 — Leicester's non-reciprocated map connections

**Context.** Building `ways.json` with a symmetry check (every Way must be
declared from both endpoints). Two of Leicester's stated connections are
not reciprocated by the other endpoint.

**Consultation log.**
1. `reference/Plantagenet Map Reference.txt`: "The town of Leicester (seat
   of Dudley) is connected to Peterborough and Lichfield by Road and to
   Nottingham and Northampton by Highway." But Peterborough's line lists
   "Northampton by Road and Ely and Lincoln by Highway" (no Leicester),
   and Nottingham's line lists "Lincoln and Derby by Road" (no Leicester).
   Leicester's other two connections ARE reciprocated: Lichfield lists
   Leicester by Road; Northampton lists Leicester by Highway.
2. `reference/Plantagenet map.rtf`: identical text — same inconsistency.
   No external/historical sources were consulted.

**What is ambiguous.** Whether Leicester actually connects to Peterborough
(Road) and to Nottingham (Highway). The reference is internally
inconsistent: Leicester's own line asserts these edges; the reciprocal
lines omit them.

**Options.**
- (a) The edges exist (Leicester's line is authoritative; the other
  Locales' lines are merely incomplete reciprocal listings). Add
  Leicester–Peterborough (Road) and Leicester–Nottingham (Highway).
- (b) The edges do not exist (Leicester's line over-lists). Keep them out.
- (c) Some combination (e.g. one exists, one doesn't), per the physical
  board.

**Current encoding.** Both disputed edges are EXCLUDED from `ways.json`
and recorded under `_meta.disputed_pending_adjudication` pending this
answer. The builder (`scripts/build_map_data.py`) carries them in
`PENDING_ASYMMETRIC`.

**Affects.** `ways.json`, all movement/path logic touching Leicester
(March, Supply, Tax routes, Parley adjacency).

**Blocking?** No for Phase 0. Should be resolved before Phase 3a (March).
