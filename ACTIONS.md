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
| `levy_capability` | — | 3.4.6 | **deferred — Arts of War cards (Phase 4)** |
| `end_muster` | — | 3.4 | done (passes the segment Rebel -> King -> done) |

Influence check (1.4.2): spends 1 base point + `extra_spend` + Way distance
(Parley only), toward the opponent; success on a d6 roll <= the modified
rating, with "1" always succeeding and "6" always failing.

The Levy sequence proceeds Rebel side then King's side (3.1-3.4). Arts of
War draw (3.1) and Pay (3.2; skipped on Turn 1) are Phase 4 / later-turn
concerns; a freshly loaded scenario begins at the Muster step.

### Campaign (Phase 3)

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

### System / flow actions

`pass`, `advance_step`, and similar phase-flow actions are documented as
the sequence of play is implemented.

> **Status:** Phase 0 fixes only the envelope and this catalog skeleton.
> No action is executable yet; the CLI `do` command is a stub.
