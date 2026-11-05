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
