"""Arts of War draw (3.1) — the first Levy step, Rebel then King.

First Levy of a scenario (3.1.2): each side draws two cards and deploys them
as Capabilities at Mustered Lord mats (discarding any it cannot assign).
Second and later Levies (3.1.3): each side draws two cards and implements
their Events — Hold Events go to the held pile, This Levy / This Campaign
Events become active for the phase (after target selection where needed),
and other Events resolve and return to the deck.

This module wires the draw, deck, and Event-type lifecycle; card effects
themselves are applied by the rules-engine modules (events / ratings /
battle / reactions). The first Levy exposes every maximum-card Capability
allocation so the owning player, not state iteration order, chooses the mats.
"""

from __future__ import annotations

from typing import Any, cast

from plantagenet import static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus, Side

SIDES = ("lancastrian", "yorkist")


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _shuffle_unused(state: GameState, side: str) -> None:
    """Collect and shuffle every unused card before a later-Levy draw (3.1.1).

    Cards physically in ``draw`` or ``discard`` are unused. Held Events,
    Capabilities on Lord mats, active/pending Events, and ``set_aside`` cards
    live outside those piles and therefore stay out of the Event deck. The
    first Levy's shuffle is performed during scenario/War setup; every later
    Levy rebuilds the deck here immediately before that side draws.
    """
    deck = state.decks.setdefault(side, {"draw": [], "discard": [], "held": []})
    pool = [*deck.get("draw", []), *deck.get("discard", [])]
    roller = state.dice()
    roller.shuffle(pool)
    state.store_dice(roller)
    deck["draw"] = pool
    deck["discard"] = []


def capability_assignment_options(
        state: GameState, side: str, drawn: list[str]) -> list[dict[str, str | None]]:
    """All legal first-Levy allocations that deploy as many drawn cards as possible.

    Rule 3.1.2 says to deploy both drawn cards and discard only a card the side
    *cannot* assign. The two choices therefore have to be evaluated jointly: a
    greedy first placement may fill the only eligible mat for the second card
    even though another complete allocation would preserve both. Returned
    mappings contain every drawn card; ``None`` means the card truly must be
    discarded under a maximum-card allocation.
    """
    from plantagenet.actions import _capabilities_in_play, _capability_eligible

    cards = static_data.load_cards()
    in_play = _capabilities_in_play(state, side)
    lords = [v for v in state.lords.values()
             if v.side == side and v.status == LordStatus.MUSTERED]
    assigned: dict[str, list[str]] = {v.lord_id: list(v.capabilities) for v in lords}
    all_options: list[dict[str, str | None]] = []

    def eligible(cid: str, lid: str) -> bool:
        held = assigned[lid]
        title = cards[cid]["capability"]["title"]
        return (cid not in in_play and len(held) < 2
                and _capability_eligible(cid, lid)
                and all(cards[c]["capability"]["title"] != title for c in held))

    def walk(index: int, choice: dict[str, str | None]) -> None:
        if index == len(drawn):
            all_options.append(dict(choice))
            return
        cid = drawn[index]
        for lord in lords:
            lid = lord.lord_id
            if not eligible(cid, lid):
                continue
            assigned[lid].append(cid)
            choice[cid] = lid
            walk(index + 1, choice)
            assigned[lid].pop()
        choice[cid] = None
        walk(index + 1, choice)
        choice.pop(cid, None)

    walk(0, {})
    if not all_options:
        return [{cid: None for cid in drawn}]
    most = max(sum(lid is not None for lid in option.values()) for option in all_options)
    # Recursion follows stable Lord/card order, so this order is deterministic
    # and the first entry remains a safe legacy default for callers that omit
    # the newly exposed player choice.
    return [option for option in all_options
            if sum(lid is not None for lid in option.values()) == most]


def _normalise_assignments(raw: Any, drawn: list[str]) -> dict[str, str | None] | None:
    if raw is None:
        return None
    _require(isinstance(raw, dict), "bad_capability_assignments",
             "assignments must map every drawn card to a Lord id or null (3.1.2)")
    assert isinstance(raw, dict)
    _require(set(raw) == set(drawn), "bad_capability_assignments",
             "assignments must name every and only the two drawn cards (3.1.2)")
    out: dict[str, str | None] = {}
    for cid in drawn:
        lid = raw[cid]
        _require(lid is None or isinstance(lid, str), "bad_capability_assignments",
                 "each drawn card must map to a Lord id or null (3.1.2)")
        out[cid] = lid
    return out


