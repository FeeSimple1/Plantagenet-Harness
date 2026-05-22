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

## Q-005 — Scripted Succession card swaps and remaining play-timing Events

**Context.** Two clusters of effects remain consumer-adjudicated because they
require either structured encoding of currently-prose data or the reaction
framework of Q-004:

**(a) Per-War scripted Succession (6.2-6.3).** The general mechanic is coded
(`succession.on_heir_removed`: a Heir removed by Death/Shipwreck brings the
next-ranked Heir to the next Calendar box, creating its LordState if absent).
But each War's *scripted* steps live as verbatim prose in
`wars_of_the_roses.json` (e.g. War I: "remove Arts of War L15 and L17, add L27
and L31; Muster of Margaret assigns L26 EDWARD as a free mandatory Capability";
Renewed-War setup transitions). These need structured encoding (an ADD /
REPLACE / TO-CALENDAR / SEATS / ARTS-OF-WAR trigger schema per War) before they
can be auto-applied.

**(b) Reaction / play-timing Events not yet automated:** The King's Name (Y32,
cancel a Lancastrian Levy — reactive, see Q-004), For Trust Not Him (L7, capture
an Enemy Vassal mid-Battle), Rebel Supply Depot (L28) and Surprise Landing (L33,
post-Sail bonuses), Exile Pact (Y8, voluntary move to a Friendly Exile box),
Parliament's Truce (Y12/L20, prohibit Approach/Intercept — needs a "play held
event" campaign-flag action), Sun in Splendour (Y24) / Yorkist Parade (Y20,
play a Held Event during Levy), Be Sent For (L4, Muster Exiles from anywhere),
Aspielles (Y13/L13, inspect hidden information — no board state change).

**Recommendation.** Encode the per-War Succession triggers as structured data
(a follow-up data task), and add a `play_held_event` action + the Q-004 reaction
hook to cover the play-timing/reactive Events. All other card effects (the large
majority) are automated and tested.

---

_Other than Q-004 and Q-005, no open questions._

(Resolved: Q-001 Sea adjacency -> D-001; Q-002 Leicester edges -> D-002;
Q-003 Strongholds table -> D-004. See `RULES_DECISIONS.md`.)
