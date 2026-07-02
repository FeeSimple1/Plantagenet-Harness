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

## Round 20 (Phase 4-ix - influence/favour & active-event card effects)

Added ratings.event_active / event_against helpers and wired three cards that
turn on active This-Levy / This-Campaign events or a Held-in-Battle play:
- Rising Wages (L9, This-Levy): the Yorkist side pays 1 Coin to Levy Troops
  (normally free); enforced in actions._h_levy_troops via event_against, code
  rising_wages_no_coin when the Coin is unavailable.
- New Act of Parliament (L10, This-Campaign): a Yorkist campaign Parley
  consumes the whole card (actions_remaining -> 0) instead of 1 action; wired
  in commands.parley_campaign.
- Suspicion (Y5, Hold in Battle): before Array, an Influence check (1.4.2) by
  a Friendly Lord with strictly higher PRINTED Influence than an enemy Lord
  disbands that enemy Lord with no Influence loss; wired via
  battle._resolve_suspicion (codes bad_suspicion, no_suspicion,
  suspicion_influence). Result attached as res["suspicion"].
No SMOKEs. 196 tests pass; ruff clean; round-trip clean.

## Rounds 21-26 (Phase 4-x: remaining card effects, Waves A-F)

Wave A (rating mods): ratings.rating now sums printed + Special-Vassal +
Capability + active-Event modifiers (action-scoped for Parley); check_influence
routed through it. Caps: Thomas Bourchier, York's Favoured Son, Fair Arbiter,
Fallen Brother, In the Name of the King, Expert Counsellors, Veteran of French
Wars, Married to a Neville, Loyal Somerset. Events: Richard of York, Privy
Council.

Wave B (Tides scoring): capability region-Domination overrides (Welshmen,
Southerners, Northmen) + flat Influence (First Son, Council Member, Margaret
Takes the Reins) + We Done Deeds of Charity (decisions['charity']).

Wave C (battle caps): troop-adds (Muster'd My Soldiers, Pembroke, Welsh Lord,
Percy's North Y27/Y37, Kingdom United, Philibert), uniform/phase Armour (Church
Blessing, Barded Horse, Chevaliers, Piquiers), Yeomen of the Crown, Final
Charge, Bloody Thou Art, Vanguard, Swift Maneuver, Captain (effective Marshal).

Wave D (command/economy): Quartermasters/Woodvilles/Chamberlains no-Deplete,
The Commons, Soldiers of Fortune, Harbingers, Stafford Branch, Hay Wains,
Scourers, So Wise So Young, Two Roses, Percy's Power, Madame La Grande, Stafford
Estates, High Admiral, England Is My Home; new Command actions Agitators,
Merchants, Heralds. Deferred reactive Naval Blockade / King's Parley -> Q-004.

