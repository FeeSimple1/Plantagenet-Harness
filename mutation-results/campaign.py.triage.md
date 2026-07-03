# Mutation triage: src/plantagenet/campaign.py

Survivors triaged: 113 (plus 28 uncovered sites, not triaged beyond counting).

- **GAP-killed: 92** - behavioral gaps now pinned by tests/test_mutation_kills_campaign.py (20 tests; every kill verified by applying the mutation, watching the test fail, and reverting).
- **GAP-open: 2** - behavioral but scenario/Capability-gated; left classified under the 20-test cap.
- **EQUIVALENT: 7**
- **LOW: 12** (log/result-field only, or unreachable-in-practice states)

| site | line | desc | verdict | reason |
|---|---|---|---|---|
| 509 | 138 | bool Or->And L138 | GAP-killed | killed by test_reveal_advances_one_card_and_skips_offmap_lord |
| 545 | 174 | int 1->2 L174 | GAP-killed | killed by test_reveal_advances_one_card_and_skips_offmap_lord |
| 549 | 176 | int 0->1 L176 | LOW | actions_remaining is overwritten by the next _reveal on every continuing path; at step 'end' the step guard blocks all commands |
| 584 | 216 | bool And->Or L216 | GAP-killed | killed by test_forage_friendly_with_enemy_adjacent_rolls |
| 593 | 224 | int 1->2 L224 | GAP-killed | killed by test_forage_thresholds |
| 595 | 225 | int 0->1 L225 | LOW | result 'provender_added' on a FAILED forage only; no assets change |
| 643 | 271 | int 0->1 L271 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 723 | 344 | bool And->Or L344 | LOW | needs a Special Vassal whose Capability card was already removed elsewhere (stale state) to differ |
| 741 | 360 | bin Add->Sub L360 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 1133 | 84 | bool And->Or L84 | GAP-killed | killed by test_begin_campaign_grants_nothing_without_stafford_estates |
| 1160 | 97 | bool And->Or L97 | LOW | reachable states still raise (plan_already_built), or the pre-campaign path raises AttributeError instead of IllegalAction; error path only |
| 1256 | 140 | int 0->1 L140 | LOW | actions_remaining=1 with active_lord None is unusable - _active_command_lord raises no_active_lord first |
| 1271 | 149 | bool And->Or L149 | LOW | wrong-step guard: misuse raises differently (no_active_lord / AttributeError) but every legal path is unchanged |
| 1313 | 167 | bool And->Or L167 | LOW | wrong-step guard for end_activation; only an illegal call reaches the difference |
| 1401 | 213 | cmp Eq->NotEq L213 | GAP-killed | killed by test_forage_friendly_with_enemy_adjacent_rolls |
| 1403 | 213 | const False->True L213 | GAP-killed | killed by test_forage_exile_box |
| 1418 | 223 | cmp LtE->Lt L223 | GAP-killed | killed by test_forage_thresholds |
| 1514 | 276 | bin Mult->FloorDiv L276 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 1530 | 281 | cmp Eq->NotEq L281 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 1538 | 285 | bin Mult->FloorDiv L285 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 1547 | 294 | bool And->Or L294 | LOW | needs a second concurrently-Captured Lord held by a different captor; only Henry VI is capturable in these scenarios |
| 1611 | 331 | bin Sub->Add L331 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 1645 | 357 | int 0->1 L357 | EQUIVALENT | vassals.json defines 'service' for every regular Vassal and state.vassals holds only regular Vassals; default dead |
| 1656 | 360 | bin Sub->Add L360 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 1668 | 370 | bool And->Or L370 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 1700 | 397 | cmp LtE->Lt L397 | EQUIVALENT | at amount == 0 the loop body computes take = min(provender, 0) = 0 and subtracts nothing |
| 1806 | 485 | bool And->Or L485 | LOW | extra candidates need a stale calendar_box on a non-Calendar Lord (always cleared) or a Calendar Lord with box None (never) |
| 1831 | 507 | int 0->1 L507 | GAP-killed | killed by test_tides_of_war_exact_points |
| 1863 | 540 | cmp NotEq->Eq L540 | GAP-killed | killed by test_tides_of_war_exact_points |
| 2083 | 732 | bool And->Or L732 | GAP-killed | killed by test_end_campaign_guard_and_reset |
| 2208 | 804 | int 0->1 L804 | GAP-killed | killed by test_end_campaign_guard_and_reset |
| 2212 | 806 | const False->True L806 | GAP-killed | killed by test_end_campaign_guard_and_reset |
| 2214 | 807 | const False->True L807 | GAP-killed | killed by test_end_campaign_guard_and_reset |
| 2287 | 84 | cmp Eq->NotEq L84 | GAP-open | Stafford Estates grant would go to a non-Mustered holder; needs L22 in play at begin_campaign |
| 2352 | 111 | bool And->Or L111 | GAP-killed | killed by test_plan_validation |
| 2364 | 115 | int 1->2 L115 | GAP-killed | killed by test_plan_validation |
| 2366 | 116 | cmp LtE->Lt L116 | GAP-killed | killed by test_plan_validation |
| 2539 | 186 | cmp Eq->NotEq L186 | LOW | result 'next_side' field only |
| 2585 | 210 | bool And->Or L210 | GAP-killed | killed by test_forage_thresholds |
| 2608 | 222 | bool Or->And L222 | GAP-killed | killed by test_forage_thresholds |
| 2609 | 222 | int 3->4 L222 | GAP-killed | killed by test_forage_thresholds |
| 2610 | 222 | int 4->5 L222 | GAP-killed | killed by test_forage_thresholds |
| 2635 | 232 | cmp Eq->NotEq L232 | GAP-killed | killed by test_forage_exile_box |
| 2690 | 259 | const True->False L259 | GAP-killed | killed by test_forage_friendly_with_enemy_adjacent_rolls |
| 2716 | 276 | int 2->3 L276 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 2743 | 283 | cmp Eq->NotEq L283 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 2747 | 285 | int 2->3 L285 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 2771 | 300 | const False->True L300 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 2817 | 331 | int 6->7 L331 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 2856 | 360 | int 6->7 L360 | GAP-killed | killed by test_disband_lord_vassal_and_captive |
| 2935 | 416 | const False->True L416 | GAP-killed | killed by test_feed_shortfall_pillages_then_disbands |
| 2952 | 426 | bool And->Or L426 | GAP-killed | killed by test_feed_shortfall_pillages_then_disbands |
| 2968 | 434 | bin Add->Sub L434 | GAP-killed | killed by test_feed_shortfall_pillages_then_disbands |
| 3050 | 501 | bool And->Or L501 | EQUIVALENT | every special_rules entry in all scenario files and grand-scenario wars is a dict with a 'name' key, so both operands agree on all real data |
| 3132 | 559 | int 3->4 L559 | GAP-open | Queen Regent would award +4 instead of +3; needs the Warwick's Rebellion scenario with Margaret at London |
| 3243 | 628 | cmp LtE->Lt L628 | GAP-killed | killed by test_victory_threshold_boundary |
| 3279 | 656 | cmp GtE->Gt L656 | GAP-killed | killed by test_victory_threshold_boundary |
| 3286 | 660 | bool Or->And L660 | GAP-killed | killed by test_test_of_arms_only_at_campaign_end |
| 3351 | 700 | cmp LtE->Lt L700 | GAP-killed | killed by test_disembark_shipwreck_and_landing |
| 3371 | 726 | cmp In->NotIn L726 | GAP-killed | killed by test_disembark_shipwreck_and_landing |
| 3435 | 753 | const True->False L753 | LOW | result 'waste' flag only; _waste itself already ran |
| 3500 | 786 | int 0->1 L786 | GAP-killed | killed by test_waste_resets_coin_to_setup |
| 3563 | 55 | int 9->10 L55 | GAP-killed | killed by test_season_grow_waste_boxes |
| 3564 | 55 | int 14->15 L55 | GAP-killed | killed by test_season_grow_waste_boxes |
| 3568 | 55 | int 10->11 L55 | GAP-killed | killed by test_season_grow_waste_boxes |
| 3686 | 115 | int 0->1 L115 | GAP-killed | killed by test_plan_validation |
| 3856 | 210 | cmp Eq->NotEq L210 | GAP-killed | killed by test_forage_thresholds |
| 3857 | 211 | cmp Eq->NotEq L211 | GAP-killed | killed by test_forage_thresholds |
| 3874 | 222 | cmp Eq->NotEq L222 | GAP-killed | killed by test_forage_thresholds |
| 3889 | 228 | int 0->1 L228 | GAP-killed | killed by test_forage_exile_box |
| 3935 | 273 | int 0->1 L273 | GAP-killed | killed by test_pillage_yields_influence_and_favour |
| 4093 | 399 | int 0->1 L399 | GAP-killed | killed by test_feed_needs_and_sharing |
| 4099 | 400 | int 0->1 L400 | GAP-killed | killed by test_feed_needs_and_sharing |
| 4120 | 419 | int 6->7 L419 | GAP-killed | killed by test_feed_needs_and_sharing |
| 4212 | 486 | cmp Gt->GtE L486 | EQUIVALENT | at calendar_box == cur the branch assigns cur - a no-op |
| 4215 | 488 | bool And->Or L488 | GAP-killed | killed by test_foreign_haven_shift_boundaries |
| 4256 | 516 | int 1->2 L516 | GAP-killed | killed by test_tides_of_war_exact_points |
| 4402 | 593 | int 1->2 L593 | GAP-killed | killed by test_tides_deeds_of_charity |
| 4411 | 597 | int 0->1 L597 | GAP-killed | killed by test_tides_deeds_of_charity |
| 4494 | 662 | cmp In->NotIn L662 | GAP-killed | killed by test_test_of_arms_only_at_campaign_end |
| 4518 | 672 | cmp Gt->GtE L672 | EQUIVALENT | the li == yi case already returned in the preceding FAQ-#5 tie branch, so equality is unreachable at this comparison |
| 4537 | 691 | cmp Eq->NotEq L691 | GAP-killed | killed by test_disembark_shipwreck_and_landing |
| 4561 | 702 | bin Add->Sub L702 | GAP-killed | killed by test_disembark_shipwreck_and_landing |
| 4790 | 108 | const True->False L108 | EQUIVALENT | the pass flag is only read by _reveal, which treats entries without a 'lord' as Pass regardless; succession's plan rewrite reads only entry['lord'] |
| 4924 | 234 | cmp Eq->NotEq L234 | GAP-killed | killed by test_forage_exile_box |
| 5074 | 423 | int 0->1 L423 | GAP-killed | killed by test_feed_shortfall_pillages_then_disbands |
| 5109 | 436 | cmp IsNot->Is L436 | GAP-killed | killed by test_feed_shortfall_pillages_then_disbands |
| 5173 | 488 | cmp Gt->GtE L488 | EQUIVALENT | at calendar_box == cur+1 the branch assigns cur+1 - a no-op |
| 5206 | 514 | bool And->Or L514 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5234 | 529 | bool And->Or L529 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5244 | 537 | int 1->2 L537 | LOW | uniformly doubles both sides' counts; leader and inequality predicate unchanged, only the detail log differs |
| 5393 | 642 | cmp Eq->NotEq L642 | GAP-killed | killed by test_victory_51_presence_via_next_turn_exile |
| 5394 | 642 | cmp Eq->NotEq L642 | GAP-killed | killed by test_victory_51_presence_via_next_turn_exile |
| 5396 | 643 | cmp Eq->NotEq L643 | GAP-killed | killed by test_victory_51_presence_via_next_turn_exile |
| 5512 | 718 | const True->False L718 | GAP-killed | killed by test_disembark_shipwreck_and_landing |
| 5842 | 488 | bin Add->Sub L488 | GAP-killed | killed by test_foreign_haven_shift_boundaries |
| 5866 | 514 | cmp Eq->NotEq L514 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5867 | 514 | cmp In->NotIn L514 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5868 | 515 | cmp Eq->NotEq L515 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5897 | 529 | cmp Eq->NotEq L529 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5898 | 529 | cmp Eq->NotEq L529 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5899 | 530 | cmp Eq->NotEq L530 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5913 | 538 | bool And->Or L538 | GAP-killed | killed by test_tides_of_war_exact_points |
| 5926 | 550 | bool And->Or L550 | GAP-killed | killed by test_tides_of_war_exact_points |
| 6001 | 643 | bin Add->Sub L643 | GAP-killed | killed by test_victory_51_presence_via_next_turn_exile |
| 6083 | 713 | int 0->1 L713 | GAP-killed | killed by test_disembark_shipwreck_and_landing |
| 6204 | 429 | int 0->1 L429 | GAP-killed | killed by test_feed_shortfall_pillages_then_disbands |
| 6240 | 488 | int 1->2 L488 | GAP-killed | killed by test_foreign_haven_shift_boundaries |
| 6295 | 538 | cmp Eq->NotEq L538 | GAP-killed | killed by test_tides_of_war_exact_points |
| 6296 | 538 | cmp Eq->NotEq L538 | GAP-killed | killed by test_tides_of_war_exact_points |
| 6313 | 550 | cmp Eq->NotEq L550 | GAP-killed | killed by test_tides_of_war_exact_points |
| 6314 | 551 | cmp In->NotIn L551 | GAP-killed | killed by test_tides_of_war_exact_points |
| 6356 | 643 | int 1->2 L643 | GAP-killed | killed by test_victory_51_presence_via_next_turn_exile |
