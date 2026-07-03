# Mutation triage: src/plantagenet/succession.py

Survivors: 25 (of 113 total sites; 1 uncovered not triaged).
Killing tests: tests/test_mutation_kills_succession.py (3 tests).
Every KILLED verdict was verified by hand-applying the mutation, watching the
named test fail, and reverting.

## Summary

| verdict     | count |
|-------------|------:|
| EQUIVALENT  |    11 |
| GAP-killed  |     5 |
| GAP-open    |     0 |
| LOW         |     9 |

## Sites

| site | line | desc | verdict | reason |
|-----:|-----:|------|---------|--------|
| 1305 | 72  | cmp In->NotIn   | GAP-killed | is_global_heir inverted: the cross-War -8 penalty hits non-Heirs and spares Heirs |
| 812  | 145 | bool And->Or    | GAP-killed | setup-only Wars run the King/count recompute at setup: IIIL with one Heir gains a phantom Y16 in the deck |
| 3516 | 146 | bool Or->And    | GAP-killed | same guard broken via the war-lookup fallback |
| 833  | 160 | bool And->Or    | EQUIVALENT | the inner spec["lord"] == lord_id guard re-filters, and every data muster trigger carries only assign_capability, so wrongly-entered iterations are no-ops |
| 1419 | 162 | bool And->Or    | EQUIVALENT | in data every on:muster trigger has assign_capability with spec.lord == trigger lord == mustering lord; spec is never None there, so neither operand can disagree or crash |
| 424  | 214 | cmp NotIn->In   | EQUIVALENT | never marking keys only re-fires triggers whose effects are idempotent in reachable states: calendar targets never return to AVAILABLE, deck adds are source-guarded, and a King id can never become highest twice (REMOVED is permanent) |
| 448  | 241 | bool Or->And    | EQUIVALENT | the guard's conditions are individually unreachable: replace triggers only fire for a present Heir (o exists) and every rep["new"] in data is a real Lord id |
| 955  | 256 | bool And->Or    | EQUIVALENT | every id in a mat's .vassals is a regular Vassal keyed in state.vassals with on_lord == that Lord (vassal-book invariant), so both operands agree in reachable states |
| 470  | 267 | const False->True | LOW | calendar_exile on a REMOVED Lord is never read: only CALENDAR-status Lords are checked and REMOVED is permanent |
| 496  | 286 | const True->False | LOW | the Lord is already seated by the time the return is read; only the result flips replaced_in_place -> to_box (reporting) |
| 2618 | 305 | bool Or->And    | EQUIVALENT | fired keys only need uniqueness/stability; no War has two heir_count triggers with the same side and n, so the shortened key still discriminates |
| 1088 | 365 | const False->True | EQUIVALENT | all five Wars define successions.setup_only explicitly (war_i/iiy/iil false, iiiy/iiil true); the get default is dead |
| 1669 | 367 | const True->False | LOW | result field only; the sole caller (battle._kill_lord) reads only automatic_victory |
| 2688 | 378 | bin Add->Sub    | LOW | result["to_box"] reporting; the actual box is set inside _enter_calendar |
| 3089 | 378 | int 1->2        | LOW | same reporting field |
| 2690 | 379 | const True->False | EQUIVALENT | with explicit unset the general rule also runs, but after a scripted to_calendar the successor is in play or REMOVED and the per-War heir tables leave no lower AVAILABLE Heir, so _general_next_heir provably returns None |
| 3115 | 398 | bin Add->Sub    | LOW | result["to_box"] reporting (replace-to-Calendar branch) |
| 3427 | 398 | int 1->2        | LOW | same reporting field |
| 2710 | 402 | const True->False | EQUIVALENT | IIL's somerset_1 replace is the last-ranked lancastrian entry; nothing ranks below it, so the general rule returns None (same argument as 2690) |
| 561  | 411 | bool And->Or    | EQUIVALENT | setup_only is always False here (the function returned at line 366 otherwise), so the mutant merely runs the general rule after explicit triggers -- provably a no-op (see 2690/2710) |
| 1153 | 438 | bin Add->Sub    | GAP-killed | an AVAILABLE scripted successor enters turn_box - 1 instead of the next Calendar box |
| 1749 | 438 | int 1->2        | GAP-killed | scripted successor skips a Calendar box |
| 2787 | 474 | bin Add->Sub    | LOW | result["to_box"] reporting; the LordState gets its own turn_box + 1 on line 473 |
| 3184 | 474 | int 1->2        | LOW | same reporting field |
| 3204 | 517 | bool Or->And    | EQUIVALENT | _is_third_war only matters for third_war_only heir entries, which exist only in the global table; every War defines per-War heirs for both sides, so the global table is reached only via is_global_heir, which does not filter |
