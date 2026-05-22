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
                           "kind": "capability", "priority": 20})
    return offers


_TRIGGER_OFFERS = {
    "uses_port_on_sea": [_naval_blockade_offers],
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


_REACTORS = {
    "Y15": _react_naval_blockade,
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
        inter["log"].append(_REACTORS[card](state, inter, offer, action))
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
