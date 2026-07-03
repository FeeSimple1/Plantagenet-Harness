# Mutation triage: src/plantagenet/events.py

Survivors triaged: **91** (of 253 mutants: 143 killed by the
pre-existing suite, 19 uncovered - not triaged per instructions).

| Verdict | Count |
|---|---|
| GAP - killed by new tests | 76 |
| GAP - open (classified, no test: 20-test cap) | 0 |
| EQUIVALENT | 5 |
| LOW | 10 |

Killing tests: `tests/test_mutation_kills_events.py` (20 tests). Every killed mutant was verified by
hand-applying the mutation to the source line, confirming the test file fails, and
reverting (`git status --short src/` clean). Where a desc is ambiguous (the operator or
literal occurs twice on the line), both candidate positions were applied and verified;
the row notes the outcome. Equivalent/LOW verdicts were also machine-checked to survive
the new tests.

| site | line | desc | verdict | reason |
|---|---|---|---|---|
| 1047 | 33 | int 0->1 L33 | LOW | pool default only read for units without a pool entry; all Event-granted units have pools in shipped data |
| 1051 | 34 | int 0->1 L34 | GAP (killed) | max(0,..)->max(1,..) mints a Troop past the pool; killed by test_earl_rivers_bounds_and_defaults (pool-full case) |
| 2120 | 34 | bin Sub->Add L34 | GAP (killed) | pool-in_play -> pool+in_play removes the pool limit; killed by test_earl_rivers_bounds_and_defaults (pool-full case) |
| 3296 | 36 | int 0->1 L36 | GAP (killed) | keyless mat gets a phantom base Troop from _pool_add; killed by test_earl_rivers_bounds_and_defaults (march militia==2) |
| 2131 | 42 | bool And->Or L42 | GAP (killed) | all Locales are dicts, so and->or makes every Region contain the whole map (Yorkist North / Welsh Rebellion scope); killed by test_yorkist_north_counts |
| 2152 | 50 | int 1->2 L50 | GAP (killed) | Charles the Bold grants 2 Provender instead of 1; killed by test_charles_the_bold_and_french_war_loans |
| 3318 | 50 | int 0->1 L50 | GAP (killed) | keyless Lord gets a phantom base Provender; killed by test_charles_the_bold_and_french_war_loans |
| 1091 | 57 | bin Add->Sub L57 | GAP (killed) | French War Loans would SUBTRACT Coin/Provender; killed by test_charles_the_bold_and_french_war_loans |
| 2169 | 57 | int 1->2 L57 | GAP (killed) | French War Loans grant doubled; killed by test_charles_the_bold_and_french_war_loans |
| 3327 | 57 | int 0->1 L57 | GAP (killed) | keyless Lord gets a phantom base asset; killed by test_charles_the_bold_and_french_war_loans |
| 1093 | 58 | bin Add->Sub L58 | GAP (killed) | French War Loans would SUBTRACT Coin/Provender; killed by test_charles_the_bold_and_french_war_loans |
| 2175 | 58 | int 1->2 L58 | GAP (killed) | French War Loans grant doubled; killed by test_charles_the_bold_and_french_war_loans |
| 3332 | 58 | int 0->1 L58 | GAP (killed) | keyless Lord gets a phantom base asset; killed by test_charles_the_bold_and_french_war_loans |
| 2197 | 68 | cmp LtE->Lt L68 | GAP (killed) | Earl Rivers 0<=n<=2 bound tightened; killed by test_earl_rivers_bounds_and_defaults (n=0 and n=2 both legal); both <= positions verified killed |
| 3345 | 68 | int 0->1 L68 | GAP (killed) | lower bound 0->1 rejects a declined Lord (n=0); killed by test_earl_rivers_bounds_and_defaults |
| 3349 | 68 | int 2->3 L68 | GAP (killed) | Earl Rivers cap 2->3 Militia; killed by test_earl_rivers_bounds_and_defaults (bad_militia) |
| 1146 | 81 | bin Add->Sub L81 | EQUIVALENT | x + 0 -> x - 0 is the identity either way |
| 2232 | 81 | int 0->1 L81 | LOW | inflates only the reported men_at_arms count in the result dict; the mat gets the correct Troops via _pool_add |
| 3377 | 81 | int 1->2 L81 | GAP (killed) | The Scots add 2 Men-at-Arms instead of 1; killed by test_scots_adds_one_of_each |
| 2238 | 82 | int 1->2 L82 | GAP (killed) | The Scots add 2 Militia instead of 1; killed by test_scots_adds_one_of_each |
| 2259 | 91 | bool And->Or L91 | GAP (killed) | any on-map Lancastrian would count as 'at a Port', losing the no-effect guard; killed by test_french_troops_preconditions |
| 1179 | 98 | bool And->Or L98 | GAP (killed) | French Troops could reinforce an enemy (Yorkist) Lord; killed by test_french_troops_preconditions (bad_lord) |
| 1186 | 101 | bool And->Or L101 | GAP (killed) | French Troops at a non-Port Locale; killed by test_french_troops_preconditions (not_port) |
| 2285 | 103 | int 2->3 L103 | GAP (killed) | min(2,..) cap raised to 3 Men-at-Arms; killed by test_french_troops_amount_cap; line has two 2s - cap position killed, default position equivalent |
| 4402 | 103 | int 2->3 L103 | EQUIVALENT | the get default 2->3 is clamped by the outer min(2, ..): requesting the default still yields 2; cap-position twin (2285) is killed |
| 2291 | 104 | int 2->3 L104 | GAP (killed) | min(2,..) cap raised to 3 Militia; killed by test_french_troops_amount_cap; line has two 2s - cap position killed, default position equivalent |
| 4406 | 104 | int 2->3 L104 | EQUIVALENT | the get default 2->3 is clamped by the outer min(2, ..); cap-position twin (2291) is killed |
| 2305 | 111 | int 1->2 L111 | GAP (killed) | Yorkist North counts each Stronghold twice; killed by test_yorkist_north_counts |
| 3428 | 111 | cmp Eq->NotEq L111 | GAP (killed) | counts non-Yorkist North Strongholds instead; killed by test_yorkist_north_counts |
| 2308 | 112 | int 1->2 L112 | GAP (killed) | counts each North Lord twice; killed by test_yorkist_north_counts |
| 3431 | 112 | cmp In->NotIn L112 | GAP (killed) | counts Yorkist Lords OUTSIDE the North; killed by test_yorkist_north_counts |
| 1226 | 113 | bin Add->Sub L113 | GAP (killed) | Influence gain strongholds+lords -> strongholds-lords; killed by test_yorkist_north_counts |
| 2327 | 120 | int 1->2 L120 | GAP (killed) | Henry Pressures Parliament counts each Vassal twice; killed by test_henry_pressures_parliament_counts |
| 4428 | 120 | cmp Eq->NotEq L120 | GAP (killed) | counts non-Mustered Vassals instead; killed by test_henry_pressures_parliament_counts |
| 3448 | 125 | bool And->Or L125 | GAP (killed) | Lancastrian Lords' Special Vassals would count against the Yorkists; killed by test_henry_pressures_parliament_counts |
| 488 | 132 | int 0->1 L132 | LOW | gained=0 initializer only feeds the result field in the no-effect branch; no Influence is moved either way |
| 2349 | 134 | int 5->6 L134 | GAP (killed) | Henry Released grants 6 Influence instead of 5; killed by test_henry_released_and_sir_richard_leigh |
| 2384 | 153 | int 0->1 L153 | GAP (killed) | with favour_extra==1, Y21 would strip London to neutral instead of removing the extra marker; killed by test_henry_released_and_sir_richard_leigh |
| 518 | 158 | cmp Eq->NotEq L158 | GAP (killed) | Y21 on a neutral London would no longer place Yorkist Favour; killed by test_henry_released_and_sir_richard_leigh |
| 2439 | 182 | cmp Eq->NotEq L182 | GAP (killed) | Henry's Proclamation would shift non-Mustered Vassals instead; killed by test_henrys_proclamation_shifts_yorkist_vassals |
| 2440 | 182 | cmp IsNot->Is L182 | GAP (killed) | service-marker presence test inverted; killed by test_henrys_proclamation_shifts_yorkist_vassals |
| 1368 | 194 | bool And->Or L194 | GAP (killed) | without Edward IV in the scenario, Y26 must be a no-effect (mutant crashes); killed by test_dubious_clarence |
| 4512 | 198 | int 0->1 L198 | GAP (killed) | Y26 extra_spend default 0->1 overspends the Influence check; killed by test_dubious_clarence (spent==1) |
| 2493 | 211 | cmp Eq->NotEq L211 | GAP (killed) | L27 would target non-Mustered Vassals (owner map empty -> no-effect); killed by test_aragne_targets_and_need |
| 2494 | 211 | cmp IsNot->Is L211 | GAP (killed) | on_lord presence test inverted; killed by test_aragne_targets_and_need |
| 1405 | 216 | bool And->Or L216 | GAP (killed) | Lancastrian Lords' Special Vassals would become L27 targets, changing the required selection count; killed by test_aragne_targets_and_need |
| 1412 | 221 | int 2->3 L221 | GAP (killed) | selection count min(2,..)->min(3,..) demands a third Vassal; killed by test_aragne_targets_and_need |
| 2544 | 231 | cmp In->NotIn L231 | GAP (killed) | a failed check on a regular Vassal would take the Special-Vassal discard path instead of Disbanding to the Calendar; killed by test_aragne_targets_and_need |
| 2586 | 251 | bool And->Or L251 | GAP (killed) | Warwick's Propaganda could strip Favour from non-Yorkist Strongholds; killed by test_warwicks_propaganda (not_yorkist) |
| 3690 | 257 | int 0->1 L257 | GAP (killed) | with favour_extra==1 the extra marker must come off first; killed by test_warwicks_propaganda |
| 3725 | 277 | bool And->Or L277 | GAP (killed) | while-condition and->or strips ALL Troops instead of 2; killed by test_welsh_rebellion_removes_two_troops_or_disbands |
| 4632 | 277 | cmp Lt->LtE L277 | GAP (killed) | removes 3 Troops (taken<2 -> <=2); killed by test_welsh_rebellion_removes_two_troops_or_disbands |
| 4633 | 277 | cmp Gt->GtE L277 | GAP (killed) | forces>0 -> >=0 drives a Troop count negative; killed by test_welsh_rebellion_removes_two_troops_or_disbands |
| 5248 | 277 | int 2->3 L277 | GAP (killed) | removes 3 Troops (2->3); killed by test_welsh_rebellion_removes_two_troops_or_disbands |
| 5599 | 277 | int 0->1 L277 | EQUIVALENT | ambiguous position: the get default is never read (t iterates existing force keys); the other 0 (>0 -> >1) is killed by test_welsh_rebellion_removes_two_troops_or_disbands - both verified |
| 4636 | 278 | int 1->2 L278 | GAP (killed) | removes 2 Troops per loop pass (4 total, and can go negative); killed by test_welsh_rebellion_removes_two_troops_or_disbands |
| 5605 | 287 | int 0->1 L287 | GAP (killed) | Troop-less detection corrupted -> Lord not Disbanded (L25); killed by test_welsh_rebellion_removes_two_troops_or_disbands; both 0-positions verified |
| 648 | 294 | int 0->1 L294 | GAP (killed) | favour-removal counter starts at 1 -> only one marker removed; killed by test_welsh_rebellion_favour_branch |
| 1522 | 296 | cmp GtE->Gt L296 | GAP (killed) | n>=2 -> n>2 removes a third Favour; killed by test_welsh_rebellion_favour_branch |
| 2660 | 296 | int 2->3 L296 | GAP (killed) | cap 2->3 Favour removals; killed by test_welsh_rebellion_favour_branch |
| 1524 | 298 | cmp Eq->NotEq L298 | GAP (killed) | removes Favour from NON-Yorkist Welsh Strongholds; killed by test_welsh_rebellion_favour_branch |
| 2668 | 300 | int 1->2 L300 | GAP (killed) | counter += 2 -> only one marker removed; killed by test_welsh_rebellion_favour_branch |
| 1541 | 308 | cmp LtE->Lt L308 | GAP (killed) | <=2 -> <2 rejects a legal two-target play; killed by test_wilful_disobedience_and_robins_rebellion |
| 2683 | 308 | int 2->3 L308 | GAP (killed) | cap 2->3 accepts a third target; killed by test_wilful_disobedience_and_robins_rebellion (bad_count) |
| 2700 | 315 | int 2->3 L315 | EQUIVALENT | targets[:2] vs [:3] is identical because the <=2 require already bounds len(targets) |
| 2706 | 317 | bool And->Or L317 | GAP (killed) | target near BOTH sides' Lords would qualify; killed by test_wilful_disobedience_and_robins_rebellion (bad_target) |
| 1592 | 334 | cmp LtE->Lt L334 | GAP (killed) | <=3 -> <3 rejects a legal three-marker play (L31); killed by test_wilful_disobedience_and_robins_rebellion |
| 2738 | 334 | int 3->4 L334 | GAP (killed) | cap 3->4 markers; killed by test_wilful_disobedience_and_robins_rebellion (too_many) |
| 2789 | 361 | cmp Eq->NotEq L361 | GAP (killed) | Tudor Banners would no-effect while Henry Tudor IS Mustered; killed by test_tudor_banners_and_yorkist_parade |
| 2791 | 363 | cmp Eq->NotEq L363 | GAP (killed) | friendly-Stronghold precondition inverted; killed by test_tudor_banners_and_yorkist_parade |
| 1679 | 386 | bool Or->And L386 | GAP (killed) | non-Yorkist Lords would Tax under Y10; killed by test_tax_collectors (henry_vi coin unchanged); both or positions verified killed |
| 3940 | 391 | cmp In->NotIn L391 | GAP (killed) | vassal-Seat Tax targets lost (v in regular inverted); killed by test_tax_collectors (ipswich) |
| 1689 | 392 | bool Or->And L392 | GAP (killed) | a Mustered Lord in an Exile box (location None) could Tax its Seat; killed by test_tax_collectors (march unchanged) |
| 3949 | 394 | cmp In->NotIn L394 | GAP (killed) | target in vassal_seats inverted -> vassal-Seat Tax rejected; killed by test_tax_collectors |
| 3984 | 410 | int 0->1 L410 | LOW | tax-yield coin default only read for Strongholds without a tax entry; all legal Y10 targets have one in shipped data |
| 3989 | 411 | int 0->1 L411 | GAP (killed) | keyless Lord gets a phantom base Coin; killed by test_tax_collectors (coin==2 exactly) |
| 2905 | 414 | const True->False L414 | LOW | result-field only (success flag in the taxes dict); killed anyway by test_tax_collectors' full-dict assert |
| 1789 | 456 | bool Or->And L456 | LOW | active_events entries always carry both card and side, so the or->and skip guard never sees the divergent input |
| 3000 | 483 | bool And->Or L483 | GAP (killed) | Rebel Supply Depot at a non-Port (location truthy suffices); killed by test_rebel_supply_depot (not_at_port) |
| 4096 | 485 | int 0->1 L485 | GAP (killed) | keyless Lord gets a phantom base Provender; killed by test_rebel_supply_depot (provender==4) |
| 1839 | 487 | int 4->5 L487 | LOW | result-field only (provender_each in the returned dict); killed anyway by test_rebel_supply_depot's result assert |
| 1840 | 487 | const True->False L487 | LOW | result-field only (ignore_next_feed in the returned dict; the state flag is set on L486); killed anyway by test_rebel_supply_depot's result assert |
| 1880 | 508 | const True->False L508 | LOW | result-field only ({'free_action': True}); the extra Command action is granted on the preceding lines regardless |
| 1896 | 516 | bool And->Or L516 | GAP (killed) | Sun in Splendour could re-Muster an already-Mustered Edward IV (resetting his mat); killed by test_sun_in_splendour_musters_edward |
| 931 | 533 | const False->True L533 | GAP (killed) | Mustered Edward's cylinder wrongly stays Exile-marked in Calendar bookkeeping; killed by test_sun_in_splendour_musters_edward |
| 3112 | 544 | bool And->Or L544 | GAP (killed) | any Mustered Lord at London would satisfy Y20's York/Warwick requirement; killed by test_tudor_banners_and_yorkist_parade |
| 4172 | 544 | cmp In->NotIn L544 | GAP (killed) | York/Warwick excluded from their own requirement; killed by test_tudor_banners_and_yorkist_parade |
| 3214 | 593 | bool And->Or L593 | GAP (killed) | any same-side pending Event would mark a standalone play as drawn, duplicating the card into the draw pile; killed by test_play_event_pending_scope_and_first_levy |
| 3229 | 598 | const True->False L598 | LOW | result-field only ({'active': True}); the Y34 Event is appended to active_events regardless |
| 3261 | 622 | cmp Eq->NotEq L622 | GAP (killed) | first-Levy detection inverted -> Arts of War would advance to pay on the first Levy; killed by test_play_event_pending_scope_and_first_levy |
| 4296 | 622 | bool Or->And L622 | GAP (killed) | first_box or turn_box -> and makes every later Levy look like the first (muster instead of pay); killed by test_play_event_pending_scope_and_first_levy |
