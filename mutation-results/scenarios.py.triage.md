# Mutation triage: src/plantagenet/scenarios.py

Survivors: 44 (of 181 total sites; 4 uncovered not triaged).
Killing tests: tests/test_mutation_kills_scenarios.py (15 tests).
Every KILLED verdict was verified by hand-applying the mutation, watching the
named test fail, and reverting. Ambiguous sites were verified against both
variants; the outcome below names the surviving one.

## Summary

| verdict     | count |
|-------------|------:|
| EQUIVALENT  |    15 |
| GAP-killed  |    21 |
| GAP-open    |     0 |
| LOW         |     8 |

Notes: LOW sites 661 and 2936 (the unused `_apply_lost_heir_influence` return
total) happen to be killed by the new influence-penalty test anyway.

## Sites

| site | line | desc | verdict | reason |
|-----:|-----:|------|---------|--------|
| 1128 | 57  | cmp Eq->NotEq   | GAP-killed | battle-only scenarios would give the first action to the Rebel side, not the King's (Bosworth active_side flips) |
| 2394 | 73  | bool And->Or    | EQUIVALENT | the extra dict keys ("KING", "*_per_succession") can never equal a lord_cards id, and on_map is only read via lord-id lookups |
| 2450 | 93  | bool And->Or    | EQUIVALENT | every special_rules entry in the data is a dict with "name"; the disjuncts co-vary |
| 3907 | 93  | cmp In->NotIn   | EQUIVALENT | the Montagu block is a redundant no-op: somersets_return on_map data already assigns L23 + montagu to Warwick (verified: disabling the block changes nothing) |
| 445  | 102 | cmp In->NotIn   | GAP-killed | Montagu applied to every NON-Montagu scenario: henry_vi's Warwick gains a phantom L23 Capability + Special Vassal |
| 1201 | 104 | bool And->Or    | EQUIVALENT | the only Montagu scenario always contains warwick_yorkist and L23 exists in cards; the guard's disjuncts never disagree |
| 2462 | 104 | cmp IsNot->Is   | EQUIVALENT | disables the redundant Montagu block (see 3907) |
| 2463 | 104 | cmp In->NotIn   | EQUIVALENT | disables the redundant Montagu block (see 3907) |
| 2466 | 107 | cmp NotIn->In   | EQUIVALENT | montagu is already in special_vassals from data, so the append is a no-op either way |
| 5113 | 133 | cmp In->NotIn   | EQUIVALENT | is_mustered_hint is an unused parameter of _lord_state (never read in the body) |
| 497  | 170 | cmp Is->IsNot   | EQUIVALENT | every scenario with an "end" calendar marker also sets turns.end_marker_box to the same box; scenarios without either have no marker to find |
| 2572 | 172 | cmp In->NotIn   | GAP-killed | end_box set from non-end calendar entries: henry_vi gains a phantom game-end box |
| 4041 | 184 | int 1->2        | GAP-killed | battle-only Bosworth (no turns block) starts at turn_box 2 |
| 5806 | 184 | int 1->2        | EQUIVALENT | the `or` fallback is dead: every scenario/War defines a truthy levy_box (or first_box) |
| 543  | 219 | const False->True | GAP-killed | every on-map / battle-only Lord carries a stale calendar_exile=True through disbands and re-levies |
| 2732 | 270 | bool And->Or    | GAP-killed | all_except mode off-maps EVERY regular Vassal (Warwick's Rebellion loses its Vassals) |
| 4231 | 306 | cmp NotIn->In   | GAP-killed | grand-scenario Arts of War decks built empty (in-play filter inverted) |
| 4258 | 327 | cmp Eq->NotEq   | GAP-killed | both Eq variants verified: enemy-side or rose-only cards form the Renewed-War base deck |
| 5328 | 327 | int 0->1        | GAP-killed | Renewed-War base deck built from rose-1 cards instead of no-rose |
| 1564 | 357 | cmp Is->IsNot   | EQUIVALENT | every King candidate is in the War's lord_cards (so ls is never None) with empty caps/ring; the fresh-replace branch rewrites every field it doesn't copy, producing an identical LordState |
| 661  | 375 | int 0->1        | LOW | `total` is a return value no production caller reads (renew_war discards it); killed incidentally by the penalty test |
| 1598 | 384 | bool And->Or    | GAP-killed | the -8 penalty is charged for any removed Lord, not just 6.2.1 Heirs |
| 2936 | 386 | int 8->9        | LOW | mutates the unused running total, not the marker movement; killed incidentally by asserting the return |
| 1674 | 432 | const False->True | GAP-killed | _unplace_lord leaves a stale Exile marker (IIY's displaced Margaret stays exile-flagged) |
| 3054 | 456 | cmp GtE->Gt     | GAP-killed | tied Stronghold-type counts hand the marker to the Lancastrians, not Yorkist-at-0 |
| 4439 | 456 | int 0->1        | GAP-killed | same tie handling off by one |
| 756  | 491 | cmp LtE->Lt     | GAP-killed | IIY Pembroke no longer joins at exactly two Heirs |
| 1743 | 491 | int 2->3        | GAP-killed | IIY Pembroke joins with three Heirs still alive |
| 1746 | 493 | const True->False | LOW | log-dict field only; renew_war discards the log |
| 4542 | 549 | cmp Eq->NotEq   | GAP-killed | IIIY Rutland's Heir card flips Y31<->Y20 depending on the wrong King |
| 828  | 563 | cmp Eq->NotEq   | GAP-killed | IIIY Gloucester (1) gains Y28 with the wrong King |
| 3272 | 578 | bool And->Or    | EQUIVALENT | every Lord has a Seat present in locales; the only behavior change would be london-Seat writes, which line 580 overwrites with the King's side |
| 1897 | 595 | const True->False | LOW | log field (rutland_removed_by_y28) only |
| 1916 | 610 | const True->False | LOW | log field (warwick_king) only |
| 5492 | 612 | int 2->3        | LOW | kept[:2]->[:3] changes only log["kept_heirs"]; placement still uses kept[0] and kept[1] |
| 1937 | 624 | const True->False | LOW | log field (northumberland_2) only |
| 2034 | 694 | cmp Eq->NotEq   | GAP-killed | IIIL Margaret-as-King loses her mandatory L26 EDWARD Capability |
| 4751 | 703 | bool Or->And    | GAP-killed | the Y28 set-aside flag reads as False: Gloucester (2) never becomes the sole IIIL Heir |
| 4759 | 706 | cmp In->NotIn   | GAP-killed | same Y28 branch broken via the membership test |
| 3502 | 717 | const True->False | EQUIVALENT | heirs is [] in that branch, so line 718 immediately re-sets warwick_heir=True |
| 3567 | 757 | const False->True | LOW | {"applied": ...} return is discarded by renew_war; report field only |
| 3594 | 767 | int 1->2        | EQUIVALENT | every natural_causes entry in the data specifies "dice"; the default is dead |
| 3604 | 770 | cmp Lt->LtE     | GAP-killed | Natural Causes removes a Heir whose roll exactly equals the last Turn box |
| 2242 | 803 | const False->True | EQUIVALENT | the surviving site is the .get default: renew_war always writes gloucester_as_heir_played when the source War has order 2, and War I has order 1 (the reachable else-branch sibling, site 3687, was already killed; the new flag test kills it too) |
