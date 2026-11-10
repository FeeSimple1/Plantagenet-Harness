"""Shared test helpers for advancing the Levy flow past the Arts of War draw."""

from __future__ import annotations

from plantagenet import actions, events, legal_moves


def fill_event_decisions(state, card, side):
    """Minimal legal ``decisions`` for a drawn immediate Event (test scaffolding,
    standing in for a consumer's choices). Most Events default to empty (they are
    deterministic, or the choice is optional and declining is legal). Mandatory
    selection Events need a default choice, sized to availability."""
    if card == "Y22":
        from plantagenet.events import loyalty_and_trust_targets
        targets = loyalty_and_trust_targets(state, side)
        return {"target": targets[0]} if targets else {}
    if card in ("L23", "L24"):                  # Warwick's Propaganda: min(3, available)
        if side == "yorkist":
            return {"stronghold": events.propaganda_next_stronghold(state.pending_events[0]),
                    "choice": "remove"}
        return {"strongholds": events.propaganda_strongholds(state)[:3]}
    if card == "L27":                           # L'Universelle Aragne: min(2, available)
        if side == "yorkist":
            target = events.aragne_next_check(state.pending_events[0])
            return {"vassal": target["vassal"], "extra_spend": 0}
        return {"vassals": list(events.aragne_vassal_owners(state))[:2]}
    if card == "L29":
        return {"strongholds": events.wilful_disobedience_targets(state)[:2]}
    return {}


def resolve_pending_events(state):
    """Resolve every immediate Event queued by an Arts of War draw (3.1.3),
    supplying minimal legal decisions."""
    while state.pending_events:
        move = legal_moves.legal_moves(state)[0]
        if "decisions" not in move:
            move["decisions"] = fill_event_decisions(state, move["card"], move["side"])
        actions.apply_action(state, move)
    return state


def to_muster(state):
    """Advance through the Arts of War draw (3.1, Rebel then King), resolving any
    drawn immediate Events, to Muster."""
    while state.phase == "levy" and state.levy_step == "arts_of_war":
        if state.pending_events:
            resolve_pending_events(state)
        else:
            actions.apply_action(state, {"type": "draw", "side": state.active_side})
    return state


def apply_drawn_event(state, action):
    queue_drawn_event(state, action["card"])
    return actions.apply_action(state, action)


def queue_drawn_event(state, card):
    """Place an immediate Event in a legal later-Levy draw window for effect tests.

    The fixture deliberately chooses the drawn card; production callers must
    obtain pending Events through draw (3.1.3).
    """
    from plantagenet import static_data
    side = static_data.load_cards()[card]["side"]
    state.phase = "levy"
    state.levy_step = "arts_of_war"
    state.turn_box = (state.calendar.first_box or state.turn_box) + 1
    state.active_side = side
    for pile in state.decks[side].values():
        while card in pile:
            pile.remove(card)
    state.pending_events = [{"card": card, "side": side}]
