"""Reaction protocol (Q-004): a typed trigger registry + a serializable
pause/resolve loop for opponent reactions that fire mid-action.

Flow:
  * A handler commits the action's cost (Lordship/Command -- spent regardless),
    then calls ``gate(state, trigger, ctx, resume_key, finish_data)`` at the
    reaction checkpoint.
  * ``gate`` finds eligible reactors (ordered by published priority). If none,
    it immediately runs the resume function and returns the final result. If
    some, it records a pending interaction on ``state.pending`` and returns a
    ``pending_reactions`` result; the acting side waits.
  * The consumer answers each offer with a ``react`` action ({"play": card} or
    {"pass": true}). When the last offer resolves -- or a reaction cancels the
    action -- the engine runs the resume function (with ``cancelled``) and
    clears ``state.pending``.

All interaction state lives in ``state.pending`` (JSON-serializable): offers,
index, the resume_key string, finish_data, and a per-offer log. No opaque
tokens, so a paused game round-trips through save/load.
"""

from __future__ import annotations

import importlib
from typing import Any

from plantagenet import static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus

_MUSTERED = LordStatus.MUSTERED


def _require(cond, code, msg):
    if not cond:
        raise IllegalAction(code, msg)


def _has_cap(state, lord_id, title):
    cards = static_data.load_cards()
    return any(cards[c]["capability"]["title"] == title
               for c in state.lords[lord_id].capabilities)


def _held(state, side, title):
    cards = static_data.load_cards()
    for cid in state.decks.get(side, {}).get("held", []):
        if cards[cid]["event"]["title"] == title:
            return cid
    return None


def _port_sea():
    seas = static_data.load_seas()
    return {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}


# --------------------------------------------------------------- offer finders
def _naval_blockade_offers(state, ctx):
    """Naval Blockade (Y15 Capability, Warwick at a Port): cancels Lancastrian
    actions using Ports on that Sea unless a roll of 1-2 (per-action, persistent)."""
    if ctx.get("side") != "lancastrian":
        return []
    locs = static_data.load_locales()
    psea = _port_sea()
    offers = []
    for lid, ls in state.lords.items():
        if ls.side == "yorkist" and ls.status == _MUSTERED \
                and _has_cap(state, lid, "NAVAL BLOCKADE") \
                and locs.get(ls.location, {}).get("port") \
                and psea.get(ls.location) in set(ctx.get("seas", [])):
            offers.append({"side": "yorkist", "card": "Y15", "lord": lid,
                           "kind": "capability", "priority": 20, "effect": "naval_blockade"})
    return offers


def _other(side):
    return "lancastrian" if side == "yorkist" else "yorkist"


def _on_approach_offers(state, ctx):
    """Reactions to an Approach (4.3.5): King's Parley (L15, Henry VI) and
    Parliament's Truce cancel it; Blocked Ford forces Battle (no Exile).
    Priority is canonical: King's Parley forecloses Blocked Ford (errata)."""
    offers = []
    appside = ctx["approaching_side"]
    if appside == "yorkist" and "henry_vi" in ctx.get("target_lords", []) \
            and _has_cap(state, "henry_vi", "KING'S PARLEY"):
        offers.append({"side": "lancastrian", "card": "L15", "lord": "henry_vi",
                       "kind": "capability", "priority": 10, "effect": "kings_parley"})
    for side in ("lancastrian", "yorkist"):
        cid = _held(state, side, "PARLIAMENT'S TRUCE")
        if cid:
            offers.append({"side": side, "card": cid, "kind": "held",
                           "priority": 20, "effect": "parliaments_truce"})
    for side in ("lancastrian", "yorkist"):
        cid = _held(state, side, "BLOCKED FORD")
        if cid:
            offers.append({"side": side, "card": cid, "kind": "held",
                           "priority": 30, "effect": "blocked_ford"})
    return offers


def _kings_name_offers(state, ctx):
    """The King's Name (Y32 Event): after a successful Lancastrian Levy action,
    Gloucester (not Richard III) may pay 1 Influence to cancel it."""
    cards = static_data.load_cards()
    active = any(e["card"] == "Y32" and e["side"] == "yorkist"
                 and cards[e["card"]]["event"]["title"] == "THE KING'S NAME"
                 for e in state.active_events)
    if not active or ctx.get("actor_side") != "lancastrian":
        return []
    glo = [lid for lid in ("gloucester_1", "gloucester_2")
           if lid in state.lords and state.lords[lid].status == _MUSTERED]
    if not glo:
        return []
    return [{"side": "yorkist", "card": "Y32", "lord": glo[0],
             "kind": "event", "priority": 10, "effect": "kings_name"}]


_TRIGGER_OFFERS = {
    "uses_port_on_sea": [_naval_blockade_offers],
    "on_approach": [_on_approach_offers],
    "after_successful_levy_action": [_kings_name_offers],
}


def _offers(state, trigger, ctx):
    out = []
    for finder in _TRIGGER_OFFERS.get(trigger, []):
        out.extend(finder(state, ctx))
    out.sort(key=lambda o: o.get("priority", 50))   # published priority order
    return out


