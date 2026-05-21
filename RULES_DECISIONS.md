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
