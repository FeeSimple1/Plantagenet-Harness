"""Campaign Command-menu actions: March, Sail, Tax, Parley (4.3, 4.6.1-.4).

These plug into the Activation loop (4.2): each consumes Command actions of
the Active Lord. March-via-Path and Sail consume the entire card (4.2.1).

Movement causing enemy contact resolves Approach (4.3.5) / Intercept (4.3.4)
via `battle.py`. This module also implements Supply (4.5), the Capability
command actions (Agitators/Merchants/Heralds/Exile Pact), and the Naval
Blockade reaction checkpoints.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

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
from plantagenet.state import CampaignState, Favour, GameState, LordState, LordStatus

_SHAKY_PAIR = {"margaret": "warwick_lancastrian", "warwick_lancastrian": "margaret"}


def _shaky_allies_block(state: GameState, mover_ids: list[str], dest: str) -> bool:
    """Shaky Allies (IIY / Warwick's Rebellion): Margaret and Warwick may never
    enter the same Stronghold. True if this move would co-locate them at dest."""
    if "Shaky Allies" not in campaign._active_special_rules(state):
        return False
    movers = set(mover_ids)
    if {"margaret", "warwick_lancastrian"} <= movers:      # both moving to the same dest
        return True
    for m in movers:
        other = _SHAKY_PAIR.get(m)
        o = state.lords.get(other) if other else None
        if o is not None and o.status == LordStatus.MUSTERED and o.location == dest \
                and other not in movers:
            return True
    return False


_NAVAL_BLOCKADE = "NAVAL BLOCKADE"        # Y15 (Warwick): gates Lancastrian Sea actions


def _port_sea_map() -> dict[str, str]:
    seas = static_data.load_seas()
    return {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}


def _live_blockade_seas(state: GameState) -> set[str]:
    """Seas on which a Mustered Yorkist Lord with Naval Blockade (Y15) sits at a
    Port -- the only Seas on which the Blockade can fire (Y15 reaction)."""
    psea = _port_sea_map()
    locs = static_data.load_locales()
    out: set[str] = set()
    for lid, ls in state.lords.items():
        if (ls.side == "yorkist" and ls.status == LordStatus.MUSTERED
                and ratings.has_capability(state, lid, _NAVAL_BLOCKADE)
                and locs.get(ls.location or "", {}).get("port")):
            sea = psea.get(ls.location or "")
            if sea:
                out.add(sea)
    return out


def _route_used_seas(base_cost: int, recompute: Callable[[str], int | None],
                     candidates: set[str]) -> list[str]:
    """Among ``candidates`` Seas, those whose Ship sea-hops are load-bearing for
    a Route -- i.e. blocking that Sea raises the Way cost (or makes the target
    unreachable). Per Naval Blockade (Y15) the action only "uses a Port on that
    Sea" when that Sea is needed; an equally short land route routes around it."""
    used = []
    for sea in candidates:
        c = recompute(sea)
        if c is None or c > base_cost:
            used.append(sea)
    return used


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
def _effective_title(state: GameState, lord_id: str) -> str | None:
    """Static title, or "marshal" via Captain (Y30): a Lord with the Captain
    Capability is a Marshal at any Locale with no other Friendly Marshal or
    Lieutenant (4.3.1 / 1.9.1)."""
    statics = static_data.load_lords()
    title: str | None = statics[lord_id].get("title")
    if title in ("marshal", "lieutenant"):
        return title
    lord = state.lords[lord_id]
    if any(static_data.load_cards()[c]["capability"]["title"] == "CAPTAIN"
           for c in lord.capabilities):
        here = lord.location
        rivals = [lid for lid, ls in state.lords.items()
                  if lid != lord_id and ls.status == LordStatus.MUSTERED
                  and ls.location == here and ls.side == lord.side
                  and statics[lid].get("title") in ("marshal", "lieutenant")]
        if not rivals:
            return "marshal"
    return title


def _shared_lords(state: GameState, lord: LordState,
                  share_ids: list[str] | None) -> list[LordState]:
    """Co-located, same-side, Mustered Lords whose Assets may be Shared (1.5.3).
    Lords Share Assets (Carts, Ships, Provender, Coin) -- never Retinues,
    Vassals, Troops, or Valour -- and only while at the same Locale."""
    out: list[LordState] = []
    for sid in share_ids or []:
        ally = state.lords.get(sid)
        _require(ally is not None and ally.lord_id != lord.lord_id and ally.side == lord.side
                 and ally.status == LordStatus.MUSTERED, "bad_share",
                 f"{sid!r} is not a Friendly Mustered Lord to Share with (1.5.3)")
        assert ally is not None
        same = ((ally.location is not None and ally.location == lord.location)
                or (ally.exile_box is not None and ally.exile_box == lord.exile_box)
                or (ally.at_sea is not None and ally.at_sea == lord.at_sea))
        _require(same, "share_not_co_located",
                 f"{sid} is not at the same Locale as {lord.lord_id} (Sharing, 1.5.3)")
        out.append(ally)
    return out


def _shared_asset(state: GameState, lord: LordState, asset: str,
                  share_ids: list[str] | None) -> int:
    """The active Lord's ``asset`` plus the same total Shared by co-located
    allies (1.5.3); used for capacity requirements (Ships, Carts)."""
    return (lord.assets.get(asset, 0)
            + sum(a.assets.get(asset, 0) for a in _shared_lords(state, lord, share_ids)))


def march(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    loc = lord_location(lord)
    _require(loc is not None, "lord_not_on_locale", "the Lord must be at a Locale to March")
    assert loc is not None
    kind, here = loc
    dest = cast(str, action.get("to"))
    _require(dest in state.locales, "unknown_dest", f"no such Stronghold {dest!r}")

    # Owain Glyndwr (Y25): no Lancastrian March to a Stronghold in Wales.
    _require(not (lord.side == "lancastrian" and _active_event(state, "OWAIN GLYNDWR")
                  and static_data.load_locales().get(dest, {}).get("region") == "wales"),
             "owain_glyndwr", "Owain Glyndwr bars Lancastrian March into Wales (Y25)")

    # Road-as-Highway for a lone Lord: Yorkists Never Wait (Y11 Capability) /
    # Forced Marches (L8 Event, Lancastrian) -- enables the Road 2-for-1 chain.
    lone = not action.get("group")
    roads_as_highway = lone and (
        ratings.has_capability(state, lord.lord_id, "YORKISTS NEVER WAIT")
        or (lord.side == "lancastrian" and _active_event(state, "FORCED MARCHES")))

    # Determine speed/cost to the destination (4.3.3).
    cost = _march_cost(state, here, dest, kind, roads_as_highway, side=lord.side)
    _require(cost is not None, "no_march_route",
             f"{dest} is not reachable from {here} in one March action (4.3.3)")
    assert cost is not None
    way_kind, whole_card = cost
    if state.flags.get("surprise_march_lord") == lord.lord_id:   # L33 Surprise Landing
        _require(way_kind != "path", "surprise_landing_no_path",
                 "the Surprise Landing free March may not use a Path (L33)")
        state.flags.pop("surprise_march_lord", None)

    dest_has_enemy = enemy_lord_at(state, dest, lord.side)

    # Group March (4.3.1): a Marshal brings any; a Lieutenant all but a Marshal.
    movers = [lord]
    group = action.get("group", [])
    if group:
        title = _effective_title(state, lord.lord_id)
        _require(title in ("marshal", "lieutenant"), "not_group_leader",
                 "only a Marshal or Lieutenant may lead a Group March (4.3.1)")
        for gid in group:
            g = state.lords.get(gid)
            _require(g is not None and g.status == LordStatus.MUSTERED
                     and g.location == here and g.side == lord.side,
                     "bad_group_member", f"{gid} is not a Friendly Lord co-located at {here}")
            assert g is not None
            if title == "lieutenant":
                _require(static_data.load_lords()[gid].get("title") != "marshal",
                         "lieutenant_cannot_lead_marshal",
                         "a Lieutenant may not lead a Marshal (4.3.1)")
            movers.append(g)

    _require(not _shaky_allies_block(state, [m.lord_id for m in movers], dest),
             "shaky_allies", "Margaret and Warwick may never enter the same Stronghold (IIY)")
    # Haul (4.3.2): discard Provender exceeding Carts -- including Sharing across a
    # Group (a groupmate's spare Carts carry an ally's surplus). Provender stays on
    # its owner's mat for Feed; only the group's overall excess is discarded.
    def _carts(m: LordState) -> int:
        c = m.assets.get("cart", 0)
        return c * 2 if ratings.has_capability(state, m.lord_id, "HAY WAINS") else c  # L8
    if len(movers) > 1:
        excess = max(0, sum(m.assets.get("provender", 0) for m in movers)
                     - sum(_carts(m) for m in movers))
        for m in movers:                        # trim the group's overall surplus
            if excess <= 0:
                break
            drop = min(excess, m.assets.get("provender", 0))
            m.assets["provender"] = m.assets.get("provender", 0) - drop
            excess -= drop
    else:
        if lord.assets.get("provender", 0) > _carts(lord):
            lord.assets["provender"] = _carts(lord)
    for m in movers:
        m.location = dest
        m.exile_box = None
        m.moved_fought = True

    decisions = action.get("decisions") or {}
    # Parliament's Truce (Y12/L20): no Approach or Intercept this Campaign.
    truce = _active_event(state, "PARLIAMENT'S TRUCE")
    _require(not (truce and dest_has_enemy), "parliaments_truce",
             "Parliament's Truce prohibits Approach this Campaign (Y12/L20)")
    intercept_log = (None if (dest_has_enemy or truce)
                     else _try_intercept(state, dest, lord.side, decisions))
    approach = None
    if intercept_log and intercept_log["success"] and intercept_log.get("flank_attack"):
        from plantagenet import battle  # interceptor (+Group) Attacks the Marching Lords
        approach = battle.approach(
            state, dest,
            [intercept_log["interceptor"], *intercept_log.get("group", [])], decisions)
        state.campaign.actions_remaining = 0
    elif intercept_log and intercept_log["success"]:
        dest_has_enemy = True

    if approach is None and dest_has_enemy:
        # Approach (4.3.5): commit the card cost, then open the reaction window
        # (King's Parley / Parliament's Truce cancel; Blocked Ford forces Battle).
        state.campaign.actions_remaining = 0
        target_lords = [lid for lid, ls in state.lords.items()
                        if ls.status == LordStatus.MUSTERED and ls.location == dest
                        and ls.side != lord.side]
        ctx = {"approaching_side": lord.side, "dest": dest, "target_lords": target_lords}
        finish_data = {"movers": [m.lord_id for m in movers], "leader": lord.lord_id,
                       "origin": here, "origin_kind": kind, "dest": dest, "way": way_kind,
                       "group": [m.lord_id for m in movers[1:]], "whole_card": whole_card,
                       "intercept": intercept_log, "decisions": decisions}
        from plantagenet import reactions
        return reactions.gate(state, "on_approach", ctx, "commands:march_finish", finish_data)
    if whole_card:
        state.campaign.actions_remaining = 0
    else:
        state.campaign.actions_remaining -= 1
    return {"type": "march", "by_lord": lord.lord_id, "to": dest, "way": way_kind,
            "group": [m.lord_id for m in movers[1:]], "whole_card": whole_card,
            "intercept": intercept_log, "approach": approach}


def _maybe_open_hold_window(state: GameState, action_type: str,
                            movers: list[str], dest: str) -> None:
    """Open the Hold-event timing window (1.9.1) after a qualifying March / Sail
    that ends with mover(s) at a Port -- the trigger for Rebel Supply Depot (L28)
    and Surprise Landing (L33). No-op if the destination is not a Port or no
    mover actually ended there (e.g. removed in a Battle)."""
    if not static_data.load_locales().get(dest, {}).get("port"):
        return
    at_port = [m for m in movers if state.lords[m].location == dest]
    if not at_port:
        return
    state.hold_window = {"action": action_type, "side": state.lords[at_port[0]].side,
                         "lords": at_port, "dest": dest}


def march_finish(state: GameState, data: dict[str, Any], *, cancelled: bool) -> dict[str, Any]:
    """Resume after the Approach reaction window (4.3.5 / Q-004)."""
    base = {"type": "march", "by_lord": data["leader"], "to": data["dest"],
            "way": data["way"], "group": data["group"], "whole_card": data["whole_card"],
            "intercept": data["intercept"]}
    if cancelled:
        # King's Parley / Parliament's Truce: rewind the movers; the cancelled
        # March's movers are not marked Moved/Fought; the Command card ends.
        for mid in data["movers"]:
            m = state.lords[mid]
            # Restore the pre-March position. An Exile-box origin must go back to
            # ``exile_box`` (not ``location``, which is for Strongholds) -- else the
            # Lord is recorded "at" a box id that is not a Locale.
            if data.get("origin_kind") == "exile":
                m.exile_box = data["origin"]
                m.location = None
            else:
                m.location = data["origin"]
                m.exile_box = None
            m.moved_fought = False
        cast(CampaignState, state.campaign).actions_remaining = 0
        base["approach"] = None
        base["approach_cancelled"] = data.get("cancel_reason", True)
        return base
    from plantagenet import battle
    decisions = dict(data.get("decisions") or {})
    if data.get("blocked_ford"):
        decisions["blocked_ford"] = data["blocked_ford"]
    for mid in data["movers"]:
        _apply_burgundians(state, state.lords[mid])      # Y14/Y23 Burgundians at a Port
    base["approach"] = battle.approach(state, data["dest"], data["movers"], decisions)
    cast(CampaignState, state.campaign).actions_remaining = 0
    _maybe_open_hold_window(state, "march", data["movers"], data["dest"])
    return base


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
    assert itc is not None
    from plantagenet import battle
    # 4.3.4: an Intercepting Marshal/Lieutenant may bring co-located Lords (Group).
    group = decisions.get("intercept_group", []) or []
    movers = [itc]
    if group:
        title = _effective_title(state, iid)
        _require(title in ("marshal", "lieutenant"), "not_group_leader",
                 "only a Marshal or Lieutenant may bring a Group when Intercepting (4.3.4)")
        for gid in group:
            g = state.lords.get(gid)
            _require(g is not None and g.status == LordStatus.MUSTERED
                     and g.side == itc.side and g.location == itc.location,
                     "bad_group_member", f"{gid} is not a Friendly Lord co-located with {iid}")
            assert g is not None
            if title == "lieutenant":
                _require(static_data.load_lords()[gid].get("title") != "marshal",
                         "lieutenant_cannot_lead_marshal",
                         "a Lieutenant may not lead a Marshal (4.3.1)")
            movers.append(g)
    valour = ratings.rating(state, iid, "valour")
    flank = bool(decisions.get("flank_attack"))
    if flank:                            # Flank Attack (Y2/L2): auto-succeed, become Attacker
        cid = battle._side_held_event(state, itc.side, battle.FLANK_ATTACK)
        _require(cid is not None, "no_flank_attack",
                 f"{itc.side} has no Flank Attack Held Event to play (4.3.4)")
        assert cid is not None
        battle._use_held_event(state, itc.side, cid)
        roll: int | None = None
        success = True
    else:
        roller = state.dice()
        roll = roller.d6()
        state.store_dice(roller)
        success = roll <= valour
    if success:                          # the Interceptor (and Group) March to dest
        for m in movers:
            carts = m.assets.get("cart", 0)
            if m.assets.get("provender", 0) > carts:
                m.assets["provender"] = carts
            m.location = dest
            m.moved_fought = True
    return {"interceptor": iid, "roll": roll, "valour": valour, "success": success,
            "flank_attack": flank, "group": [m.lord_id for m in movers[1:]]}


def _apply_burgundians(state: GameState, lord: LordState) -> int:
    """Burgundians (Y14/Y23): the first time this Lord (with the Capability) is at
    any Port, add 2 Handgunners -- the only way Handgunners enter play (pool-limited)."""
    if not ratings.has_capability(state, lord.lord_id, "BURGUNDIANS"):
        return 0
    flag = f"burgundians_{lord.lord_id}"
    if state.flags.get(flag):
        return 0
    if lord.location is None or not static_data.load_locales().get(lord.location, {}).get("port"):
        return 0
    pool = static_data.load_forces()["handgunners"].get("pool", 0)
    in_play = sum(v.forces.get("handgunners", 0) for v in state.lords.values())
    give: int = max(0, min(2, pool - in_play))
    if give:
        lord.forces["handgunners"] = lord.forces.get("handgunners", 0) + give
        state.flags[flag] = True
    return give


def _march_cost(state: GameState, here: str, dest: str, kind: str,
                roads_as_highway: bool = False,
                side: str | None = None) -> tuple[str, bool] | None:
    """Return (way_kind, whole_card) for marching ``here``->``dest`` in one
    action, or None. Scotland marches by one-way Path to Carlisle/Bamburgh.
    ``roads_as_highway`` (Yorkists Never Wait Y11 / Forced Marches L8) lets a
    lone Lord use Roads for the Highway 2-for-1 chain (4.3.3)."""
    if kind == "exile":
        boxes = static_data.load_exile_boxes()
        if here == "scotland" and dest in boxes["scotland"].get("land_exits", []):
            return ("path", True)
        return None
    fast = ("highway", "road") if roads_as_highway else ("highway",)
    ways = _ways_between(here, dest)
    if "road" in ways:
        return ("road", False)
    if "highway" in ways:
        return ("highway", False)
    if "path" in ways:
        return ("path", True)
    # Highway 2-for-1 (4.3.3): two fast Ways via an intermediate Stronghold. The
    # Lord enters the intermediate, so it cannot chain through one holding an
    # Enemy Lord -- that would force an Approach (4.3.5) and stop there.
    for mid, t1 in _adjacency().get(here, []):
        if t1 in fast and _ways_between(mid, dest) & set(fast):
            if side is not None and enemy_lord_at(state, mid, side):
                continue
            return ("highway2", False)
    return None


# --------------------------------------------------------------- 4.6.1 Sail
def _forces_units(lord: LordState) -> int:
    forces_static = static_data.load_forces()
    troops_and_retinue = sum(
        n for f, n in lord.forces.items() if f in forces_static)
    return troops_and_retinue + len(lord.vassals)


def sail(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    seas = static_data.load_seas()
    zones = seas["zones"]
    port_sea = {p: z for z, zone in zones.items() for p in zone.get("ports", [])}
    box_sea = {b: zone_id for zone_id, zone in zones.items()
               for b in zone.get("exile_boxes", [])}
    adj = {frozenset(pair) for pair in seas["adjacency"]}

    # Origin Sea: at a Port, an Exile box, or already at Sea (4.6.1).
    origin_at_sea = lord.at_sea is not None
    kind: str | None = None
    here: str | None = None
    if origin_at_sea:
        from_sea = lord.at_sea
    else:
        loc = lord_location(lord)
        _require(loc is not None, "lord_not_on_locale",
                 "the Lord must be at a Port, Exile box, or at Sea to Sail")
        assert loc is not None
        kind, here = loc
        if kind == "exile":
            from_sea = box_sea.get(here)
        else:
            _require(static_data.load_locales()[here].get("port"), "not_port",
                     "Sail requires a Port, Exile box, or being at Sea (4.6.1)")
            from_sea = port_sea.get(here)
    _require(from_sea is not None, "no_sea", "the Lord is not on a Sea")

    # French Fleet (L21): Yorkist Lords may not Sail this Campaign.
    _require(not (lord.side == "yorkist" and _active_event(state, "FRENCH FLEET")),
             "french_fleet", "French Fleet prohibits Yorkist Sailing this Campaign (L21)")

    # Group Sail (4.6.1): a Marshal/Lieutenant may Sail with co-located Lords,
    # Sharing Ships among the Group (4.3.1). Members must share the leader's origin.
    movers = [lord]
    group = action.get("group", [])
    if group:
        title = _effective_title(state, lord.lord_id)
        _require(title in ("marshal", "lieutenant"), "not_group_leader",
                 "only a Marshal or Lieutenant may lead a Group Sail (4.6.1, 4.3.1)")
        for gid in group:
            g = state.lords.get(gid)
            if origin_at_sea:
                same = g is not None and g.at_sea == from_sea
            elif kind == "exile":
                same = g is not None and g.exile_box == here and g.at_sea is None
            else:
                same = g is not None and g.location == here and g.at_sea is None
            _require(g is not None and g.status == LordStatus.MUSTERED
                     and g.side == lord.side and same, "bad_group_member",
                     f"{gid} is not a Friendly Lord co-located with the Sailing leader (4.6.1)")
            assert g is not None
            if title == "lieutenant":
                _require(static_data.load_lords()[gid].get("title") != "marshal",
                         "lieutenant_cannot_lead_marshal",
                         "a Lieutenant may not lead a Marshal (4.3.1)")
            movers.append(g)

    dest = cast(str, action.get("to"))
    into_sea = dest in zones
    if into_sea:                       # 4.6.1: move "into that or an adjacent Sea" -> at Sea
        dest_sea = dest
        _require(dest_sea == from_sea or frozenset({from_sea, dest_sea}) in adj,
                 "seas_not_adjacent", f"{dest} is not the current or an adjacent Sea (4.6.1)")
        dest_has_enemy = False
    else:                              # to a Port, Enemy-free
        _require(dest in port_sea, "dest_not_port", f"{dest!r} is not a Port or a Sea (4.6.1)")
        dest_sea = port_sea[dest]
        # A Lord at a Port/Exile box may Sail Port-to-Port only WITHIN a Sea; a
        # Lord already at Sea may also reach a Port on an adjacent Sea. Direct
        # cross-Sea Port-to-Port is never allowed -- transit at Sea (4.6.1, FAQ #1).
        if origin_at_sea:
            reachable = dest_sea == from_sea or frozenset({from_sea, dest_sea}) in adj
            _require(reachable, "seas_not_adjacent",
                     f"{dest} is not on the current or an adjacent Sea (4.6.1)")
        else:
            _require(dest_sea == from_sea, "cross_sea_port_to_port",
                     f"{dest} is on a different Sea; a Port-to-Port Sail stays within one "
                     "Sea -- cross-Sea moves transit at Sea (4.6.1, FAQ #1)")
        dest_has_enemy = enemy_lord_at(state, dest, lord.side)
        if dest_has_enemy:
            _require(ratings.has_capability(state, lord.lord_id, "HIGH ADMIRAL"),
                     "dest_has_enemy",
                     f"{dest} is not free of Enemy Lords (4.6.1)")   # High Admiral (L29)
            _require(not _active_event(state, "PARLIAMENT'S TRUCE"), "parliaments_truce",
                     "Parliament's Truce prohibits the High Admiral Approach (Y12/L20)")
        _require(not _shaky_allies_block(state, [m.lord_id for m in movers], dest),
                 "shaky_allies",
                 "Margaret and Warwick may never enter the same Stronghold (IIY)")

    # Ship requirement: 1 Ship per 6 Forces, per 2 Provender, per 2 Carts (4.6.1).
    # A single Ship carries up to each limit. Ships may be Shared (1.5.3): from
    # co-located Friendly Lords for a lone Lord, or pooled across the Group.
    cap = 2 if ratings.has_capability(state, lord.lord_id, "GREAT SHIPS") else 1
    if len(movers) > 1:
        ships = sum(m.assets.get("ship", 0) for m in movers)   # Shared among the Group
        tot_forces = sum(_forces_units(m) for m in movers)
        tot_prov = sum(m.assets.get("provender", 0) for m in movers)
        tot_carts = sum(m.assets.get("cart", 0) for m in movers)
    else:
        ships = _shared_asset(state, lord, "ship", action.get("share"))
        tot_forces = _forces_units(lord)
        tot_prov = lord.assets.get("provender", 0)
        tot_carts = lord.assets.get("cart", 0)
    need = max(-(-tot_forces // (6 * cap)),
               -(-tot_prov // (2 * cap)),
               -(-tot_carts // (2 * cap)))
    _require(ships >= need, "insufficient_ships",
             f"Sail needs {need} Ship(s) (1 per 6 Forces / 2 Provender / 2 Carts); "
             f"available (incl. Shared) {ships} (4.6.1)")

    # Owain Glyndwr (Y25): no Lancastrian Sail to a Stronghold in Wales.
    _require(not (lord.side == "lancastrian" and _active_event(state, "OWAIN GLYNDWR")
                  and not into_sea
                  and static_data.load_locales().get(dest, {}).get("region") == "wales"),
             "owain_glyndwr", "Owain Glyndwr bars Lancastrian Sail into Wales (Y25)")

    # Commit the Command card cost NOW (spent regardless of any Naval Blockade).
    if _active_event(state, "SEAMANSHIP", lord.side):   # Seamanship (Y6/L6): just 1 action
        state.campaign.actions_remaining -= 1
    else:
        state.campaign.actions_remaining = 0            # Sail uses the entire card (4.2.1)

    # Reaction checkpoint (Q-004): Naval Blockade may cancel a Lancastrian Sail
    # using a Port on this Sea, before the move resolves.
    from plantagenet import reactions
    ctx = {"actor": lord.lord_id, "side": lord.side, "seas": [from_sea, dest_sea]}
    finish_data = {"lord": lord.lord_id, "dest": dest, "into_sea": into_sea,
                   "from_sea": from_sea, "to_sea": dest_sea,
                   "movers": [m.lord_id for m in movers],
                   "dest_has_enemy": dest_has_enemy, "decisions": action.get("decisions")}
    return reactions.gate(state, "uses_port_on_sea", ctx, "commands:sail_finish", finish_data)


def sail_finish(state: GameState, data: dict[str, Any], *, cancelled: bool) -> dict[str, Any]:
    """Resume after the Sail reaction window (4.6.1 / Q-004)."""
    lord = state.lords[data["lord"]]
    if cancelled:                       # Naval Blockade cancelled the Sail (card cost stands)
        return {"type": "sail", "by_lord": lord.lord_id, "to": data["dest"],
                "cancelled": True}
    movers = [state.lords[mid] for mid in data.get("movers", [data["lord"]])]
    for m in movers:
        m.exile_box = None
        m.moved_fought = True
        if data.get("into_sea"):        # ended the Sail at Sea (4.6.1); Disembark at 4.8.2
            m.location = None
            m.at_sea = data["dest"]
        else:
            m.location = data["dest"]
            m.at_sea = None
    group = [mid for mid in data.get("movers", []) if mid != data["lord"]]
    if data.get("into_sea"):
        return {"type": "sail", "by_lord": lord.lord_id, "to_sea": data["dest"],
                "at_sea": data["dest"], "group": group}
    for m in movers:
        _apply_burgundians(state, m)                     # Y14/Y23 Burgundians at a Port
    out = {"type": "sail", "by_lord": lord.lord_id, "to": data["dest"],
           "from_sea": data["from_sea"], "to_sea": data["to_sea"], "group": group}
    _maybe_open_hold_window(state, "sail", [m.lord_id for m in movers], data["dest"])
    if data["dest_has_enemy"]:          # High Admiral: Sail triggers Approach (4.3.5)
        from plantagenet import battle
        out["approach"] = battle.approach(state, data["dest"],
                                          [m.lord_id for m in movers], data.get("decisions"))
    return out


# ---------------- new Command actions from Capabilities (1.9.1) -------------
def _ec_ports() -> set[str]:
    return set(static_data.load_seas()["zones"]["english_channel"]["ports"])


def exile_pact(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Exile Pact (Y8 Event): a Yorkist Lord may use a Command action to place
    its cylinder into a Friendly Exile box at no Influence cost (this Campaign)."""
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    _require(lord.side == "yorkist" and _active_event(state, "EXILE PACT", "yorkist"),
             "no_exile_pact", "Exile Pact is not in effect for the Yorkist side (Y8)")
    box = cast(str, action.get("box"))
    boxes = static_data.load_exile_boxes()
    _require(box in boxes, "bad_box", f"{box!r} is not an Exile box (Y8)")
    _require(state.exile_alignment.get(box) == "yorkist", "not_friendly_box",
             f"{box} is not a Friendly Exile box (Y8)")
    _require(not (lord.status == LordStatus.MUSTERED and lord.exile_box == box
                 and lord.location is None),
             "already_in_box", f"{lord.lord_id} is already in Exile box {box} (Y8 no-op)")
    # A Lord in an Exile box is Mustered there (Reference: "Each Mustered ... Lord,
    # even Exile box"; "All on-map ... Lords, including Exile boxes"). Using a dead
    # -end EXILE status stranded the Lord; MUSTERED lets it later Sail/act and keeps
    # it on-map for scoring, matching muster_exiles. Y8: "no effect on Assets/Vassals".
    lord.status = LordStatus.MUSTERED
    lord.exile_box = box
    # The Lord now occupies exactly the Exile box: clear every other position
    # field so it is never recorded in two places at once.
    lord.location = None
    lord.at_sea = None
    lord.calendar_box = None
    lord.calendar_exile = False
    lord.captured_by = None
    state.campaign.actions_remaining -= 1
    return {"type": "exile_pact", "by_lord": lord.lord_id, "box": box}


def agitators(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Agitators (Y10 Capability): a Command action to Deplete an adjacent
    Neutral or Enemy Stronghold, or flip a Depleted one there to Exhausted."""
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    _require(ratings.has_capability(state, lord.lord_id, "AGITATORS"), "no_agitators",
             f"{lord.lord_id} lacks the Agitators Capability (Y10)")
    here = cast(tuple[str, str], lord_location(lord))[1]
    target = cast(str, action.get("target"))
    _require(target in {n for n, _t in _adjacency().get(here, [])}, "not_adjacent",
             f"{target} is not adjacent to {here} (Y10)")
    ls = state.locales[target]
    _require(cast(str, ls.favour) != cast(str, lord.side), "is_friendly",
             "Agitators targets a Neutral or Enemy Stronghold (Y10)")
    _require(ls.depletion != "exhausted", "already_exhausted", f"{target} is already Exhausted")
    ls.depletion = "exhausted" if ls.depletion == "depleted" else "depleted"
    state.campaign.actions_remaining -= 1
    return {"type": "agitators", "by_lord": lord.lord_id, "target": target,
            "depletion": ls.depletion}


def merchants(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Merchants (L30 Capability, Warwick): 1 Command action + a successful
    Influence check removes 2 Depleted/Exhausted markers at the Lord's Locale
    and/or adjacent (Exhausted->Depleted->none)."""
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    _require(ratings.has_capability(state, lord.lord_id, "MERCHANTS"), "no_merchants",
             f"{lord.lord_id} lacks the Merchants Capability (L30)")
    here = cast(tuple[str, str], lord_location(lord))[1]
    region = {here} | {n for n, _t in _adjacency().get(here, [])}
    targets = action.get("targets", [])
    _require(len(targets) <= 2 and all(t in region for t in targets), "bad_targets",
             "Merchants removes up to 2 markers at or adjacent to the Lord (L30)")
    extra = int(action.get("extra_spend", 0))
    chk = influence.check_influence(state, lord.lord_id, lord.side, extra_spend=extra)
    state.campaign.actions_remaining -= 1
    removed = []
    if chk["success"]:
        for t in targets[:2]:
            ls = state.locales[t]
            # Removing the Depletion marker clears the Stronghold outright --
            # "Removal of Exhausted leaves the Stronghold neither Exhausted nor
            # Depleted" (L30). Each removal frees one Stronghold; remove 2 if able.
            if ls.depletion in ("exhausted", "depleted"):
                ls.depletion = None
                removed.append(t)
    return {"type": "merchants", "by_lord": lord.lord_id, "removed": removed, **chk}


def heralds(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Heralds (L4 Capability): at a Port, use the full Command card for an
    Influence check; on success shift a Lord cylinder on the Calendar to the
    next Turn box (sooner entry)."""
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    _require(ratings.has_capability(state, lord.lord_id, "HERALDS"), "no_heralds",
             f"{lord.lord_id} lacks the Heralds Capability (L4)")
    here = cast(tuple[str, str], lord_location(lord))[1]
    _require(bool(static_data.load_locales()[here].get("port")), "not_port",
             "Heralds is used at a Port (L4)")
    target = cast(str, action.get("target"))
    tl = state.lords.get(target)
    _require(tl is not None and tl.status == LordStatus.CALENDAR and tl.calendar_box is not None,
             "bad_target", "Heralds shifts a Lord cylinder on the Calendar (L4)")
    assert tl is not None
    extra = int(action.get("extra_spend", 0))
    chk = influence.check_influence(state, lord.lord_id, lord.side, extra_spend=extra)
    state.campaign.actions_remaining = 0          # full Command card (L4)
    if chk["success"]:
        tl.calendar_box = state.turn_box + 1       # to the next Turn box
    return {"type": "heralds", "by_lord": lord.lord_id, "target": target, **chk}


# --------------------------------------------------------------- 4.6.3 Tax
def _tax_route_cost(state: GameState, here: str, target: str, side: str,
                    has_ship: bool, all_seas: bool = False,
                    block_sea: str | None = None) -> int | None:
    """Shortest Route (Friendly chain free of Enemy Lords) from the Lord to
    the Taxed Stronghold (4.6.3). Returns Way count, or None."""
    from plantagenet.actions import _parley_route_cost
    return _parley_route_cost(state, ("stronghold", here), target, side, has_ship,
                              all_seas=all_seas, block_sea=block_sea)


def _active_event(state: GameState, title: str, side: str | None = None) -> bool:
    cards = static_data.load_cards()
    for e in state.active_events:
        if cards[e["card"]]["event"]["title"] == title and (side is None or e["side"] == side):
            return True
    return False


def _exeter_or_adjacent(locale: str) -> bool:
    return locale == "exeter" or "exeter" in {n for n, _t in _adjacency().get(locale, [])}


def _is_own_vassal_seat(state: GameState, lord: LordState, locale: str) -> bool:
    regular = static_data.load_vassals()["regular"]
    return any(regular.get(v, {}).get("seat") == locale for v in lord.vassals)


def _supply_bonuses(state: GameState, lord: LordState, source: str, added: int) -> int:
    if ratings.has_capability(state, lord.lord_id, "HARBINGERS"):
        added *= 2                                       # Y7/L7: twice usual Provender
    if (ratings.has_capability(state, lord.lord_id, "STAFFORD BRANCH")
            and _exeter_or_adjacent(source)):
        added += 1                                       # Y29 (Devon): Exeter & adjacent +1
    return added


def tax(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = campaign._active_command_lord(state, action)
    assert state.campaign is not None
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Tax requires the acting Lord at a Friendly Locale (4.6.3)")
    loc = lord_location(lord)
    here = cast(tuple[str, str], loc)[1]
    target = cast(str, action.get("target"))
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

    # 4.6.3 EXCEPTION: Taxing the Lord's own Seat succeeds automatically (no
    # Influence check), wherever the Lord stands -- no co-location requirement.
    auto = (target == own_seat)
    # A Route free of Enemy Lords must still connect a remote target (4.6.3), but
    # Tax pays NO per-Way Influence surcharge -- that surcharge is Parley-only
    # (1.4.2). way_cost is route distance, used only for Naval Blockade, never charged.
    way_cost: int | None = 0
    if target != here:
        has_ship = lord.assets.get("ship", 0) > 0
        gs = ratings.has_capability(state, lord.lord_id, "GREAT SHIPS")
        way_cost = _tax_route_cost(state, here, target, lord.side, has_ship, all_seas=gs)
        _require(way_cost is not None, "no_route",
                 f"no Friendly Route free of Enemy Lords to {target} (4.6.3)")
        assert way_cost is not None

    extra = int(action.get("extra_spend", 0))
    _require(extra in (0, 1, 3), "bad_extra_spend",
             "added Influence spend must be 0, 1, or 3 (1.4.2)")
    # Which blockaded Sea(s) (if any) does the Tax Route use (Y15)?
    used_seas: list[str] = []
    if target != here and lord.side == "lancastrian":
        blk = _live_blockade_seas(state)
        if blk:
            gs2 = ratings.has_capability(state, lord.lord_id, "GREAT SHIPS")
            hs2 = lord.assets.get("ship", 0) > 0
            used_seas = _route_used_seas(
                cast(int, way_cost),
                lambda sea: _tax_route_cost(state, here, target, lord.side, hs2,
                                            all_seas=gs2, block_sea=sea),
                blk)
    # Command-action cost is spent regardless of any Naval Blockade (Y15 tips).
    state.campaign.actions_remaining -= 1
    from plantagenet import reactions
    ctx = {"actor": lord.lord_id, "side": lord.side, "seas": used_seas}
    finish = {"lord": lord.lord_id, "target": target, "auto": auto,
              "way_cost": way_cost, "extra": extra}
    return reactions.gate(state, "uses_port_on_sea", ctx, "commands:tax_finish", finish)


def tax_finish(state: GameState, data: dict[str, Any], *, cancelled: bool) -> dict[str, Any]:
    """Resume after the Tax reaction window (4.6.3 / Naval Blockade Y15)."""
    lord = state.lords[data["lord"]]
    target = data["target"]
    if cancelled:                       # Blockaded: no Influence paid (Y15 tips), no Coin.
        return {"type": "tax", "by_lord": lord.lord_id, "target": target, "cancelled": True}
    if data["auto"]:
        chk = {"success": True, "auto": True, "roll": None, "spent": 0}
    else:
        chk = influence.check_influence(state, lord.lord_id, lord.side,
                                        extra_spend=data["extra"], action="tax")  # no per-Way
    coin_added = 0
    if chk["success"]:
        coin_added = static_data.stronghold_yields(target).get("tax", {}).get("coin", 0)
        if (ratings.has_capability(state, lord.lord_id, "SO WISE, SO YOUNG")
                and lord.lord_id != "richard_iii"):
            coin_added += 1                      # Y34 (Gloucester): +1 Coin per Tax
        if (ratings.has_capability(state, lord.lord_id, "STAFFORD BRANCH")
                and _exeter_or_adjacent(target)):
            coin_added += 1                      # Y29 (Devon): Exeter & adjacent +1 Coin
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
    assert state.campaign is not None
    loc = lord_location(lord)
    kind, here = cast(tuple[str, str], loc)
    target = action.get("target", here)
    _require(target in state.locales, "unknown_target", f"no such Stronghold {target!r}")
    fav = state.locales[target].favour
    _require(cast(str, fav) != cast(str, lord.side), "already_friendly",
             f"{target} already Favours {lord.side}")

    new_act = ratings.event_against(state, "NEW ACT OF PARLIAMENT", lord.side)
    honest = (lord.side == "lancastrian"   # Y34 An Honest Tale: +1 each Lancastrian Parley
              and _active_event(state, "AN HONEST TALE SPEEDS BEST BEING PLAINLY TOLD"))
    if target == here:
        # Own location: automatic (4.6.4); free EXCEPT An Honest Tale still charges +1 (Y34).
        state.campaign.actions_remaining = 0 if new_act else state.campaign.actions_remaining - 1
        if honest:
            influence.spend_influence(state, lord.side, 1)
        _shift_favour(state, target, lord.side)
        return {"type": "parley", "by_lord": lord.lord_id, "target": target,
                "auto": True, "honest_tale_cost": 1 if honest else 0,
                "favour_change": _fav_desc(target, fav, lord.side)}

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
    _require(extra in (0, 1, 3), "bad_extra_spend",
             "added Influence spend must be 0, 1, or 3 (1.4.2)")
    # Dorset (Y29): Devon at Exeter Parleys for no Influence cost and auto-success.
    dorset = (lord.lord_id == "devon" and here == "exeter"
              and _active_event(state, "DORSET", "yorkist"))
    way = 0 if dorset else 1
    # The Parley "uses a Port on a Sea" only when it reaches a non-adjacent
    # same-Sea Port by Ship (Y15). Adjacent reach is overland -> no Blockade.
    used_seas: list[str] = []
    if sea_reach and not adjacent and lord.side == "lancastrian":
        sea = _port_sea_map().get(here)
        if sea and sea in _live_blockade_seas(state):
            used_seas = [sea]
    # Command-action cost is spent regardless of any Naval Blockade (Y15 tips).
    state.campaign.actions_remaining = 0 if new_act else state.campaign.actions_remaining - 1
    from plantagenet import reactions
    ctx = {"actor": lord.lord_id, "side": lord.side, "seas": used_seas}
    finish = {"lord": lord.lord_id, "target": target, "extra": extra,
              "way": way, "dorset": dorset, "fav_before": fav, "honest": honest}
    return reactions.gate(state, "uses_port_on_sea", ctx, "commands:parley_finish", finish)


def parley_finish(state: GameState, data: dict[str, Any], *, cancelled: bool) -> dict[str, Any]:
    """Resume after the Campaign Parley reaction window (4.6.4 / Y15)."""
    lord = state.lords[data["lord"]]
    target = data["target"]
    if cancelled:                       # Blockaded: no Influence paid, no Favour shift.
        return {"type": "parley", "by_lord": lord.lord_id, "target": target,
                "cancelled": True}
    chk = influence.check_influence(state, lord.lord_id, lord.side,
                                    extra_spend=data["extra"], way_cost=data["way"],
                                    discount=-1 if data.get("honest") else 0,   # Y34 +1
                                    action="parley")
    if data["dorset"]:
        chk["success"] = True
    changed = None
    if chk["success"]:
        changed = _fav_desc(target, data["fav_before"], lord.side)
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
        state.locales[target].favour = cast(Favour, side)
    elif fav == other_side(side):
        state.locales[target].favour = cast(Favour, "neutral")


def _fav_desc(target: str, before: str, side: str) -> str:
    after = side if before == "neutral" else "neutral"
    return f"{target}: {before} -> {after}"


# --------------------------------------------------------------- 4.5 Supply
def _supply_route_cost(state: GameState, here: str, source: str, side: str,
                       all_seas: bool = False, block_sea: str | None = None) -> int | None:
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
            nbrs += [p for p in port_sea if p != node
                     and not (block_sea and block_sea in (port_sea[node], port_sea[p]))]
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
    assert state.campaign is not None
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Supply requires the acting Lord at a Friendly Locale (4.5)")
    loc = lord_location(lord)
    kind, here = cast(tuple[str, str], loc)
    source = cast(str, action.get("source"))
    _require(source in state.locales, "unknown_source", f"no such Stronghold/Port {source!r}")
    _require(source not in static_data.load_exile_boxes(), "exile_not_source",
             "an Exile box is never a Supply Source (4.5.1)")
    use_ships = bool(action.get("use_ships", False))
    # Carts may be Shared from co-located Friendly Lords (1.5.3; the rule's
    # example: Share Carts to help another Lord's Supply/March).
    carts = _shared_asset(state, lord, "cart", action.get("share"))
    if ratings.has_capability(state, lord.lord_id, "HAY WAINS"):
        carts *= 2                               # Hay Wains (L8): Carts double for Supply
    is_port = bool(static_data.load_locales()[source].get("port"))

    # Exile-box Lords must Supply by Ship from a same-Sea Port (Scotland: Path).
    if kind == "exile" and here != "scotland":
        _require(use_ships and is_port and _same_sea_port_or_box(here, source),
                 "exile_needs_ship_port",
                 "an Exile-box Lord must Supply via Ship from a Port on the same Sea (4.5.1)")

    gs = ratings.has_capability(state, lord.lord_id, "GREAT SHIPS")
    blk = _live_blockade_seas(state) if lord.side == "lancastrian" else set()
    used_seas: list[str] = []

    if use_ships:
        _require(is_port, "ships_need_port", "Ship Supply requires a Port Source (4.5.1)")
        ships = _shared_asset(state, lord, "ship", action.get("share"))   # Shared (4.5.2/1.5.3)
        _require(ships > 0, "no_ships", "Ship Supply requires at least one Ship (4.5.1)")
        per_ship = 2 if gs else 1
        sea_direct = (kind == "exile" or static_data.load_locales()[here].get("port")) \
            and _same_sea_port_or_box(here, source)
        ways_out: int | None = None
        if sea_direct:
            added = ships * per_ship               # by Sea: no Carts (4.5.2)
            sea = _port_sea_map().get(source)       # Ship Supply uses the Source Port's Sea
            if sea and sea in blk:
                used_seas = [sea]
        else:
            ways = _supply_route_cost(state, here, source, lord.side, all_seas=gs)
            _require(ways is not None, "no_route", f"no Supply Route to {source} (4.5.1)")
            assert ways is not None
            added = ships * per_ship if ways == 0 else min(ships * per_ship, carts // ways)
            _require(added > 0, "insufficient_carts",
                     "need one Cart per Provender per intervening Way (4.5.1)")
            ways_out = ways
            if blk:
                used_seas = _route_used_seas(
                    ways, lambda sea: _supply_route_cost(state, here, source, lord.side,
                                                         all_seas=gs, block_sea=sea), blk)
        added = _supply_bonuses(state, lord, source, added)
        state.campaign.actions_remaining -= 1       # Command cost spent regardless (Y15)
        from plantagenet import reactions
        ctx = {"actor": lord.lord_id, "side": lord.side, "seas": used_seas}
        finish = {"lord": lord.lord_id, "source": source, "via": "ship",
                  "added": added, "ways": ways_out, "deplete": False}
        return reactions.gate(state, "uses_port_on_sea", ctx, "commands:supply_finish", finish)

    # Stronghold Source: table Provender, Cart-limited, then Deplete (4.5.2).
    _require(state.locales[source].depletion != "exhausted", "exhausted",
             f"{source} is Exhausted and may not be a Supply Source (4.5.1)")
    ways = _supply_route_cost(state, here, source, lord.side, all_seas=gs)
    _require(ways is not None, "no_route", f"no Supply Route to {source} (4.5.1)")
    assert ways is not None
    base = static_data.stronghold_yields(source).get("supply", {}).get("provender", 0)
    added = base if ways == 0 else min(base, carts // ways)
    _require(added > 0, "insufficient_carts",
             "need one Cart per Provender per intervening Way to a Source (4.5.1)")
    added = _supply_bonuses(state, lord, source, added)
    deplete = not (ratings.has_capability(state, lord.lord_id, "CHAMBERLAINS")
                   and _is_own_vassal_seat(state, lord, source))
    if blk:
        used_seas = _route_used_seas(
            ways, lambda sea: _supply_route_cost(state, here, source, lord.side,
                                                 all_seas=gs, block_sea=sea), blk)
    state.campaign.actions_remaining -= 1           # Command cost spent regardless (Y15)
    from plantagenet import reactions
    ctx = {"actor": lord.lord_id, "side": lord.side, "seas": used_seas}
    finish = {"lord": lord.lord_id, "source": source, "via": "stronghold",
              "added": added, "ways": ways, "deplete": deplete}
    return reactions.gate(state, "uses_port_on_sea", ctx, "commands:supply_finish", finish)


def supply_finish(state: GameState, data: dict[str, Any], *, cancelled: bool) -> dict[str, Any]:
    """Resume after the Supply reaction window (4.5 / Naval Blockade Y15)."""
    lord = state.lords[data["lord"]]
    source = data["source"]
    if cancelled:                       # Blockaded: no Provender gained, Source not Depleted.
        return {"type": "supply", "by_lord": lord.lord_id, "source": source,
                "cancelled": True}
    lord.assets["provender"] = lord.assets.get("provender", 0) + data["added"]
    if data["deplete"]:
        src = state.locales[source]
        src.depletion = "exhausted" if src.depletion == "depleted" else "depleted"
    out = {"type": "supply", "by_lord": lord.lord_id, "source": source,
           "via": data["via"], "provender_added": data["added"]}
    if data["ways"] is not None:
        out["ways"] = data["ways"]
    return out


def _same_sea_port_or_box(a: str, b: str) -> bool:
    seas = static_data.load_seas()
    where = {}
    for z, zone in seas["zones"].items():
        for p in zone.get("ports", []):
            where[p] = z
        for bx in zone.get("exile_boxes", []):
            where[bx] = z
    return a in where and b in where and where[a] == where[b]
