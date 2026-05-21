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
    if state.phase == "over":
        return []
    if state.phase == "campaign":
        return _campaign_moves(state)
    if state.phase == "levy" and state.levy_step == "done":
        return [{"type": "begin_campaign"}]
    if state.phase == "levy" and state.levy_step == "arts_of_war":
        return [{"type": "draw", "side": state.active_side}]
    if state.phase == "levy" and state.levy_step == "pay":
        return [{"type": "pay", "side": state.active_side}]
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

    # --- Levy Capability (3.4.6): eligible, unused, not duplicating a held name ---
    try:
        if len(lord.capabilities) < 2:
            cards = static_data.load_cards()
            in_play = actions._capabilities_in_play(state, side)
            held_titles = {cards[c]["capability"]["title"] for c in lord.capabilities}
            deck = static_data.scenario_card_deck(state.scenario, side)
            pool = deck or [c for c in cards if cards[c]["side"] == side]
            for cid in pool:
                if (cid not in in_play and actions._capability_eligible(cid, lord_id)
                        and cards[cid]["capability"]["title"] not in held_titles):
                    moves.append({"type": "levy_capability", "side": side,
                                  "by_lord": lord_id, "card": cid})
    except (KeyError, AttributeError):
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


def _campaign_moves(state: GameState) -> list[dict[str, Any]]:
    c = state.campaign
    if c is None:
        return []
    if c.step == "plan":
        # The Plan is a free construction (4.1); the consumer submits it via
        # build_plan. We surface the requirement rather than enumerate stacks.
        pending = [s for s in ("lancastrian", "yorkist") if not c.plan_built.get(s)]
        return [{"type": "build_plan", "side": s, "cards_required": c.cards_required}
                for s in pending]
    if c.step == "activation":
        side = state.active_side
        moves: list[dict[str, Any]] = []
        if c.active_lord is not None and c.actions_remaining > 0:
            moves.extend(_command_moves(state, side, c.active_lord))
        moves.append({"type": "end_activation", "side": side})
        return moves
    if c.step == "end":
        return [{"type": "end_campaign"}]
    return []