Wave E (events): events.play_event resolves ~20 immediate Events (incl. London
For York via new LocaleState.favour_extra); parley discount/auto/free-Lordship
(Succession, Parliament Votes, Jack Cade, My Crown, Gloucester as Heir, Dorset,
An Honest Tale); rating events (Yorkist Parade, Loyalty and Trust, Edward V);
Sail/March this-Campaign (Seamanship, French Fleet, Owain Glyndwr, Forced
Marches + Yorkists Never Wait); Vassal-Levy events (Yorkists Block Parliament,
Buckingham's Plot, The Earl of Richmond, Margaret Beaufort); battle Holds
(Warden of the Marches, Talbot, Patrick de la Mote). Remaining play-timing /
reactive Events -> Q-005.

Wave F (Succession 6.2-6.3): succession.on_heir_removed implements the general
mechanic (next-ranked Heir to the next Calendar box, instantiating its LordState
if absent), wired into _kill_lord for the grand scenario. Per-War scripted card
swaps + Renewed-War setup -> Q-005 (need structured encoding).

No SMOKEs. 263 tests pass; ruff clean.

## Rounds 27-29 (Phase 5a: reaction protocol, Q-004)

reactions.py: typed trigger registry + serializable pause/resolve loop on
state.pending. apply_action gained a 'react' action and a pending-guard (only
'react' is legal while paused). Flat, priority-ordered offers; an upstream
cancel forecloses downstream offers; decline (pass) is first-class; paused
state round-trips through JSON save/load.

Triggers + reactors wired:
- uses_port_on_sea -> Naval Blockade (Y15): per-action, persistent, mid-action;
  Sail commits the Command card then gates, sail_finish moves or returns
  cancelled. (Tax/Parley/Supply port-sea detection noted as a route-introspection
  refinement; Sail is the proven case.)
- on_approach -> King's Parley (L15, cancel + rewind movers, end card),
  Parliament's Truce (Y12/L20, cancel + campaign-wide A/I prohibition), Blocked
  Ford (Y11/L11, force Battle). Canonical priority: King's Parley (10) forecloses
  Parliament's Truce (20) and Blocked Ford (30) (errata). march_finish rewinds on
  cancel.
- after_successful_levy_action -> The King's Name (Y32): Gloucester pays 1
  Influence to cancel; generic _snap/_restore reverts parley/levy_lord/
  levy_vassal/levy_troops.

play_held_event windows: Rebel Supply Depot (L28), Surprise Landing (L33),
Sun in Splendour (Y24), Yorkist Parade (Y20), Aspielles (Y13/L13 peek).
Action variants: Exile Pact (Y8 Command action), Be Sent For (L4 Levy Lord).

No SMOKEs. 280 tests pass; ruff clean. NOTE: in-Battle plays (Y5/Y30/Y36/Y37/
Y19/Y2/L2/L7) still resolve via the synchronous `decisions` channel; unifying
them under an at_battle_phase trigger requires making resolve_battle resumable
(5a-iii, see report).

## Round 30 (Phase 5b-i: structured Succession engine + War I)

succession.py rewritten as a structured trigger engine for the grand scenario.
War I encoded in wars_of_the_roses.json under successions: heirs, triggers
(while_remains henry_vi -> L15/L17; remove henry_vi -> to_calendar margaret +
add L27/L31; muster margaret -> assign L26 EDWARD free/mandatory, set-aside on
disband; remove somerset_1 -> somerset_2), and Automatic War Victory.

Mechanism: deck membership of Succession-managed cards is reference-counted by
source (deck_sources[side][card] = [lord...]); a card stays while >=1 source,
so cards repeated across Lords stay put (errata). Grand loader now assembles
War I decks from Scenario Ia and runs apply_setup; decks gained a set_aside
pile. _disband_lord sets aside flagged Capabilities; levy_lord fires on_muster;
play_event suppresses Henry Released (L26) once L26 is assigned; _kill_lord
surfaces Automatic War Victory to state.victory.

No SMOKEs. 289 tests pass; ruff clean. REMAINING (5b-ii): encode Wars IIY/IIL/
IIIY/IIIL succession triggers (need on_becomes_highest_heir,
on_heir_count_at_or_below, replace_lord_in_place vocabulary) AND the Renewed-War
setup transition (E1 6.1) -- the latter is a new setup subsystem, scoped to Eric.

## Round 31 (Phase 5b-ii: Wars II/III triggers + Renewed-War transition)

5b-ii-a: succession.py engine vocabulary -- while_king (current-King deck cards,
swapped on King change), becomes_highest_heir (+ replace_lord_in_place),
heir_count_at_or_below(n) one-shot adds, replace_lord_in_place. Per-War heir
lists may group replaceable slots. setup_only Wars (III) no-op in play.
Structured successions encoded for war_iiy/iil/iiiy/iiil.

5b-ii-b: Renewed-War transition (E1 6.1). scenarios.renew_war: next War by
winner (next_war_id via respite_and_war), rebuild board from the new War's
structured setup, base decks from a new arts_of_war_spec ({add,except} over
no-rose), carry forward removed Heirs (and -8 Influence each, not Warwick),
resolve the King token to the highest surviving Heir (firing its Muster
trigger, e.g. Margaret->L26), persist set_aside, then run setup-time
Succession. Fixed apply_setup so while_king cards register only via the King
source (Somerset's while_king cards no longer leak in when he is not King).

No SMOKEs. 300 tests pass; ruff clean. RESIDUAL: IIY/IIIY base-scenario placement
is succession-conditional prose (the King resolves; finer conditional Lord
placements/Natural-Causes rolls are a refinement). IIL/IIIL structured paths
transition end-to-end.

## Round (2026-05-22): close out Q-004 and Q-005

Reviewed the two long-standing open questions against current code and the
source/reference docs. Both are resolved or implementation-only, so neither is
a live rules question:

- Q-004 (reactive interrupt Capabilities) was fully implemented in Phase 5a
  (`reactions.py`: Naval Blockade Y15, King's Parley L15, Parliament's Truce
  Y12/L20, Blocked Ford Y11/L11, The King's Name Y32). Moved to D-005.
- Q-005 (scripted Succession swaps + play-timing Events) is mostly implemented
  (`play_event`/`play_held_event`, the reaction hook, the per-War Succession
  engine, Renewed-War setup). Its residue is implementation backlog governed by
  clear card/scenario text, NOT a rules ambiguity: (a) For Trust Not Him L7
  in-battle Vassal Levy; (b) Naval Blockade also gating Tax/Parley/Supply
  (needs route->sea introspection; the card text already lists the gated
  actions); (c) Wars IIY/IIIY conditional Lord placements + Natural Causes
  rolls (Scenario Reference E4/E6; "last Turn played" = final Calendar Turn box
  per Rules §2.2). Moved to D-006. `RULES_QUESTIONS.md` now lists no open
  questions.

No code behaviour change (docs + one stale comment in `reactions.py`).
300 tests pass; ruff clean.

## Round (2026-05-22): implement L7 For Trust Not Him (D-006 residue (a))

Replaced the deferred `for_trust_not_him` stub with `battle._resolve_for_trust`,
resolved at the Battle Event step (4.4.1) right after Suspicion (priority order
preserved). A participating Lord attempts an Influence-check Levy (3.4.3) of a
regular Enemy Vassal in the Battle, ignoring Routes and the Vassal Seat's
Favour; the only Influence cost is the check + loyalty modifier (1.4.2). On
success the Vassal counter moves to the Levying Lord's mat -- and so fights the
current Battle for its new Lord (`_Force` vassal-count swing) -- with its
Calendar service marker reset as if newly Levied. Salisbury's Vassals are immune
(Y17 Alice Montagu). The `deferred` flag is removed from the L7 BATTLE_REACTIONS
entry. 6 new tests; 306 pass; ruff clean.

## Round (2026-05-22): Naval Blockade gates Tax/Parley/Supply (D-006 residue (b))

Extended the Y15 `uses_port_on_sea` reaction beyond Sail. `tax`, `parley_campaign`,
and `supply` now compute the Sea(s) their Route uses and gate through
`reactions.gate(... "uses_port_on_sea" ...)` with new `tax_finish` /
`parley_finish` / `supply_finish` resumes. Route->sea introspection threads a
`block_sea` argument through `_parley_route_cost` / `_supply_route_cost`;
`_route_used_seas` deems a Sea "used" when blocking it raises the Way cost (so an
equally short land route routes around the Blockade), while Campaign Parley uses
the Port's Sea on a non-adjacent same-Sea reach and Ship Supply uses the Source
Port's Sea. Per the Y15 tips the Command-action cost is committed before the
reaction window and a block makes no Influence payment / applies no effect. 6 new
tests; 312 pass; ruff clean.

## Round (2026-05-22): Natural Causes post-victory rolls (D-006 residue (c), part 1)

Implemented `scenarios.apply_natural_causes`, run at the top of `renew_war` when a
won second War (IIY/IIL) transitions to the third. Henry VI and York roll 2d6
(removed if the sum < the last Turn box reached); Edward IV rolls 1d6 in IIY only
(removed on a 6); IIL has no Edward IV roll. Structured `natural_causes` spec added
to wars_of_the_roses.json. Removed Heirs carry over REMOVED and incur the -8
Influence penalty; fixed `_apply_lost_heir_influence` to use the global 6.2.1 Heir
list (`succession.is_global_heir`) plus a static-side fallback, so a Heir absent
from the next War's roster (Henry VI in IIIY) is still penalised. 6 new tests; 318
pass; ruff clean. STILL PENDING for (c): the IIY/IIIY conditional Lord/Seat/Favour
placements (large; no rules ambiguity -- implementation only).

## Round (2026-05-22): co-location invariant (cross-project advisory audit)

Audited the "Retreat penalizes but never relocates" advisory against Plantagenet.
FINDING: the bug class does not apply -- Plantagenet has no Retreat and no
Siege/Storm (Rules summary p.1: "There is no Retreat: Routed Lords either Die or
Disband"; "Siege and Storm: There are none"). A battle loser is the side whose
Lords all Rout; every Routed Lord leaves the Locale via _kill_lord (REMOVED),
campaign._disband_lord (location=None, cylinder to Calendar), Escape-Ship Exile,
or the L16 Warden move. Verified the relocation mutation exists.

The one latent path: the 60-round safety cap (`while ... and n < 60`) -- if a
battle ever exits with un-Routed Lords on both sides, _ending's "both lose"
branch disposes only Routed Lords, leaving opposing Lords co-located. Not
reachable by normal play (no Concede in Plantagenet), but real.

Per advisory #3, added a runtime invariant regardless (closes the class):
`invariants.co_location_violations` / `assert_board_invariants` -- no two opposing
Mustered Lords share a `location`, exempting a Locale with an open Approach
reaction (4.3.5 / Q-004), where the Marching Lord legally co-locates while the
defender's cancel/Battle resolves. All 7 scenario setups and post-battle states
are clean. 10 new tests; 328 pass; ruff clean.

## Round (2026-05-23): War IIY succession-driven setup (D-006 residue (c), part 2)

The grand IIY had been using the standalone Scenario II roster verbatim, which
mis-seated Edward IV as King even when York survived War I (Scenario II is set
after York's historical death, so its lord list omits York/March/Rutland).
Added `scenarios.apply_iiy_setup` (+ `_place_lord` / `_unplace_lord` helpers),
run in `renew_war` for war_iiy before `succession.apply_setup`. It suppresses the
base Yorkist heir-line and re-places by War I survival per E4: King = highest
surviving Heir at London (the March->Edward IV and Gloucester(1)->Richard III
King transforms are still applied in place by apply_setup's becomes_highest_heir
triggers); March@Ludlow when York is King; Rutland@Canterbury; Gloucester(1)
silver box 9; Devon box1, Northumberland(1) box9 always; Pembroke@Pembroke only
at <=2 Heirs; Yorkist Favour at Canterbury. Lancastrian: surviving Henry VI /
Somerset(1) lead from box 9 (Exile), displacing Margaret / Somerset(2). Verified
Succession cards track the roster (York Y14/18/19/20 present; Edward IV
Y23/24/28/31 when promoted). 5 new tests; 333 pass; ruff clean. STILL PENDING:
IIIY conditional setup.

## Round (2026-05-23): War IIIY succession-driven setup (D-006 residue (c), part 3 -- COMPLETE)

`scenarios.apply_iiiy_setup` clears the base Scenario III roster (E6 "hold off
setting up any Lords") and rebuilds the whole roster from Succession: King =
highest surviving Yorkist Heir at London, next Heir kept, all others removed;
per-Heir placements with ring variants (Gloucester(1) silver@Gloucester / (2)
gold@London / Richard III gold@London; March@Ludlow vs Edward IV@London;
Rutland@Canterbury or King@London); the Y28 set-aside displaces Rutland; the
Warwick-as-King branch (+ Salisbury, Y16/17/22); Northumberland(2)@Carlisle + Y37
when one senior Heir remains; Norfolk@Arundel always; the single Lancastrian
leader (Margaret / Henry Tudor / Warwick by condition) with Oxford + Jasper
Tudor(2); Favour = London Yorkist + each in-play Lord's marked Seat. Y28
"Gloucester As Heir" set-aside is recorded at event activation in arts_of_war and
carried into IIIY by renew_war (only from a second War). Verified across all
branches incl. the co-location invariant (clean). 9 new tests; 342 pass; ruff
clean. (c) complete -- all of D-006 residue (a)/(b)/(c) is now closed.

## Round (2026-05-23): edge-case completeness (Phase 5j)

Four deferred edge-case items, all merged with tests:
- IIY/IIIY favour markers: `_recompute_stronghold_markers` sets City/Town/Fortress
  Influence-track markers from the post-setup Favour layout (E4 'slide Yorkist
  Cities marker to 1'; E6 'adjust ... per Favour'). These markers are display
  state only (Tides recomputes from live Favour).
- Muster Exiles (3.3.1): new `muster_exiles` action moves Exile-marked Calendar
  Lords to their designated Exile box (allied_networks, now carried across Wars)
  for free; enumerated in legal_moves.
- at-Sea Sailing + Disembark/Shipwreck (4.8.2): new `LordState.at_sea`; Sail can
  go 'into a Sea' and from at-Sea to a Port; End-Campaign resolves Disembark
  (Shipwreck 1-4 = removal + Unpaid penalty + Succession; Land 5-6 = chosen
  Enemy-free Port + Feed, else Disband).
- Asset Sharing (1.5.3): `sail`/`supply` accept a `share` list; co-located
  Friendly Lords' Ships/Carts are pooled for capacity (used, never transferred).
356 pass; ruff clean.

NOTE (flagged, not changed): the existing port->port Sail allows a direct hop to
a Port on an *adjacent* Sea, whereas FAQ #1 (quoted on the Great Ships card) says
Sail may not go directly port-to-port across different Seas (transit via at-Sea).
This predates Phase 5j and is governed by D-001; left unchanged here to avoid
re-opening a recorded decision. Worth a follow-up review.

## Round (2026-05-23): Advisory #2 -- co-location bug class audit (3 doors)

Audited the illegal-co-location class against Plantagenet:
- Door A (combat disposition / Retreat): N/A -- no Retreat; every battle loser
  leaves via Die/Disband/Exile (confirmed Phase 5g).
- Door B (Siege/Bypass marker lifecycle): N/A -- Plantagenet has no Siege/Storm
  or Bypass and no inside-Stronghold flag; no marker can go stale.
- Door C (on-board placement): audited every map-placement path. Levy Lord
  (3.4.2) already redirects off an Enemy-occupied Seat; Disembark Land checks
  Enemy-free; Muster Exiles places to an Exile box. FOUND + FIXED a bug: Sun in
  Splendour (Y24) Mustered Edward IV onto any Yorkist-Favour Locale WITHOUT the
  card-mandated "free of Enemy Lords" check (and missed the Yorkist Exile-box
  option) -> could co-locate Edward IV with a Lancastrian Lord. Now enforces
  Enemy-free + supports the Exile box, and validates before mutating.

Wired the co-location invariant into the legal-moves round-trip sweep test (run
after every enumerated/applied Muster move). Added tests/test_co_location_class.py.

The sweep ALSO surfaced a pre-existing crash the advisory predicted I'd been
hiding: my earlier empirical renew sweep wrapped the second transition in
try/except and silently swallowed a DataError. War IIIL's setup is unimplemented
(E7): its JSON carries prose Favour and a 'yorkist_lords_per_succession'
placeholder, so IIL->IIIL renew_war raises DataError before any board exists.
This is a setup-completeness gap (not a co-location bug); surfaced explicitly as
a strict xfail (test_iil_to_iiil_transition_builds) rather than swallowed. IIIL
needs a succession-driven setup like IIIY (E7). 368 pass, 1 xfailed; ruff clean.

## Round (2026-05-23): War IIIL succession-driven setup (E7) -- closes the last transition

Implemented `scenarios.apply_iiil_setup`, the Lancastrian-victory mirror of IIIY,
fixing the IIL->IIIL crash surfaced last round. Fixed war_iiil JSON (prose Favour
-> {}; removed the yorkist_lords_per_succession on_map placeholder). The setup:
Lancastrian King = highest surviving L Heir at London (Somerset(2) yields to
Somerset(1)) with King cards (Henry VI L15/L17; Margaret L27/L31 + L26; Somerset
L18/L20/L27), plus Oxford@Oxford and Jasper Tudor(2)@Pembroke. Yorkist Rebels by
Succession (form reversion edward_iv->march / richard_iii->gloucester_2; the
Y28/Gloucester-sole branch + Y35; York + single next-highest with Y14/Y18 and
Y20 or Gloucester(1)+Y34; Warwick-as-Heir + Y16 when no York-line Heir; Salisbury
+ Y17/Y22 when exactly one Heir; Norfolk always) placed in the Burgundy Exile box
-- or at Calais if a Yorkist Warwick is the Heir. Favour = London Lancastrian +
each in-play Lord's marked Seat; markers recomputed. Generalized the IIIY favour
helper to `_apply_succession_favour(state, king_side)`.

All four second->third War transitions (IIY/IIL x Yorkist/Lancastrian win) now
build with no co-location. Flipped the IIIL strict-xfail to a passing test.
tests/test_war_iiil_setup.py: 6 tests. 375 pass; ruff clean. The grand scenario
now transitions end-to-end through every War.

## Round (2026-05-23): Sail FAQ #1 fix (resolves the Phase 5j flag)

Resolved the cross-Sea Sail flag raised during Phase 5j. Per 4.6.1 + Errata
FAQ #1 (both cited by decision D-001), a Lord at a Port/Exile box may Sail
Port-to-Port only WITHIN a Sea; cross-Sea travel must transit at Sea. The
existing code allowed a direct Port-to-Port hop between adjacent Seas, violating
FAQ #1 (which D-001 endorses) -- so this fixes a real bug and implements D-001
correctly (it does not re-open the decision; D-001's Sea adjacency still governs
the at-Sea transit). Fixed both `commands.sail` (new `cross_sea_port_to_port`
guard; a Lord already at Sea may still reach a Port on an adjacent Sea) and the
`legal_moves` enumerator (new shared `_sail_moves`, which also enumerates "into a
Sea" moves and at-Sea-origin Sails, and mirrors French Fleet / Owain Glyndwr).
The round-trip activation sweep caught the enumerator/handler mismatch.
tests/test_sail_cross_sea.py: 4 tests. 379 pass; ruff clean.

## Round (2026-05-23): rules-coverage audit + scenario special rules (batch 1)

Thorough audit found the engine core complete (all 74 cards, full Levy/Campaign/
Battle/End sequence, victory 5.1/5.2/5.3, all six War setups). The remaining work
is scenario special rules (prose, unimplemented) + Surrender. Batch 1 (the
bounded, scoring/flow rules), all data-driven via `campaign._active_special_rules`
(reads the active scenario/War's own special_rules):
- Ravaged Land (IIIY/IIIL/My Kingdom): skip Grow AND Waste at End-Campaign.
- Brief Rebellion (Somerset's Return): skip Waste.
- Queen Regent (Warwick's Rebellion): Margaret at London -> +3 Lancastrian at Tides.
- Surrender / Concede a War (6.1.1-.2): new `concede` action -- in the grand
  scenario's first/second War a side with an Heir present concedes, setting the
  War victory to the other side (consumer then calls renew_war). Rejected in the
  third War / non-grand.
- Gloucester special rule (IIY/IIL): once Y28 GLOUCESTER AS HEIR is played/set
  aside, the FIRST SON Capability becomes unavailable (suppressed at Tides).
tests/test_special_rules.py: 7 tests. 386 pass; ruff clean.
STILL TO BUILD: Foreign Haven + Shaky Allies (IIY movement/battle), and the
standalone-scenario batch (Capture of the King, King Richard, Montagu, Norfolk
is Late, Test of Arms, Bosworth).

## Round (2026-05-23): IIY special rules Foreign Haven + Shaky Allies (batch 2)

Completes the grand-scenario special rules.
- Shaky Allies (IIY / Warwick's Rebellion): Margaret and Warwick may never enter
  the same Stronghold -- `commands._shaky_allies_block` guards March and Sail
  (and the legal_moves enumerator), blocking a move that would co-locate them
  (incl. both moving together).
- Foreign Haven (IIY): Warwick choosing Exile on Approach (battle.approach hook)
  or dying as a defender (battle._ending hook) shifts all Lancastrians on the
  Calendar left to the current Turn box and all Yorkists left to the next Turn
  box (`campaign._foreign_haven_shift`).
tests/test_special_rules.py: 10 tests total. 389 pass; ruff clean.
All grand-scenario special rules now implemented; remaining: standalone-scenario
batch (Capture of the King, King Richard, Montagu, Norfolk is Late, Test of
Arms, Bosworth).

## Round (2026-05-23): standalone special rules -- Montagu + Test of Arms (batch 3a)

- Montagu (Somerset's Return): `_apply_setup_special_rules` gives the Yorkist
  Warwick the L23 MONTAGU Capability + Montagu Special Vassal at setup.
- Test of Arms (Towton): a Battle at York sets York's Favour to the winner
  (battle._ending); at Campaign end the Favour-at-York holder wins (else draw).
  Corrected a test that wrongly expected a 5.3 victory for Towton.
391 pass; ruff clean. Remaining standalone: King Richard, Norfolk is Late,
Capture of the King, Bosworth (Victory / On Bosworth Field).

## Round (2026-05-23): standalone special rules complete (batch 3b)

Finished the standalone-scenario special rules:
- King Richard (My Kingdom): crown_richard action replaces Gloucester at London
  with Richard III in place.
- Bosworth (battle-only): battle._ending now skips the Influence award/Spoils
  when there is no Influence track/map Locale -- the battle winner wins the
  scenario (all-Rout = draw). Fixed a crash resolving Bosworth.
- Capture of the King (Scenario Ia): Yorkists beating Henry VI capture him onto
  an Unrouted Yorkist Lord's mat (no Death roll, +10 Yorkist) -- new
  LordStatus.CAPTURED + LordState.captured_by; when the holder leaves play
  (campaign._release_captive in _disband_lord, covering Disband/Exile/Death),
  Henry VI returns to the Calendar and the Lancastrians gain +10.
- Norfolk is Late (Towton): in the first Battle including Norfolk and another
  Yorkist Lord, Norfolk stays in Reserve until Round 2 (battle._reposition gains
  a `held` set; tracked once via new GameState.flags).
Schema regenerated (CAPTURED/captured_by, flags). tests/test_special_rules.py:
17 tests. 396 pass; ruff clean. ALL scenario special rules now implemented.

## Round (2026-05-23): CLI pending/history + stale-comment cleanup

- CLI: implemented the `pending` (shows state.pending + the awaiting reactor) and
  `history` (last N action/result entries) commands, replacing their stubs;
  removed the unused _NOT_YET/_stub plumbing and the "stubs" module docstring.
- Documentation debt: rewrote stale module docstrings / comments across
  actions.py, campaign.py, commands.py, legal_moves.py, scenarios.py,
  static_data.py, arts_of_war.py, state.py that still described implemented
  features as "deferred to Phase N / not yet". Schema regenerated (state.py
  docstring feeds the model schema). tests/test_cli.py updated. 397 pass; ruff
  clean.

## Round (2026-05-23): validated action palette + always-on invariants (Nevsky advisory §2/§3)

Adopted the two highest-leverage structural recommendations.
- Validated palette (§2): `legal_moves.validated_legal_moves` probes every
  enumerated move on a deep copy and drops/logs any the handler rejects
  (over-enumeration diagnostics). Safe because the RNG lives in the state
  (seed + rng_state) -- verified probing leaves the real dice untouched. Exposed
  via `legal-moves --validated`. 3 tests (incl. a deliberate over-enumeration).
- Always-on invariants (§3): added influence-marker-in-bounds, lord-status/
  position consistency (battle-only scenarios exempt -- Lords sit in an Array
  with no Locale), and card-zone (no card in two deck piles or both in a deck
  and on a mat). `invariants.board_invariant_violations` aggregates these with
  the co-location check and now runs after EVERY move in the round-trip sweep.
- BUG FOUND by the new card-zone invariant: `_h_levy_capability` (3.4.6) put the
  Levied card on the Lord's mat but left it in the deck -- so it could be drawn
  again and duplicated. Fixed (the Levied card now leaves the unused pool).
Doors A/B/C, clause-by-clause audit, decision log, and negative enumerator tests
were already in place from earlier rounds. 411 pass; ruff clean; schema in sync.

## Round (2026-05-23): random-policy Levy fuzz (advisory §5)

Added tests/test_fuzz_random_policy.py: a seeded random-policy fuzz over the Levy
(draw -> pay -> muster) across all non-battle-only scenarios x 3 seeds. At each
Muster step it asserts the validated palette offers no handler-rejected move
(enumerator clean) and board_invariant_violations stays empty, then applies a
RANDOM legal move -- walking trajectories the first-legal round-trip sweep never
reaches. 18 cases; clean. 429 pass; ruff clean.

## Round (2026-05-23): enumerate react during a pending reaction (readiness gap 1)

Readiness gap for agent-driven full-game play: while a reaction window was open
(Naval Blockade / King's Parley / Parliament's Truce / Blocked Ford / The King's
Name), legal_moves offered no react option, so the validated palette came back
EMPTY (apply_action allows only `react` while pending) -- a menu-driven agent
would stall. Fixed: legal_moves now emits the awaiting offer's react options
({play: card}, {pass: true}) when state.pending is set, and nothing else. Also
fixed a latent crash in reactions.resolve (a `pass` on a held-event offer with no
`lord` key) via offer.get('lord'). Round-trip test added (test_reactions). 430
pass; ruff clean.

## Round (2026-05-23): full-game smoke driver (readiness gap 2) -- 3 over-enumerations found

Added tests/test_full_game_smoke.py: drives complete games through the agent
interface (legal_moves -> apply_action), resolving reaction windows (via the
gap-1 react enumeration) and grand-scenario War transitions (renew_war), asserting
no enumerated move is rejected and no board invariant breaks at any step.
Standalone scenarios are driven to scenario-end; the grand scenario through its
Renewed-War transitions. As the advisory predicted, full-game play surfaced
enumerator/handler asymmetries the Levy fuzz never reached -- three over-
enumerations, all fixed by mirroring the handler gate in legal_moves:
  1. Lancastrian levy_vassal offered while Yorkists Block Parliament (Y7) active.
  2. levy_troops offered with no Coin while Rising Wages (L9) active.
  3. Lancastrian march into Wales offered while Owain Glyndwr (Y25) active.
Also: the validated palette now keeps build_plan as a templated/unvalidated
candidate (4.1 Plan is a free construction) rather than probing+rejecting it.
A 20-seed x 6-scenario sweep is clean post-fix. 448 pass; ruff clean.

## Round (2026-05-23): ChatGPT play -- immediate Arts of War Events never resolved

A ChatGPT playthrough (via scripts/chatgpt_play_helper.py) reported that immediate
Arts of War Event resolution was not integrated into the draw/legal-action flow.
Confirmed and fixed -- it was actually three coupled defects in the 3.1.3 draw:
  1. The draw routed an immediate Event's card back to the deck with the effect
     "applied by the consumer" -- but nothing applied it, and legal_moves never
     offered play_event, so the effect was silently dropped.
  2. play_event DISCARDED the card while 3.1.3 says immediate Events "return to
     deck"; resolving a drawn Event would then put one card in two zones (a
     card_zone invariant break waiting to happen).
  3. The many decision-bearing immediates can't take decisions at random-draw
     time, so a post-draw resolution step is required.
Fix: draw queues immediates on state.pending_events (no advance); legal_moves
offers a play_event template per pending Event and nothing else (apply_action
guards with events_pending); play_event resolves "as far as able", returns the
card to the deck (3.1.3), and advances the Levy when the queue empties. Five
precondition resolvers (Y26, L22, L32, L23/L24, L27) now resolve to no effect
when their card-text "No effect if ..." condition is unmet rather than raising,
and the two selection Events size to availability ("select 3 ... or all if fewer").
New tests in test_immediate_events_draw.py; full-game smoke + test helper fill
play_event decisions. 453 pass; ruff clean.

## Round (2026-05-24): ChatGPT Towton play -- reversed 5.1 winner + 3 under-enumerations

A ChatGPT playthrough of `towton` (seed 1) completed without crashing but
surfaced a substantive victory bug and several menu under-enumerations.

1. REVERSED 5.1 WINNER (substantive). campaign._victory_check returned the
   LOSING side as the winner: `"yorkist" if l_pres else "lancastrian"` awards
   Yorkist when Lancastrians have presence. Rule 5.1: the side with no Lords on
   the map (incl. Exile boxes) and no next-Turn Exile loses -- the OTHER side
   wins. Fixed to `"lancastrian" if l_pres else "yorkist"`. Also: has_presence
   now counts Exile-box Lords (status EXILE) per "including none in Exile boxes".
   This affected every scenario's 5.1 check, not just Towton; the full-game
   smoke missed it because it asserts no-crash + invariants, not winner
   correctness. New tests in test_victory_5_1.py.

2. UNDER-ENUMERATION (legal_moves._command_moves) -- moves the handler accepts
   but the menu never offered (logged by the helper as under_enum_accepted):
   a. March into enemy contact: the march loop skipped any enemy-occupied or
      enemy-adjacent destination, so attacking Marches (Intercept 4.3.4 /
      Approach + Battle 4.3.5) were never offered. Now enumerated; only
      Parliament's Truce bars marching onto an Enemy Lord.
   b. Group March (4.3.1): only solo Marches were emitted. Now offers the full
      eligible group led by a Marshal/Lieutenant (a Lieutenant not over a
      Marshal); partial groups remain available via a raw `group` list.
   c. Own-location Parley (4.6.4): Parley sat behind the `friendly_here`
      early-return, so a Lord on a non-Friendly Stronghold was never offered the
      automatic own-location Parley that flips it. Moved ahead of the gate.
   New tests in test_command_enumeration.py (assert the enumerator OFFERS each,
   per the round-trip discipline). Over-enum sweep + Towton helper play: clean.
456 pass; ruff clean.

## Round (2026-06-01): full rules-fidelity audit -- 17 findings fixed

A systematic module-by-module audit against the reference docs and Errata,
cross-checked card-by-card. The 459-test suite was green throughout, so every
item below is behaviour the prior tests did not exercise. New regression tests
live in `tests/test_audit_fixes_2026_06.py` (suite now 477; ruff clean).

CRITICAL
1. SUCCESSION DECK LOSS (succession._recompute). A becomes_highest_heir
   transformation (March->Edward IV: Y23/Y24/Y28/Y31; Gloucester->Richard III:
   Y32-Y35) registered its PERMANENT ADD cards (Scenario Ref E2) under the
   ref-counted source `king:<heir>` instead of `_PERMANENT`, and recorded
   `current_king` as the pre-replacement (now-REMOVED) heir. The next recompute
   saw the King "change" and dropped all those cards -- emptying the deck.
   Fix: apply the replacement first, register ADDs as `_PERMANENT`, and record
   the King actually in play. Reproduced and pinned.

HIGH
2. LOSSES (battle._losses) disbanded a *victorious Retinue-only* Lord. 4.4.3
   disbands only a Lord who LOSES ALL his own Troops; a Lord who never had
   Troops must survive. Now gated on `had_troops`.
3. BLOODY THOU ART (battle._ending, Y33). The card BLOCKS every "upon Death
   check" card (Escape Ship/Warden/Talbot) and Disbands Routed Yorkists, but the
   code consumed Escape Ship and let Lancastrians escape/Warden/Talbot before
   the bloody check. Now `bloody` is computed first, the escape block is skipped
   entirely, Routed Lancastrians Die and Routed Yorkists Disband.
4. JACK CADE (actions, Y4) still spent 1 Influence + 1 Lordship despite "without
   spending Influence or Lordship." Now 0/0 (free_lordship + total-spend
   discount).
5. SPECIAL VASSAL HASTINGS ignored by L15 (under-counted Influence loss) and
   L27 (could not be targeted; Y24 never discarded). `events.py` never read
   `special_vassals`. Both now include it; added `_disband_special_vassal`.
6. FEED (campaign.end_activation, 4.7) ran for the acting side only, so an
   Interceptor (inactive side, Moved-Fought) was never Fed on its card. Now both
   sides Feed, Rebel then King.

MEDIUM
7. PARLEY -1 discounts (Y18/L18 "min zero") evaporated at the home location --
   the discount only cut the Way surcharge, never the base point. `check_influence`
   gained a `discount` term so the spend can reach 0 (also fixes #4).
8. GLOUCESTER AS HEIR (Y28) wrongly waived Influence; the card grants 0 Lordship
   only. Removed the stray discount.
9. SPOILS at a Neutral locale halved per-loser; 4.4.3 totals then halves. Fixed.
10. LONDON FOR YORK (Y15) could place a third Favour marker; now capped at the
    second.
11. FORAGE from an Exile box never Depleted/Exhausted (4.6.2/1.3.1). Added
    `GameState.exile_depletion` (schema regenerated), wired Forage + Grow + the
    legal-move enumerator.
12. TIDES "Gain Lords Influence" (4.8.1) omitted EXILE-status Lords ("including
    those in Exile boxes"). Now counted.

NOTE: a reported "by-Sea Parley surcharge" was investigated and found to be a
FALSE POSITIVE -- at most one sea hop occurs in any shortest Parley route, so
counting that hop as one Way already equals "land Ways + 1 by-Sea surcharge."
No change made.

LOW
13. Unfed Lord disbanding from an Exile box now marks its cylinder as an Exile
    (3.2.4): `_feed` passes `from_exile`.
14. _release_captive placed Henry VI at `turn+1`; "as if just Disbanded" is
    `turn + (6 - Influence)`. Generalised.
15. legal_moves skipped a Lordship-exhausted Lord entirely, missing free actions
    (Stanley free Levy Troops; 0-Lordship Parleys). Added a `free_only` path; a
    `commit=False` peek lets `_parley_event_mods` be queried without consuming a
    use.
16. PAY TROOPS shortfall now honours a player `unpay_lords` choice (3.2.1) rather
    than only the default ascending-need order.
17. SHE-WOLF (Y17) clamped a service marker at box 15; a marker may shift
    off-calendar (2.2.3). Clamp removed.

DATA: data_integrity now validates the grand scenario (heirs / succession
triggers / arts_of_war_spec), which the old `sides`-only loop skipped. All
static JSON re-verified against the references: clean, no transcription errors.

## Round (2026-06-02): full rule-by-rule audit -- 20 findings fixed

A complete pass over the rulebook (sections 1-6), every Arts of War card
(Y1-Y37, L1-L37, both halves), and all scenario setups, via nine parallel
section auditors cross-checking code against the rules/Errata. Static data
(map/ways/seas/strongholds/forces/scenarios) re-verified CLEAN. Fixes, by area:

ENGINE / RULES
- Levy-action cap now uses EFFECTIVE Lordship (Y22/Y26/Y33 +Lordship Events).
- Pay (3.2.1/3.2.2) covers EXILE-status Lords (Y8 Exile Pact) -- Troops + 2/box.
- Grand-scenario Victory threshold = flat per-War value (5.2/E3-E7), not the
  henry_vi per-turn table; wins/losses had fired at the wrong Influence.
- Supply via Ship counts Shared Ships (4.5.2).
- Battle: Disband Routed Vassals of Unrouted winners (4.4.3); Losses no longer
  over-remove mat Troops when battle-local Capability Troops Rout.
- Succession: replacement-King "as long as <Lord> remains" cards (Edward IV, E4)
  drop on that Lord's removal (not _PERMANENT); general War Victory when a side's
  current-War Heirs are all removed (E2); ship-levy 9-holder cap edge.

CAPABILITIES / EVENTS (effect fixes)
- Restricted single-Lord Capability eligibility via the card "Lord:" line
  (cards.json lords==null had let any Lord Levy ~23 caps).
- Y5 Thomas Bourchier (Friendly City only); L17 Margaret Takes the Reins /
  L18 Council Member (Exile-box cases); Y7 (L7/L35/L37 supersession);
  Y34 An Honest Tale (Campaign Parley incl. own-location); L14 Percy's Power
  (Influence + Vassal Pay); L29 High Admiral (Parliament's Truce); L24/L28
  (shared-Exile-box alternative); Escape Ship + England Is My Home (Y8) plain
  Disband; Warden of the Marches (L16) destination/troopless-Disband.

NOT-IMPLEMENTED CAPABILITIES NOW IMPLEMENTED
- Y14/Y23 Burgundians (Handgunner deployment -- the only Handgunner source).
- Y18 Irishmen (5 Militia in Ireland / Irish-Sea Port, no Deplete).
- L12 Commission of Array (Levy Troops from an adjacent Friendly Stronghold).

MIS-TARGETED / PROCEDURE
- L4 Be Sent For now drives Muster Exiles (any Calendar box -> Exile box), not
  Levy Lord. Y10 Tax Collectors follows the full Tax procedure (Influence check,
  qualifying target, Deplete) for DOUBLE Coin. Intercept (4.3.4) may bring a
  Group. L33 Surprise Landing requires the Lord at a Port.

REMAINING (documented, low priority)
- L33 free action not constrained to a non-Path March (consumer-enforced).
- Somerset(1)->(2) on death enters the Calendar rather than a literal in-place
  swap (defensible; the dead cylinder is off the map). E5 says "in place".

Suite 459 -> 520; ruff clean. Commits: audit/full-rules-batch1 + batches 2-11.

## Round (2026-06-02b): closed the two documented remainders

- L33 Surprise Landing free March may not use a Path (enforced in march() via a
  per-Lord flag, consumed on a valid non-Path March, cleared at end of activation).
- Somerset (1) -> (2) now replaces IN PLACE on removal (E5): _kill_lord captures
  the board position and Succession re-seats the replacement Mustered there,
  not on the Calendar (Calendar fallback only when no map/exile position exists).

Suite 520 -> 522; ruff clean.

## Round (2026-06-11): grand-scenario playthroughs -- 5.3 tie-break + Surrender end

Full `wars_of_the_roses` playthroughs (random, survival-biased, and
battle-seeking policies; per-step `validated_legal_moves` + board invariants)
ran clean through all Renewed-War transitions, but probing the War-end paths
play rarely reaches surfaced two rules bugs, both fixed:

1. **Scenario End tie went to a draw instead of the King (Errata FAQ #5).**
   `campaign._victory_check` 5.3 returned `draw` when Influence was tied at
   the final Victory check. Errata & Clarification FAQ #5: "If a scenario is
   Tied (IP at 0 at end of scenario), victory goes to the King." Worse in the
   grand scenario: the "draw" was indecisive, so `renew_war` refused the
   transition and a tied War I/II silently ended the entire Wars of the Roses.
   Fix: 5.3 tie now resolves to the King's side (with a `tie_break` note in
   the victory dict). Towton's Test of Arms keeps its explicit no-Favour draw,
   and the 5.1 both-sides-wiped draw is unchanged.
2. **Surrender (6.1.1) did not end the conceded War.** `concede` set
   `state.victory` but left `phase` at levy/campaign, so the menu kept
   offering moves and play could continue after the concession (and a later
   victory check could overwrite the surrender result). Fix: `concede` sets
   `phase = "over"`; `legal_moves` then returns nothing and the consumer
   proceeds straight to Renewed War (6.1.2).

New regression tests in `tests/test_playthrough_findings_2026_06.py` (5).
580 pass.

## Round (2026-06-21): bug-finding gauntlet -- battle decision fuzz + mass sweeps

Built two reusable harnesses (`scripts/sweep_harness.py`, `scripts/battle_fuzz.py`)
and ran the gauntlet the prior round called for: a competent scripted player
(random / survival / aggressor / plan-order-fuzz policies) over ~950 full
`wars_of_the_roses` games plus the five standalone scenarios, with per-step board
invariants; and a dedicated battle decision-payload fuzzer (~14k fuzzed battles)
that resolves each fuzzed battle FULLY on a fork -- IllegalAction anywhere =
illegal combo (discard), any other exception or a post-resolution invariant break
= bug. Probing on `model_copy(deep=True)` is exact (the RNG lives in the state).

Mass normal play was clean (0 crashes / over-enumerations / invariant breaks);
the fuzzer surfaced two real bugs, both fixed:

1. **Malformed battle `regroup` decision crashed with a raw `TypeError`.**
   `battle.resolve_battle` expects `{"regroup": {"lord": <id>, "round": <n>}}`
   (4.4.2) and did `rg["lord"]` unconditionally, so a wrong-shaped value (a bare
   Lord-id string, or a dict missing "lord") raised `TypeError: string indices
   must be integers` / `KeyError` instead of the graceful `IllegalAction` the
   rest of the file uses. An agent-facing harness must reject bad payloads
   descriptively, never crash. Fix: validate `isinstance(rg, dict) and
   rg.get("lord")` -> `IllegalAction("bad_regroup")`. (An empty dict stays a
   legitimate no-op via the existing `if rg:` guard.)
2. **Succession deck-ADD cloned a mat Capability into the draw pile**
   (`card_in_deck_and_on_mat`). A battle that changes a side's Heir fires
   `succession._recompute`, re-registering while_king / count-threshold cards via
   `_add_to_deck`. Its `_deck_has` guard checked only deck piles, not Lords'
   mats, so a card already deployed as a Capability (surfaced with Y20 Yorkist
   Parade on rutland's mat) was duplicated into `draw`, breaking the one-zone
   invariant the engine relies on (cf. the `on_muster_lord` "not counted in both
   zones" note). Fix: `_deck_has` now also treats a card on any Friendly Lord's
   mat as in play, so `_add_to_deck` won't clone it.

New regression tests in `tests/test_fuzz_findings_2026_06b.py` (6). 580 -> 586
pass; ruff clean.

## Round (2026-06-21b): hygiene, property-based + mutation testing

Closed the cheap "honest gaps" and added two test-strength layers.

Hygiene: `requires-python` corrected `>=3.11` -> `>=3.10` (the engine runs on
3.10; ruff/mypy targets aligned); version bumped to 0.3.0; `CHANGELOG.md` added;
README Status section rewritten (it had described combat as a future phase though
combat + all 74 cards are implemented); GitHub Actions CI added (ruff + pytest on
a 3.10/3.11/3.12 matrix). mypy --strict is configured but not clean (626 errors)
so it is left out of CI for now -- recorded as a known gap.

Property-based tests (`tests/test_property_conservation.py`, Hypothesis): drive
random legal play from Hypothesis-chosen (scenario, seed, depth) and assert the
physical card one-zone law (deck piles + mats + pending; the law the Y20 bug
broke), all board invariants, and non-negative troop counts -- in every reachable
state. No counterexamples found.

Mutation testing (`scripts/mutation_probe.py`, a self-contained AST mutator --
mutmut 3.x fights this repo's src-layout in the sandbox): a baseline run on
`influence.py` (the 1.4.2 Influence check, victory-critical) initially killed only
~50% of mutants. The survivors exposed a real gap: the success rule
(crit roll==1 / fumble roll==6 / else roll<=rating), the spend formula, and the
_RATING_BONUS map were only ever exercised at rating 5, which masks every one of
those branches. Added `tests/test_influence_check_branches.py` (12 tests) pinning
each branch with the d6 forced; score rose to 31/32 killed (96.9%). The lone
survivor (`net >= 0` -> `net > 0`) is an equivalent mutant: `marker_side` is
unobservable when `marker_at == 0`.

Suite 586 -> 598 (+6 fuzz regressions earlier, +2 property, +12 influence-branch
... net 580 -> 598 across both 06-21 rounds); ruff clean.

## Round (2026-06-21c): mutation testing across the engine

Built a coverage-guided mutation harness (`scripts/mutation_cov.py`): record
per-test line coverage once (`pytest --cov-context=test`), then for each mutant
run only the tests that execute the mutated line (a test that never runs the line
cannot kill it). Sound and far faster than a blind suite re-run. Hardened against
the sandbox's hard wall-clock kills: atomic source writes (temp + os.replace),
git-restore of the target on startup, and PYTHONDONTWRITEBYTECODE in the test
subprocess (a killed run had left a stale mutant .pyc that briefly poisoned the
suite). Budgeted (`--max-seconds`) and resumable (`--resume`).

Fully swept (mutants killed / total):
- influence.py  32/32  (100%)  -- 1.4.2 Influence check
- invariants.py 45/45  (100%)
- arts_of_war.py 27/27 (100%)
- ratings.py    77/78  (98.7%) -- lone survivor is an equivalent defensive
  `or`-guard in _loc (crashes only on a nonexistent lord id, never reached)

Gaps found and closed (real, not equivalent):
- influence.py: the success rule (crit/fumble/roll<=rating), spend formula and
  _RATING_BONUS map were only ever exercised at rating 5, masking every branch.
  -> tests/test_influence_check_branches.py (12).
- ratings.py: the card-capability rating BONUSES -- exact values and the
  "... or in the same Exile box as <Lord>" alternative clauses (Y5, Y20, Y22,
  Y26, L11, L13, L20, L24, L28) plus the active-Event modifiers (Y14/Y35/Y20/
  Y22/Y33) -- were largely unasserted; a wrong +1/+2 on a card is a rules bug.
  -> tests/test_capability_rating_bonuses.py (14).

Not yet swept (the harness is resumable; run offline):
- battle, commands, actions, campaign, legal_moves, events, scenarios,
  succession, reactions, pay (~2,500 of ~2,982 sites). pay had a partial run
  with boundary survivors (e.g. pool>=need at L138) left open. These behaviour-
  heavy modules are exercised hard by the integration suite (full-game smoke +
  the sweeps), so their kill rates are expected to be high; confirming that and
  closing any stragglers is the remaining work.

Suite 600 -> 614; ruff clean.

## Round (2026-06-21d): mutation sweep continued (CI token)

Live CI added (.github/workflows/ci.yml) plus a manual-dispatch mutation job
(.github/workflows/mutation.yml) -- a full mutation sweep is a long job whose
proper home is CI, not the interactive sandbox.

Harness gained `--sample N` for sound score ESTIMATES on the big modules.

More modules swept (coverage-guided):
- reactions.py, pay.py: largely complete. pay's exact-afford boundary
  (`pool >= total_need`, _pay_troops 3.2) was a real survivor -> closed with
  tests/test_pay_afford_boundary.py (2).
- battle.py, commands.py: sampled estimates ~50-75%.

KEY METHODOLOGICAL FINDING: beyond the numeric-assertion gaps already closed,
the remaining survivors are dominated by EQUIVALENT mutants, where the mutated
program is behaviourally identical, so no test can (or should) kill them:
- reactions.py BATTLE_REACTIONS priority table (L261-283): priorities are tiered
  >=5 apart (5/10/15/20/25/30/40), so a +1 mutation never changes the resolution
  order -> all ~18 are equivalent.
- redundant multi-clause guards (e.g. battle.py L567-570 `or` chains) and
  defensive None-guards (ratings _loc) where the mutated branch is unreachable.
This means the raw "mutation score" UNDERSTATES test strength on these modules;
the actionable signal is the small set of non-equivalent survivors, which have
been triaged and closed where real (influence branches, ratings card bonuses,
pay afford-boundary).

Remaining (run via the mutation CI job): full exhaustive sweeps of battle,
commands, actions, campaign, legal_moves, events, scenarios, succession.

Suite 614 -> 616; ruff clean.

## Round (2026-06-22): coverage-guided gap hunting

Built a combined line-coverage map of the full 616-test suite (per-chunk data
files + `coverage combine` -> JSON; the slow integration tests are isolated into
their own chunk so each fits the sandbox budget). Triaged every uncovered line in
the rules modules into three buckets:

1. Defensive / unreachable -- the bulk. legal_moves is wrapped in
   `try: ... except (KeyError, AttributeError, IndexError): pass` guards around
   static-data access; those except bodies never run with valid data. Not real
   rule gaps (testing them would mean corrupting the static data).
2. Niche card / scenario branches -- real but setup-heavy: rare Capability
   combos (battle.py Patrick+Leeward, Norfolk reserve, the Regroup troop-recovery
   loop), specific Succession triggers, scenario-variant setup. Logged for later.
3. Genuinely untested rule paths -- CLOSED this round:
   - Lord-at-Sea Command enumeration (legal_moves._command_moves, 4.6.1: only
     Sail/Pass at Sea) -> tests/test_legal_moves_at_sea.py.
   - The board-invariant DETECTORS themselves. The whole test strategy asserts
     `board_invariant_violations(state) == []`, but the violation-REPORTING
     branches (calendar_no_box, captured_no_holder, incompatible_position,
     location_not_a_locale, vassal_book_mismatch, influence_marker_oob) were
     never executed -- the safety net was unverified. -> tests/
     test_invariant_detectors.py builds each violation and asserts it is caught.

Per-module line coverage after this round (rules modules): influence 97.7,
ratings 99.1, arts_of_war 98.4, reactions 98.1, pay 95.5, campaign 97.5,
actions 97.7, succession 95.6, scenarios 97.2, events 92.3, commands 95.4,
battle 93.2, legal_moves ~89 (the remainder is the defensive except-bodies).

Remaining low-coverage non-rules modules (cli 71, data_integrity 78, render 89)
are reporting/IO surfaces, lower priority.

Suite 616 -> 624; ruff clean.

## Round (2026-06-22b): ground-truth replay vs the GMT Background Book

The highest-value validation: checking the harness against an AUTHORITATIVE
external source rather than our own reading of the rules. Transcribed the
published "Examples of Play" (Background Book pp. 5-12) -- a complete worked turn
of Scenario Ia "Henry VI" -- into assertions on the deterministic outcomes (the
Arts of War draw and dice are randomised, so those are excluded). Every checked
value MATCHED the book; no discrepancies found. Encoded as
tests/test_ground_truth_background_book.py (9 tests):

- Initial setup: York@Ely, March@Ludlow, Henry VI & Somerset@London,
  Northumberland & Rutland on the Calendar.
- Printed ratings: York Ldr3/Cmd2/Val2, March Ldr2/Cmd2/Inf2/Val3,
  Henry VI Ldr2/Cmd2/Inf5/Val0, Somerset Ldr2/Inf5/Val2.
- Table yields: Ely (City) Levy Troops -> 1 Longbow + 1 Militia; Supply London 3,
  Winchester 2 Provender. Forces: Longbow 2 Missile, Militia 1/2, Men-at-Arms
  Protection 1-3, Retinue 1-4; the book's "12 Missile Hits" (5x2 + 4x0.5) checks.
- Driven actions: York Levy Transport (+2 Carts), Levy Troops at Ely
  (+1 Longbow +1 Militia, Ely Depleted).
- Feed: 8 Troops -> 2 Provender (ceil(troops/6), Retinue excluded).
- Influence-check costs (1 base + Ways + extra; Loyalty modifies rating not cost):
  March Parley (1 Way,+1)=3, Levy Vassal (0 Way,+3,Loy-1)=4, Henry VI Parley
  (1 Way)=2, base check=1 -- all match.
- Capability effects: Thomas Bourchier (Y5) York Command 2->3 at a Friendly City;
  York's Favoured Son (Y20) March +1 Influence +1 Command.

This is the first validation against ground truth external to the codebase. A
VASSAL log or full move-by-move session report would extend it to the dice- and
draw-dependent paths (battle resolution, Arts of War assignment order).

Suite 624 -> 633; ruff clean.

## Round (2026-06-22c): rules traceability matrix

Built RULES_TRACEABILITY.md, generated by scripts/build_traceability.py from the
code/tests/card data (reproducible; re-run after changes). Two code-anchored maps:
all 74 Arts of War cards x both faces (event + capability impl classified, tests
matched by id AND effect keyword), and every Plantagenet rule clause cited in
src/ with its modules and the tests citing the same number.

Limitation recorded in the doc: the repo's Rules PDF is the Seljuk series
rulebook, not Plantagenet, so there is no authoritative Plantagenet clause LIST
in-repo; the matrix is therefore reverse (code -> clause -> test), and a blank
test column in the rule table is a lower bound (behaviour may be tested without
citing the number). The card map's UNTESTED flags ARE reliable (keyword match).

The card map surfaced 5 genuinely untested cards (L8, L22, L29, L37, Y29) -- no
reference by id or effect keyword. Closed with tests/test_untraced_card_effects.py
(6): L22 French Troops (port reinforcement), L29 To Wilful Disobedience (Favour
removal), Y29 Stafford Branch (+1 Exeter Supply), L8 Hay Wains/Forced Marches
recognition, L37 Madame La Grande trigger condition. Matrix now reports 0
untested cards.

Suite 633 -> 639; ruff clean.

## Round (2026-07-01): correction -- the Rules PDF IS Plantagenet; forward traceability added

Correction of the 2026-06-22c round's "repo data issue": the claim that
source/Plantagenet_Rules_Final_web.pdf is the Seljuk series rulebook was WRONG.
Extracting the PDF text (pdftotext, 32 pages) shows it is the Plantagenet Rules
of Play, Levy & Campaign Series Volume IV: "Plantagenet" x77, "Seljuk" x0,
"Lancast-" x100, "York" x153; clause 1.4 is Influence (not Loyalty); sections
run 1.0 INTRODUCTION through 6.0 SCENARIOS with Parley / Levy Lord / Battle
Array / Tides of War / Heirs and Succession subheads. (Flagged by Eric;
verified against the file at HEAD cd91f9e. How the earlier session concluded
otherwise is unknown -- possibly a bad text extraction.)

Consequence: the stated premise that no authoritative Plantagenet clause list
exists in-repo was false, so forward traceability was never blocked. Added in
this round:

- scripts/extract_clause_index.py -- extracts the clause index from the Rules
  PDF (both pdftotext modes unioned; handles the ornament glyph U+F075 that
  precedes some headings and the rulebook's own "3.4.1. Parley" numbering typo;
  warns on numbering holes and conflicting titles). Output committed as
  source/plantagenet_clause_index.tsv: 101 clauses, 1.0-6.3, no holes.
- scripts/build_traceability.py -- now loads the index and reports rulebook
  clauses with no code citation in their chain (self, ancestor, or descendant);
  the false Seljuk note is removed from the docstring and the generated matrix.

Forward-traceability result: 9/101 clauses uncited, all triaged benign:
1.1, 1.2, 1.8 (descriptive component/intro text); 2.1, 2.1.1, 2.1.2 (physical
table setup; scenario selection is implemented under 6.x citations); 1.7.1
Accounting (making change is inherent to integer asset counters); 1.7.2 Greed
for Assets (trivially enforced -- the engine exposes no voluntary asset-discard
move); 1.9.2 Command Cards (implemented, cited as 4.1-4.2). No code changes
warranted.

Scripts and docs only -- no engine or test changes. Suite unchanged at 639;
ruff clean.

## Round (2026-07-01b): niche-branch closure finds two real bugs

Set out to close the niche branches logged in the coverage-triage round
(Regroup recovery, Patrick+Leeward, Norfolk reserve, Succession triggers).
Writing the deterministic setups surfaced two real bugs:

1. RULES BUG -- general Succession skipped in-play Heirs (succession.py).
   `_general_next_heir` looked for the next-ranked Heir with status AVAILABLE
   or no LordState, SKIPPING Heirs already in play, and so instantiated the
   first lower-ranked ABSENT Heir instead. War I: Margaret's removal with
   Somerset (1) Mustered wrongly created Somerset (2) on the Calendar. The
   War I sheet scripts nothing for Margaret's removal -- Somerset (2) enters
   only on Somerset (1)'s own removal ("whether or not highest Heir"). Fixed:
   the Heir role passes to the next-ranked LIVING Heir; if he is already in
   the game (Mustered/Calendar/Exile/Captured) NO new Lord enters; only an
   AVAILABLE or never-instantiated next Heir goes to the next Calendar box;
   REMOVED entries (incl. multi-id entries, March-or-Edward-IV) are skipped as
   dead. tests/test_succession_general_rule.py (7).

2. ROBUSTNESS BUG -- battle dice order depended on PYTHONHASHSEED (battle.py).
   `_TROOP_TYPES` was a set; `_Force.count` insertion order followed set
   iteration, and two dice loops iterate that order: the Regroup troop-recovery
   loop (4.4.2) and the Aftermath Loss rolls (4.4.3, EVERY battle). Same seed,
   same state -> different battle outcomes in different processes. In-process
   forks stayed consistent (why the fuzz oracle and suite never saw it), but
   save/replay across processes -- including the planned VASSAL ground-truth
   replay -- would diverge. Fixed: `_TROOP_TYPES` is an ordered tuple. Verified
   seed-stable across PYTHONHASHSEED=0/1/2 before and after.

Niche branches closed (tests/test_battle_niche_branches.py, 10): Regroup
recovery via fork-oracle (identical Round 1, higher Round-2 strike total with
recovered Troops); Patrick de la Mote doubling Culverins dice with Leeward
halving them exactly (ceil(p/2) on the same dice); Norfolk is Late holding
Norfolk in Reserve Round 1 (incl. popping him from a declared front position)
and firing only once; Swift Maneuver play; Warden of the Marches moving a
Routed Lancastrian to a Friendly North Stronghold instead of the Death roll,
NOT burning L16 when no window opens, and illegal outside the North; Talbot
disband-instead-of-death; Vanguard validation; engagement-order declaration.

Also: the rule-clause table in RULES_TRACEABILITY.md now shows each clause's
rulebook title and flags cited numbers absent from the clause index (catches
annotation typos). First run flagged one: "2.5" -- a ceil(2.5) decimal in a
test comment, not a citation; comment reworded.

Coverage: battle.py 93.2 -> 96.9, succession.py 95.6 -> 97.8.
Suite 639 -> 656; ruff clean; suite verified under multiple hash seeds.

## Round (2026-07-01c): mypy --strict clean (626 -> 0) + CI type gate

The handoff triaged the 626 mypy --strict complaints as cosmetic (missing
annotations, not bugs). Now closed: all 27 source modules type-check clean
under mypy --strict, and CI gained a `typecheck` job so it stays that way.

Edit discipline (annotation-only, zero behavior): parameter/return/variable
annotations; `cast()` (runtime no-op) for the Side/Favour str-enum pattern
(pydantic use_enum_values keeps runtime values plain str -- enum members were
never assigned, which WOULD have changed runtime); `assert x is not None`
only immediately after an existing `_require`/raise guard that already
guarantees it; `.get(key or "", default)` only where key=None already
produced that default. Two `from plantagenet.commands import _adjacency`
sites now import from `plantagenet.actions` (its defining module; same
object) to satisfy strict no-implicit-reexport.

Behavioral-equivalence check, stronger than the suite: full seeded random-
policy games (henry_vi, towton, wars_of_the_roses x 3 seeds) played on the
annotated tree vs a pristine pre-annotation worktree produce byte-identical
final-state JSON under pinned PYTHONHASHSEED (verified at hash seeds 0 and 1).
Plus: 656 tests pass, ruff clean.

OBSERVATION (pre-existing, logged not fixed): full-game TRAJECTORIES from
(scenario, seed) still vary with PYTHONHASHSEED on both trees -- some
hash-ordered iteration still influences move-enumeration order (the random
policy indexes into the legal-moves list). Distinct from the fixed battle
dice-order bug: it does not affect rules correctness or replay of recorded
action sequences, only seed-trajectory reproducibility across processes.
Candidate hunt: set iteration in legal_moves/events enumeration.

Suite unchanged at 656; ruff clean; mypy --strict clean.
