# Mutation triage: src/plantagenet/battle.py

Input: `mutation-results/battle.py.jsonl` — 170 survived sites triaged (35 `uncovered` sites noted but not triaged, per brief).

Killing tests: `tests/test_mutation_kills_battle.py` (25 test functions, all deterministic via seeds, state-roller peeking, or a `_SeqDice` stub monkeypatched onto `GameState.dice`).

Every verdict below was verified empirically: each mutation was hand-applied to a copy of the module, the kill suite re-run against it, and the source restored. GAP-killed = suite fails under the mutant; EQUIVALENT/LOW verdicts were confirmed to still survive the new suite and carry a one-line reason.

## Summary

| verdict | count |
|---|---|
| GAP-killed | 124 |
| GAP-open | 0 (19 killed 2026-07-02c; 969 proven equivalent) |
| EQUIVALENT | 19 |
| LOW | 7 |
| **total survived** | **170** |

Site-id/occurrence note: on lines where one literal occurs twice and only line-level descriptions exist (L406 `0->1`: 7511/9874; L795 `0->1`: 10089/10580), the two occurrences were tested separately; ids are assigned by AST order (condition before fallback). In both pairs one occurrence is killed and the other is provably equivalent, so the pair is fully accounted for either way.

## Per-site verdicts

| site | line | desc | verdict | reason |
|---|---|---|---|---|
| 559 | 100 | cmp In->NotIn L100 | GAP-killed | used Culverins Capability never leaves the Lord (double-discard); killed by count==1 |
| 3015 | 119 | bool Or->And L119 | GAP-killed | overland-route escape denied; killed by ely->lynn route sub-case |
| 5085 | 119 | cmp Eq->NotEq L119 | GAP-killed | escape granted to an unreachable remote port; killed by no-route sub-case |
| 5086 | 119 | cmp IsNot->Is L119 | GAP-killed | route test inverted; killed by no-route sub-case |
| 3029 | 131 | bool And->Or L131 | GAP-killed | crashes (list(None)) for special Vassals without Armour mods; killed by hastings case |
| 623 | 170 | bool Or->And L170 | GAP-killed | Y37 denied when tracing a route to Carlisle; killed by hexham route case |
| 1529 | 170 | cmp Eq->NotEq L170 | GAP-killed | Y37 granted with NO route to Carlisle; killed by hostile-Carlisle case |
| 634 | 178 | bool And->Or L178 | GAP-killed | L33 fires at any Friendly locale; killed by inland-york case |
| 9750 | 207 | int 0->1 L207 | GAP-killed | battle-cap Troops of a new type get +1 phantom unit; killed by count==2 |
| 8699 | 208 | int 0->1 L208 | GAP-killed | battle-cap-added type starts with 1 Rout; killed by routed==0 |
| 1585 | 215 | bool And->Or L215 | GAP-killed | Church Blessing Armour granted to every Lord; killed by prot==[1,3] assert |
| 7214 | 233 | bin Sub->Add L233 | EQUIVALENT | MaA Armour lo is always 1 and hi>=3, so max(lo+1, hi-1)==hi-1==max(lo-1, hi-1) |
| 8728 | 233 | int 1->2 L233 | EQUIVALENT | with lo==1, max(lo-2, hi-1)==hi-1 exactly as max(lo-1, hi-1) |
| 1603 | 237 | bool And->Or L237 | GAP-killed | yeomen granted without the Capability; killed by no-cap force assert |
| 5279 | 238 | cmp Eq->NotEq L238 | GAP-killed | opt-in set equality inverted; killed by not-opted-in assert |
| 8738 | 238 | const True->False L238 | GAP-killed | blanket {True} opt-in stops working; killed by fy.yeomen is True |
| 3226 | 249 | bool Or->And L249 | LOW | differs only if a mustered mat ever records retinue 0/missing or >1; scenario data always has retinue==1 |
| 5297 | 249 | int 1->2 L249 | LOW | differs only if a mustered mat ever records retinue 0/missing or >1; scenario data always has retinue==1 |
| 7237 | 249 | int 1->2 L249 | LOW | differs only if a mustered mat ever records retinue 0/missing or >1; scenario data always has retinue==1 |
| 1628 | 257 | const False->True L257 | GAP-killed | every Force starts fled -> all Death rolls -2; killed by death-roll-3 _ending test |
| 1637 | 261 | const False->True L261 | GAP-killed | every Force gets the Yeomen redirect without L31; killed by plain-force assert |
| 3283 | 278 | bin Add->Sub L278 | GAP-killed | Piquiers counter subtracts Militia Routs; killed by 2+1-Routs expiry assert |
| 7283 | 278 | int 0->1 L278 | GAP-killed | phantom Routed MaA expires Piquiers early; killed by militia-only force |
| 7286 | 278 | int 0->1 L278 | GAP-killed | phantom Routed Militia expires Piquiers early; killed by MaA-only force |
| 1685 | 302 | const True->False L302 | GAP-killed | legacy valour_lords=False becomes reroll-for-all; killed by no-reroll assert |
| 5411 | 310 | cmp NotIn->In L310 | GAP-killed | unit types missing from absorb_order become untargetable; killed by militia-order case |
| 7361 | 322 | cmp Gt->GtE L322 | GAP-killed | an absorb plan Routs an exhausted unit past its count; killed by routed==count assert |
| 5487 | 352 | cmp Eq->NotEq L352 | GAP-killed | Yeomen redirect keys on NON-Retinue hits; killed by retinue-hit redirect assert |
| 9842 | 367 | int 3->4 L367 | EQUIVALENT | zip with the 3-slot _FILL_ORDER truncates a 4th defender regardless of the slice |
| 5519 | 368 | int 3->4 L368 | GAP-killed | a 4th Defender vanishes instead of entering Reserve; killed by res_def==[d4] |
| 3443 | 369 | cmp In->NotIn L369 | GAP-killed | Attackers array opposite EMPTY slots; killed by apos=={1:a1} |
| 5532 | 372 | cmp NotIn->In L372 | GAP-killed | explicit attacker_positions duplicates positioned Lords into Reserve; killed directly |
| 3501 | 390 | bool Or->And L390 | GAP-killed | Routed Lords never leave the Array; killed by reposition d2-advance assert |
| 3514 | 395 | bool And->Or L395 | GAP-killed | held (Norfolk) reserves advanceable by choice; killed by held-reserve assert |
| 5612 | 406 | bool And->Or L406 | GAP-killed | an empty chosen wing leaves the Center unfilled; killed by fallback assert |
| 7511 | 406 | int 0->1 L406 | EQUIVALENT | tuple occurrence: center_from=0 falls back to [0,2] which tries wing 0 first, and cf=1 cannot pass "cf in pos" because slot 1 is empty by the guard |
| 7512 | 406 | int 2->3 L406 | GAP-killed | center_from=2 falls back to the left (both 2->3 occurrences die); killed by right-wing case |
| 9874 | 406 | int 0->1 L406 | GAP-killed | list occurrence: default Center fill skips the wing; killed by lone-wing cases (paired tuple occurrence 7511 is equivalent) |
| 3546 | 417 | bool And->Or L417 | EQUIVALENT | _reposition purges None/Routed entries from positions immediately before every _engagements call, so the filter never sees them |
| 3551 | 419 | bool And->Or L419 | EQUIVALENT | _reposition purges None/Routed entries from positions immediately before every _engagements call, so the filter never sees them |
| 1841 | 438 | bool And->Or L438 | GAP-killed | a unique nearest target can be overridden by flank choice; killed by 2-eng assert |
| 3589 | 438 | cmp Gt->GtE L438 | GAP-killed | a unique nearest target can be overridden by flank choice; killed by 2-eng assert |
| 3595 | 442 | bool And->Or L442 | GAP-killed | an out-of-range integer choice crashes (KeyError); killed by fallback assert |
| 5705 | 442 | cmp In->NotIn L442 | GAP-killed | a valid tie-breaking integer choice is ignored; killed by a1-with-d2 assert |
| 1886 | 462 | bool And->Or L462 | LOW | an attacker-only component needs an empty enemy front (held-solo-reserve edge); adds only an empty log entry with no strikes |
| 1912 | 478 | bool And->Or L478 | GAP-killed | Suspicion accepts a target outside the battle; killed by bad_suspicion code assert |
| 3745 | 506 | cmp Eq->NotEq L506 | GAP-killed | Vassal Loyalty modifier sign flipped; killed by direct +1/-1 asserts |
| 5915 | 557 | int 1->2 L557 | GAP-killed | For Trust strips two Vassal units from the old Lord; killed by count 2->1 assert |
| 7725 | 557 | int 0->1 L557 | EQUIVALENT | the old Lord holds the target Vassal, so count["vassal"] exists (get default dead) |
| 3872 | 559 | int 0->1 L559 | GAP-killed | the levied Vassal arrives already Routed; killed by routed==0 assert |
| 5971 | 578 | cmp GtE->Gt L578 | GAP-killed | flee_rounds round 1 rejected as illegal; killed by test_flee_rounds_accepts_round_one |
| 7751 | 578 | int 1->2 L578 | GAP-killed | flee_rounds round 1 rejected as illegal; killed by test_flee_rounds_accepts_round_one |
| 967 | 586 | bool Or->And L586 | GAP-open | engagement_order decision silently ignored (or-> and nulls a provided value) |
| 969 | 587 | bool Or->And L587 | EQUIVALENT | tie branch unreachable: 4.4.2 Reposition mandatorily fills the center (2,085-config sweep) |
| 971 | 588 | bool Or->And L588 | GAP-open | absorb_lords decision silently ignored |
| 973 | 589 | bool Or->And L589 | GAP-open | reposition decisions silently ignored |
| 975 | 590 | bool Or->And L590 | GAP-open | absorb_plan decisions silently ignored |
| 2173 | 594 | const True->False L594 | GAP-killed | Y36 break disabled by default swift_maneuver_end; killed by 1-engagement assert |
| 4085 | 641 | int 2->3 L641 | GAP-open | Regroup default Round becomes 3; needs a fork-oracle battle without "round" |
| 6161 | 669 | bool And->Or L669 | GAP-killed | Final Charge validation passes any Lord in the battle; killed by no_final_charge raise |
| 1061 | 672 | const False->True L672 | GAP-killed | Patrick active without playing the card; killed by exact one-die diff |
| 2289 | 685 | const True->False L685 | GAP-killed | playing Patrick has no effect; killed by exact two-dice diff |
| 1071 | 690 | const False->True L690 | GAP-killed | Warden/Talbot default ON without the Held Events; killed by seed-4 Somerset death |
| 6217 | 723 | bool And->Or L723 | GAP-killed | Norfolk is Late triggers with no other Yorkist; killed by solo-Norfolk battle |
| 7858 | 723 | cmp NotEq->Eq L723 | GAP-killed | Norfolk is Late triggers with no other Yorkist; killed by solo-Norfolk battle |
| 7859 | 723 | cmp Eq->NotEq L723 | GAP-killed | Norfolk is Late triggers with no other Yorkist; killed by solo-Norfolk battle |
| 7872 | 731 | cmp NotIn->In L731 | GAP-killed | Norfolk never returns from Reserve in Round 2; killed by Round-2 membership assert |
| 1110 | 739 | bool And->Or L739 | GAP-killed | loop-Or makes every battle run to the 60-Round cap; killed by draw test (len(rounds)==1) |
| 2376 | 739 | cmp Lt->LtE L739 | GAP-killed | emergency cap becomes 61 Rounds; killed by vanguard test (len(rounds)==60) |
| 4280 | 739 | int 60->61 L739 | GAP-killed | emergency cap becomes 61 Rounds; killed by vanguard test (len(rounds)==60) |
| 6264 | 745 | const True->False L745 | GAP-killed | Flee flag never set, so no -2 on the Death roll; killed by seed-7 e2e disband test |
| 6266 | 746 | const True->False L746 | GAP-killed | a fleeing Lord keeps fighting; killed by draw test (engagements must be empty) |
| 6283 | 755 | bool Or->And L755 | GAP-open | int-keyed per-Round reposition decisions ignored (str-key fallback nulls them) |
| 2395 | 756 | bool And->Or L756 | GAP-open | Regroup recovery would fire EVERY Round instead of once |
| 6298 | 759 | int 0->1 L759 | GAP-open | Regroup recovery counter starts at 1: one Rout undone for free |
| 9176 | 760 | int 0->1 L760 | EQUIVALENT | routed is initialised with a key for every count type, so the get default is dead |
| 7934 | 762 | cmp LtE->Lt L762 | GAP-open | Regroup recovery roll boundary (lo/hi) not pinned |
| 9190 | 763 | int 1->2 L763 | GAP-open | each successful Regroup roll would recover 2 Troops |
| 2402 | 770 | bool And->Or L770 | GAP-killed | Ravine keeps excluding its target after Round 1; killed by Round-2 return assert |
| 9206 | 773 | cmp NotEq->Eq L773 | GAP-killed | Ravine erases all OTHER Defenders; killed by round-1 structure assert |
| 4343 | 775 | cmp Eq->NotEq L775 | GAP-killed | Vanguard restricts the wrong Round; killed by Round-1/Round-2 engagement counts |
| 6329 | 775 | int 1->2 L775 | GAP-killed | Vanguard restricts the wrong Round; killed by Round-1/Round-2 engagement counts |
| 7964 | 777 | bool Or->And L777 | GAP-killed | Vanguard membership filter inverted; killed by engagement membership asserts |
| 9215 | 777 | cmp In->NotIn L777 | GAP-killed | Vanguard membership filter inverted; killed by engagement membership asserts |
| 9216 | 777 | cmp In->NotIn L777 | GAP-killed | Vanguard membership filter inverted; killed by engagement membership asserts |
| 6339 | 779 | int 0->1 L779 | EQUIVALENT | "retinue" is keyed in routed for every Force from __init__ |
| 6342 | 780 | cmp Eq->NotEq L780 | GAP-killed | Swift watches YORKIST Retinues; killed by swift break assert |
| 9254 | 795 | cmp LtE->Lt L795 | LOW | left is never negative, so only a user-supplied NEGATIVE caltrops split diverges |
| 10089 | 795 | int 0->1 L795 | EQUIVALENT | get-default occurrence: caltrops_left is built with both sides as keys |
| 10580 | 795 | int 0->1 L795 | GAP-killed | comparison occurrence: a remaining Caltrops budget of 1 is skipped; killed by [1,1] split assert (paired get-default occurrence 10089 is equivalent) |
| 10586 | 798 | cmp Lt->LtE L798 | GAP-killed | a short caltrops_split list crashes (IndexError); killed by [1] split case |
| 10126 | 809 | int 3->4 L809 | GAP-killed | Final Charge adds 4 Melee Hits; killed by exact ceil(3+2)+3==8 |
| 9279 | 815 | cmp Gt->GtE L815 | LOW | needs the owner to Rout his own last Retinue via absorb_plan during Missile of the same Engagement while Troops still stand |
| 10136 | 815 | int 0->1 L815 | GAP-killed | Retinue self-hit skipped at avail 1; killed by winner-flip assert |
| 10140 | 817 | cmp LtE->Lt L817 | GAP-killed | self-hit save fails on the Armour bounds; killed by rolls of exactly 4 and 1 |
| 10141 | 818 | bool And->Or L818 | GAP-killed | Valour reroll fires after a SUCCESSFUL save; killed by dice-shift winner assert |
| 10642 | 818 | cmp Gt->GtE L818 | GAP-open | Final Charge Valour gate at valour==0/1 not pinned (needs a 0/1-Valour Lord) |
| 10885 | 818 | int 0->1 L818 | GAP-open | Final Charge Valour gate at valour==0/1 not pinned (needs a 0/1-Valour Lord) |
| 10888 | 819 | cmp In->NotIn L819 | GAP-killed | valour_lords membership inverted; killed by valour=False fork (dice exhaustion) |
| 10646 | 820 | int 1->2 L820 | GAP-open | Final Charge reroll burns 2 Valour; unobservable within a one-Round battle |
| 10648 | 821 | cmp LtE->Lt L821 | GAP-killed | Valour reroll save fails on the bounds; killed by reroll-4 winner assert |
| 10904 | 828 | bool And->Or L828 | GAP-killed | Yorkist Culverins roll 2 dice without Patrick; killed by exact one-die diff |
| 10905 | 828 | int 2->3 L828 | GAP-killed | Patrick Culverins roll 3 dice; killed by exact two-dice diff |
| 10906 | 828 | int 1->2 L828 | GAP-killed | Yorkist Culverins roll 2 dice without Patrick; killed by exact one-die diff |
| 11040 | 828 | cmp Eq->NotEq L828 | GAP-killed | Patrick boosts non-Yorkist Culverins; killed by exact two-dice diff |
| 10919 | 836 | bool And->Or L836 | GAP-killed | Patrick boosts a LANCASTRIAN defender Culverins; killed by defender one-die assert |
| 10920 | 836 | int 2->3 L836 | GAP-killed | Yorkist-defender Patrick dice count wrong; killed by defender two-dice assert |
| 10921 | 836 | int 1->2 L836 | GAP-killed | defender Culverins roll 2 dice unaided; killed by defender one-die assert |
| 11055 | 836 | cmp Eq->NotEq L836 | GAP-killed | Yorkist-defender Patrick dice count wrong; killed by defender two-dice assert |
| 4383 | 857 | int 1->2 L857 | GAP-killed | Caltrops slot index skips an Engagement; killed by [1,0] split assert |
| 4385 | 858 | bool Or->And L858 | GAP-killed | swift_end is True test broken -> no mid-Round break; killed by swift test |
| 6394 | 858 | cmp Is->IsNot L858 | GAP-killed | swift_end is True test broken -> no mid-Round break; killed by swift test |
| 8072 | 858 | const True->False L858 | GAP-killed | swift_end is True test broken -> no mid-Round break; killed by swift test |
| 4386 | 860 | bool And->Or L860 | GAP-killed | break fires without Swift Maneuver played; killed by no-swift 2-engagement assert |
| 6397 | 860 | cmp Eq->NotEq L860 | GAP-killed | break fires without Swift Maneuver played; killed by no-swift 2-engagement assert |
| 9352 | 861 | bool And->Or L861 | GAP-open | Swift break too eager once a Lancastrian is already Routed; observable only in a later Round with 2+ Engagements |
| 10202 | 861 | cmp Gt->GtE L861 | GAP-open | Swift break too eager once a Lancastrian is already Routed; observable only in a later Round with 2+ Engagements |
| 10941 | 861 | int 0->1 L861 | EQUIVALENT | routed always has "retinue" and lanc_ret_before is iterated over its own keys |
| 10944 | 861 | int 0->1 L861 | EQUIVALENT | routed always has "retinue" and lanc_ret_before is iterated over its own keys |
| 10203 | 862 | cmp Eq->NotEq L862 | GAP-killed | new-Rout detection keys on avail!=0 / ==1; killed by swift break assert |
| 10699 | 862 | int 0->1 L862 | GAP-killed | new-Rout detection keys on avail!=0 / ==1; killed by swift break assert |
| 1135 | 876 | cmp IsNot->Is L876 | GAP-killed | for_trust_not_him key set when the Event was NOT played; killed by draw test |
| 4438 | 885 | cmp Eq->NotEq L885 | GAP-killed | Warden refuge picks a NON-Lancastrian North Stronghold; killed by direct assert |
| 2494 | 899 | bool And->Or L899 | GAP-killed | both-sides-Routed draw would crown the Defender; killed by test_both_sides_fleeing_is_a_draw |
| 8144 | 914 | bin Add->Sub L914 | GAP-killed | winner Influence award subtracts Vassals; killed by award==6 with one Vassal |
| 8168 | 923 | int 0->1 L923 | EQUIVALENT | with no Vassals the sliced list is empty regardless; otherwise routed["vassal"] exists |
| 4535 | 925 | cmp In->NotIn L925 | GAP-killed | a Disbanded Routed Vassal stays on the winner mat; killed by vassal_disbands assert |
| 4557 | 941 | bool Or->And L941 | GAP-killed | naming an Unrouted Lord burns the Escape Ship card; killed by card-kept assert |
| 6567 | 946 | cmp NotIn->In L946 | GAP-killed | Escape Ship Held Event never consumed; killed by port-escape card-burn assert |
| 8262 | 998 | bin Add->Sub L998 | GAP-killed | Exile cost subtracts Vassals; killed by exact 5+1 Influence delta |
| 8282 | 1010 | int 10->11 L1010 | GAP-killed | Capture of the King pays 11; killed by exact +10 delta assert |
| 2618 | 1027 | bool And->Or L1027 | GAP-killed | every Routed Lancastrian Disbands as if Talbot were played; killed by death asserts |
| 2623 | 1031 | bin Sub->Add L1031 | GAP-killed | Flee modifier becomes +2; killed by fled d6=4 -> Disband assert |
| 6690 | 1031 | int 2->3 L1031 | GAP-killed | Flee modifier becomes -3; killed by fled d6=5 -> Death assert |
| 6691 | 1031 | int 0->1 L1031 | GAP-killed | non-fled Lords get -1 on the Death roll; killed by roll-of-3 death assert |
| 2624 | 1032 | cmp GtE->Gt L1032 | GAP-killed | Death threshold moves off roll>=3; killed by stubbed roll-of-exactly-3 death |
| 4674 | 1032 | int 3->4 L1032 | GAP-killed | Death threshold moves off roll>=3; killed by stubbed roll-of-exactly-3 death |
| 1240 | 1043 | bool And->Or L1043 | GAP-open | Foreign Haven death-shift conditions (Warwick/defender/rule) untested |
| 2644 | 1043 | cmp In->NotIn L1043 | GAP-open | Foreign Haven death-shift conditions (Warwick/defender/rule) untested |
| 2645 | 1043 | cmp In->NotIn L1043 | GAP-open | Foreign Haven death-shift conditions (Warwick/defender/rule) untested |
| 2649 | 1046 | const True->False L1046 | LOW | flips only the result["foreign_haven"] reporting flag; the Calendar shift still runs |
| 1243 | 1048 | bool And->Or L1048 | GAP-killed | Test of Arms fires from battles anywhere; killed by cambridge no-change assert |
| 2651 | 1048 | cmp Eq->NotEq L1048 | GAP-killed | Test of Arms never fires at York / fires per rule-check inversion; killed by flee-battle favour asserts |
| 2653 | 1049 | cmp In->NotIn L1049 | GAP-killed | Test of Arms never fires at York / fires per rule-check inversion; killed by flee-battle favour asserts |
| 2695 | 1072 | int 0->1 L1072 | EQUIVALENT | taken[a] is unconditionally overwritten with move before any read |
| 2696 | 1072 | int 0->1 L1072 | EQUIVALENT | taken[a] is unconditionally overwritten with move before any read |
| 8368 | 1077 | int 0->1 L1077 | GAP-killed | losers with no cart entry yield a phantom Spoil; killed by taken==0 assert |
| 4768 | 1082 | cmp LtE->Lt L1082 | EQUIVALENT | a remaining==0 iteration takes min(0, x)==0 and changes nothing |
| 6764 | 1082 | int 0->1 L1082 | GAP-killed | a final Spoil of 1 is never drawn from the losers; killed by two-loser neutral case |
| 8384 | 1085 | int 0->1 L1085 | GAP-killed | a keyless loser is debited a phantom asset; killed by march-keeps-1 assert |
| 4775 | 1086 | bin Sub->Add L1086 | GAP-killed | Spoils ADD to the losers instead of draining them; killed by loser-cart==0 assert |
| 8389 | 1086 | int 0->1 L1086 | GAP-killed | a keyless loser is left with a phantom 1; killed by york-cart==0 assert |
| 9565 | 1089 | int 0->1 L1089 | GAP-killed | spoils_to with a missing asset key fails validation; killed by sparse spoils_to case |
| 9581 | 1093 | int 0->1 L1093 | GAP-killed | spoils_to credits a phantom +1 (both get-defaults die); killed by sparse-assets asserts |
| 4813 | 1107 | int 0->1 L1107 | GAP-killed | battle-local Troops take Loss rolls; killed by zero-dice mercenaries assert |
| 8436 | 1108 | int 0->1 L1108 | EQUIVALENT | routed is keyed for every count type, so the get default is dead |
| 4819 | 1110 | cmp LtE->Lt L1110 | GAP-killed | Losses recovery roll fails on the low Protection bound; killed by militia roll-1 assert |
| 6838 | 1111 | int 1->2 L1111 | GAP-killed | Losses report double-counts recoveries; killed by exact recovered==1 |
| 9603 | 1113 | int 1->2 L1113 | GAP-killed | each failed Loss roll removes 2 Troops from the mat; killed by militia 2->1 assert |
| 10347 | 1113 | int 0->1 L1113 | EQUIVALENT | the Loss loop runs only when persistent>=1, so lord.forces[t] exists (get default dead) |
| 4889 | 1150 | bool And->Or L1150 | GAP-killed | Approach accepts an attacker who is elsewhere; killed by no_attacker raise |
| 4913 | 1162 | bool And->Or L1162 | GAP-killed | Blocked Ford without the card raises AssertionError not IllegalAction; killed by code assert |
| 4938 | 1174 | bool And->Or L1174 | GAP-open | Foreign Haven shift on Approach-Exile fires for any exile / without the rule |
| 2893 | 1192 | bin Add->Sub L1192 | GAP-killed | Exile Influence cost subtracts Vassals; killed by exact 5+1 spend |
| 4993 | 1195 | cmp Eq->NotEq L1195 | GAP-killed | Exile transfer fraction inverted (full take at a hostile locale); killed by favour case |
| 1388 | 1196 | cmp Gt->GtE L1196 | GAP-killed | half-Spoils taken at a locale favouring the exile; killed by no-transfer assert |
| 6993 | 1199 | int 0->1 L1199 | GAP-killed | a missing asset key exiles a phantom 1; killed by provender-unchanged assert |
| 8562 | 1200 | bin Mult->FloorDiv L1200 | GAP-killed | neutral Exile moves ceil(amt//0.5)=2*amt; killed by exact ceil(3*0.5)==2 |
| 5009 | 1201 | bin Sub->Add L1201 | EQUIVALENT | dead store: campaign._disband_lord clears the exiled Lord's assets immediately after |
| 8572 | 1202 | int 0->1 L1202 | GAP-killed | a cart-less attacker gains a phantom +1; killed by exact cart==2 |