def _command_moves(state: GameState, side: str, lord_id: str) -> list[dict[str, Any]]:
    """Enumerate Command actions for the Active Lord (4.3-4.6), mirroring the
    handler pre-checks so nothing offered is rejected (round-trip discipline)."""
    from plantagenet import actions, commands
    lord = state.lords[lord_id]
    loc = actions.lord_location(lord)
    out: list[dict[str, Any]] = [{"type": "pass", "side": side, "by_lord": lord_id}]
    if loc is None:
        return out
    kind, here = loc
    # Forage (4.6.2): any Locale not yet Exhausted (Exile boxes are foragable).
    if kind == "exile" or state.locales[here].depletion != "exhausted":
        out.append({"type": "forage", "side": side, "by_lord": lord_id})
    friendly_here = actions.lord_at_friendly_locale(state, lord)

    # March (4.3): destinations reachable in one action with no enemy contact.
    try:
        for dest in state.locales:
            if dest == here:
                continue
            if commands._march_cost(state, here, dest, kind) is None:
                continue
            if actions.enemy_lord_at(state, dest, side):
                continue
            if commands._enemy_adjacent_by_land(state, dest, side):
                continue
            out.append({"type": "march", "side": side, "by_lord": lord_id, "to": dest})
    except (KeyError, AttributeError, IndexError):
        pass

    # Sail (4.6.1): same/adjacent-Sea Ports, free of enemy, ship requirement met.
    try:
        seas = static_data.load_seas()
        port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
        box_sea = {b: z for z, zone in seas["zones"].items() for b in zone.get("exile_boxes", [])}
        from_sea = box_sea.get(here) if kind == "exile" else port_sea.get(here)
        on_sea = kind == "exile" or static_data.load_locales()[here].get("port")
        if from_sea is not None and on_sea:
            adj = {frozenset(pr) for pr in seas["adjacency"]}
            ships = lord.assets.get("ship", 0)
            need = max(-(-commands._forces_units(lord) // 6),
                       -(-lord.assets.get("provender", 0) // 2),
                       -(-lord.assets.get("cart", 0) // 2))
            if ships >= need:
                for dest, dsea in port_sea.items():
                    if dest == here:
                        continue
                    if dsea == from_sea or frozenset({from_sea, dsea}) in adj:
                        if not actions.enemy_lord_at(state, dest, side):
                            out.append({"type": "sail", "side": side,
                                        "by_lord": lord_id, "to": dest})
    except (KeyError, AttributeError, IndexError):
        pass

    if not friendly_here:
        return out

    # Tax (4.6.3): own Seat / Vassal Seats / Special Strongholds, reachable, not Exhausted.
    try:
        statics = static_data.load_lords()[lord_id]
        regular = static_data.load_vassals()["regular"]
        targets = {statics["seat"]}
        targets |= {regular[v]["seat"] for v in lord.vassals if v in regular}
        targets |= {"london", "calais", "harlech"}
        has_ship = lord.assets.get("ship", 0) > 0
        for t in targets:
            if t not in state.locales or state.locales[t].depletion == "exhausted":
                continue
            if t == here or (t == statics["seat"] and here == statics["seat"]):
                out.append({"type": "tax", "side": side, "by_lord": lord_id, "target": t})
            elif commands._tax_route_cost(state, here, t, side, has_ship) is not None:
                out.append({"type": "tax", "side": side, "by_lord": lord_id, "target": t})
    except (KeyError, AttributeError, IndexError):
        pass

    # Supply (4.5): Friendly non-Exhausted Stronghold Sources reachable with
    # enough Carts; Port Sources via Ship.
    try:
        carts = lord.assets.get("cart", 0)
        for src in state.locales:
            if src == here:
                base = static_data.stronghold_yields(src).get("supply", {}).get("provender", 0)
                if base and state.locales[src].depletion != "exhausted":
                    out.append({"type": "supply", "side": side, "by_lord": lord_id,
                                "source": src})
                continue
            if state.locales[src].depletion == "exhausted":
                continue
            ways = commands._supply_route_cost(state, here, src, side)
            if ways is None:
                continue
            base = static_data.stronghold_yields(src).get("supply", {}).get("provender", 0)
            if base and (carts // ways) >= 1:
                out.append({"type": "supply", "side": side, "by_lord": lord_id,
                            "source": src})
        if lord.assets.get("ship", 0) > 0:
            seas = static_data.load_seas()
            ports = {p for zone in seas["zones"].values() for p in zone.get("ports", [])}
            for src in ports:
                if src != here and commands._same_sea_port_or_box(here, src):
                    out.append({"type": "supply", "side": side, "by_lord": lord_id,
                                "source": src, "use_ships": True})
    except (KeyError, AttributeError, IndexError):
        pass

    # Parley (4.6.4): own location (if not Friendly) or adjacent / same-Sea Port.
    try:
        if kind == "stronghold" and state.locales[here].favour != side:
            out.append({"type": "parley", "side": side, "by_lord": lord_id, "target": here})
        has_ship = lord.assets.get("ship", 0) > 0
        reach = {n for n, _t in actions._adjacency().get(here, [])}
        if has_ship:
            reach |= {p for p in _same_sea_ports(here)}
        for t in reach:
            if (t in state.locales and state.locales[t].favour != side
                    and not actions.enemy_lord_at(state, t, side)):
                out.append({"type": "parley", "side": side, "by_lord": lord_id, "target": t})
    except (KeyError, AttributeError, IndexError):
        pass
    return out


def _same_sea_ports(here: str) -> set[str]:
    seas = static_data.load_seas()
    port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
    if here not in port_sea:
        return set()
    z = port_sea[here]
    return {p for p, zz in port_sea.items() if zz == z and p != here}
