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

from plantagenet import campaign, influence, ratings, static_data
from plantagenet.actions import (
    _adjacency,
    enemy_lord_at,
    is_friendly_stronghold,
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

    dest_has_enemy = enemy_lord_at(state, dest, lord.side)

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

    decisions = action.get("decisions") or {}
    intercept_log = (None if dest_has_enemy
                     else _try_intercept(state, dest, lord.side, decisions))
    approach = None
    if intercept_log and intercept_log["success"] and intercept_log.get("flank_attack"):
        from plantagenet import battle  # interceptor Attacks the Marching Lords
        approach = battle.approach(state, dest, [intercept_log["interceptor"]], decisions)
        state.campaign.actions_remaining = 0
    elif intercept_log and intercept_log["success"]:
        dest_has_enemy = True

    if approach is None and dest_has_enemy:
        from plantagenet import battle
        approach = battle.approach(state, dest, [m.lord_id for m in movers], decisions)
        state.campaign.actions_remaining = 0   # Approach ends the card (4.3.5)
    elif whole_card:
        state.campaign.actions_remaining = 0
    else:
        state.campaign.actions_remaining -= 1
    return {"type": "march", "by_lord": lord.lord_id, "to": dest, "way": way_kind,
            "group": [m.lord_id for m in movers[1:]], "whole_card": whole_card,
            "intercept": intercept_log, "approach": approach}


def _try_intercept(state: GameState, dest: str, side: str,
                   decisions: dict[str, Any]) -> dict[str, Any] | None:
    """Intercept (4.3.4): a named Enemy Lord at a Locale adjacent to ``dest``
    by Road/Highway may roll <= its Valour to move to ``dest`` (then the
    Marching Lord Approaches it there)."""
    iid = decisions.get("intercept")
    if not iid:
        return None
    itc = state.lords.get(iid)
    eligible = (itc is not None and itc.status == LordStatus.MUSTERED and itc.side != side
                and itc.location is not None
                and any(n == dest and t in ("road", "highway")
                        for n, t in _adjacency().get(itc.location, [])))
    _require(eligible, "bad_intercept",
             f"{iid} cannot Intercept at {dest} (must be an Enemy adjacent by Road/Highway, 4.3.4)")
    from plantagenet import battle
    valour = ratings.rating(state, iid, "valour")
    flank = bool(decisions.get("flank_attack"))
    if flank:                            # Flank Attack (Y2/L2): auto-succeed, become Attacker
        cid = battle._side_held_event(state, itc.side, battle.FLANK_ATTACK)
        _require(cid is not None, "no_flank_attack",
                 f"{itc.side} has no Flank Attack Held Event to play (4.3.4)")
        battle._use_held_event(state, itc.side, cid)
        roll, success = None, True
    else:
        roller = state.dice()
        roll = roller.d6()
        state.store_dice(roller)
        success = roll <= valour
    if success:                          # the Interceptor Marches to dest (Carts limit Provender)
        carts = itc.assets.get("cart", 0)
        if itc.assets.get("provender", 0) > carts:
            itc.assets["provender"] = carts
        itc.location = dest
        itc.moved_fought = True
    return {"interceptor": iid, "roll": roll, "valour": valour, "success": success,
            "flank_attack": flank}


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
    cap = 2 if ratings.has_capability(state, lord.lord_id, "GREAT SHIPS") else 1
    need = max(-(-_forces_units(lord) // (6 * cap)),
               -(-lord.assets.get("provender", 0) // (2 * cap)),
               -(-lord.assets.get("cart", 0) // (2 * cap)))
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
                    has_ship: bool, all_seas: bool = False) -> int | None:
    """Shortest Route (Friendly chain free of Enemy Lords) from the Lord to
    the Taxed Stronghold (4.6.3). Returns Way count, or None."""
    from plantagenet.actions import _parley_route_cost
    return _parley_route_cost(state, ("stronghold", here), target, side, has_ship,
                              all_seas=all_seas)


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
            gs = ratings.has_capability(state, lord.lord_id, "GREAT SHIPS")
            way_cost = _tax_route_cost(state, here, target, lord.side, has_ship, all_seas=gs)
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

    new_act = ratings.event_against(state, "NEW ACT OF PARLIAMENT", lord.side)
    if target == here:
        # Own location: automatic, no Influence check or spend (4.6.4).
        state.campaign.actions_remaining = 0 if new_act else state.campaign.actions_remaining - 1
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
    state.campaign.actions_remaining = 0 if new_act else state.campaign.actions_remaining - 1
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


# --------------------------------------------------------------- 4.5 Supply
def _supply_route_cost(state: GameState, here: str, source: str, side: str,
                       all_seas: bool = False) -> int | None:
    """Shortest land Supply Route (Friendly chain free of Enemy Lords, NOT
    across any Sea), including both the Lord's Locale and the Source, which
    must itself be Friendly (4.5.1). Returns the Way count, or None."""
    from collections import deque
    if source == here:
        return 0
    if not is_friendly_stronghold(state, source, side) or enemy_lord_at(state, source, side):
        return None
    port_sea = {}
    if all_seas:
        seas = static_data.load_seas()
        port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
    seen = {here}
    q = deque([(here, 0)])
    while q:
        node, dist = q.popleft()
        nbrs = [n for n, _t in _adjacency().get(node, [])]
        if all_seas and node in port_sea:          # Great Ships: all Ports 1 Way apart
            nbrs += [p for p in port_sea if p != node]
        for nxt in nbrs:
            if nxt in seen:
                continue
            seen.add(nxt)
            if nxt == source:
                return dist + 1
            if is_friendly_stronghold(state, nxt, side) and not enemy_lord_at(state, nxt, side):
                q.append((nxt, dist + 1))
    return None


def supply(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Supply requires the acting Lord at a Friendly Locale (4.5)")
    loc = lord_location(lord)
    kind, here = loc
    source = action.get("source")
    _require(source in state.locales, "unknown_source", f"no such Stronghold/Port {source!r}")
    _require(source not in static_data.load_exile_boxes(), "exile_not_source",
             "an Exile box is never a Supply Source (4.5.1)")
    use_ships = bool(action.get("use_ships", False))
    carts = lord.assets.get("cart", 0)
    is_port = bool(static_data.load_locales()[source].get("port"))

    # Exile-box Lords must Supply by Ship from a same-Sea Port (Scotland: Path).
    if kind == "exile" and here != "scotland":
        _require(use_ships and is_port and _same_sea_port_or_box(here, source),
                 "exile_needs_ship_port",
                 "an Exile-box Lord must Supply via Ship from a Port on the same Sea (4.5.1)")

    if use_ships:
        _require(is_port, "ships_need_port", "Ship Supply requires a Port Source (4.5.1)")
        ships = lord.assets.get("ship", 0)
        _require(ships > 0, "no_ships", "Ship Supply requires at least one Ship (4.5.1)")
        per_ship = 2 if ratings.has_capability(state, lord.lord_id, "GREAT SHIPS") else 1
        sea_direct = (kind == "exile" or static_data.load_locales()[here].get("port")) \
            and _same_sea_port_or_box(here, source)
        if sea_direct:
            added = ships * per_ship               # by Sea: no Carts (4.5.2)
        else:
            ways = _supply_route_cost(state, here, source, lord.side,
                                      all_seas=ratings.has_capability(state, lord.lord_id,
                                                                      "GREAT SHIPS"))
            _require(ways is not None, "no_route", f"no Supply Route to {source} (4.5.1)")
            added = ships * per_ship if ways == 0 else min(ships * per_ship, carts // ways)
            _require(added > 0, "insufficient_carts",
                     "need one Cart per Provender per intervening Way (4.5.1)")
        lord.assets["provender"] = lord.assets.get("provender", 0) + added
        state.campaign.actions_remaining -= 1
        return {"type": "supply", "by_lord": lord.lord_id, "source": source,
                "via": "ship", "provender_added": added}

    # Stronghold Source: table Provender, Cart-limited, then Deplete (4.5.2).
    _require(state.locales[source].depletion != "exhausted", "exhausted",
             f"{source} is Exhausted and may not be a Supply Source (4.5.1)")
    ways = _supply_route_cost(state, here, source, lord.side,
                              all_seas=ratings.has_capability(state, lord.lord_id, "GREAT SHIPS"))
    _require(ways is not None, "no_route", f"no Supply Route to {source} (4.5.1)")
    base = static_data.stronghold_yields(source).get("supply", {}).get("provender", 0)
    added = base if ways == 0 else min(base, carts // ways)
    _require(added > 0, "insufficient_carts",
             "need one Cart per Provender per intervening Way to a Source (4.5.1)")
    lord.assets["provender"] = lord.assets.get("provender", 0) + added
    src = state.locales[source]
    src.depletion = "exhausted" if src.depletion == "depleted" else "depleted"
    state.campaign.actions_remaining -= 1
    return {"type": "supply", "by_lord": lord.lord_id, "source": source,
            "via": "stronghold", "ways": ways, "provender_added": added}


def _same_sea_port_or_box(a: str, b: str) -> bool:
    seas = static_data.load_seas()
    where = {}
    for z, zone in seas["zones"].items():
        for p in zone.get("ports", []):
            where[p] = z
        for bx in zone.get("exile_boxes", []):
            where[bx] = z
    return a in where and b in where and where[a] == where[b]
