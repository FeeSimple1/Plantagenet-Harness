# SMOKE Test Findings — Plantagenet Harness

Append-only log of every SMOKE finding (bug surfaced during development or
auditing), with round-by-round context. Nothing here is ever overwritten;
the SMOKE numbering is the institutional memory of every bug found and how
it was fixed.

Each entry: SMOKE-NNN, round, the pattern (see `FUTURE_PROJECTS_LESSONS.md`),
a description, the fix, and the commit/test that closes it.

---

## Round 0 (Phase 0 — skeleton + static data)

No SMOKEs yet (no game logic implemented). Two map data-integrity
findings were surfaced by the `ways.json` symmetry check during data
encoding and routed to `RULES_QUESTIONS.md` rather than logged as SMOKEs,
because they are source ambiguities, not code bugs:

- Q-001: Sea adjacency between Ports is not enumerated in the references.
- Q-002: Leicester's connections to Peterborough and Nottingham are
  declared from Leicester's line only, not reciprocated.

The symmetry check itself (every Way declared from both endpoints) is the
Phase-0 analogue of the enumerator/handler round-trip discipline described
in `CROSS_PROJECT_LESSONS.md` — it catches transcription divergence in the
static data before any logic depends on it.

## Round 1 (Phase 0 — map corrections)

Applied user-supplied map corrections (resolving Q-001/Q-002, see
`RULES_DECISIONS.md` D-001/D-002/D-003):
- Encoded Sea zones (Irish Sea / English Channel / North Sea) with Port
  and Exile-box membership and zone adjacency (`seas.json`).
- Set Bristol as a Port (Irish Sea); added the two confirmed Leicester
  edges (Peterborough/Road, Nottingham/Highway).

Re-ran the reciprocity discipline two ways and they agree: the
`ways.json` builder symmetry check passes with no pending edges, and an
independent prose parse of the Map Reference (`scripts/reciprocity_sweep.py`)
reports 81 reciprocal pairs and zero one-sided edges or type mismatches.

## Round 2 (Phase 0 cleanup)

Removed `reference/Plantagenet map.rtf` (a duplicate of `Plantagenet Map
Reference.txt`) to eliminate the two-sources-of-truth drift risk flagged
after the map corrections. The `.txt` is now the single canonical map
reference.

## Round 3 (Phase 1 — state model, loader, display)

No game-logic SMOKEs (no rules logic yet). Two issues caught during
development before commit, noted for the record:
- RNG state serialized the Mersenne-Twister internal as a tuple, which a
  JSON round-trip turned into a list, breaking save/load identity. Fixed
  by list-ifying fully in `DiceRoller.get_state` (test:
  `test_save_load_round_trip`).
- The focused Lord view duplicated the status token. Cosmetic; fixed.

Guardrails added: `state.schema.json` is regenerated from the Pydantic
model (`scripts/generate_schema.py`) and a test asserts the committed
schema matches the model so it cannot silently drift. Initial
`active_side` is set to the King's side as a provisional pointer; precise
turn order per the Sequence of Play is a Phase 2 concern (documented in
`scenarios.py`).

## Round 4 (Phase 2 — Levy mechanics)

**SMOKE-001 (Pattern: card-text/setup fidelity).** The Phase 1 scenario
loader marked Scenario III's Henry Tudor, Jasper Tudor (2), and Oxford as a
no-mat `EXILE` status because their setup placement names an Exile box. But
the Scenario Reference lists them under "Mustered Lord Mats," and 3.4 lets
Lords in Exile boxes take Levy actions (except Levy Troops). They are
Mustered Lords *located in* the France Exile box. Surfaced while reading the
3.4 Muster requirements. Fixed in `scenarios.py` (`_lord_state`): an
Exile-box placement now yields `MUSTERED` with `exile_box` set and starting
Forces/Assets. Regression: `test_iii_exile_lords_mustered_in_france_*`.

Also corrected (rules-grounded, not a bug per se): initial `active_side` is
now the Rebel side, since the Levy sequence is "Rebel then King's" (3.1-3.4);
Phase 1 had used a provisional King-side pointer.

Data gap logged as **Q-003**: the Strongholds table (Troop-Levy and Pillage
yields per Stronghold type) is not in the repo sources, so Levy Troops
(3.4.4) is deferred (raises `needs_strongholds_table`) rather than guessed.

Round-trip discipline: `scripts/roundtrip_sweep.py` plus
`test_round_trip_every_emitted_move_applies` confirm every enumerated Levy
move is accepted by the handler across all scenarios and seeds.

