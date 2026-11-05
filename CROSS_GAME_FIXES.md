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

## Second audit, batch 2 — P2-1 and P2-4

- **P2-1 — Unpaid Disband in Exile:** Unpaid Troops now preserve the Lord's
  Exile marker when placing its cylinder on the Calendar. The normal Influence
  penalty and Calendar delay still apply. Once ready, the saved/loaded Lord
  can return through free Muster Exiles to its side's permitted Exile box.
- **P2-4 — Approach Exile Spoils:** the approaching owner can distribute Carts
  and Provender among approaching Lords. `exile_spoils_to` controls this pool;
  `spoils_to` is also accepted when no Battle follows. When some defenders
  Exile and others fight, Exile allocation completes before the Battle and
  `spoils_to` retains its existing meaning for the later Battle's Spoils.
  Neutral Exile Spoils still round separately for each Exiling Lord, unlike
  the aggregate calculation for ordinary Battle Spoils. Default allocation
  to the first approaching Lord and England Is My Home remain intact.

Battle and Exile allocation share validation of eligible recipients,
nonnegative integer counts, permitted Assets, and exact totals. This also
closes a Battle loophole allowing negative allocations balanced by extra
Assets on another mat. Invalid public actions restore the entire preceding
state, including movement, earlier Exiles, Influence, history and RNG.
The action reference and chat combat help document both allocation keys.

This batch also corrects a regression introduced by batch 1: the Sail origin
check used `locale` where the location helper returns `stronghold`, allowing
Port-to-Sea Sail to skip Naval Blockade. The origin Port now triggers the
reaction before cargo is discarded or movement occurs.

Validation: **1,188 tests passed**, including 28 new Exile/allocation cases
and one new Port-to-Sea Blockade case; repository-wide Ruff and strict mypy
passed. The targeted Exile/Sail suites passed all 80 cases. Comparison with
the preceding main revision produced 25 failures and four passes across the
29 new cases (including assertions for the new allocation result fields).
Twelve smoke games across Henry VI, Warwick's Rebellion and My Kingdom for a
Horse (two seeds, survival/aggressor policies) all reached game end over
2,555 actions, with zero findings.

Second-audit progress: **4 of 4 Plantagenet groups fixed**. All four original
audit groups remain fixed.

## Third audit, batch 1 — P3-01 and P3-02

- **P3-01 — Escape Ship:** one played Event now covers every selected eligible
  Routed Lord of its side. Resolving a second Lord no longer requires a spare
  Held copy. Duplicate selections are handled once in stable input order;
  hash randomization cannot decide which Lord escapes. Port-route eligibility,
  owner subsets, Bloody Thou Art and England Is My Home retain their rules.
- **P3-02 — Transport lists:** Supply, March and Intercept reject repeated Lord
  IDs before counting transport. Their list validation also rejects the leader
  as a groupmate/donor, non-string members and malformed list structures.
  Sail uses the same distinct-Lord validation. Valid partial groups and donor
  choices remain available; Shared transport remains on its owner's mat.

Thirty-nine regressions cover both factions, both Yorkist Event copies,
one-card and spare-card hands, reversed/subset/duplicate escape selections,
Port-route restrictions, England Is My Home, save/load, physical Ship/Cart
capacity, all four Supply/March/Intercept flows, malformed inputs, full-state
and retained-reference rollback, and equivalent legal retries. The pre-fix
run failed 25 cases and passed 14 preservation/control cases.

Validation: **1,227 tests passed**, including all 202 focused cases;
repository-wide Ruff and strict mypy passed. Separate-process Escape Ship
results match with hash seeds 1 and 4, which previously produced different
victims. Twelve smoke games across Henry VI, Warwick's Rebellion and My
Kingdom for a Horse (two seeds, survival/aggressor policies) completed over
1,784 actions, with zero findings.

Third-audit progress: **2 of 3 Plantagenet groups fixed** (2 of 23 across all
five games). P3-03, Warden refuge and Lord-selection choices, remains open.
All findings from the first two audits remain closed.
