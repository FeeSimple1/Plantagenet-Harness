# Action Grammar — Plantagenet Harness

Actions are submitted to `do` as JSON. Every action type has a schema; the
harness rejects malformed actions with a clear error (an `IllegalAction`
carrying a stable `code` and a rule citation). This document is the
authoritative grammar and grows as each phase lands.

## Envelope (all actions)

```json
{
  "type": "<action_type>",
  "side": "lancastrian | yorkist",
  "by_lord": "<lord_id>",
  "...": "action-specific fields"
}
```

- `type` — the action identifier (see the catalog below).
- `side` — the acting side; must match the active player.
- `by_lord` — the acting Lord where the action is Lord-scoped.
- Action-specific fields are documented per action as implemented.

A successful `do` returns a structured result: the mutated state delta,
every die rolled with its context, markers placed/removed, Influence
changes, and (for combat) hits assigned and Routs. Errors return
`{ "error": { "code": "...", "message": "...", "rule": "..." } }`.
Rejected actions leave the game, RNG, pending windows, and history unchanged,
including when using the in-memory Python API.

## Action catalog (by phase)

The catalog is the action requirements summary from the Errata (corrected
table), to be filled in with concrete JSON schemas as each phase
implements them.

### Levy — Arts of War draw (3.1) — IMPLEMENTED in Phase 4-iii

The Levy begins with the Arts of War draw, Rebel then King:

| Action | Args | Rule | Status |
|---|---|---|---|
| `draw` | `side` | 3.1 | done (first Levy deploys 2 Capabilities; later Levies draw 2 Events; immediate Events queue on `pending_events` for resolution) |
| `play_event` | `card`, `side`, `decisions?` | 3.1.3 / 1.9.1 | done (resolve a drawn immediate Event as far as able; returns card to deck; only legal move while `pending_events` set) |

First Levy of a scenario (3.1.2): each side draws two cards and deploys them
as Capabilities at Mustered Lord mats (default first eligible Lord; discard
if unassignable). Later Levies (3.1.3): each side draws two Events — Hold ->
held pile, This Levy / This Campaign -> active, otherwise resolve and return
to the deck. (Event/Capability *effects* are applied by the consumer until
coded in later increments.) After both draws -> Muster (first Turn) or Pay.
Immediate Events must be resolved in draw order: `play_event` accepts only the
first card in `pending_events`, for the active side. Undrawn cards cannot be
played through this action.

### Levy — Muster segment (3.4) — IMPLEMENTED in Phase 2

All Muster actions take `{"type", "side", "by_lord", ...}` and spend one
point of the acting Lord's Lordship (3.4). Optional `"extra_spend": 0|1|3`
adds +0/+1/+2 to the Influence rating for that check (1.4.2).

| Action | Args | Rule | Status |
|---|---|---|---|
| `parley` | `target` (Stronghold; default current), `extra_spend`, `use_parliament_votes?` | 3.4.1 | done |
| `levy_lord` | `target` (Ready Lord id), `extra_spend` | 3.4.2 | done |
| `levy_vassal` | `target` (regular Vassal id), `extra_spend` | 3.4.3 | done |
| `levy_transport` | `transport`: `"cart"` (2 Carts) or `"ship"` (1 Ship) | 3.4.5 | done |
| `levy_troops` | — | 3.4.4 | done (uses the Strongholds table, D-004; pool-limited; Depletes/Exhausts) |
| `levy_capability` | `card` | 3.4.6 | done (attach an unused eligible Capability, <=2/no-dup; effect tracked as data) |
| `end_muster` | — | 3.4 | done (passes the segment Rebel -> King -> done) |

Influence check (1.4.2): spends 1 base point + `extra_spend` + Way distance
(Parley only), toward the opponent; success on a d6 roll <= the modified
rating, with "1" always succeeding and "6" always failing.

The Levy sequence proceeds Rebel side then King's side (3.1-3.4). Arts of
War draw (3.1) and Pay (3.2; skipped on Turn 1) are Phase 4 / later-turn
concerns; a freshly loaded scenario begins at the Muster step.

### Campaign — Phase 3a-i (IMPLEMENTED): framework + Forage

The Campaign turn (4.0): `begin_campaign` (after Levy) -> Plan -> Activation
-> End Campaign. Turn order is Rebel then King throughout (4.2).

