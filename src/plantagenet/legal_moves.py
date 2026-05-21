"""Legal-move enumeration for the Levy Muster segment (3.4).

Emits the palette of currently-permissible actions for the active side.
Every option mirrors a handler pre-check in `actions.py`; the goal is that
nothing emitted here is rejected by `apply_action` (the round-trip
discipline from CROSS_PROJECT_LESSONS). When a pre-check depends on
static data, it is wrapped so a data hiccup suppresses the option rather
than crashing the enumerator (bias: miss a legal move over offering a
phantom-legal one).

The one deferred Muster action intentionally NOT enumerated is
levy_capability (Arts of War cards, Phase 4).
"""

from __future__ import annotations

from typing import Any

from plantagenet import actions, static_data
from plantagenet.state import GameState, LordStatus, VassalStatus


def legal_moves(state: GameState) -> list[dict[str, Any]]:
    if state.levy_step != "muster":
        return []
    side = state.active_side
    out: list[dict[str, Any]] = []
    for lord_id, lord in state.lords.items():
        if lord.side != side or lord.status != LordStatus.MUSTERED:
            continue
        if actions.lord_location(lord) is None or lord.mustered_this_segment:
            continue
        if lord.lordship_spent >= actions._lordship(lord_id):
            continue
        out.extend(_moves_for_lord(state, lord_id, lord, side))
    # The active side may always end its Muster segment.
    out.append({"type": "end_muster", "side": side})
    return out


def _moves_for_lord(state: GameState, lord_id: str, lord, side: str) -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []
    friendly_here = actions.lord_at_friendly_locale(state, lord)

    # --- Parley (3.4.1) ---
    try:
        moves.extend(_parley_moves(state, lord_id, lord, side, friendly_here))
    except (KeyError, AttributeError):
        pass

    if not friendly_here:
        return moves  # at an Enemy/Neutral Stronghold, only Parley is allowed (3.4)

    # --- Levy Lord (3.4.2): Ready targets of this side ---
    try:
        seat_fallback = actions._friendly_enemyfree_seat_exists(state, side)
        for tid, t in state.lords.items():
            if (t.side == side and t.status == LordStatus.CALENDAR
                    and t.calendar_box is not None and t.calendar_box <= state.turn_box):
                seat = static_data.load_lords()[tid]["seat"]
                if not actions.enemy_lord_at(state, seat, side) or seat_fallback is not None:
                    moves.append({"type": "levy_lord", "side": side,
                                  "by_lord": lord_id, "target": tid})
    except (KeyError, AttributeError):
        pass

    # --- Levy Vassal (3.4.3): at-seat Vassals whose Seat is Friendly + Enemy-free ---
    try:
        regular = static_data.load_vassals()["regular"]
        for vid, vs in state.vassals.items():
            if vs.status != VassalStatus.AT_SEAT:
                continue
            seat = regular[vid]["seat"]
            if (actions.is_friendly_stronghold(state, seat, side)
                    and not actions.enemy_lord_at(state, seat, side)):
                moves.append({"type": "levy_vassal", "side": side,
                              "by_lord": lord_id, "target": vid})
    except (KeyError, AttributeError):
        pass

    # --- Levy Troops (3.4.4): at a Friendly Stronghold (not Exile box), not Exhausted ---
    try:
        loc = actions.lord_location(lord)
        if loc[0] == "stronghold" and state.locales[loc[1]].depletion != "exhausted":
            moves.append({"type": "levy_troops", "side": side, "by_lord": lord_id})
    except (KeyError, AttributeError, IndexError):
        pass

    # --- Levy Transport (3.4.5) ---
    moves.append({"type": "levy_transport", "side": side, "by_lord": lord_id, "transport": "cart"})
    try:
        loc = actions.lord_location(lord)
        at_port_or_exile = loc[0] == "exile" or static_data.load_locales()[loc[1]].get("port")
        if (at_port_or_exile and actions._ships_in_play(state) < 9
                and lord.assets.get("ship", 0) < 2):
            moves.append({"type": "levy_transport", "side": side,
                          "by_lord": lord_id, "transport": "ship"})
    except (KeyError, AttributeError, IndexError):
        pass
    return moves


def _parley_moves(state, lord_id, lord, side, friendly_here) -> list[dict[str, Any]]:
    loc = actions.lord_location(lord)
    kind, here = loc
    moves: list[dict[str, Any]] = []
    has_ship = lord.assets.get("ship", 0) > 0
    # Current location, if a Stronghold not yet Friendly to us.
    if kind == "stronghold" and state.locales[here].favour != side:
        moves.append({"type": "parley", "side": side, "by_lord": lord_id, "target": here})
    if not friendly_here:
        return moves
    # Reachable Strongholds that don't already Favour us.
    for tid, ls in state.locales.items():
        if tid == here or ls.favour == side:
            continue
        if actions._parley_route_cost(state, loc, tid, side, has_ship) is not None:
            moves.append({"type": "parley", "side": side, "by_lord": lord_id, "target": tid})
    return moves
