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