| Action | Args | Rule | Status |
|---|---|---|---|
| `begin_campaign` | — | 4.0/4.1 | done (enters Plan; sizes the stack by season) |
| `build_plan` | `side`, `plan`: ordered list of `{"lord": id}` / `{"pass": true}` | 4.1 | done (size = season cards; <=3 per Lord) |
| `forage` | `side`, `by_lord` | 4.6.2 | done (Friendly auto; Neutral 1-4; Enemy/adj 1-3; Depletes) |
| `pass` | `side`, `by_lord` | 4.6.5 | done (consumes one Command action) |
| `end_activation` | `side` | 4.2/4.7 | done (Feed, then reveal the other side's next card) |
| `end_campaign` | — | 4.8 | done (Tides of War, Victory check, Grow, Waste, advance Turn) |

Activation: a revealed Lord takes up to its Command rating in actions; a
Pass card or off-map Lord does nothing (4.2.3). Feed (4.7) runs at each
card's end (a no-op until movement lands in 3a-ii). End Campaign computes
Tides of War (4.8.1: Areas/Dominance, Special-Stronghold Favour,
Most-Favour by type, Gain-Lords-Influence), checks Victory (4.8.3 / 5.x),
runs Grow (4.8.4) and Waste (4.8.5), then advances to the next Turn's Levy.

Phase 3a-ii adds the movement/economy Commands:

| Action | Args | Rule | Status |
|---|---|---|---|
| `march` | `side`, `by_lord`, `to`, optional `group`, `decisions` | 4.3 | done (speeds + Haul + Group; into an Enemy Locale -> Approach 4.3.5) |
| `sail` | `side`, `by_lord`, `to` (Port) | 4.6.1 | done (same/adjacent Sea, free of enemy; Ship per 6 Forces / 2 Prov / 2 Cart; whole card) |
| `tax` | `side`, `by_lord`, `target`, `extra_spend` | 4.6.3 | done (own Seat auto; Vassal Seat / Special via Route + Influence; strongholds Coin; Depletes) |
| `parley` | `side`, `by_lord`, `target`, `extra_spend` | 4.6.4 | done (own location auto; else adjacent / same-Sea Port + Influence) |
| `supply` | `side`, `by_lord`, `source`, optional `use_ships` | 4.5 | done (Stronghold table Provender + Deplete, or Port via Ships; land Route with 1 Cart/Provender/Way; Exile box uses Ship+same-Sea Port) |

Feed (4.7) is now live: a Moved-Fought Lord removes 1 Provender per 6 Troops;
if short it Pillages an Unexhausted Stronghold (3.2.1) and Feeds from the
gain, else Unfed-Disbands (3.2.4). March into an Enemy Locale (Approach
4.3.5) or adjacent to an Enemy by land (Intercept 4.3.4) is rejected with a
`*_phase_3b` code (Battle is Phase 3b).

The Campaign Command menu (4.2.2) is complete: March, Sail, Supply, Forage,
Tax, Parley, Pass.

### Levy Pay (3.2) — Phase 3a-iv (IMPLEMENTED)

On a rolled-over Turn the Levy begins at Pay (skipped on Turn 1, 3.2),
Rebel then King:

| Action | Args | Rule | Status |
|---|---|---|---|
| `pay` | `side`, optional `disband_lords`, `pillage_by`, `unpay_vassals` | 3.2 | done |

`pay` resolves Pay Troops (3.2.1: 1 Coin / 6 Troops, Sharing within a
Locale, Pillage an Unexhausted Stronghold then re-Pay, else Unpaid-Disband
with the −Influence−1/Vassal penalty), Pay Lords (3.2.2: optional voluntary
Disband, then −1 Influence per Lord at a Stronghold and −2 per Lord in an
Exile box), and Pay Vassals (3.2.3: −1 Influence per Mustered Vassal due in
the current Turn box → shift right, else Disband). After King's Pay, Ready
Vassals (3.3.2) returns due Disbanded Vassals to their Seats and play
proceeds to Muster.

Optional `pay_order` lists this side's Lords in the owner's order of payment
when sharing limited Coin; omitted Lords follow in state order. Existing
`unpay_lords` preferences put those Lords last, but cannot withhold available
Coin. Every Lord first spends Coin from his own mat, even if insufficient;
surplus Coin is then Shared. Unpaid Lords Pillage if able and owe their full
payment again, regardless of Coin spent before Pillage (3.2.1).

Phase 3a is COMPLETE (full Levy + Campaign turn cycle). DEFERRED: Muster
Exiles (3.3.1 — needs scenario Exile-box mapping; a no-op without due Exile
cylinders), the Arts-of-War draw (3.1, Phase 4), cross-Lord Cart Sharing for
Supply (1.5.3). Combat (Intercept/Approach/Battle) is Phase 3b; Arts-of-War
card effects are Phase 4.

### Campaign (later phases)

| Action | At Friendly Locale? | Route? | Check Influence? | Deplete/Exhaust? | Special |
|---|---|---|---|---|---|
| `parley` (3.4.1, 4.6.4) | — | — | Yes | — | Adjacent (or by Sea): no Enemy Lord. At target: no check |
| `march` (4.3) | — | — | — | — | From Stronghold or Scotland. Path: entire card |
| `supply` (4.5) | Yes | Yes | — | Yes | Route to Stronghold or Port: 1 Cart / Prov / Way |
| `sail` (4.6.1) | — | — | — | — | Ships from Port, Exile, Sea. Entire card. No Enemy Lord |
| `forage` (4.6.2) | — | — | — | Yes | Enemy or Neutral Locale or Enemy adjacent: roll |
| `tax` (4.6.3) | Yes | Yes | Yes | Yes | Seat or Special Stronghold. Lord's Seat: no check |

(Source: Errata & Clarification, corrected Action Requirements Summary,
Rules of Play p. 32.)

### Combat sub-decisions (Phase 3b)

Approach, Avoid Battle, Withdraw, Battle Array choices, Hit allocation,
Reserve advance, etc. flow through a decision context and are documented
when implemented.

Naval Blockade (Y15) gates Lancastrian Sea actions via the `uses_port_on_sea`
reaction trigger: `sail`, `tax`, `parley` (campaign), and `supply` pause for a
Yorkist Warwick (Y15) at a Port whenever the action uses a Port on his Sea. The
Command-action cost is spent regardless; a block cancels the action before the
Influence check / effect.

In-Battle Held-Event / Capability plays are passed via the `resolve_battle`
`decisions` payload at the Event step (4.4.1): e.g. `leeward`, `caltrops`,
`ravine`, `suspicion`, and `for_trust_not_him` (L7 -- a participating Lord
attempts to Levy a regular Enemy Vassal in the Battle onto its own mat;
`{"by": <lord>, "target": <vassal_id>}`; ignores Routes/Seat Favour, Salisbury's
Vassals immune via Y17).

Within `absorb_plan`, a Vassal Hit can identify its counter explicitly, for
example `{"lord":"warwick_yorkist","unit":"vassal","vassal":"montagu"}`.
Both regular and Special Vassals fight and may absorb Hits. A Routed Special
Vassal Disbands with its associated Capability discarded after the Battle.

A March or Sail move that would resolve a Battle (its `to` holds an Enemy Lord)
is annotated by `legal_moves` with a `battle_reactions` list -- the in-Battle
reaction windows playable in that Battle, from `reactions.available_battle_reactions`
gated by location and capability (e.g. Warden of the Marches only in the North,
Patrick de la Mote only with a Yorkist Culverins and Falconets present). It is
advisory metadata for menu-driven play: `apply_action` ignores the extra key, and
the effects are still submitted via the move's `decisions` payload.

These windows are gated and consumed at their real timing (4.4.3): Warden (L16)
and Talbot (L36) are committed only when the Death-check window actually opens --
for a Routed Lancastrian Lord that will reach a Death roll (not one taking the
Escape Ship, not Henry VI captured), and never under Bloody Thou Art (Y33), which
suppresses Death checks. Patrick de la Mote (Y37) requires a Yorkist Culverins
and Falconets in the Battle.

### Edge-case completeness (Phase 5j)

`muster_exiles` (3.3.1): {`side`, `lords`} — during the Muster window, move the
listed Exile-marked Calendar Lords (current/earlier box) to their designated
Exile box, free; enumerated in `legal_moves`.

`sail` into a Sea (4.6.1): `to` may name a Sea zone (same/adjacent), leaving the
Lord at Sea (`LordState.at_sea`); a later `sail` from at Sea reaches a Port. At
End-Campaign, Lords at Sea Disembark (4.8.2): Shipwreck (die 1-4, permanent
removal + Unpaid penalty + Succession) or Land (5-6, to a chosen Enemy-free Port
via `decisions.disembark_land`, then Feed; else Disband).

Asset Sharing (1.5.3): `sail` and `supply` accept a `share` list of co-located
Friendly Lords whose Ships / Carts are pooled for the capacity requirement
(used, never transferred).

### Bosworth setup and Battle (Scenario IIIb)

Bosworth starts in `phase="battle"`, but the Battle cannot resolve until both
players have selected and distributed four Capability cards and committed their
Arrays. `legal_moves` enumerates individual card assignments and all six possible
Fronts. These setup actions cost no Lordship, Influence, or dice rolls.

`choose_battle_capability`: `{"type":"choose_battle_capability","side":"yorkist",
"by_lord":"richard_iii","card":"Y33"}` selects one card for one Lord. Choose
exactly four per side from that side's no-rose/three-rose deck. Livery eligibility,
card uniqueness, two cards per mat, and no duplicate Capability names per mat are
enforced. Cards are kept in the unrevealed `battle_setup` zone until both sides
commit; Special Vassals and mat effects are applied on simultaneous reveal.

`array_battle`: `{"type":"array_battle","side":"yorkist",
"front":["norfolk","richard_iii","northumberland_2"]}` commits the selected
cards and the three Lords in **Left, Center, Right** order. All three must appear
exactly once, with none in Reserve. Then the other side makes its choices.
The summary shows only the active side's uncommitted selections. The full state
and history remain administrative, omniscient interfaces, like Campaign Plans.

`resolve_battle`: `{"type":"resolve_battle","decisions":{...}}` becomes legal
only after both sides finish setup. It resolves the set-piece Battle and sets
the scenario result (winner wins; all-Rout is a draw). The Rebel side is Attacker
and the King side Defender. Tactical Capability/Valour decisions remain available;
`attacker_positions` and `defender_positions` cannot override the committed Arrays.

### System / flow actions

`renew_war` (6.1.2): `{"type":"renew_war"}` — after a decisive victory in
the first or second War of the grand scenario, set up the next War and retain
the game history. Offered by `legal_moves` only when a next War exists. The CLI
also accepts `plantagenet renew-war game.state.json`. Draws, standalone games,
unfinished Wars, and the final War do not permit renewal.

For We Done Deeds of Charity (Y4), `end_campaign` accepts
`decisions.charity` keyed by Capability holder. An integer spends that Lord's
own Provender. To Share, use `{"pay":2,"share":["march"]}` instead of the
integer: spend the holder's Provender first, then the listed co-located friendly
Lords' Provender in order. The payment is 0, 1, or 2 and grants equal Influence.

### Special Command / Event / Capability actions

These actions are accepted by `apply_action` and are now also surfaced by
`legal_moves` (round-trip discipline), each gated on the same pre-checks its
handler enforces:

`exile_pact` (Y8 Event): {`side`, `by_lord`, `box`} — while the Yorkist EXILE
PACT Event is in effect, the Active Yorkist Lord enters a Friendly Exile box for
free (no Influence cost). Offered on every Friendly Yorkist Exile box the Lord
does not already occupy, whether the Lord stands at a Locale or at Sea; entering
the box clears every other position field (location / at_sea / Calendar / captor)
so the Lord is never recorded in two places, and re-entering the box it already
occupies is rejected as a no-op (`already_in_box`).

`agitators` (Y10 Capability): {`side`, `by_lord`, `target`} — the Active Lord
with Agitators Depletes an adjacent Neutral/Enemy Stronghold, or flips a Depleted
one there to Exhausted. Offered for each adjacent Stronghold not Favouring the
mover that is not already Exhausted.

`merchants` (L30 Capability, Warwick): {`side`, `by_lord`, `targets`,
`extra_spend?`} — one Command action plus a successful Influence check removes up
to two Depletion markers, one per Stronghold, at/adjacent to the Lord. Removing a
marker clears the Stronghold outright: "Removal of Exhausted leaves the
Stronghold neither Exhausted nor Depleted" (L30). The menu offers every maximal
target set (two distinct marked Strongholds when able, else one).

`heralds` (L4 Capability): {`side`, `by_lord`, `target`, `extra_spend?`} — at a
Port, the full Command card buys an Influence check that, on success, advances a
Lord cylinder on the Calendar to the next Turn box. The shifted Lord is the
capability owner's own side ("typically Lancastrian, possibly marked Exile", L4),
so the menu offers each own-side Lord on the Calendar while the Active Lord is at
a Port.

`crown_richard` (My Kingdom for a Horse, King Richard 6.2): {`side`} — the
Yorkist player replaces a Gloucester Lord Mustered at London with Richard III in
place (the new Lord inherits Gloucester's board position, Capabilities, and
Vassals; Gloucester leaves play). Offered to the Yorkist player during its Muster
and during Campaign activation whenever Gloucester is Mustered at London.

### Own-timing Held Events (1.9.1, play_held_event)

`play_held_event` plays a Held Event in one of its own-timing windows. All six
coded cards are now advertised by `legal_moves` for the active side, each
emitted fully-formed (decisions filled) so it is directly playable, and each
mirroring its handler pre-check:

`Y13` / `L13` Aspielles — inspect the Enemy's Held cards. Any moment; offered
whenever held. `{card, side}`.

`Y20` Yorkist Parade — `{card, side}`. Offered whenever London Favours the
Yorkists with York or Warwick there.

`Y24` Sun in Splendour — `{card, side, decisions:{target}}`. Offered during the
Levy while Edward IV is on the Calendar/Exile; one move per Friendly Enemy-free
Stronghold or Yorkist Exile box.

`L28` Rebel Supply Depot — `{card, side, decisions:{lords, provender?}}`. Movement-triggered:
offered only while the Hold-event timing window opened by a qualifying March or
Sail to a Port is open; the named Lord(s) must be unique movers. Grants four
Provender **total**, distributed using `provender:{lord_id:amount,...}` with
nonnegative integer amounts summing to four. For one Lord the distribution may
be omitted; for a Group it is required. The move palette offers every allocation.
Selected movers ignore their next Feed. The result's `provender_added` mapping
records the allocation.

`L33` Surprise Landing — `{card, side}`. Offered only while the window records a
Sail (not a March) to a Port.

The Hold-event timing window (`state.hold_window`) is opened by a completed
March or Sail when mover(s) end at a Port and is cleared by the next accepted
non-Held action; the L28/L33 handlers validate it independently, so the engine no longer
grants those plays without a preceding qualifying Move.

### Manual-adjudication actions (not enumerated)

`concede` (6.1.1 Surrender): {`side`} — in the grand scenario's first or second
War, a side with an Heir still present may concede that War as the loser, so the
consumer proceeds to Renewed War. `apply_action` validates the grand-scenario,
War-order, and surviving-Heir conditions, but the Surrender's timing window —
"just before the last Heir's Death roll" (6.1.1) — is **not** modeled in state.
For that reason `concede` is intentionally **omitted from `legal_moves`** and is
treated as a manual-adjudication action: the consumer chooses when to submit it
as a raw action at the correct moment. Enumerating it on every step of the first
two Wars (the only condition the engine can check) would misrepresent its legal
window; modeling that window in state is the prerequisite for enumerating it.

> **Status:** Phase 0 fixes only the envelope and this catalog skeleton.
> No action is executable yet; the CLI `do` command is a stub.

### Parliament Votes and automatic Influence checks

For Levy Parley with L18 active, `use_parliament_votes` is a JSON boolean,
defaulting to `true`. Set it to `false` to roll normally and reserve that Lord's
once-per-Levy benefit for a later target. Both choices appear in `legal_moves`
while the benefit is available. Taking the benefit reduces Influence cost by one
and succeeds without a die roll; it does not waive the remaining route cost.

Rules-granted automatic checks (L18, Y18, Y4, L32, L37) return `roll: null` and
do not advance the RNG. Normal Influence and Lordship costs still apply unless
the granting effect explicitly waives them. Players cannot request automatic
success independently of a rules-granted effect. Held Events are not unused
Capabilities: `levy_capability` rejects them until a permitted play/discard
returns them to the unused deck.
