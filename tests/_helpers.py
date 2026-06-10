"""Shared test helpers for advancing the Levy flow past the Arts of War draw."""

from __future__ import annotations

from plantagenet import actions
from plantagenet.state import LordStatus, VassalStatus


def fill_event_decisions(state, card, side):
    """Minimal legal ``decisions`` for a drawn immediate Event (test scaffolding,
    standing in for a consumer's choices). Most Events default to empty (they are
    deterministic, or the choice is optional and declining is legal); only the two
    mandatory-selection Events need a default selection, sized to availability."""
    if card in ("L23", "L24"):                  # Warwick's Propaganda: min(3, available)
        ys = [loc for loc, ls in state.locales.items() if ls.favour == "yorkist"]
        return {"strongholds": {loc: "remove" for loc in ys[:min(3, len(ys))]}}
    if card == "L27":                           # L'Universelle Aragne: min(2, available)
        av = [vid for vid, v in state.vassals.items()
              if v.status == VassalStatus.MUSTERED and v.on_lord is not None
              and state.lords.get(v.on_lord) is not None
              and state.lords[v.on_lord].side == "yorkist"]
        for ld in state.lords.values():         # Special Vassals count too (handler parity)
            if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED:
                av.extend(ld.special_vassals)
        return {"vassals": av[:min(2, len(av))]}
    return {}


def resolve_pending_events(state):
    """Resolve every immediate Event queued by an Arts of War draw (3.1.3),
    supplying minimal legal decisions."""
    while state.pending_events:
        pe = state.pending_events[0]
        actions.apply_action(state, {
            "type": "play_event", "side": pe["side"], "card": pe["card"],
            "decisions": fill_event_decisions(state, pe["card"], pe["side"])})
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