# --------------------------------------------------------------- reactions
def _react_naval_blockade(state, inter, offer, action):
    roller = state.dice()
    roll = roller.d6()
    state.store_dice(roller)
    blocked = roll > 2                       # 1-2 lets the action proceed; 3-6 cancels
    if blocked:
        inter["cancelled"] = True
    return {"card": "Y15", "lord": offer["lord"], "roll": roll, "blocked": blocked}


def _discard_held(state, side, cid):
    held = state.decks.get(side, {}).get("held", [])
    if cid in held:
        held.remove(cid)
    state.decks.setdefault(side, {}).setdefault("discard", []).append(cid)


def _react_kings_parley(state, inter, offer, action):   # L15 (cap, discarded)
    hv = state.lords["henry_vi"]
    if offer["card"] in hv.capabilities:
        hv.capabilities.remove(offer["card"])
    state.decks.setdefault("lancastrian", {}).setdefault("discard", []).append(offer["card"])
    inter["cancelled"] = True
    inter["finish_data"]["cancel_reason"] = "kings_parley"
    return {"card": offer["card"], "effect": "kings_parley", "cancels_approach": True}


def _react_parliaments_truce(state, inter, offer, action):   # Y12/L20 (held)
    _discard_held(state, offer["side"], offer["card"])
    state.active_events.append({"card": offer["card"], "side": offer["side"],
                                "scope": "this_campaign"})       # prohibits further A/I
    inter["cancelled"] = True
    inter["finish_data"]["cancel_reason"] = "parliaments_truce"
    return {"card": offer["card"], "effect": "parliaments_truce", "cancels_approach": True}


def _react_blocked_ford(state, inter, offer, action):   # Y11/L11 (held) -- forces Battle
    # Signal only; the (tested) approach path consumes the Held Event and applies
    # the no-Exile effect. 5a-iii unifies this consumption into the registry.
    inter["finish_data"].setdefault("blocked_ford", []).append(offer["side"])
    return {"card": offer["card"], "effect": "blocked_ford", "forces_battle": True}


def _react_kings_name(state, inter, offer, action):     # Y32 (Event stays active)
    from plantagenet import influence
    influence.spend_influence(state, "yorkist", 1)       # Yorkist pays 1 Influence
    inter["cancelled"] = True
    return {"card": "Y32", "lord": offer["lord"], "effect": "kings_name",
            "cancels_levy": True}


_EFFECT_REACTORS = {
    "naval_blockade": _react_naval_blockade,
    "kings_parley": _react_kings_parley,
    "parliaments_truce": _react_parliaments_truce,
    "blocked_ford": _react_blocked_ford,
    "kings_name": _react_kings_name,
}


# --------------------------------------------------------------- resume plumbing
def _resolve_resume(resume_key):
    mod_name, fn_name = resume_key.split(":")
    mod = importlib.import_module(f"plantagenet.{mod_name}")
    return getattr(mod, fn_name)


def gate(state: GameState, trigger: str, ctx: dict[str, Any],
         resume_key: str, finish_data: dict[str, Any]) -> dict[str, Any]:
    """Reaction checkpoint. Returns the final result (no reactors) or a
    ``pending_reactions`` result (reactors present; the action pauses)."""
    offers = _offers(state, trigger, ctx)
    if not offers:
        return _resolve_resume(resume_key)(state, finish_data, cancelled=False)
    state.pending = [{
        "kind": "reaction", "trigger": trigger, "ctx": ctx,
        "offers": offers, "idx": 0, "resume_key": resume_key,
        "finish_data": finish_data, "cancelled": False, "log": [],
    }]
    return {"type": "pending_reactions", "trigger": trigger,
            "awaiting": offers[0], "remaining": len(offers)}


def resolve(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Handle a ``react`` action against the current pending interaction."""
    _require(state.pending, "no_pending", "there is no pending reaction to resolve")
    inter = state.pending[0]
    offer = inter["offers"][inter["idx"]]
    if action.get("pass"):
        inter["log"].append({"card": offer["card"], "lord": offer["lord"], "passed": True})
    else:
        card = action.get("play")
        _require(card == offer["card"], "wrong_reaction",
                 f"the awaiting reaction is {offer['card']} by {offer['side']}")
        inter["log"].append(_EFFECT_REACTORS[offer["effect"]](state, inter, offer, action))
    inter["idx"] += 1

    if inter["cancelled"] or inter["idx"] >= len(inter["offers"]):
        resume = _resolve_resume(inter["resume_key"])
        log = inter["log"]
        cancelled = inter["cancelled"]
        finish_data = inter["finish_data"]
        state.pending = []
        final = resume(state, finish_data, cancelled=cancelled)
        final["reactions"] = log
        return final
    return {"type": "pending_reactions", "trigger": inter["trigger"],
            "awaiting": inter["offers"][inter["idx"]], "resolved": inter["log"]}