## Round 5 (Phase 2b — Strongholds table)

User supplied the Strongholds table and an Influence/Parley reference
(resolving Q-003 -> D-004). Encoded `strongholds.json` (Levy/Supply/Tax/
Pillage/Tides per type, with the Favour-vs-Most-Favour basis distinction the
user emphasized) and troop pool counts (1.6, 128 pieces) in `forces.json`.
Implemented Levy Troops (3.4.4): adds the Stronghold's Troops (pool-limited),
then Depletes/Exhausts the Locale (new `LocaleState.depletion`). Enumerator
now offers levy_troops; round-trip sweep stays clean. Levy Troops verified
against the Background Book example (Ely City -> 1 Longbow + 1 Militia).

## Round 6 (Phase 3a-i — Campaign backbone)

Implemented the Campaign turn structure (4.0-4.2, 4.6.2, 4.6.5, 4.7, 4.8):
Plan (season-sized stacks, <=3 activations/Lord), Activation (Rebel/King
alternation; up to Command rating actions; Pass card / off-map Lord = do
nothing), Forage, Feed (no-op until movement), and End Campaign — full
Tides of War scoring (Areas/Dominance, Special-Stronghold Favour,
Most-Favour by type, Gain-Lords-Influence), Victory check (5.1-5.3), Grow,
Waste, and Turn advance. No SMOKEs. The enumerator is now phase-aware
(Levy Muster vs Campaign). Deferred (tracked, not guessed): movement/route
Commands (March/Sail/Supply/Tax/campaign-Parley) and Pay (3.2) -> Phase
3a-ii; combat -> Phase 3b; a rolled-over Turn lands at the Muster step
until Pay/Arts-of-War-draw land.

## Round 7 (Phase 3a-ii - movement & economy Commands)

Implemented March (4.3: Road/Highway/Highway-2-for-1/Path, Haul 4.3.2,
Moved-Fought, Group March 4.3.1), Sail (4.6.1: same/adjacent-Sea Ports, Ship
requirement, whole card), Tax (4.6.3: own-Seat auto, Vassal-Seat/Special via
Route + Influence, strongholds Coin, Deplete), and campaign Parley (4.6.4).
Feed (4.7) is now live with Pillage (3.2.1) and Unfed-Disband (3.2.4). March
into enemy contact (Approach 4.3.5 / Intercept 4.3.4) is deferred to Phase
3b with explicit codes.

The campaign-activation round-trip test caught one enumerator bug
(pre-merge): the enumerator offered `forage` at an Exhausted Locale, which
the handler rejects (4.6.2). Fixed by gating the forage option on
non-Exhaustion. No shipped SMOKEs. Deferred (tracked): Supply (4.5) and Pay
(3.2) -> Phase 3a-iii.

## Round 8 (Phase 3a-iii - Supply)

Implemented Supply (4.5): a Friendly Stronghold Source yields its table
Provender then Depletes (or a Port Source yields Ships-many Provender,
ignoring Depletion); the land Supply Route is a Friendly chain free of Enemy
Lords (not across Sea), limited by Carts (one Cart per Provender per
intervening Way); Exile-box Lords Supply by Ship from a same-Sea Port
(Scotland by Path). This completes the Campaign Command menu (4.2.2). No
SMOKEs. Note: cross-Lord Cart Sharing (1.5.3) for Supply uses the acting
Lord's own Carts for now (Sharing is a follow-on). Deferred: Pay (3.2) and
the Turn-2 Levy flow -> Phase 3a-iv.

## Round 9 (Phase 3a-iv - Pay; Phase 3a complete)

Implemented the Levy Pay step (3.2) in pay.py, run Rebel then King on a
rolled-over Turn: Pay Troops (3.2.1 - 1 Coin/6 Troops, Sharing within a
Locale, Pillage an Unexhausted Stronghold then re-Pay, else Unpaid-Disband
with the -Influence-1/Vassal penalty), Pay Lords (3.2.2 - voluntary Disband,
then -1 inf/Stronghold and -2/Exile box), Pay Vassals (3.2.3 - pay+shift or
Disband). Added VassalStatus.DISBANDED with a Calendar return box and Ready
Vassals (3.3.2). Turn rollover now lands at the Pay step; the full Levy +
Campaign cycle runs across Turns. No SMOKEs. Deferred: Muster Exiles (3.3.1,
needs scenario Exile-box mapping), Arts-of-War draw (3.1, Phase 4),
cross-Lord Cart Sharing for Supply. Combat -> Phase 3b.

