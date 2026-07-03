# Mutation triage: src/plantagenet/commands.py

Survivors triaged: 147 (plus 34 uncovered sites, not triaged beyond counting).

- **GAP-killed: 87** - behavioral gaps now pinned by tests/test_mutation_kills_commands.py (20 tests; every kill verified by applying the mutation, watching the test fail, and reverting).
- **GAP-open: 30** - behavioral in principle, mostly gated behind a specific Capability/Event (Y14/Y15/Y25/Y29/Y34/L4/L6/L10/L15) or intercept-group setups; left classified under the 20-test cap.
- **EQUIVALENT: 15**
- **LOW: 15** (log/result-field only, or unreachable-in-practice input)

| site | line | desc | verdict | reason |
|---|---|---|---|---|
| 667 | 172 | bool And->Or L172 | GAP-killed | killed by test_road_chain_needs_capability_or_event |
| 692 | 216 | cmp Gt->GtE L216 | EQUIVALENT | for a single mover the group-haul branch computes exactly the lone-lord trim (same _carts), so >=1 is identical |
| 783 | 333 | bool And->Or L333 | GAP-killed | killed by test_intercept_rules |
| 874 | 440 | bin Add->Sub L440 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 1018 | 642 | const False->True L642 | LOW | calendar_exile on a MUSTERED Lord is never read before _disband_lord/_release_captive overwrite it |
| 1048 | 664 | int 1->2 L664 | GAP-open | agitators would consume 2 actions instead of 1 (Y10 Capability action economy) |
| 1073 | 684 | int 1->2 L684 | GAP-killed | killed by test_merchants_targets_and_cost |
| 1103 | 716 | int 0->1 L716 | GAP-open | heralds would leave 1 action instead of consuming the full card (L4) |
| 1183 | 787 | int 0->1 L787 | LOW | initial way_cost only reaches finish_data['way_cost'], which tax_finish never reads |
| 1184 | 788 | cmp NotEq->Eq L788 | GAP-killed | killed by test_tax_remote_target_needs_route |
| 1196 | 801 | bool And->Or L801 | EQUIVALENT | Yorkist ctx is discarded by _naval_blockade_offers (side check); Lancastrian target==here yields route cost 0 so no Sea is marked used |
| 1201 | 812 | int 1->2 L812 | GAP-killed | killed by test_tax_costs_and_extra_spend |
| 1225 | 831 | int 0->1 L831 | LOW | coin_added=1 only survives into the result of a FAILED tax; assets unchanged |
| 1256 | 863 | bool And->Or L863 | GAP-killed | killed by test_parley_own_location_auto |
| 1265 | 880 | cmp Gt->GtE L880 | GAP-killed | killed by test_parley_sea_reach_needs_ship_and_same_sea_port |
| 1269 | 882 | bool And->Or L882 | GAP-killed | killed by test_parley_sea_reach_needs_ship_and_same_sea_port |
| 1275 | 890 | bool And->Or L890 | GAP-killed | killed by test_parley_remote_spend_math |
| 1324 | 933 | bool And->Or L933 | GAP-killed | killed by test_parley_sea_reach_needs_ship_and_same_sea_port |
| 1353 | 958 | bool Or->And L958 | GAP-killed | killed by test_supply_route_rules |
| 1527 | 64 | bool And->Or L64 | EQUIVALENT | only widens the candidate Sea set; _naval_blockade_offers independently re-verifies a mustered Yorkist Y15 Lord at a Port on each ctx Sea |
| 1669 | 173 | bool Or->And L173 | GAP-killed | killed by test_road_chain_needs_capability_or_event |
| 1728 | 216 | int 1->2 L216 | GAP-killed | killed by test_group_haul_math |
| 1737 | 226 | cmp Gt->GtE L226 | EQUIVALENT | at provender == carts the assignment provender = carts is a no-op |
| 1760 | 238 | bool Or->And L238 | LOW | differs only for an intercept decision supplied while marching onto an enemy-held Locale - contradictory input legal_moves never emits |
| 1772 | 246 | int 0->1 L246 | BUG-FIXED | clean code fell through to the tail decrement ending at -1; fixed 2026-07-02c, pinned at 0 |
| 1779 | 253 | int 0->1 L253 | LOW | actions_remaining=1 is overwritten to 0 by march_finish on every resume path; visible only while the reaction window is pending |
| 1968 | 373 | cmp LtE->Lt L373 | GAP-killed | killed by test_intercept_rules |
| 1995 | 389 | int 0->1 L389 | EQUIVALENT | _apply_burgundians' return value is ignored at all three call sites |
| 2009 | 395 | int 0->1 L395 | EQUIVALENT | forces.json defines 'pool' for handgunners, so the .get default is dead code |
| 2016 | 397 | int 0->1 L397 | GAP-open | burgundians would grant a Handgunner past the pool floor; needs Y14/Y23 with exhausted pool |
| 2022 | 400 | const True->False L400 | GAP-open | burgundians first-time flag never set: repeat grants after losses; needs Y14/Y23 |
| 2035 | 413 | bool And->Or L413 | GAP-killed | killed by test_march_from_exile_boxes |
| 2172 | 509 | const False->True L509 | EQUIVALENT | on the into_sea path dest_has_enemy is only read by sail_finish after its into_sea early return |
| 2188 | 538 | int 2->3 L538 | GAP-killed | killed by test_sail_great_ships_capacity |
| 2189 | 538 | int 1->2 L538 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 2192 | 539 | int 1->2 L539 | GAP-killed | killed by test_sail_group_rules |
| 2340 | 621 | bool And->Or L621 | GAP-open | exile_pact would work for any Yorkist without the Y8 Event |
| 2472 | 680 | bool And->Or L680 | GAP-killed | killed by test_merchants_targets_and_cost |
| 2535 | 711 | bool And->Or L711 | GAP-open | heralds could target a Mustered Lord (sets calendar_box on a mustered cylinder); needs L4 |
| 2592 | 736 | bool And->Or L736 | GAP-killed | killed by test_sail_at_sea_to_adjacent_sea_port |
| 2688 | 789 | cmp Gt->GtE L789 | GAP-killed | killed by test_tax_route_by_ship_needs_a_ship |
| 2774 | 837 | bool And->Or L837 | GAP-killed | killed by test_tax_own_seat_yield_exact |
| 2879 | 890 | cmp Eq->NotEq L890 | GAP-open | Dorset auto-parley for a non-Devon Lord at Exeter; needs Y29 Event active |
| 2880 | 890 | cmp Eq->NotEq L890 | GAP-open | Dorset auto-parley for Devon away from Exeter; needs Y29 Event active |
| 2884 | 892 | int 0->1 L892 | EQUIVALENT (post-fix) | Dorset now skips check_influence entirely, so the way value is dead code on that path (verified: full suite passes under the mutant) |
| 2885 | 892 | int 1->2 L892 | GAP-killed | killed by test_parley_remote_spend_math |
| 2897 | 898 | bool And->Or L898 | EQUIVALENT | widened used_seas has no Y15 Lord on the extra Sea, so no reaction offers can appear (see 1527) |
| 2902 | 901 | int 0->1 L901 | GAP-open | New Act of Parliament parley would leave 1 action instead of ending the card; needs L10 Event |
| 3007 | 940 | cmp Eq->NotEq L940 | GAP-killed | killed by test_parley_own_location_auto |
| 3013 | 945 | cmp Eq->NotEq L945 | LOW | _fav_desc builds a log string only |
| 3051 | 969 | bool And->Or L969 | GAP-open | Great Ships supply BFS would add all-port hops from non-port nodes; needs L6/Y6 and a crafted route |
| 3109 | 999 | int 2->3 L999 | GAP-killed | killed by test_supply_route_rules |
| 3115 | 1003 | cmp NotEq->Eq L1003 | GAP-open | Scotland-box Lords would need Ship+Port supply while continental boxes skip the check; error-code + Scotland overland supply path |
| 3139 | 1017 | bool And->Or L1017 | GAP-killed | killed by test_supply_by_ship |
| 3158 | 1038 | int 1->2 L1038 | GAP-killed | killed by test_supply_by_ship |
| 3186 | 1051 | int 0->1 L1051 | EQUIVALENT | strongholds.json defines supply.provender for every locale type; default dead |
| 3203 | 1056 | bool And->Or L1056 | GAP-killed | killed by test_supply_route_rules |
| 3372 | 82 | cmp Gt->GtE L82 | GAP-open | Naval Blockade would fire on Seas whose blocking does NOT raise the route cost; needs Y15 in play |
| 3465 | 150 | int 0->1 L150 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 3505 | 174 | bool And->Or L174 | GAP-killed | killed by test_road_chain_needs_capability_or_event |
| 3558 | 202 | cmp Eq->NotEq L202 | GAP-killed | killed by test_march_group_validation |
| 3568 | 214 | int 0->1 L214 | GAP-killed | killed by test_road_march_cost_and_haul |
| 3570 | 215 | bin Mult->FloorDiv L215 | GAP-killed | killed by test_road_march_cost_and_haul |
| 3580 | 220 | cmp LtE->Lt L220 | EQUIVALENT | at excess == 0 the loop iterates but drop = min(0, provender) = 0; no state change |
| 3585 | 223 | bin Sub->Add L223 | GAP-killed | killed by test_group_haul_math |
| 3758 | 310 | const True->False L310 | LOW | approach_cancelled result-field default; log only |
| 3852 | 354 | cmp Eq->NotEq L354 | GAP-open | a Lieutenant could bring a Marshal when Intercepting; needs an intercept-group setup |
| 3897 | 377 | cmp Gt->GtE L377 | EQUIVALENT | at provender == carts the assignment is a no-op (intercept haul) |
| 3902 | 380 | const True->False L380 | GAP-killed | killed by test_intercept_rules |
| 3936 | 397 | int 2->3 L397 | EQUIVALENT | handgunners pool is 2, so pool - in_play <= 2 and min(3, x) == min(2, x) |
| 3937 | 397 | bin Sub->Add L397 | GAP-open | burgundians pool arithmetic pool+in_play; needs Y14/Y23 with units already in play |
| 3959 | 413 | cmp Eq->NotEq L413 | GAP-killed | killed by test_march_from_exile_boxes |
| 3960 | 413 | cmp In->NotIn L413 | GAP-killed | killed by test_march_from_exile_boxes |
| 3973 | 419 | const False->True L419 | GAP-killed | killed by test_road_march_cost_and_haul |
| 4094 | 497 | cmp Eq->NotEq L497 | GAP-open | a Lieutenant could lead a Marshal in a Group Sail |
| 4165 | 547 | int 0->1 L547 | LOW | a Mustered Lord always has >=1 Force unit so the forces term already forces need >= ceil(1/2); phantom provender cannot raise the max |
| 4169 | 548 | int 0->1 L548 | LOW | same as 4165 for the carts term |
| 4262 | 595 | cmp NotEq->Eq L595 | LOW | result 'group' listing only; movers were already applied to the board |
| 4452 | 680 | cmp LtE->Lt L680 | GAP-killed | killed by test_merchants_targets_and_cost |
| 4457 | 682 | int 0->1 L682 | GAP-killed | killed by test_merchants_targets_and_cost |
| 4523 | 714 | int 0->1 L714 | GAP-open | heralds default extra_spend becomes 1 (extra Influence point); needs L4 |
| 4589 | 747 | cmp Eq->NotEq L747 | GAP-open | Chamberlains would test vassal seats with != (deplete own seat / spare others); needs L10 Capability |
| 4646 | 772 | cmp In->NotIn L772 | GAP-killed | killed by test_tax_costs_and_extra_spend |
| 4666 | 789 | int 0->1 L789 | GAP-killed | killed by test_tax_route_by_ship_needs_a_ship |
| 4690 | 796 | int 0->1 L796 | GAP-killed | killed by test_tax_costs_and_extra_spend |
| 4710 | 805 | cmp Gt->GtE L805 | EQUIVALENT | only flips hs2 at 0 Ships, where sea hops never enter either route; used_seas identical in all reachable states |
| 4773 | 833 | int 0->1 L833 | EQUIVALENT | strongholds.json defines tax.coin for every locale type; default dead |
| 4863 | 867 | bin Sub->Add L867 | GAP-killed | killed by test_parley_own_location_auto |
| 4893 | 880 | int 0->1 L880 | GAP-killed | killed by test_parley_sea_reach_needs_ship_and_same_sea_port |
| 4908 | 886 | int 0->1 L886 | GAP-killed | killed by test_parley_remote_spend_math |
| 5099 | 969 | cmp In->NotIn L969 | GAP-open | Great Ships supply BFS port-hop membership flipped; needs L6/Y6 and a crafted route |
| 5108 | 976 | cmp Eq->NotEq L976 | GAP-killed | killed by test_supply_route_rules |
| 5110 | 978 | bool And->Or L978 | GAP-killed | killed by test_supply_route_rules |
| 5174 | 1004 | bool And->Or L1004 | LOW | every input that the guard rejects still raises IllegalAction downstream (no_route/ships_need_port); only the error code differs |
| 5201 | 1015 | cmp Gt->GtE L1015 | GAP-killed | killed by test_supply_by_ship |
| 5221 | 1023 | bool And->Or L1023 | EQUIVALENT | widened used_seas has no Y15 Lord on that Sea, so no reaction offers can appear (see 1527) |
| 5261 | 1042 | const False->True L1042 | GAP-killed | killed by test_supply_by_ship |
| 5358 | 1077 | int 0->1 L1077 | GAP-killed | killed by test_supply_by_ship |
| 5545 | 138 | cmp Eq->NotEq L138 | GAP-open | Sharing co-location via a DIFFERENT Exile box would pass; needs exile-box Sharing setup |
| 5548 | 139 | cmp Eq->NotEq L139 | GAP-open | Sharing co-location via a different Sea would pass; needs at-sea Sharing setup |
| 5591 | 174 | cmp Eq->NotEq L174 | GAP-killed | killed by test_road_chain_needs_capability_or_event |
| 5621 | 198 | bool And->Or L198 | GAP-killed | killed by test_march_group_validation |
| 5646 | 215 | int 2->3 L215 | GAP-killed | killed by test_road_march_cost_and_haul |
| 5656 | 220 | int 0->1 L220 | GAP-killed | killed by test_group_haul_math |
| 5671 | 226 | int 0->1 L226 | LOW | for a keyless Lord it merely writes an explicit provender: 0 entry; every reader uses .get(..., 0) |
| 5719 | 255 | bool And->Or L255 | GAP-open | Approach ctx target_lords widened to nearly all Lords; observable only via King's Parley (L15) eligibility |
| 5835 | 335 | bool And->Or L335 | GAP-killed | killed by test_intercept_rules |
| 5853 | 350 | bool And->Or L350 | GAP-open | intercept group member validation weakened; needs an intercept-group setup |
| 5901 | 376 | int 0->1 L376 | GAP-killed | killed by test_intercept_rules |
| 5962 | 414 | const True->False L414 | GAP-killed | killed by test_march_from_exile_boxes |
| 5983 | 439 | cmp In->NotIn L439 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 6061 | 493 | bool And->Or L493 | GAP-killed | killed by test_sail_group_rules |
| 6092 | 517 | cmp In->NotIn L517 | GAP-killed | killed by test_sail_at_sea_to_adjacent_sea_port |
| 6152 | 550 | bin Mult->FloorDiv L550 | GAP-killed | killed by test_sail_great_ships_capacity |
| 6155 | 551 | bin Mult->FloorDiv L551 | GAP-killed | killed by test_sail_great_ships_capacity |
| 6161 | 557 | cmp Eq->NotEq L557 | GAP-open | Owain Glyndwr would bar YORKIST (not Lancastrian) Sails into Wales; needs Y25 Event |
| 6356 | 680 | int 2->3 L680 | GAP-killed | killed by test_merchants_targets_and_cost |
| 6367 | 687 | int 2->3 L687 | EQUIVALENT | the bad_targets guard limits len(targets) <= 2, so targets[:3] == targets[:2] |
| 6501 | 789 | int 0->1 L789 | GAP-killed | killed by test_tax_route_by_ship_needs_a_ship |
| 6527 | 797 | int 1->2 L797 | GAP-killed | killed by test_tax_costs_and_extra_spend |
| 6528 | 797 | int 3->4 L797 | GAP-killed | killed by test_tax_costs_and_extra_spend |
| 6544 | 805 | int 0->1 L805 | EQUIVALENT | same argument as 4710 (default only matters at 0 Ships) |
| 6594 | 840 | int 0->1 L840 | GAP-killed | killed by test_tax_own_seat_yield_exact |
| 6641 | 867 | int 1->2 L867 | GAP-killed | killed by test_parley_own_location_auto |
| 6645 | 869 | int 1->2 L869 | GAP-open | An Honest Tale own-location parley would cost 2 Influence instead of 1; needs Y34 Event |
| 6656 | 872 | int 0->1 L872 | GAP-killed | killed by test_parley_own_location_auto |
| 6683 | 887 | int 1->2 L887 | GAP-killed | killed by test_parley_remote_spend_math |
| 6684 | 887 | int 3->4 L887 | GAP-killed | killed by test_parley_remote_spend_math |
| 6731 | 918 | int 0->1 L918 | GAP-killed | killed by test_parley_remote_spend_math |
| 7178 | 151 | int 0->1 L151 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 7263 | 222 | int 0->1 L222 | GAP-killed | killed by test_group_haul_math |
| 7268 | 223 | int 0->1 L223 | GAP-killed | killed by test_group_haul_math |
| 7370 | 335 | cmp Eq->NotEq L335 | GAP-killed | killed by test_intercept_rules |
| 7417 | 377 | int 0->1 L377 | LOW | same as 5671 for the interceptor |
| 7528 | 492 | bool And->Or L492 | GAP-killed | killed by test_sail_group_rules |
| 7592 | 540 | int 0->1 L540 | GAP-killed | killed by test_sail_group_rules |
| 7601 | 542 | int 0->1 L542 | GAP-killed | killed by test_sail_group_rules |
| 7606 | 543 | int 0->1 L543 | GAP-killed | killed by test_sail_group_rules |
| 7617 | 549 | int 6->7 L549 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 7622 | 550 | int 2->3 L550 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 7627 | 551 | int 2->3 L551 | GAP-killed | killed by test_sail_ship_requirement_counts_vassals |
| 7871 | 805 | int 0->1 L805 | GAP-open | blockade recompute default-ship (second literal); observable only with Y15 in play |
| 7977 | 918 | int 1->2 L918 | GAP-open | An Honest Tale remote-parley surcharge doubled (discount -2); needs Y34 Event |
| 8350 | 269 | int 1->2 L269 | LOW | result 'group' listing (movers[2:]) only |
| 8867 | 217 | int 0->1 L217 | GAP-killed | killed by test_group_haul_math |
| 8896 | 260 | int 1->2 L260 | LOW | result 'group' listing in the approach finish_data only |
| 9095 | 979 | int 1->2 L979 | GAP-killed | killed by test_supply_route_rules |