def draw(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = cast(str, action.get("side"))
    _require(side in SIDES, "bad_side", "side must be a valid side")
    _require(state.phase == "levy" and state.levy_step == "arts_of_war", "wrong_step",
             "the Arts of War draw runs in the Levy's first step (3.1)")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's draw (Rebel then King, 3.1)")

    first_levy = state.turn_box == (state.calendar.first_box or state.turn_box)
    deck = state.decks.setdefault(side, {"draw": [], "discard": [], "held": []})
    cards = static_data.load_cards()
    if not first_levy:
        _shuffle_unused(state, side)
    drawn = [deck["draw"].pop(0) for _ in range(min(2, len(deck["draw"])))]
    result: dict[str, Any] = {"type": "draw", "side": side, "first_levy": first_levy,
                              "drawn": drawn, "deployed": [], "held": [], "active": [],
                              "pending": [], "resolved": [], "discarded": []}

    if first_levy:                                   # 3.1.2 Draw Capabilities
        options = capability_assignment_options(state, side, drawn)
        chosen = _normalise_assignments(action.get("assignments"), drawn)
        if chosen is None:
            chosen = options[0]                      # legacy/default delegation
        _require(chosen in options, "illegal_capability_assignment",
                 "the Capability allocation is ineligible or discards an assignable card (3.1.2)")
        from plantagenet.actions import _muster_special_vassal
        for cid in drawn:                            # resolve in draw order
            lid = chosen[cid]
            if lid is None:
                deck["discard"].append(cid)
                result["discarded"].append(cid)
                continue
            lord = state.lords[lid]
            lord.capabilities.append(cid)
            # 3.1.2 deploys the Capability with all its effects (1.5.4).
            _muster_special_vassal(state, lord, cid)
            result["deployed"].append({"card": cid, "lord": lid})
    else:                                            # 3.1.3 Draw Events
        for cid in drawn:
            etype = cards[cid]["event"]["type"]
            if etype == "hold":
                deck["held"].append(cid)
                result["held"].append(cid)
            elif cid == "Y22":                      # Loyalty and Trust needs a chosen Lord
                state.pending_events.append({"card": cid, "side": side})
                result["pending"].append(cid)
            elif etype in ("this_levy", "this_campaign"):
                state.active_events.append({"card": cid, "side": side, "scope": etype})
                result["active"].append(cid)
                # Gloucester (IIY/IIL special rule): playing Y28 GLOUCESTER AS HEIR
                # sets it aside for reference in the next War's setup (6.2.2).
                if state.grand_scenario and \
                        cards[cid]["event"]["title"] == "GLOUCESTER AS HEIR":
                    state.grand_scenario["gloucester_as_heir_played"] = True
            else:                                    # immediate (3.1.3): queue for resolution
                # The effect is resolved by a subsequent play_event action (the
                # consumer supplies any decisions); the card returns to the deck
                # then. The Levy does not advance until pending_events is empty.
                state.pending_events.append({"card": cid, "side": side})
                result["pending"].append(cid)

    if state.pending_events:                          # drawn Events await resolution/selection
        result["next"] = "resolve_events"
        return result
    result["next"] = advance_after_draw(state, side, first_levy)
    return result


def advance_after_draw(state: GameState, side: str, first_levy: bool) -> str:
    """Advance the Arts of War sequence once `side` has finished its draw and
    resolved any immediate Events: Rebel -> King draw, then -> muster (first
    Levy) or pay (later Levy). Returns the "next" label."""
    rebel = [s for s, r in state.roles.items() if r == "rebel"][0]
    king = [s for s, r in state.roles.items() if r == "king"][0]
    if side == rebel:
        state.active_side = cast(Side, king)
        return "king_draw"
    state.levy_step = "muster" if first_levy else "pay"
    state.active_side = cast(Side, rebel)
    return state.levy_step
