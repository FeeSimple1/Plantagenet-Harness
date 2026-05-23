# Rules Decisions — Plantagenet Harness

Adjudicated rules calls. Each entry records the user's verbatim answer,
any rules citation, and the commit hash where the decision is encoded.
**Decisions are permanent — never delete an entry.** `[HOUSE RULE]` marks
a decision made where the rules are silent; it is authoritative and cited
like any rule.

---

## D-001 — Sea-zone groupings and Sail adjacency (resolves Q-001)

**Date.** 2026-05-20.

**Question.** The reference text marks Ports but does not enumerate which
Ports share a Sea, nor the Sea adjacency used by Sail.

**User adjudication (verbatim).**
> Irish Sea ports: Bristol, Pembroke, Harlech, Ireland (exile box; acts
> similarly to a Port per Rules §1.3.1).
> English Channel ports: Truro, Plymouth, Exeter, Dorchester, Southampton,
> Hastings, Dover, Calais, France (exile box; acts similarly to a Port),
> Burgundy (exile box; acts similarly to a Port).
> North Sea ports: Ipswich, Lynn, Ravenspur, Scarborough, Newcastle,
> Scotland (exile box; Rules §1.3.1 explicitly assigns Scotland to the
> North Sea).
> Sea adjacency for Sail (Rules §4.6.1, FAQ #1): Irish Sea <-> English
> Channel; English Channel <-> North Sea; Irish Sea and North Sea are NOT
> directly adjacent (must transit via English Channel). Great Ships (Y6)
> does NOT shortcut this for the Sail action; it only collapses cross-Sea
> distance for Parley, Tax, and Supply.

**Citation.** Rules of Play §1.3.1, §4.6.1; Errata & Clarification FAQ #1.

**Encoded in.** `data/static/seas.json`, `data/static/exile_boxes.json`
(sea_zone + acts_as_port), `data_integrity.py` (sea-zone checks),
`reference/Plantagenet Map Reference.txt` (new Sea Adjacency section). Commit: see the phase-0-map-corrections merge.

---

## D-002 — Leicester land connections (resolves Q-002)

**Date.** 2026-05-20.

**Question.** Leicester's connections to Peterborough (Road) and
Nottingham (Highway) were declared only from Leicester's line in the Map
Reference, not reciprocated by Peterborough or Nottingham.

**User adjudication (verbatim).**
> Both edges are valid and bidirectional. Fix the reciprocity. Confirmed
> Leicester edges (all bidirectional): Leicester <-> Lichfield (Road);
> Leicester <-> Peterborough (Road); Leicester <-> Nottingham (Highway);
> Leicester <-> Northampton (Highway).

**Citation.** User adjudication; reciprocity correction to the Map
Reference.

**Encoded in.** `data/static/ways.json` (both edges now emitted; 81 land
ways), `scripts/build_map_data.py` (reciprocated in ADJ;
`PENDING_ASYMMETRIC` cleared), `reference/Plantagenet Map Reference.txt`
(Peterborough and Nottingham entries updated).
Commit: see the phase-0-map-corrections merge.

---

## D-003 — Bristol is a Port (Map Reference omission)

**Date.** 2026-05-20.

**Question.** The Map Reference entry for Bristol omitted its Port
designation.

**User adjudication (verbatim).**
> It is missing the port designation. ... Bristol is on the Irish Sea.

**Citation.** User adjudication / Map Reference correction.

**Encoded in.** `data/static/locales.json` (bristol `port: true`),
`scripts/build_map_data.py`, `data/static/seas.json` (Irish Sea), and the Map Reference (.txt). Commit: see the phase-0-map-corrections merge.

## D-004 — Strongholds table (resolves Q-003)

**Date.** 2026-05-20.

**Question.** The Strongholds table (Troop-Levy and Pillage/Tax/Supply
yields per Stronghold type, plus the Tides-of-War award) is on the
player-aid foldout, absent from the repo sources; needed for Levy Troops
(3.4.4) and later Pillage/Tax/Forage.

**User adjudication.** Provided `reference/Plantagenet Strongholds
Reference.txt` (transcribed foldout) and `reference/Plantagenet Influence
Points & Parley Reference.txt`. Levy-Troops yields: City = 1 Longbow + 1
Militia; Town = 2 Militia; Fortress = 1 Men-at-Arms + 1 Longbow; London = 1
Men-at-Arms + 1 Longbow + 1 Militia; Calais = 2 Men-at-Arms + 1 Longbow;
Harlech = 1 Men-at-Arms + 2 Longbow. Supply/Tax/Pillage and Tides-of-War
awards per the reference.

**Favour vs Most Favour (user emphasis).** Tides of War (4.8.1): REGULAR
Strongholds (City/Town/Fortress) award Influence to the side with the MOST
total Favour of that type (one award per type). SPECIAL Strongholds
(London/Calais/Harlech) award INDIVIDUALLY to whichever side has Favour
there. Encoded as `tides_of_war.basis` ("most_favour" vs "favour") in
`strongholds.json`.

**Citation.** Rules 3.4.4, 3.2.1, 4.6.2-.3, 4.8.1; player-aid foldout
(transcribed). Background Book example confirms City = 1 Longbow + 1 Militia.

**Encoded in.** `data/static/strongholds.json`; `forces.json` (troop pool
counts, 1.6); `static_data.load_strongholds`/`stronghold_yields`;
`actions.py` `_h_levy_troops` (3.4.4); `data_integrity.py`. Levy Troops is
now executable. Pillage/Tax/Forage yields will use the same table in Phase 3.

---

## D-005 — Reactive "interrupt" Capabilities implemented (resolves Q-004)

**Date.** 2026-05-22.

**Question.** Q-004 asked how to model Capabilities that trigger *during the
opponent's action* (Naval Blockade Y15, King's Parley L15), since
`apply_action` had no reaction window.

