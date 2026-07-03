# Mutation triage: src/plantagenet/legal_moves.py

Survivors: 76 (of 275 total sites; 9 uncovered not triaged).
Killing tests: tests/test_mutation_kills_legal_moves.py (15 tests).
Every KILLED verdict was verified by hand-applying the mutation, watching the
named test fail, and reverting (`git checkout`). Ambiguous sites (two identical
operators on one line) were verified against BOTH variants.

## Summary

| verdict     | count |
|-------------|------:|
| EQUIVALENT  |     9 |
| GAP-killed  |    63 |
| GAP-open    |     1 |
| LOW         |     3 |

## Sites

| site | line | desc | verdict | reason |
|-----:|-----:|------|---------|--------|
| 612  | 37  | int 0->1        | EQUIVALENT | "idx" is always set when a pending interaction is created (reactions.py:225); the get default is dead |
| 209  | 38  | cmp GtE->Gt     | EQUIVALENT | reactions.resolve clears state.pending once idx reaches len(offers); idx==len with pending non-empty is unreachable |
| 690  | 79  | bool Or->And    | GAP-killed | a Lord with mustered_this_segment would enumerate a second Levy menu |
| 2363 | 88  | cmp Eq->NotEq   | GAP-killed | BE SENT FOR relaxation flips to the Yorkists; Lancastrian later-box Muster Exiles vanishes |
| 2418 | 131 | cmp Eq->NotEq   | GAP-killed | Stanley free Levy Troops (L35) suppressed at a Stronghold |
| 4137 | 131 | int 0->1        | GAP-killed | loc[1]=="stronghold" never true; Stanley free Levy Troops never offered |
| 2436 | 143 | cmp Eq->NotEq   | GAP-killed | both Eq variants: enemy Lords offered / Calendar filter inverted; exact-target-set test kills either |
| 2437 | 144 | cmp IsNot->Is   | GAP-killed | ready Calendar Lords excluded from Levy Lord |
| 2438 | 144 | cmp LtE->Lt     | GAP-killed | a Lord ready exactly this Turn box is not levyable |
| 2441 | 146 | bool Or->And    | GAP-killed | seat-fallback (3.4.2) stops rescuing targets whose Seat holds an enemy |
| 749  | 155 | bool And->Or    | GAP-killed | Lancastrians could never Levy Vassals (Y7 gate always on) |
| 1495 | 155 | cmp Eq->NotEq   | GAP-killed | Y7 blocks the Yorkists instead of the Lancastrians |
| 1526 | 174 | cmp Eq->NotEq   | GAP-killed | Levy Troops never offered at a Stronghold |
| 3421 | 174 | int 0->1        | GAP-killed | loc[1]=="stronghold" never true; Levy Troops never offered |
| 4818 | 174 | int 1->2        | GAP-killed | loc[2] IndexError swallowed; Levy Troops never offered |
| 2488 | 175 | bool And->Or    | GAP-killed | a coinless Lord loses Levy Troops even without Rising Wages |
| 3427 | 175 | cmp Lt->LtE     | GAP-killed | Rising Wages wrongly blocks a Lord holding exactly 1 Coin |
| 4213 | 175 | int 1->2        | GAP-killed | Rising Wages threshold becomes 2 Coin |
| 4822 | 175 | int 0->1        | GAP-killed | a Lord with no "coin" key evades Rising Wages (phantom move) |
| 781  | 204 | bool Or->And    | GAP-killed | Ship Levy Transport vanishes at Ports and Exile boxes |
| 3474 | 204 | int 0->1        | GAP-killed | Exile-box Lords lose the Ship option (KeyError swallowed) |
| 4859 | 204 | int 1->2        | GAP-killed | Port Lords lose the Ship option (IndexError swallowed) |
| 3480 | 205 | int 0->1        | EQUIVALENT | mutated get default only turns a missing ship 0 into 1; both satisfy `< 2`, its only use |
| 1575 | 206 | bool Or->And    | GAP-killed | a Lord holding a Ship loses the option when the 9-Ship pool is full |
| 2539 | 206 | cmp Gt->GtE     | GAP-killed | shipless Lord offered a Ship with the pool exhausted (phantom) |
| 2540 | 206 | cmp Lt->LtE     | GAP-killed | pool cap off by one (phantom at 9 in play) |
| 3483 | 206 | int 0->1        | GAP-killed | both int-0 variants (`>1` / default 1) verified killed |
| 3486 | 206 | int 9->10       | GAP-killed | Ship pool cap raised to 10 (phantom) |
| 4255 | 206 | int 0->1        | GAP-killed | sibling variant of 3483; both verified |
| 4266 | 218 | const False->True | GAP-killed | enumeration peek commits Jack Cade uses: legal_moves mutates state |
| 816  | 223 | int 0->1        | GAP-killed | shipless Lord parleys across the Sea (phantom targets) |
| 1624 | 231 | cmp Eq->NotEq   | GAP-killed | both Eq variants (tid==here / favour==side) verified against exact target set |
| 382  | 277 | bool And->Or    | GAP-killed | every Yorkist Sail blocked even without French Fleet |
| 905  | 277 | cmp Eq->NotEq   | GAP-killed | French Fleet blocks the Lancastrians instead of the Yorkists |
| 4296 | 281 | int 0->1        | EQUIVALENT | a Mustered Lord always has a Retinue, so the units term of the max() is >= 1 >= ceil(1/2) from the mutated provender default |
| 2680 | 282 | int 2->3        | GAP-killed | Cart shipping capacity 2->3: under-shipped Lord offered Sail (phantom) |
| 4299 | 282 | int 0->1        | EQUIVALENT | same max()/Retinue argument for the cart default |
| 388  | 283 | cmp Lt->LtE     | GAP-killed | a Lord with exactly enough Ships loses all Sail moves |
| 923  | 285 | cmp Eq->NotEq   | GAP-killed | Owain Glyndwr bars the wrong side from Welsh Ports |
| 1740 | 290 | bool Or->And    | GAP-killed | a Lord at Sea reaches no Ports at all |
| 2691 | 290 | cmp Eq->NotEq   | GAP-killed | same-Sea Ports lost, non-adjacent-Sea Ports gained (both asserted) |
| 2692 | 290 | cmp In->NotIn   | GAP-killed | Sea adjacency inverted (calais lost, newcastle gained) |
| 1747 | 294 | cmp Eq->NotEq   | GAP-killed | Owain skips every non-Welsh Port instead of Welsh ones |
| 1755 | 300 | cmp Eq->NotEq   | GAP-killed | cannot Sail into the current Sea; any Sea becomes reachable |
| 2771 | 344 | bool And->Or    | GAP-killed | Agitators offered against Friendly/Exhausted Strongholds (phantom) |
| 3677 | 358 | bool And->Or    | GAP-killed | Merchants treats every nearby Locale as a Depletion marker |
| 2788 | 360 | int 2->3        | GAP-killed | Merchants offers 3-marker removals (rule caps at 2) |
| 3753 | 443 | cmp Eq->NotEq   | GAP-killed | Sun in Splendour targets enemy Exile boxes, loses Yorkist ones |
| 3759 | 447 | bool And->Or    | GAP-killed | Y24 targets any enemy-free Locale, not just Friendly ones |
| 1078 | 481 | bool Or->And    | LOW | battle_reactions is advisory annotation only; apply_action ignores it (no menu entries change) |
| 2937 | 485 | bool And->Or    | LOW | defender list feeds the advisory annotation only |
| 3803 | 486 | cmp Eq->NotEq   | LOW | same advisory-annotation defender list |
| 1107 | 503 | cmp IsNot->Is   | GAP-killed | a Lord at Sea loses its only real action (Sail) |
| 4506 | 505 | const True->False | GAP-killed | at-Sea origin treated as Port: adjacent-Sea Ports lost |
| 1117 | 511 | cmp NotEq->Eq   | GAP-killed | Exile-box Forage inverted (offered only when Exhausted) |
| 1128 | 522 | bool And->Or    | GAP-killed | Lancastrians barred from Wales without Owain Glyndwr |
| 2005 | 522 | cmp Eq->NotEq   | GAP-killed | Owain bars the Yorkists instead |
| 2033 | 542 | bool And->Or    | GAP-killed | all marches into Wales blocked permanently |
| 2039 | 548 | bool And->Or    | GAP-killed | phantom Group-March entries with group=[] |
| 2071 | 565 | cmp Eq->NotEq   | GAP-killed | Exile-box Lords cannot Sail (KeyError swallowed) |
| 1162 | 566 | bool And->Or    | EQUIVALENT | seas.json Ports and locales.json port flags are the same set, so from_sea/on_sea are truthy together |
| 3103 | 584 | cmp In->NotIn   | GAP-killed | Vassal Seats vanish from Tax targets |
| 3106 | 586 | int 0->1        | GAP-killed | shipless Lord gains Sea-hop Tax routes; ids transposed — re-baseline shows 3106 killed, twin 2111 is the equivalent occurrence |
| 3110 | 588 | cmp NotIn->In   | GAP-killed | every Tax target skipped; no Tax at all |
| 2117 | 590 | bool Or->And    | EQUIVALENT | t==here falls to the elif where _tax_route_cost(target==here) returns 0 (not None) and emits the identical move |
| 3975 | 603 | int 0->1        | EQUIVALENT | every Stronghold in static data yields provender >= 1; the get default is dead |
| 3146 | 613 | int 0->1        | EQUIVALENT | same data fact for the routed-supply branch |
| 3149 | 614 | cmp GtE->Gt     | GAP-killed | a Lord with exactly enough Carts loses Supply |
| 3994 | 614 | int 1->2        | GAP-killed | Cart requirement doubled |
| 2147 | 617 | int 0->1        | GAP-killed | shipless Lord offered Ship Supply (phantom) |
| 4009 | 621 | cmp NotEq->Eq   | GAP-killed | Ship Supply flips to self-Port only; same-Sea sources lost |
| 2162 | 629 | int 0->1        | GAP-killed | shipless Lord gains Sea-reach Parley targets (phantom) |
| 565  | 646 | cmp NotIn->In   | GAP-killed | _same_sea_ports returns nothing for actual Ports |
| 3205 | 649 | cmp NotEq->Eq   | GAP-killed | same-Sea Parley reach becomes {here} |
| 1294 | 686 | cmp NotIn->In   | GAP-killed | validated_legal_moves probes and drops the build_plan requirement from the agent palette |
| 1298 | 688 | cmp NotIn->In   | GAP-open | play_event without decisions gets probed: a pending Event whose handler demands decisions (e.g. L23/L24 selections) would be dropped from the validated palette, soft-locking the agent; test cap (15) reached before covering it |
