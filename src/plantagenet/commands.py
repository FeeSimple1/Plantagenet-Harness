"""Campaign Command-menu actions: March, Sail, Tax, Parley (4.3, 4.6.1-.4).

These plug into the Activation loop (4.2): each consumes Command actions of
the Active Lord. March-via-Path and Sail consume the entire card (4.2.1).

Phase 3a-ii scope. Movement that would cause enemy contact (Approach 4.3.5
or an Intercept opportunity 4.3.4) is rejected with a code rather than
resolved, because Battle is Phase 3b. Supply (4.5) and Pay (3.2) are
Phase 3a-iii.
"""

from __future__ import annotations

from typing import Any

from plantagenet import campaign, influence, static_data
from plantagenet.actions import (
    _adjacency,
    enemy_lord_at,
    lord_at_friendly_locale,
    lord_location,
    other_side,
)
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _ways_between(a: str, b: str) -> set[str]:
    return {t for n, t in _adjacency().get(a, []) if n == b}


def _enemy_adjacent_by_land(state: GameState, locale_id: str, side: str) -> bool:
    for nbr, t in _adjacency().get(locale_id, []):
        if t in ("road", "highway") and enemy_lord_at(state, nbr, side):
            return True
    return False


# --------------------------------------------------------------- 4.3 March
def march(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    loc = lord_location(lord)
    _require(loc is not None, "lord_not_on_locale", "the Lord must be at a Locale to March")
    kind, here = loc
    dest = action.get("to")
    _require(dest in state.locales, "unknown_dest", f"no such Stronghold {dest!r}")

    # Determine speed/cost to the destination (4.3.3).
    cost = _march_cost(state, here, dest, kind)
    _require(cost is not None, "no_march_route",
             f"{dest} is not reachable from {here} in one March action (4.3.3)")
    way_kind, whole_card = cost

    # Enemy contact (Approach 4.3.5 / Intercept 4.3.4) is Phase 3b.
    _require(not enemy_lord_at(state, dest, lord.side), "approach_phase_3b",
             f"{dest} holds an Enemy Lord; Approach/Battle is Phase 3b (4.3.5)")
    _require(not _enemy_adjacent_by_land(state, dest, lord.side), "intercept_phase_3b",
             f"{dest} is adjacent to an Enemy Lord; Intercept is Phase 3b (4.3.4)")

    # Group March (4.3.1): a Marshal brings any; a Lieutenant all but a Marshal.
    movers = [lord]
    group = action.get("group", [])
    if group:
        title = static_data.load_lords()[lord.lord_id].get("title")
        _require(title in ("marshal", "lieutenant"), "not_group_leader",
                 "only a Marshal or Lieutenant may lead a Group March (4.3.1)")
        for gid in group:
            g = state.lords.get(gid)
            _require(g is not None and g.status == LordStatus.MUSTERED
                     and g.location == here and g.side == lord.side,
                     "bad_group_member", f"{gid} is not a Friendly Lord co-located at {here}")
            if title == "lieutenant":
                _require(static_data.load_lords()[gid].get("title") != "marshal",
                         "lieutenant_cannot_lead_marshal",
                         "a Lieutenant may not lead a Marshal (4.3.1)")
            movers.append(g)

    for m in movers:
        # Haul (4.3.2): discard Provender exceeding Carts before moving.
        carts = m.assets.get("cart", 0)
        if m.assets.get("provender", 0) > carts:
            m.assets["provender"] = carts
        m.location = dest
        m.exile_box = None
        m.moved_fought = True

    if whole_card:
        state.campaign.actions_remaining = 0
    else:
        state.campaign.actions_remaining -= 1
    return {"type": "march", "by_lord": lord.lord_id, "to": dest, "way": way_kind,
            "group": [m.lord_id for m in movers[1:]], "whole_card": whole_card}


def _march_cost(state: GameState, here: str, dest: str, kind: str):
    """Return (way_kind, whole_card) for marching ``here``->``dest`` in one
    action, or None. Scotland marches by one-way Path to Carlisle/Bamburgh."""
    if kind == "exile":
        boxes = static_data.load_exile_boxes()
        if here == "scotland" and dest in boxes["scotland"].get("land_exits", []):
            return ("path", True)
        return None
    ways = _ways_between(here, dest)
    if "road" in ways:
        return ("road", False)
    if "highway" in ways:
        return ("highway", False)
    if "path" in ways:
        return ("path", True)
    # Highway 2-for-1 (4.3.3): two Highways via an intermediate Stronghold.
    for mid, t1 in _adjacency().get(here, []):
        if t1 == "highway" and "highway" in _ways_between(mid, dest):
            return ("highway2", False)
    return None


# --------------------------------------------------------------- 4.6.1 Sail
def _forces_units(lord) -> int:
    forces_static = static_data.load_forces()
    troops_and_retinue = sum(
        n for f, n in lord.forces.items() if f in forces_static)
    return troops_and_retinue + len(lord.vassals)


def sail(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    loc = lord_location(lord)
    _require(loc is not None, "lord_not_on_locale",
             "the Lord must be at a Port or Exile box to Sail")
    kind, here = loc
    seas = static_data.load_seas()
    port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
    box_sea = {b: zone_id for zone_id, zone in seas["zones"].items()
               for b in zone.get("exile_boxes", [])}
    if kind == "exile":
        from_sea = box_sea.get(here)
    else:
        _require(static_data.load_locales()[here].get("port"), "not_port",
                 "Sail requires a Port or Exile box (4.6.1)")
        from_sea = port_sea.get(here)
    _require(from_sea is not None, "no_sea", f"{here} is not on a Sea")

    dest = action.get("to")
    _require(dest in port_sea, "dest_not_port", f"{dest!r} is not a Port (4.6.1)")
    dest_sea = port_sea[dest]
    adj = {frozenset(pair) for pair in seas["adjacency"]}
    reachable = dest_sea == from_sea or frozenset({from_sea, dest_sea}) in adj
    _require(reachable, "seas_not_adjacent",
             f"{dest} is not on the same or an adjacent Sea (4.6.1)")
    _require(not enemy_lord_at(state, dest, lord.side), "dest_has_enemy",
             f"{dest} is not free of Enemy Lords (4.6.1)")

    # Ship requirement: 1 Ship per 6 Forces, per 2 Provender, per 2 Carts (4.6.1).
    ships = lord.assets.get("ship", 0)
    need = max(-(-_forces_units(lord) // 6),
               -(-lord.assets.get("provender", 0) // 2),
               -(-lord.assets.get("cart", 0) // 2))
    _require(ships >= need, "insufficient_ships",
             f"Sail needs {need} Ship(s) (1 per 6 Forces / 2 Provender / 2 Carts); "
             f"the Lord has {ships} (4.6.1)")

    lord.location = dest
    lord.exile_box = None
    lord.moved_fought = True
    state.campaign.actions_remaining = 0   # Sail uses the entire card (4.2.1)
    return {"type": "sail", "by_lord": lord.lord_id, "to": dest,
            "from_sea": from_sea, "to_sea": dest_sea}


# --------------------------------------------------------------- 4.6.3 Tax
def _tax_route_cost(state: GameState, here: str, target: str, side: str,
                    has_ship: bool) -> int | None:
    """Shortest Route (Friendly chain free of Enemy Lords) from the Lord to
    the Taxed Stronghold (4.6.3). Returns Way count, or None."""
    from plantagenet.actions import _parley_route_cost
    return _parley_route_cost(state, ("stronghold", here), target, side, has_ship)


def tax(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Tax requires the acting Lord at a Friendly Locale (4.6.3)")
    loc = lord_location(lord)
    here = loc[1]
    target = action.get("target")
    _require(target in state.locales, "unknown_target", f"no such Stronghold {target!r}")

    statics = static_data.load_lords()[lord.lord_id]
    own_seat = statics["seat"]
    vassal_seats = {static_data.load_vassals()["regular"][v]["seat"]
                    for v in lord.vassals if v in static_data.load_vassals()["regular"]}
    specials = {"london", "calais", "harlech"}
    _require(target == own_seat or target in vassal_seats or target in specials,
             "bad_tax_target",
             "Tax targets the Lord's own Seat, a Vassal's Seat, or a Special "
             "Stronghold (4.6.3)")
    _require(state.locales[target].depletion != "exhausted", "exhausted",
             f"{target} is Exhausted and may not be Taxed (4.6.3)")

    auto = target == own_seat and here == own_seat
    way_cost = 0
    if not auto:
        has_ship = lord.assets.get("ship", 0) > 0
        if target == here:
            way_cost = 0
        else:
            way_cost = _tax_route_cost(state, here, target, lord.side, has_ship)
            _require(way_cost is not None, "no_route",
                     f"no Friendly Route free of Enemy Lords to {target} (4.6.3)")

    extra = int(action.get("extra_spend", 0))
    if auto:
        chk = {"success": True, "auto": True, "roll": None, "spent": 0}
    else:
        chk = influence.check_influence(state, lord.lord_id, lord.side,
                                        extra_spend=extra, way_cost=way_cost)
    state.campaign.actions_remaining -= 1
    coin_added = 0
    if chk["success"]:
        coin_added = static_data.stronghold_yields(target).get("tax", {}).get("coin", 0)
        lord.assets["coin"] = lord.assets.get("coin", 0) + coin_added
        ls = state.locales[target]
        ls.depletion = "exhausted" if ls.depletion == "depleted" else "depleted"
    return {"type": "tax", "by_lord": lord.lord_id, "target": target,
            "coin_added": coin_added, **chk}


# ------------------------------------------------------------- 4.6.4 Parley
def parley_campaign(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Campaign Parley (4.6.4): like Levy Parley (3.4.1) but the Route may
    reach only an adjacent Stronghold (or a same-Sea Port via Ship); Parley
    at the Lord's own location succeeds automatically, free of cost."""
    lord = campaign._active_command_lord(state, action)
    loc = lord_location(lord)
    kind, here = loc
    target = action.get("target", here)
    _require(target in state.locales, "unknown_target", f"no such Stronghold {target!r}")
    fav = state.locales[target].favour
    _require(fav != lord.side, "already_friendly", f"{target} already Favours {lord.side}")

    if target == here:
        # Own location: automatic, no Influence check or spend (4.6.4).
        state.campaign.actions_remaining -= 1
        _shift_favour(state, target, lord.side)
        return {"type": "parley", "by_lord": lord.lord_id, "target": target,
                "auto": True, "favour_change": _fav_desc(target, fav, lord.side)}

    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Campaign Parley beyond the Lord's location requires a Friendly Locale (4.6.4)")
    _require(not enemy_lord_at(state, target, lord.side), "target_has_enemy",
             f"{target} must be free of Enemy Lords (4.6.4)")
    # Reach: an adjacent Stronghold, or a same-Sea Port via Ship.
    has_ship = lord.assets.get("ship", 0) > 0
    adjacent = target in {n for n, _t in _adjacency().get(here, [])}
    sea_reach = has_ship and _same_sea_port(here, target)
    _require(adjacent or sea_reach, "out_of_reach",
             "Campaign Parley reaches only an adjacent Stronghold or a same-Sea Port (4.6.4)")

    extra = int(action.get("extra_spend", 0))
    chk = influence.check_influence(state, lord.lord_id, lord.side,
                                    extra_spend=extra, way_cost=1)
    state.campaign.actions_remaining -= 1
    changed = None
    if chk["success"]:
        changed = _fav_desc(target, fav, lord.side)
        _shift_favour(state, target, lord.side)
    return {"type": "parley", "by_lord": lord.lord_id, "target": target,
            **chk, "favour_change": changed}


def _same_sea_port(a: str, b: str) -> bool:
    seas = static_data.load_seas()
    port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
    return a in port_sea and b in port_sea and port_sea[a] == port_sea[b]


def _shift_favour(state: GameState, target: str, side: str) -> None:
    fav = state.locales[target].favour
    if fav == "neutral":
        state.locales[target].favour = side
    elif fav == other_side(side):
        state.locales[target].favour = "neutral"


def _fav_desc(target: str, before: str, side: str) -> str:
    after = side if before == "neutral" else "neutral"
    return f"{target}: {before} -> {after}"