**Resolution.** Option (a) of Q-004 was adopted and built (Phase 5a): a typed
trigger registry plus a serializable pause/resolve loop on `state.pending`.
`apply_action` gained a `react` action and a pending-guard; paused state
round-trips through JSON. Triggers implemented: `uses_port_on_sea` (Naval
Blockade Y15, gating Sail), `on_approach` (King's Parley L15 cancel+rewind;
Parliament's Truce Y12/L20; Blocked Ford Y11/L11; priority 10/20/30),
`after_successful_levy_action` (The King's Name Y32). In-battle plays are
unified under a single `BATTLE_REACTIONS` catalog; battle resolution stays
synchronous (all participants are known at battle entry — a deliberate design
call). No rules ambiguity remained; this was a structural implementation.

**Citation.** Card texts Y15, L15, Y12/L20, Y11/L11, Y32; Rules of Play
§4.3.5 (Approach), §4.6.1 (Sail).

**Encoded in.** `reactions.py` (trigger registry + reaction handlers),
`commands.py` (Sail/Approach reaction checkpoints + resume),
`actions.py` (`react` action + pending-guard), `tests/test_reactions.py`.
Commit: see the Phase 5a reaction-protocol merge.

---

## D-006 — Q-005 closed: scripted Succession & play-timing Events are implemented or implementation-only (resolves Q-005)

**Date.** 2026-05-22.

**Question.** Q-005 bundled two clusters: per-War scripted Succession
(6.2-6.3) and a list of reaction / play-timing Events not yet automated.

**Determination.** Q-005 was an implementation backlog rather than a genuine
rules question. The large majority is now implemented and tested:
`play_event` / `play_held_event`, the Q-004 reaction hook (The King's Name
Y32, Parliament's Truce Y12/L20, Exile Pact Y8, etc.), and the per-War
Succession trigger engine (`succession.py`) plus the Renewed-War setup
transition (`scenarios.renew_war`). Three residue items remain, and each is
fully governed by explicit card/scenario text — there is nothing for an
adjudicator to decide:

- **(a) For Trust Not Him (L7).** The card text fully specifies the mechanic
  (a participating Lord attempts an in-battle Levy per 3.4.3, ignoring Routes
  and the Vassal Seat's Favour; on success the Vassal marker moves to that
  Lord's mat and the Calendar marker shifts as if newly Levied). IMPLEMENTED
  (2026-05-22): `battle._resolve_for_trust` (Event step 4.4.1) moves the
  captured regular Enemy Vassal to the Levying Lord's mat -- so it fights the
  current Battle for its new Lord -- with its service marker reset as if newly
  Levied; Salisbury's Vassals are immune (Y17 Alice Montagu). The `deferred`
  flag is removed from `reactions.py`. Tests in `tests/test_card_for_trust.py`.
- **(b) Naval Blockade (Y15).** The card's own text/Tips enumerate every
  gated action — Parley, Levy Ship, Supply, Sail, and Tax (3.4.1, 4.6.4,
  3.4.5, 4.5, 4.6.1, 4.6.3). IMPLEMENTED (2026-05-22): the `uses_port_on_sea`
  reaction now also gates Lancastrian Tax / Campaign Parley / Supply, not just
  Sail. Route->sea introspection: an action "uses a Port on Sea S" when a Ship
  sea-hop over S is load-bearing for its Route -- i.e. blocking S raises the
  Way cost or makes the target unreachable (`commands._route_used_seas`); an
  equally short overland route routes around the Blockade. Campaign Parley uses
  S only when it reaches a non-adjacent same-Sea Port by Ship, and Ship Supply
  uses the Sea of its Port Source. Ordering follows the Y15 tips: the
  Command-action cost is committed before the reaction window; on a block the
  Influence check is never made (no Influence paid, no effect). Tests in
  `tests/test_naval_blockade_actions.py`.
- **(c) Wars IIY / IIIY base-scenario setup.** The conditional Lord
  placements and the Natural Causes post-victory rolls are fully specified by
  the scenario prose (Scenario Reference E4 "War IIY" / E6 "War IIIY") plus
  the Calendar rule: per §2.2 the 15 Calendar boxes ARE the Turn boxes, so
  Natural Causes' "a roll less than the last Turn played" compares the dice to
  the final Calendar Turn box reached. King resolution and the IIL/IIIL
  structured paths already transition end-to-end. Pure implementation.
  - **Natural Causes IMPLEMENTED (2026-05-22):** `scenarios.apply_natural_causes`
    runs at the start of `renew_war` when leaving a won second War. Henry VI and
    York roll 2d6 (removed if the sum < the last Turn box reached, `state.turn_box`);
    Edward IV rolls 1d6 in IIY only (removed on a 6); IIL omits the Edward IV
    roll. Structured spec lives in `wars_of_the_roses.json` (`natural_causes`).
    Removed Heirs are permanently out and carried into the next War, and incur
    the -8 Influence penalty -- which now keys off the global 6.2.1 Heir list
    (`succession.is_global_heir`) with a static-side fallback, so a Heir absent
    from the next War's roster (e.g. Henry VI in IIIY) is still penalised.
    Tests in `tests/test_natural_causes.py`.
  - **IIY conditional setup IMPLEMENTED (2026-05-23):** `scenarios.apply_iiy_setup`
    suppresses the standalone Scenario II Yorkist roster and places the IIY
    roster by War I survival: King = highest surviving Heir at London (with the
    in-place March->Edward IV / Gloucester(1)->Richard III King transforms left
    to `succession.apply_setup`); March at Ludlow when York is King; Rutland at
    Canterbury; Gloucester (1) silver-ring box 9; Devon box 1 and Northumberland
    (1) box 9 always; Pembroke at Pembroke only at <=2 Heirs; Yorkist Favour at
    Canterbury. Lancastrian: a surviving Henry VI / Somerset (1) lead from box 9
    (Exile), displacing Margaret / Somerset (2). Tests in
    `tests/test_war_iiy_setup.py`.
  - **IIIY conditional setup IMPLEMENTED (2026-05-23):** `scenarios.apply_iiiy_setup`
    clears the entire base Scenario III roster ("hold off setting up any Lords")
    and places the whole roster from Succession per E6: surviving Yorkist Heirs
    -> King = highest at London with the next Heir kept and all others removed;
    per-Heir placements with ring variants (Gloucester(1) silver@Gloucester /
    (2) gold@London / Richard III gold@London by who is King; March@Ludlow vs
    Edward IV@London; Rutland@Canterbury Heir-to-York/Edward IV or King@London);
    the Y28 "Gloucester As Heir" set-aside displaces Rutland (both remain); the
    Warwick-as-King branch (Yorkist Warwick + Salisbury + Y16/17/22 when Rutland
    is the sole Heir); Northumberland(2)@Carlisle + Y37 when exactly one senior
    Heir remains; Norfolk@Arundel always; the one Lancastrian leader
    (Margaret / Henry Tudor / Warwick by condition) with Oxford + Jasper Tudor(2)
    following the leader; and Favour = London Yorkist + each in-play Lord's marked
    Seat. The Y28 set-aside is tracked from `arts_of_war` (event activation) and
    carried into IIIY by `renew_war`. Tests in `tests/test_war_iiiy_setup.py`.
  - **(c) is now fully implemented; all of D-006 residue (a)/(b)/(c) is closed.**
  - **War IIIL setup IMPLEMENTED (2026-05-23):** `scenarios.apply_iiil_setup` (E7),
    the Lancastrian-victory mirror of IIIY, closes the last grand-scenario
    transition (the IIL->IIIL crash from the unimplemented prose-Favour setup).
    All four second->third War transitions now build co-location-clean.

**Citation.** Card texts L7, Y15; Scenario Reference E4 (War IIY), E6
(War IIIY); Rules of Play §2.2 (Calendar), §3.4.3 (Levy Vassal), §4.3.5,
§4.6.1.

**Encoded in.** Implemented portions across `events.py`, `reactions.py`,
`succession.py`, `scenarios.py`. Residue (a)/(b)/(c) is tracked as
implementation backlog in `BRIEF.md` open items and the `SMOKE_TEST_FINDINGS.md`
round log — NOT as open rules questions. Commit: see the Q-004/Q-005 close-out
merge.
