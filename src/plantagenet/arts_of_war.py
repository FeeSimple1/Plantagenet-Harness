"""Arts of War draw (3.1) — the first Levy step, Rebel then King.

First Levy of a scenario (3.1.2): each side draws two cards and deploys them
as Capabilities at Mustered Lord mats (discarding any it cannot assign).
Second and later Levies (3.1.3): each side draws two cards and implements
their Events — Hold Events go to the held pile, This Levy / This Campaign
Events become active for the phase, and other Events resolve and return to
the deck.

Card EFFECTS are tracked as data (the consumer applies them) until coded in
a later Phase-4 increment; this module wires the draw, deck, and Event-type
lifecycle. Capability deployment defaults to the first eligible Mustered
Lord.
"""

from __future__ import annotations

from typing import Any

from plantagenet import static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus

SIDES = ("lancastrian", "yorkist")


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _first_eligible_lord(state: GameState, side: str, card_id: str):
    from plantagenet.actions import _capabilities_in_play, _capability_eligible
    cards = static_data.load_cards()
    title = cards[card_id]["capability"]["title"]
    in_play = _capabilities_in_play(state, side)
    if card_id in in_play:
        return None
    for v in state.lords.values():
        if (v.side == side and v.status == LordStatus.MUSTERED and len(v.capabilities) < 2
                and _capability_eligible(card_id, v.lord_id)
                and all(cards[c]["capability"]["title"] != title for c in v.capabilities)):
            return v
    return None


def draw(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = action.get("side")
    _require(side in SIDES, "bad_side", "side must be a valid side")
    _require(state.phase == "levy" and state.levy_step == "arts_of_war", "wrong_step",
             "the Arts of War draw runs in the Levy's first step (3.1)")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's draw (Rebel then King, 3.1)")

    first_levy = state.turn_box == (state.calendar.first_box or state.turn_box)
    deck = state.decks.setdefault(side, {"draw": [], "discard": [], "held": []})
    cards = static_data.load_cards()
    drawn = [deck["draw"].pop(0) for _ in range(min(2, len(deck["draw"])))]
    result: dict[str, Any] = {"type": "draw", "side": side, "first_levy": first_levy,
                              "drawn": drawn, "deployed": [], "held": [], "active": [],
                              "resolved": [], "discarded": []}

    if first_levy:                                   # 3.1.2 Draw Capabilities
        for cid in drawn:
            lord = _first_eligible_lord(state, side, cid)
            if lord is not None:
                lord.capabilities.append(cid)
                result["deployed"].append({"card": cid, "lord": lord.lord_id})
            else:                                    # cannot assign -> discard (3.1.2)
                deck["discard"].append(cid)
                result["discarded"].append(cid)
    else:                                            # 3.1.3 Draw Events
        for cid in drawn:
            etype = cards[cid]["event"]["type"]
            if etype == "hold":
                deck["held"].append(cid)
                result["held"].append(cid)
            elif etype in ("this_levy", "this_campaign"):
                state.active_events.append({"card": cid, "side": side, "scope": etype})
                result["active"].append(cid)
            else:                                    # immediate: resolve, return to deck
                deck["draw"].append(cid)             # (Event effect applied by the consumer)
                result["resolved"].append(cid)

    rebel = [s for s, r in state.roles.items() if r == "rebel"][0]
    king = [s for s, r in state.roles.items() if r == "king"][0]
    if side == rebel:
        state.active_side = king
        result["next"] = "king_draw"
    else:
        state.levy_step = "muster" if first_levy else "pay"
        state.active_side = rebel
        result["next"] = state.levy_step
    return result
