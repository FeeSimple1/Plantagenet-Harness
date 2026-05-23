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

## Action catalog (by phase)

The catalog is the action requirements summary from the Errata (corrected
table), to be filled in with concrete JSON schemas as each phase
implements them.

### Levy — Arts of War draw (3.1) — IMPLEMENTED in Phase 4-iii

The Levy begins with the Arts of War draw, Rebel then King:

| Action | Args | Rule | Status |
|---|---|---|---|
| `draw` | `side` | 3.1 | done (first Levy deploys 2 Capabilities; later Levies draw 2 Events) |

First Levy of a scenario (3.1.2): each side draws two cards and deploys them
as Capabilities at Mustered Lord mats (default first eligible Lord; discard
if unassignable). Later Levies (3.1.3): each side draws two Events — Hold ->
held pile, This Levy / This Campaign -> active, otherwise resolve and return
to the deck. (Event/Capability *effects* are applied by the consumer until
coded in later increments.) After both draws -> Muster (first Turn) or Pay.

### Levy — Muster segment (3.4) — IMPLEMENTED in Phase 2

All Muster actions take `{"type", "side", "by_lord", ...}` and spend one
point of the acting Lord's Lordship (3.4). Optional `"extra_spend": 0|1|3`
adds +0/+1/+2 to the Influence rating for that check (1.4.2).

| Action | Args | Rule | Status |
|---|---|---|---|
| `parley` | `target` (Stronghold; default current), `extra_spend` | 3.4.1 | done |
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

### System / flow actions

`pass`, `advance_step`, and similar phase-flow actions are documented as
the sequence of play is implemented.

> **Status:** Phase 0 fixes only the envelope and this catalog skeleton.
> No action is executable yet; the CLI `do` command is a stub.
