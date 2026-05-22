# Rules Questions — Plantagenet Harness

Open questions awaiting user adjudication. Each must contain all required
fields (see BRIEF.md "Question Format"). When answered, MOVE the entry to
`RULES_DECISIONS.md`.

---

## Q-004 — Reactive "interrupt" Capabilities (Naval Blockade Y15, King's Parley L15)

**Context.** Two Capabilities trigger *during the opponent's action*, as
reactions:
- **Naval Blockade (Y15, Warwick):** "This Lord at a Port cancels Lancastrian
  actions using Ports on that Sea unless a roll of 1-2."
- **King's Parley (L15, Henry VI):** "Upon Yorkist Approach to this Lord,
  discard this card to cancel that Approach and end Command card."

**Issue.** The harness applies actions atomically via `apply_action`; it has no
"reaction window" framework in which the *non-active* side may interject a
discard/roll mid-resolution. Every other implemented card is either a
persistent modifier, an active This-Levy/Campaign Event, or a play bundled into
the acting side's own `decisions` payload. Modeling these two faithfully needs a
small reaction protocol (pause the opponent's Sail/Tax/Supply or Approach, offer
the holder the option, resolve the roll/cancel).

**Options.**
(a) Add a generic reaction hook: when an action "uses a Port on a Sea" or is an
    "Approach to lord X", `apply_action` checks for an eligible reactor and
    surfaces a pending decision the consumer answers.
(b) Model them purely as `decisions` flags the *acting* side passes (consumer
    declares the reaction up-front) — simpler but leaks the reaction to the
    wrong side.
(c) Leave as consumer-adjudicated for now (the harness flags the card is in
    play; the LLM/human applies the cancel manually).

**Recommendation.** (a), but it is a structural addition; deferring until the
rest of Phase 4 is complete. Implemented everything else in Wave D.

---

_Other than Q-004, no open questions._

(Resolved: Q-001 Sea adjacency -> D-001; Q-002 Leicester edges -> D-002;
Q-003 Strongholds table -> D-004. See `RULES_DECISIONS.md`.)
