# Mutation triage: src/plantagenet/actions.py

Survivors triaged: **111** (of 351 mutants: 226 killed by the
pre-existing suite, 14 uncovered - not triaged per instructions).

| Verdict | Count |
|---|---|
| GAP - killed by new tests | 97 |
| GAP - open (classified, no test: 20-test cap) | 1 |
| EQUIVALENT | 8 |
| LOW | 5 |

Killing tests: `tests/test_mutation_kills_actions.py` (20 tests). Every killed mutant was verified by
hand-applying the mutation to the source line, confirming the test file fails, and
reverting (`git status --short src/` clean). Where a desc is ambiguous (the operator or
literal occurs twice on the line), both candidate positions were applied and verified;
the row notes the outcome. Equivalent/LOW verdicts were also machine-checked to survive
the new tests.

| site | line | desc | verdict | reason |
|---|---|---|---|---|
| 1616 | 173 | int 0->1 L173 | LOW | return 0 only reached at target==start, where callers shadow the value or only test None-ness; killed anyway by test_parley_route_cost_ways_and_great_ships |
| 7437 | 181 | bool And->Or L181 | GAP (killed) | Great Ships all-Ports hop must respect a Naval-Blockaded Sea; killed by test_parley_route_cost_ways_and_great_ships |
| 8257 | 182 | bool And->Or L182 | GAP (killed) | Great Ships all-Ports hop must respect a Naval-Blockaded Sea; killed by test_parley_route_cost_ways_and_great_ships |
| 8369 | 182 | cmp In->NotIn L182 | GAP (killed) | Great Ships all-Ports hop must respect a Naval-Blockaded Sea; killed by test_parley_route_cost_ways_and_great_ships |
| 6476 | 206 | bin Add->Sub L206 | GAP (killed) | BFS intermediate distance drives Parley Way cost (Influence per Way); killed by test_parley_route_cost_ways_and_great_ships (2-Way route) |
| 7466 | 206 | int 1->2 L206 | GAP (killed) | BFS intermediate distance drives Parley Way cost (Influence per Way); killed by test_parley_route_cost_ways_and_great_ships (2-Way route) |
| 5071 | 215 | cmp In->NotIn L215 | GAP (killed) | undo snapshot loses Vassal state, so a King's Name (Y32) cancel fails to restore the Levied Vassal; killed by test_kings_name_cancel_restores_vassal |
| 5177 | 269 | int 1->2 L269 | GAP (killed) | per-Lord Event usage counter mis-increments, halving My Crown/Jack Cade uses; killed by test_parley_event_mods_usage_limits |
| 6559 | 269 | int 0->1 L269 | GAP (killed) | per-Lord Event usage counter mis-increments, halving My Crown/Jack Cade uses; killed by test_parley_event_mods_usage_limits |
| 731 | 282 | cmp Eq->NotEq L282 | GAP (killed) | Jack Cade benefit gated to Yorkist side/Event; killed by test_jack_cade_eligibility (eligible Lord gets auto+free) |
| 3440 | 284 | bool And->Or L284 | GAP (killed) | Jack Cade eligibility check skipped -> any Yorkist gets free auto-Parleys; killed by test_jack_cade_eligibility (ineligible Lord assert) |
| 5190 | 284 | cmp Eq->NotEq L284 | GAP (killed) | Jack Cade benefit gated to Yorkist side/Event; killed by test_jack_cade_eligibility (eligible Lord gets auto+free) |
| 733 | 292 | cmp Eq->NotEq L292 | GAP (killed) | Henry VI no longer gets My Crown's 0-Lordship Parley; killed by test_parley_event_mods_usage_limits |
| 5205 | 294 | int 2->3 L294 | GAP (killed) | My Crown limit 2->3 grants a third free Parley; killed by test_parley_event_mods_usage_limits |
| 5207 | 295 | const True->False L295 | GAP (killed) | My Crown stops granting free Lordship at all; killed by test_parley_event_mods_usage_limits |
| 5212 | 298 | int 3->4 L298 | GAP (killed) | Gloucester as Heir limit 3->4 grants a fourth free Parley; killed by test_parley_event_mods_usage_limits |
| 737 | 301 | bool And->Or L301 | GAP (killed) | An Honest Tale surcharge would hit every Lancastrian Parley without Y34 active; killed by test_parley_event_mods_usage_limits (discount==0 assert) |
| 6613 | 313 | bool Or->And L313 | GAP (killed) | adjacent-Region contribution to Jack Cade eligibility dropped; killed by test_jack_cade_eligibility (Lord at york, adjacent all-Yorkist North) |
| 5230 | 317 | bool And->Or L317 | GAP (killed) | Region membership / all-Yorkist test corrupted -> eligible Lord denied; killed by test_jack_cade_eligibility |
| 6621 | 317 | cmp Eq->NotEq L317 | GAP (killed) | Region membership / all-Yorkist test corrupted -> eligible Lord denied; killed by test_jack_cade_eligibility |
| 1816 | 318 | bool And->Or L318 | GAP (killed) | eligibility collapses to always-True -> ineligible Lord gets Jack Cade; killed by test_jack_cade_eligibility |
| 6623 | 318 | cmp Eq->NotEq L318 | GAP (killed) | Region membership / all-Yorkist test corrupted -> eligible Lord denied; killed by test_jack_cade_eligibility |
| 758 | 320 | const False->True L320 | GAP (killed) | eligibility collapses to always-True -> ineligible Lord gets Jack Cade; killed by test_jack_cade_eligibility |
| 3509 | 326 | const False->True L326 | EQUIVALENT | else-branch mods dict is built only when by_lord is not a known Lord, and _active_lord then raises before any mod value is read |
| 3510 | 326 | int 0->1 L326 | EQUIVALENT | else-branch mods dict is built only when by_lord is not a known Lord, and _active_lord then raises before any mod value is read |
| 3511 | 326 | const False->True L326 | EQUIVALENT | else-branch mods dict is built only when by_lord is not a known Lord, and _active_lord then raises before any mod value is read |
| 3535 | 333 | int 0->1 L333 | GAP (killed) | extra_spend default 0->1 silently spends +1 Influence on every Parley; killed by test_parley_costs_and_unfriendly_location (spent==2) |
| 779 | 334 | cmp Gt->GtE L334 | GAP (killed) | has_ship becomes always-True (>=0 / default 1) -> free Sea hops without a Ship; killed by test_parley_costs_and_unfriendly_location (no_route) |
| 3538 | 334 | int 0->1 L334 | GAP (killed) | has_ship becomes always-True (>=0 / default 1) -> free Sea hops without a Ship; killed by test_parley_costs_and_unfriendly_location (no_route) |
| 1859 | 336 | cmp Eq->NotEq L336 | GAP (killed) | own-unfriendly-location shortcut would fire for target!=here, zeroing Way cost; killed by test_parley_costs_and_unfriendly_location (way_cost==1) |
| 1860 | 336 | cmp Eq->NotEq L336 | EQUIVALENT | only diverges when target==here at an unfriendly stronghold, where the route branch also returns Way cost 0 (target==start) |
| 1868 | 340 | int 0->1 L340 | GAP (killed) | current-location Parley Way cost 0->1 overcharges Influence; killed by test_parley_costs_and_unfriendly_location (way_cost==0, spent==1) |
| 3731 | 423 | int 0->1 L423 | GAP (killed) | Levy Lord extra_spend default 0->1 overspends Influence; killed by test_levy_lord_costs_seat_favour_and_fallback (spent==1) |
| 866 | 426 | int 1->2 L426 | GAP (killed) | Levy Lord spends 2 Lordship instead of 1; killed by test_levy_lord_costs_seat_favour_and_fallback |
| 2050 | 434 | const False->True L434 | GAP (killed) | Mustered Lord's cylinder wrongly stays Exile-marked on the Calendar bookkeeping; killed by test_levy_lord_costs_seat_favour_and_fallback |
| 2057 | 438 | bool And->Or L438 | GAP (killed) | fallback Muster would flip the enemy-occupied Seat's Favour; killed by test_levy_lord_costs_seat_favour_and_fallback (york stays neutral) |
| 3778 | 438 | cmp NotEq->Eq L438 | GAP (killed) | Mustering at a not-yet-Friendly Seat must flip its Favour (3.4.2); killed by test_levy_lord_costs_seat_favour_and_fallback |
| 880 | 440 | bool And->Or L440 | GAP (open) | in the grand scenario a FAILED Levy Lord would fire succession.on_muster_lord (e.g. assign L26 EDWARD); needs a grand-scenario failed-levy test (test cap) |
| 2088 | 453 | int 0->1 L453 | GAP (killed) | Vassals without Loyalty would get mod 1; killed by test_levy_vassal_costs_loyalty_and_buckingham (loyalty_mod==0) |
| 3815 | 455 | cmp Eq->NotEq L455 | GAP (killed) | Loyalty sign inverted (white/red colour match); killed by test_levy_vassal_costs_loyalty_and_buckingham (loyalty_mod==+1) |
| 5499 | 464 | cmp Eq->NotEq L464 | GAP (killed) | Yorkists Block Parliament (Y7) would bar the wrong side; killed by test_levy_vassal_gates (blocked_parliament) |
| 909 | 469 | bool And->Or L469 | GAP (killed) | Margaret Beaufort's Seat-check waiver leaks to non-Henry-Tudor Lords; killed by test_levy_vassal_gates (seat_not_friendly still raised) |
| 2111 | 469 | cmp Eq->NotEq L469 | GAP (killed) | Margaret Beaufort's Seat-check waiver leaks to non-Henry-Tudor Lords; killed by test_levy_vassal_gates (seat_not_friendly still raised) |
| 2133 | 477 | bool And->Or L477 | GAP (killed) | a Mustered Vassal could be Levied again; killed by test_levy_vassal_gates (vassal_not_at_seat) |
| 3875 | 486 | int 0->1 L486 | GAP (killed) | Levy Vassal extra_spend default 0->1 overspends; killed by test_levy_vassal_costs_loyalty_and_buckingham (spent==1) |
| 2148 | 488 | bool And->Or L488 | GAP (killed) | Buckingham's Plot +2 would apply to every Yorkist Vassal Levy without L34; killed by test_levy_vassal_costs_loyalty_and_buckingham (spent==1) |
| 2149 | 488 | int 2->3 L488 | GAP (killed) | Buckingham's Plot surcharge 2->3; killed by test_levy_vassal_costs_loyalty_and_buckingham (spent==3) |
| 3877 | 488 | cmp Eq->NotEq L488 | GAP (killed) | Buckingham's Plot side test inverted; killed by test_levy_vassal_costs_loyalty_and_buckingham (spent==3 with L34) |
| 2150 | 489 | int 0->1 L489 | GAP (killed) | non-Buckingham Vassal Levies would cost +1 Way; killed by test_levy_vassal_costs_loyalty_and_buckingham (spent==1) |
| 930 | 493 | bool Or->And L493 | GAP (killed) | Two Roses auto-success would additionally require Earl of Richmond; killed by test_levy_vassal_auto_success_events |
| 2162 | 494 | bool And->Or L494 | GAP (killed) | every Lancastrian Vassal Levy would auto-succeed without L37; killed by test_levy_vassal_auto_success_events (plain check fails) |
| 3895 | 494 | cmp Eq->NotEq L494 | GAP (killed) | Earl of Richmond auto-success side test inverted; killed by test_levy_vassal_auto_success_events |
| 934 | 497 | int 1->2 L497 | GAP (killed) | Levy Vassal spends 2 Lordship instead of 1; killed by test_levy_vassal_costs_loyalty_and_buckingham |
| 5591 | 503 | int 15->16 L503 | GAP (killed) | Alice Montagu's +1 Service must cap at Calendar box 15; killed by test_levy_vassal_costs_loyalty_and_buckingham (service_box==15) |
| 3949 | 518 | int 1->2 L518 | GAP (killed) | each Ship-holding Lord counted twice -> nine-Ship limit hit at five; killed by test_ship_limit_counting (case C) |
| 5619 | 519 | bool And->Or L519 | GAP (killed) | every Mustered Lord counts as a Ship holder; killed by test_ship_limit_counting (case A) |
| 6867 | 519 | cmp Eq->NotEq L519 | GAP (killed) | non-Mustered Lords with Ships counted instead; killed by test_ship_limit_counting (case B) |
| 6868 | 519 | cmp Gt->GtE L519 | GAP (killed) | ship>=0 counts all Mustered Lords toward the limit; killed by test_ship_limit_counting (case A) |
| 7665 | 519 | int 0->1 L519 | GAP (killed) | missing ship key counted as a Ship (default 0->1); killed by test_ship_limit_counting (case A); both 0-positions verified killed |
| 8080 | 519 | int 0->1 L519 | GAP (killed) | Lords with exactly one Ship not counted (>0 -> >1); killed by test_ship_limit_counting (case B); both 0-positions verified killed |
| 5638 | 530 | int 0->1 L530 | GAP (killed) | cart default 0->1 gives 3 Carts to a Lord without the key; killed by test_levy_transport_cart_ship_and_two_ship_cap |
| 4004 | 540 | cmp Gt->GtE L540 | GAP (killed) | ship>=0 always bypasses the nine-Ship limit; killed by test_ship_limit_counting (case B) |
| 4005 | 540 | cmp Lt->LtE L540 | GAP (killed) | limit <9 -> <=9 permits a tenth Ship; killed by test_ship_limit_counting (B) |
| 5655 | 540 | int 0->1 L540 | GAP (killed) | keyless Lord treated as Ship holder bypasses the limit; killed by test_ship_limit_counting (case B); both 0-positions verified killed |
| 5658 | 540 | int 9->10 L540 | GAP (killed) | nine-Ship limit raised to ten; killed by test_ship_limit_counting (case B) |
| 6884 | 540 | int 0->1 L540 | GAP (killed) | a one-Ship Lord loses its limit bypass for the second Ship (>0 -> >1); killed by test_ship_limit_counting (case D); both 0-positions verified killed |
| 2259 | 542 | cmp Lt->LtE L542 | GAP (killed) | two-Ship cap <2 -> <=2 allows a third Ship; killed by test_levy_transport_cart_ship_and_two_ship_cap |
| 4009 | 542 | int 2->3 L542 | GAP (killed) | two-Ship cap raised to three; killed by test_levy_transport_cart_ship_and_two_ship_cap |
| 5661 | 542 | int 0->1 L542 | EQUIVALENT | get default only read when the ship key is absent, and both 0 and 1 satisfy < 2, so the require outcome is identical |
| 978 | 544 | bin Add->Sub L544 | GAP (killed) | Ship Levy would SUBTRACT a Ship; killed by test_levy_transport_cart_ship_and_two_ship_cap (ship==1) |
| 2267 | 544 | int 1->2 L544 | GAP (killed) | Ship Levy adds two Ships; killed by test_levy_transport_cart_ship_and_two_ship_cap |
| 4014 | 544 | int 0->1 L544 | GAP (killed) | keyless Lord would get a phantom base Ship; killed by test_levy_transport_cart_ship_and_two_ship_cap |
| 981 | 545 | int 1->2 L545 | GAP (killed) | Ship Levy spends 2 Lordship; killed by test_levy_transport_cart_ship_and_two_ship_cap (lordship_spent==2 after 2 actions) |
| 4036 | 558 | cmp Eq->NotEq L558 | GAP (killed) | Chamberlains' own-Vassal-Seat test inverted -> Depletion applied anyway; killed by test_commission_target_and_chamberlains |
| 4067 | 573 | bool And->Or L573 | GAP (killed) | Irishmen would work from any Exile box, not just Ireland; killed by test_irishmen_levy (in_exile_box) |
| 5705 | 574 | cmp Eq->NotEq L574 | GAP (killed) | Irishmen at any Port (or nowhere) instead of Irish-Sea Ports; killed by test_irishmen_levy; both == positions on the line verified killed |
| 7695 | 574 | int 0->1 L574 | GAP (killed) | loc[0]->loc[1] disables the Irish-Sea-Port branch entirely; killed by test_irishmen_levy (5 Militia at Harlech) |
| 4094 | 587 | bool And->Or L587 | GAP (killed) | Commission of Array target no longer needs Friendly AND Enemy-free; killed by test_commission_target_and_chamberlains (bad_commission_target) |
| 4121 | 601 | cmp GtE->Gt L601 | GAP (killed) | Rising Wages would demand 2 Coins (>=1 -> >1); killed by test_rising_wages_coin |
| 5750 | 601 | int 1->2 L601 | GAP (killed) | Rising Wages cost 1->2 Coins; killed by test_rising_wages_coin |
| 6953 | 601 | int 0->1 L601 | GAP (killed) | coinless Lord passes the Rising Wages check via default 1 (then goes negative); killed by test_rising_wages_coin (rising_wages_no_coin) |
| 1039 | 610 | bool And->Or L610 | GAP (killed) | The Commons bonus available without the Event (or to Lancastrians); killed by test_the_commons_extras (militia==1 without Y16) |
| 5770 | 611 | int 0->1 L611 | GAP (killed) | commons_extra default 0->1 adds a free Militia under Y16; killed by test_the_commons_extras |
| 4145 | 612 | cmp LtE->Lt L612 | GAP (killed) | 0<=extra<=2 bound tightened; killed by test_the_commons_extras (extra 0 and 2 both legal); both <= positions verified killed |
| 5772 | 612 | int 0->1 L612 | GAP (killed) | extra lower bound 0->1 rejects the default; killed by test_the_commons_extras |
| 5776 | 612 | int 2->3 L612 | GAP (killed) | The Commons cap 2->3 Militia; killed by test_the_commons_extras (bad_commons) |
| 6968 | 614 | int 0->1 L614 | GAP (killed) | Strongholds without a Militia table line would get a phantom base Militia; killed by test_the_commons_extras (Lynn +2) |
| 6979 | 619 | int 0->1 L619 | GAP (killed) | coinless Lord passes the Soldiers of Fortune Coin check via default 1; killed by test_soldiers_of_fortune (no_coin) |
| 4185 | 626 | int 0->1 L626 | LOW | pool default only read for units without a pool entry; every unit a Stronghold or Event can yield has a pool in shipped data |
| 6999 | 630 | int 0->1 L630 | GAP (killed) | Lord without the unit key gets a phantom extra Troop; killed by test_soldiers_of_fortune (mercenaries==2) |
| 5832 | 633 | int 0->1 L633 | EQUIVALENT | guarded by the >=1 Coin require using the same get: the coin key must exist (default 0 would have raised), so the default is never read |
| 2414 | 640 | bool And->Or L640 | GAP (killed) | no-Deplete if the Lord merely stands at a Vassal Seat (no Chamberlains); killed by test_commission_target_and_chamberlains (depletion applied) |
| 5863 | 649 | int 0->1 L649 | EQUIVALENT | guarded by the Rising Wages >=1 Coin require using the same get: the coin key exists when the deduction runs |
| 2465 | 665 | bool And->Or L665 | LOW | active_events entries always carry a same-side card id, so the disjunction only diverges on entries that never occur |
| 1101 | 675 | bool Or->And L675 | EQUIVALENT | verified over all cards x lords in shipped data: the 'Lords:' text line regex reproduces the data field's eligibility exactly |
| 2522 | 701 | bool And->Or L701 | GAP (killed) | Levying an enemy-side card must fail as unknown_card (stable error contract); killed by test_levy_capability_wrong_side_and_hastings_pool |
| 8154 | 748 | int 0->1 L748 | GAP (killed) | in-play count inflated by keyless mats -> Hastings' pool-limited +2 clipped; killed by test_levy_capability_wrong_side_and_hastings_pool |
| 6009 | 749 | bin Sub->Add L749 | GAP (killed) | pool-free computation pool-in_play -> pool+in_play ignores the pool; killed by test_levy_capability_wrong_side_and_hastings_pool (give==1) |
| 7811 | 749 | int 0->1 L749 | LOW | pool default only read for units without a pool entry; special-Vassal add_forces units (men_at_arms) always have one |
| 7153 | 750 | int 0->1 L750 | GAP (killed) | max(0,..)->max(1,..) mints a Troop when the pool is full; killed by test_levy_capability_wrong_side_and_hastings_pool |
| 8167 | 752 | int 0->1 L752 | GAP (killed) | keyless mat gets a phantom base Troop; killed by test_levy_capability_wrong_side_and_hastings_pool |
| 2665 | 787 | bool And->Or L787 | LOW | degenerate input only: an empty (or non-list truthy) lords payload would return an empty success instead of no_lords; no rules effect |
| 4589 | 845 | bool And->Or L845 | GAP (killed) | Surrender's has-Heir gate corrupted (any in-play Lord / inverted rank test); killed by test_concede_requires_heir |
| 6148 | 845 | cmp IsNot->Is L845 | GAP (killed) | Surrender's has-Heir gate corrupted (any in-play Lord / inverted rank test); killed by test_concede_requires_heir |
| 2820 | 863 | cmp Eq->NotEq L863 | GAP (killed) | end_muster would reset the OPPONENT's per-Levy Muster flags; killed by test_end_muster_resets_only_own_side_flags |
| 4628 | 864 | const False->True L864 | GAP (killed) | end_muster would SET mustered_this_segment, barring the side's next Levy; killed by test_end_muster_resets_only_own_side_flags |
| 6194 | 885 | cmp Eq->NotEq L885 | GAP (killed) | Rebel/King role or side detection inverted -> wrong Lords Array as Attacker/Defender in a battle-only scenario; killed by test_resolve_battle_sides_and_combatants |
| 6198 | 886 | cmp Eq->NotEq L886 | GAP (killed) | Rebel/King role or side detection inverted -> wrong Lords Array as Attacker/Defender in a battle-only scenario; killed by test_resolve_battle_sides_and_combatants |
| 6204 | 888 | cmp Eq->NotEq L888 | GAP (killed) | Rebel/King role or side detection inverted -> wrong Lords Array as Attacker/Defender in a battle-only scenario; killed by test_resolve_battle_sides_and_combatants |
| 6211 | 890 | cmp Eq->NotEq L890 | GAP (killed) | Rebel/King role or side detection inverted -> wrong Lords Array as Attacker/Defender in a battle-only scenario; killed by test_resolve_battle_sides_and_combatants |
| 2874 | 891 | bool And->Or L891 | GAP (killed) | battle would resolve with one side empty; killed by test_resolve_battle_sides_and_combatants (no_combatants) |