## Round 10 (Phase 3b-i - combat, 1v1)

Implemented Approach (4.3.5) and the single-Lord-per-side Battle engine
(4.4) in battle.py. A March into an Enemy Locale triggers Approach; each
Defender Exiles (lose Influence rating+Vassals, give Carts/Provender Spoils
by Favour, Disband to Calendar Exile) or fights a Battle. Battle: per-Round
Flee, Missile then Melee Strikes (total Hits from the Forces table - verified
against the Background Book's 5 Longbow + 4 Militia = 12 Missile Hits
example), per-Hit Protection rolls with Valour rerolls, unit Rout, Lord Rout
(all Troops or Retinue Routed), multi-Round; Ending (4.4.3): winner Influence
(losers' ratings +1/Vassal), Spoils (Favour-based Carts/Provender), Losses
(recover/lose Routed Troops; Disband if all own Troops Lost), Death check
(3-6, -2 if Fled) -> Death (permanent removal) or Disband. Decisions via an
optional payload with deterministic defaults. No SMOKEs. Deferred:
multi-Lord Battles/Arrays/Flanking/Reposition and Intercept (4.3.4) ->
Phase 3b-ii; "in Battle" Held Events -> Phase 4.

## Round 11 (Phase 3b-ii - multi-Lord Battles + Intercept; Phase 3b complete)

Generalized battle.py to N Lords per side: Array (4.4.1; center-first fill,
Attacker opposite; overridable), per-Round Reposition (Rout removal, Reserve
Advance, Center fill), Flanking Engagements (union-find over opposite/nearest
targets), per-Engagement Strikes totaling both sides, and multi-Lord Ending
(Influence/Spoils/Losses/Death). approach() now allows multiple Defenders.
Intercept (4.3.4): a March with decisions.intercept names a Road/Highway-
adjacent Enemy that rolls <= Valour to move to the destination, then is
Approached. The intercept_phase_3b March rejection is removed (adjacent-to-
enemy Marches are legal). No SMOKEs. Phase 3b (combat) is COMPLETE.
Remaining: Phase 4 (Arts-of-War card draw + Event/Capability effects +
Succession); small deferrals (Muster Exiles 3.3.1, Disembark 4.8.2, Supply
Cart Sharing 1.5.3).

## Round 12 (Phase 4-i - Arts of War card-data layer)

Parsed the Arts of War Reference into data/static/cards.json via
scripts/build_cards.py: 74 cards (37 Yorkist + 37 Lancastrian), each with
its Event (type: hold/this_levy/this_campaign/immediate) and Capability
(title + eligible-Lords line), and a rose group (0=all/1=I/2=II/3=III).
Added static_data.load_cards() and scenario_card_deck() (no-rose + matching
rose; II excludes L4) + data_integrity checks. Verified the rose
distribution (13/9/9/6 per side) and deck sizes (Ia 22/22, II 21 Lanc /22
Yorkist, III 19/19) against the Scenario Reference. No SMOKEs. Card effects,
the draw (3.1), and Levy Capability (3.4.6) come in later Phase-4 increments.

## Round 13 (Phase 4-ii - Levy Capability 3.4.6)

Implemented Levy Capability as a Muster action: a Lord at a Friendly Locale
attaches one unused, eligible scenario Capability card to its mat (<=2 per
Lord, no duplicate Capability name; card must be in the scenario deck and of
the Lord's side). Eligibility: "Any", a Special-Vassal Capability's eligible
Lords, or a base-name match of the card's Lords line. Enumerated during
Muster; round-trip sweep stays clean. The Capability is tracked as data; its
mechanical effect is the consumer's to apply until implemented in a later
Phase-4 increment (per BRIEF interim). No SMOKEs. Remaining Phase 4: the
mandatory 3.1 draw (Events/Capabilities), per-card effects, and Succession.

## Round 14 (Phase 4-iii - Arts of War draw 3.1)

Added the mandatory Arts of War draw as the first Levy step (arts_of_war),
Rebel then King: first Levy of a scenario deploys 2 Capabilities to Mustered
Lords (default first eligible; discard if unassignable); later Levies draw 2
Events (Hold -> held pile, This Levy/Campaign -> active_events, immediate ->
resolve+return). GameState gained decks (draw/discard/held per side) and
active_events; DiceRoller.shuffle orders the draw piles; loader/rollover land
at arts_of_war. This Levy events cleared after Muster, This Campaign after
Campaign. The flow reorder churned ~56 tests (advancing through the draw via
a tests/_helpers.to_muster helper); all updated. Card EFFECTS remain
consumer-applied until coded. No SMOKEs. 170 tests pass; round-trip clean.

## Round 15 (Phase 4-iv - battle-modifier card effects, batch 1)

Wired the first card effects into battle.py via the decisions payload:
- Culverins and Falconets (Y1&Y2/L1&L2 Capability): at Round 1, a named Lord
  discards it to add 1 d6 of Missile Hits to its side's outgoing total.
- Leeward Battle Line (Y1/L1 Hold Event): a side plays its held copy to halve
  (round up) the Missile Hits it receives; if both sides play, neither has
  effect (4.4.1 Event step). Adds card helpers (find/consume capability and
  held event). Validated against held/mat cards (no_culverins/no_leeward).
  Verified the hit math from the round logs. No SMOKEs. 174 tests pass.

## Round 16 (Phase 4-v - combat-timing card effects, batch 2)

Wired four more card effects into battle.py/approach via the decisions
payload: Caltrops (Y19 Hold Event, +2 Melee Hits/Round, one Engagement),
Ravine (L12 Hold Event, ignore an enemy Lord for Engage/Strike in Round 1),
Blocked Ford (Y11/L11 Hold Event, forbid Exile on Approach -> all Battle),
and Barricades (Y9 Capability, Armour 1-4 Men-at-Arms / 1-2 Longbow & Militia
at a Friendly Stronghold; NOT for Losses). Fixed _losses to roll UNMODIFIED
Protection (4.4.3). All validated against held/mat cards and consumed on use.
No SMOKEs. 179 tests pass. Deferred to a later batch: Flank Attack (attacker
flip), Escape Ship (Death-check -> Exile, needs route-to-Port), Regroup
(mid-battle timed recovery).

## Round 17 (Phase 4-vi - combat cards Flank Attack, Escape Ship, Regroup)

Completed the combat-card category: Flank Attack (Y2/L2 Hold) in
commands._try_intercept — auto-succeeds and flips the Interceptor to
Attacker (the Marching Lord Defends); Escape Ship (Y3&Y9/L3 Hold) at the
battle Death check (4.4.3) — selected Routed Lords with a Friendly Route to a
Port (new battle._escape_route, reusing the Supply route) Exile (4.3.5,
to the Calendar marked Exile + Influence penalty) instead of rolling Death;
Regroup (Y30 Hold) — once at a chosen Round, a Lord's Routed Troops roll
their (modified) Protection to recover. All validated against held cards and
consumed on use. No SMOKEs. 183 tests pass.

## Round 18 (Phase 4-vii - Special Vassal effects)

Added a `ratings.py` effective-rating layer (printed rating + Special-Vassal
Command/Valour modifiers), wired into Campaign activation (Command), battle
_Force Valour, and Intercept Valour. Levying a Special-Vassal Capability now
Musters the linked Vassal free onto the Lord (`_muster_special_vassal`):
Hastings (Y24) +2 Men-at-Arms + Command +1; Edward Prince of Wales (L26),
Clifford (L21), Trollope (L19) +1 Valour; Montagu (L23) Warwick's Retinue
Armour 1-5 in battle; Thomas Stanley (L35) a free Levy Troops once per Levy
(0 Lordship; LordState.free_troops_used, reset each Levy). Disbanding a Lord
now discards its Capabilities (to the deck discard) and releases Special
Vassals (1.5.3/4.4.3). Structured `modifiers` added to vassals.json special
entries. No SMOKEs. 188 tests pass.

## Round 19 (Phase 4-viii - levy/economy card effects)

Added ratings.has_capability and wired three economy capabilities:
- Beloved Warwick (Y16): Levy Troops yields 5 Militia (pool-limited) instead
  of the Stronghold's table Troops.
- Alice Montagu (Y17): a Levied Vassal's Calendar Service marker is placed
  one box further right (+1 Service, capped at box 15).
- Great Ships (Y6): each Ship counts double for Sail (12 Forces / 4 Provender
  / 4 Carts) and Supply (+2 Provender per Ship from a Port), and connects all
  Ports across Seas as 1 Way for Parley, Tax, and Supply (NOT Sail, FAQ #1) -
  threaded via an all_seas flag through the Parley/Tax/Supply route finders.
No SMOKEs. 192 tests pass; round-trip clean.
