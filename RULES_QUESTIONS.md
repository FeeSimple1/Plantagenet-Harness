# Rules Questions — Plantagenet Harness

Open questions awaiting user adjudication. Each must contain all required
fields (see BRIEF.md "Question Format"). When answered, MOVE the entry to
`RULES_DECISIONS.md`.

---

## Q-003 — Strongholds table (Troop-Levy and Pillage/Tax/Forage yields)

**Context.** Implementing the Levy phase (Phase 2). Levy Troops (3.4.4)
"adds Troops ... as listed for the Lord's current location on the foldout's
Strongholds table," and Pillage (3.2.1) adds "Coin and Provender ... per the
foldout's Strongholds table." The table maps each Stronghold type (and the
Special Strongholds) to the units/assets produced.

**Consultation log.**
1. `reference/` curated `.txt` files — none reproduces the Strongholds table.
2. Rules of Play — sections 1.3.1, 3.2.1, 3.4.4 all explicitly defer to
   "the Strongholds table on the player aid foldout" (e.g. p.10/11) rather
   than printing it.
3. Background Book — gives only a single worked fragment: "Ely is a City, so
   York will add 1 Longbowmen unit and 1 Militia unit" (Examples of Play).
   The full per-type table (Town / City / Fortress / Special, for both
   Troop Levy and Pillage/Tax/Forage) is not reproduced.
4. The player-aid foldout itself is not among the repo `source/` files.
   No external/historical sources were consulted.

**What is ambiguous / missing.** The complete Strongholds table: for each
Stronghold type, (a) the Troops gained by Levy Troops, and (b) the
Coin/Provender gained by Pillage (and Tax/Forage, used in Phase 3a).

**Options.**
- (a) User provides the Strongholds table (the cleanest path; it is fixed
  printed data).
- (b) Operator transcribes it from the player-aid foldout if that file is
  added to `source/`.

**Affects.** Levy Troops (3.4.4) and Pillage yields (3.2.1) — both currently
raise `IllegalAction("needs_strongholds_table")`. Also Tax (4.6.3) and
Forage (4.6.2) in Phase 3a. `actions.py`, future `levy_troops`/`pillage`.

**Blocking?** Levy Troops is blocked now (deferred with the code above).
Everything else in the Levy Muster segment is implemented. Pillage is not
reachable until turns advance (Phase 3), and Pay is skipped on Turn 1 (3.2).
