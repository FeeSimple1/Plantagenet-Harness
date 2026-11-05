# Cross-game audit repairs

This batch addresses all four Plantagenet groups from the November 4, 2026
cross-game audit:

- **P1 — Own-first Feed:** every feeding Lord spends his own food before any
  surplus is shared. Feed accepts `feed_order={side: [lord_id, ...]}` and
  `pillage_by={locale_id: unfed_lord_id}` through end_activation. The chat
  helper describes these parameters and restricts player overrides to their
  own side; referee payloads can combine both owners' choices.
- **P2 — Pillage timing:** partial food is spent before Pillage. Lords still
  Unfed after the first pass must meet their full Feed requirement again with
  newly available food, following the imported Pay procedure.
- **P3 — Special Vassal penalties:** Unpaid, Unfed and Shipwreck penalties use
  a shared Influence-cost helper counting regular and Special Vassals before
  those Vassals are Disbanded.
- **P4 — Warden of the Marches:** escaping Lords retain only Unrouted Troops.
  Battle-local routed counts are subtracted from the persistent mat; an escape
  leaving no Troops still Disbands the Lord.

Regression tests cover the original public Feed and seeded Warden examples,
scarce-food order, optional Pillager selection, food sharing, invalid-choice
rollback, all three penalty causes with both Vassal types, and player-bound
interface parameters. Full suite: 1,108 passed; Ruff and strict mypy passed.

Four of four audited Plantagenet defect groups are fixed.

## Second audit, batch 1 — P2-2 and P2-3

- **P2-2 — Special Vassals aboard Ships:** Sail counts each Special Vassal
  counter as a Force along with Retinue, Troops and regular Vassal counters.
  The same count applies to every moving Lord on a Group Sail and to menus.
- **P2-3 — Discard to Sail:** the owner can explicitly leave excess Provender
  and/or Carts behind, including choosing which moving mats supply a Group's
  discard. Capacity is checked against the remaining cargo. Greed rejects
  unnecessary extra discards, invalid counts and assets from nonmoving Lords;
  bare Sail never silently discards cargo. Actual results report each mat's
  discarded amounts.

The menu offers discard-to-Sail choices, Shared Ships and Group Sails. It
advertises all eligible Group members and Ship donors, as well as alternate
discard allocations. Custom partial groups, donor subsets and arbitrary legal
allocations remain available through the documented action parameters and
state-bound ID overrides. A full group that cannot Sail does not hide its
feasible partial groups. Duplicate mover/donor IDs cannot multiply capacity.
Great Ships stays attached to its owner's Ships, including when lent.

The same review corrected adjacent Sail issues: High Admiral's legal enemy
Port Approaches now appear in menus, and Naval Blockade checks only Seas
whose Ports the Sail actually uses. Sea-to-Sea or Exile-to-Sea movement uses
no Port. Command cost is spent before the reaction, but elected cargo stays
on its mats if Blockade cancels the action. Saved reactions retain the discard
and apply it once if the Sail proceeds. Player views conceal prospective
discards and menu hints from the opponent; completed discards remain visible.

Fifty-one regressions cover the six/seven-Force boundary, regular and Special
Vassals, solo/Group capacity, both cargo types, arbitrary owner allocations,
all origins, Shared/Great Ships, partial groups, malformed and duplicate
inputs, Greed, rollback, Naval Blockade, save/load, Seamanship, High Admiral,
Truce, private views, menu agreement and parameter discovery. The old Cart
capacity mutation test now requires the legal one-Cart discard rather than
expecting all Sails to disappear.

Validation: **1,159 tests passed**, with repository-wide Ruff and strict mypy
passing. Forty-four new cases fail against the preceding main revision;
seven preservation cases pass. Twelve smoke games across Henry VI, Warwick's
Rebellion and My Kingdom for a Horse (two seeds, survival/aggressor policies)
all reached game end over 2,502 actions, with zero findings.

Second-audit progress: **2 of 4 Plantagenet groups fixed**. P2-1 (Unpaid
Exile markers) and P2-4 (Approach Exile Spoils allocation) remain open. All
four original audit groups remain fixed.
