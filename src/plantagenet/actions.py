"""Action handlers for the Levy phase (Rules 3.x).

`apply_action(state, action)` validates a JSON action against the rules,
mutates the state, and returns a structured result (including any dice
rolled). Invalid actions raise `IllegalAction` with a stable code and a
rule citation.

Phase 2 scope — the Muster segment (3.4) for the active side:
  parley (3.4.1), levy_lord (3.4.2), levy_vassal (3.4.3),
  levy_transport (3.4.5), and end_muster to pass the segment to the other
  side. Two Muster actions are intentionally NOT executable yet:
    - levy_capability (3.4.6): card effects are deferred to Phase 4.
levy_troops (3.4.4) is implemented using the Strongholds table (D-004).
The full Pay (3.2) detail (Pillage yields) likewise needs the Strongholds
table and is not reachable on the first Turn (3.2 skips Pay on Turn 1).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from plantagenet import influence, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import (
    Favour,
    GameState,
    LordState,
    LordStatus,
    Side,
    VassalState,
    VassalStatus,
)

SIDES = ("lancastrian", "yorkist")


def other_side(side: str) -> str:
    return Side.YORKIST.value if side == Side.LANCASTRIAN.value else Side.LANCASTRIAN.value


# ----------------------------------------------------------------- adjacency
@lru_cache(maxsize=1)
def _adjacency() -> dict[str, list[tuple[str, str]]]:
    adj: dict[str, list[tuple[str, str]]] = {}
    for w in static_data.load_ways():
        adj.setdefault(w["from"], []).append((w["to"], w["type"]))
        adj.setdefault(w["to"], []).append((w["from"], w["type"]))
    return adj


@lru_cache(maxsize=1)
def _port_sea() -> dict[str, str]:
    """Map each Port / Exile box id -> its Sea zone id."""
    out: dict[str, str] = {}
    seas = static_data.load_seas()
    for zid, zone in seas["zones"].items():
        for p in zone.get("ports", []):
            out[p] = zid
        for b in zone.get("exile_boxes", []):
            out[b] = zid
    return out


# ----------------------------------------------------------------- helpers
def enemy_lord_at(state: GameState, locale_id: str, side: str) -> bool:
    foe = other_side(side)
    return any(v.status == LordStatus.MUSTERED and v.location == locale_id and v.side == foe
               for v in state.lords.values())


def is_friendly_stronghold(state: GameState, locale_id: str, side: str) -> bool:
    ls = state.locales.get(locale_id)
    return ls is not None and ls.favour == side


def lord_location(lord: LordState) -> tuple[str, str] | None:
    """Return ('stronghold', id) or ('exile', box) or None (not on a Locale)."""
    if lord.location is not None:
        return ("stronghold", lord.location)
    if lord.exile_box is not None:
        return ("exile", lord.exile_box)
    return None


def lord_at_friendly_locale(state: GameState, lord: LordState) -> bool:
    loc = lord_location(lord)
    if loc is None:
        return False
    kind, ident = loc
    if kind == "exile":
        return True  # Exile boxes are Friendly to Lords there (1.3.1)
    return is_friendly_stronghold(state, ident, lord.side)


# --------------------------------------------------------------- validation
def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _active_lord(state: GameState, action: dict[str, Any],
                 require_lordship: bool = True) -> LordState:
    side = action.get("side")
    _require(side in SIDES, "bad_side", "side must be 'lancastrian' or 'yorkist'")
    _require(state.levy_step == "muster", "wrong_step",
             f"Muster actions require the Muster step (3.4); step is {state.levy_step!r}")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's Muster (3.4: Rebel then King)")
    lord_id = action.get("by_lord")
    _require(lord_id in state.lords, "unknown_lord", f"no such Lord {lord_id!r}")
    lord = state.lords[lord_id]
    _require(lord.side == side, "wrong_side_lord", f"{lord_id} is not a {side} Lord")
    _require(lord.status == LordStatus.MUSTERED, "lord_not_mustered",
             f"{lord_id} is not Mustered (only on-map/in-exile Lords use Lordship, 3.4)")
    _require(lord_location(lord) is not None, "lord_not_on_locale",
             f"{lord_id} must be at a Locale to use Lordship (3.4)")
    _require(not lord.mustered_this_segment, "mustered_this_segment",
             f"{lord_id} was brought on this Muster and may not Levy (3.4)")
    if require_lordship:
        rating = _lordship(lord_id)
        _require(lord.lordship_spent < rating, "lordship_exhausted",
                 f"{lord_id} has spent all {rating} Lordship this Levy (3.4)")
    return lord


def _lordship(lord_id: str) -> int:
    return static_data.load_lords()[lord_id]["ratings"]["lordship"]


# ----------------------------------------------------------------- dispatch
def apply_action(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    atype = action.get("type")
    handler = _HANDLERS.get(atype)
    if handler is None:
        raise IllegalAction("unknown_action", f"unknown action type {atype!r}")
    result = handler(state, action)
    state.history.append({"action": action, "result": result})
    return result


# ------------------------------------------------------------- 3.4.1 Parley
def _parley_route_cost(state: GameState, start: tuple[str, str], target: str,
                       side: str, has_ship: bool, all_seas: bool = False) -> int | None:
    """Shortest Route cost in Ways from the Lord to ``target`` Stronghold.

    A Route is a chain of adjacent Locales free of Enemy Lords whose
    intermediate Strongholds are all Friendly; the target may be Neutral
    or Enemy (3.4.1). Returns the Way count, or None if no Route exists.
    Current-location Parley (target == start Locale) costs 0.
    """
    kind, start_id = start
    if target == start_id:
        return 0
    adj = _adjacency()
    port_sea = _port_sea()

    def neighbours(node: str) -> list[str]:
        out = [n for n, _t in adj.get(node, [])]
        if node in port_sea:
            if all_seas:                          # Great Ships: connect all Ports (any Sea)
                out += [p for p in port_sea if p != node]
            elif has_ship:                        # Sea hop (1.4.2): same-Sea Ports
                sea = port_sea[node]
                out += [p for p, z in port_sea.items() if z == sea and p != node]
        return out

    # BFS over Ways; expanding a node requires it to be a legal Route step.
    from collections import deque
    seen = {start_id}
    q = deque([(start_id, 0)])
    while q:
        node, dist = q.popleft()
        for nxt in neighbours(node):
            if nxt in seen:
                continue
            seen.add(nxt)
            if nxt == target:
                if enemy_lord_at(state, nxt, side):
                    continue  # target must still be reachable free of Enemy Lords
                return dist + 1
            # intermediate node: must be Friendly and free of Enemy Lords
            if enemy_lord_at(state, nxt, side) or not is_friendly_stronghold(state, nxt, side):
                continue
            q.append((nxt, dist + 1))
    return None


def _h_parley(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = _active_lord(state, action)
    loc = lord_location(lord)
    kind, here = loc
    target = action.get("target", here)
    _require(target in state.locales, "unknown_target", f"no such Stronghold {target!r}")
    extra = int(action.get("extra_spend", 0))
    has_ship = lord.assets.get("ship", 0) > 0

    own_unfriendly_here = (target == here and kind == "stronghold"
                           and not is_friendly_stronghold(state, here, lord.side))
    if own_unfriendly_here:
        way_cost = 0  # Parley at a not-yet-Friendly current location targets it only
    else:
        gs = ratings.has_capability(state, lord.lord_id, "GREAT SHIPS")
        way_cost = _parley_route_cost(state, loc, target, lord.side, has_ship, all_seas=gs)
        _require(way_cost is not None, "no_route",
                 f"no Route free of Enemy Lords (Friendly except target) to {target} (3.4.1)")

    fav = state.locales[target].favour
    _require(fav != lord.side, "already_friendly",
             f"{target} already Favours {lord.side} (3.4.1)")

    chk = influence.check_influence(state, lord.lord_id, lord.side,
                                    extra_spend=extra, way_cost=way_cost, action="parley")
    lord.lordship_spent += 1
    changed = None
    if chk["success"]:
        if fav == Favour.NEUTRAL.value:
            state.locales[target].favour = lord.side
            changed = f"{target}: neutral -> {lord.side}"
        else:  # Enemy favour -> Neutral
            state.locales[target].favour = Favour.NEUTRAL.value
            changed = f"{target}: {fav} -> neutral"
    return {"type": "parley", "by_lord": lord.lord_id, "target": target,
            "way_cost": way_cost, **chk, "favour_change": changed}


# --------------------------------------------------------- 3.4.2 Levy Lord
def _friendly_enemyfree_seat_exists(state: GameState, side: str) -> str | None:
    lords = static_data.load_lords()
    for lid, lord in state.lords.items():
        if lord.side != side:
            continue
        seat = lords[lid]["seat"]
        if is_friendly_stronghold(state, seat, side) and not enemy_lord_at(state, seat, side):
            return seat
    return None


def _h_levy_lord(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = _active_lord(state, action)
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Levy Lord requires the acting Lord at a Friendly Locale (3.4.2)")
    target_id = action.get("target")
    _require(target_id in state.lords, "unknown_target", f"no such Lord {target_id!r}")
    target = state.lords[target_id]
    _require(target.side == lord.side, "target_wrong_side",
             f"{target_id} is not a {lord.side} Lord")
    _require(target.status == LordStatus.CALENDAR and target.calendar_box is not None
             and target.calendar_box <= state.turn_box, "target_not_ready",
             f"{target_id} is not Ready (cylinder on the Calendar in the current or a "
             "lower Turn box) (3.4.2)")
    seat = static_data.load_lords()[target_id]["seat"]
    seat_free = not enemy_lord_at(state, seat, lord.side)
    fallback = None if seat_free else _friendly_enemyfree_seat_exists(state, lord.side)
    _require(seat_free or fallback is not None, "no_seat",
             f"{target_id}'s Seat is not free of Enemy Lords and the side has no Friendly, "
             "Enemy-free Seat to Muster at (3.4.2)")

    extra = int(action.get("extra_spend", 0))
    chk = influence.check_influence(state, lord.lord_id, lord.side, extra_spend=extra,
                                    action="levy")
    lord.lordship_spent += 1
    if chk["success"]:
        place_at = seat if seat_free else fallback
        statics = static_data.load_lords()[target_id]
        target.status = LordStatus.MUSTERED
        target.location = place_at
        target.calendar_box = None
        target.calendar_exile = False
        target.forces = dict(statics.get("forces", {}))
        target.assets = dict(statics.get("assets", {}))
        target.mustered_this_segment = True
        if seat_free and state.locales[seat].favour != lord.side:
            state.locales[seat].favour = lord.side
    return {"type": "levy_lord", "by_lord": lord.lord_id, "target": target_id, **chk}


# -------------------------------------------------------- 3.4.3 Levy Vassal
def _loyalty_mod(vid: str, side: str) -> int:
    loy = static_data.load_vassals()["regular"][vid].get("loyalty")
    if not loy:
        return 0
    colour_side = {"red": "lancastrian", "white": "yorkist"}[loy["color"]]
    return loy["value"] if colour_side == side else -loy["value"]


def _h_levy_vassal(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = _active_lord(state, action)
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Levy Vassal requires the acting Lord at a Friendly Locale (3.4.3)")
    vid = action.get("target")
    regular = static_data.load_vassals()["regular"]
    _require(vid in regular, "unknown_vassal", f"no such regular Vassal {vid!r}")
    vstate = state.vassals.get(vid)
    _require(vstate is not None and vstate.status == VassalStatus.AT_SEAT,
             "vassal_not_at_seat", f"{vid}'s markers must be on the map at its Seat (3.4.3)")
    seat = regular[vid]["seat"]
    _require(is_friendly_stronghold(state, seat, lord.side), "seat_not_friendly",
             f"{vid}'s Seat {seat} must be Friendly to the Levying side (3.4.3)")
    _require(not enemy_lord_at(state, seat, lord.side), "seat_has_enemy",
             f"{vid}'s Seat {seat} must be free of Enemy Lords (3.4.3)")

    extra = int(action.get("extra_spend", 0))
    chk = influence.check_influence(state, lord.lord_id, lord.side, extra_spend=extra,
                                    loyalty_mod=_loyalty_mod(vid, lord.side), action="levy")
    if ratings.has_capability(state, lord.lord_id, "TWO ROSES"):
        chk["success"] = True              # L32 (Henry Tudor): Vassal Levy always succeeds
    lord.lordship_spent += 1
    if chk["success"]:
        service = regular[vid]["service"]
        box = state.turn_box + service
        if ratings.has_capability(state, lord.lord_id, "ALICE MONTAGU"):
            box = min(15, box + 1)              # Y17: +1 Service (capped at box 15)
        state.vassals[vid] = VassalState(
            vassal_id=vid, status=VassalStatus.MUSTERED, on_lord=lord.lord_id,
            service_box=box)
        if vid not in lord.vassals:
            lord.vassals.append(vid)
    return {"type": "levy_vassal", "by_lord": lord.lord_id, "target": vid,
            "loyalty_mod": _loyalty_mod(vid, lord.side), **chk}


# ----------------------------------------------------- 3.4.5 Levy Transport
def _ships_in_play(state: GameState) -> int:
    return sum(1 for v in state.lords.values()
               if v.status == LordStatus.MUSTERED and v.assets.get("ship", 0) > 0)


def _h_levy_transport(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = _active_lord(state, action)
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Levy Transport requires the acting Lord at a Friendly Locale (3.4.5)")
    kind = action.get("transport", "cart")
    _require(kind in ("cart", "ship"), "bad_transport", "transport must be 'cart' or 'ship'")
    if kind == "cart":
        lord.assets["cart"] = lord.assets.get("cart", 0) + 2
        lord.lordship_spent += 1
        return {"type": "levy_transport", "by_lord": lord.lord_id, "added": "2 cart"}
    # Ship requirements (3.4.5)
    loc = lord_location(lord)
    at_port_or_exile = loc[0] == "exile" or static_data.load_locales()[loc[1]].get("port")
    _require(at_port_or_exile, "not_port",
             "Ship Levy requires a Friendly Port or Exile box (3.4.5)")
    _require(_ships_in_play(state) < 9, "ship_limit",
             "fewer than nine Lords on both sides may have Ships (3.4.5)")
    _require(lord.assets.get("ship", 0) < 2, "two_ships",
             "a Lord may not exceed two Ships (1.7.3, 3.4.5)")
    lord.assets["ship"] = lord.assets.get("ship", 0) + 1
    lord.lordship_spent += 1
    return {"type": "levy_transport", "by_lord": lord.lord_id, "added": "1 ship"}


# ------------------------------------------------ deferred Muster actions
def _troops_in_play(state: GameState, force_id: str) -> int:
    """Count wooden Troop pieces of ``force_id`` currently on all Lord mats."""
    return sum(v.forces.get(force_id, 0) for v in state.lords.values())


def _is_own_vassal_seat(state: GameState, lord, locale: str) -> bool:
    regular = static_data.load_vassals()["regular"]
    return any(regular.get(v, {}).get("seat") == locale for v in lord.vassals)


def _h_levy_troops(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Levy Troops (3.4.4): add the Stronghold's listed Troops, then Deplete
    (or Exhaust if already Depleted). No Influence check. Pool-limited (1.6)."""
    pre = state.lords.get(action.get("by_lord"))
    stanley_free = (pre is not None and "thomas_stanley" in pre.special_vassals
                    and not pre.free_troops_used)
    lord = _active_lord(state, action, require_lordship=not stanley_free)
    loc = lord_location(lord)
    _require(loc[0] == "stronghold", "in_exile_box",
             "Levy Troops requires a Stronghold, not an Exile box (3.4.4)")
    here = loc[1]
    _require(is_friendly_stronghold(state, here, lord.side), "not_friendly_locale",
             "Levy Troops requires a Friendly Stronghold (3.4.4)")
    ls = state.locales[here]
    _require(ls.depletion != "exhausted", "exhausted",
             f"{here} is Exhausted and may not be Levied for Troops (3.4.4)")
    rising_wages = ratings.event_against(state, "RISING WAGES", lord.side)
    if rising_wages:                          # L9: pay 1 Coin per Levy Troops action
        _require(lord.assets.get("coin", 0) >= 1, "rising_wages_no_coin",
                 "Rising Wages requires 1 Coin per Levy Troops action (L9)")

    if ratings.has_capability(state, lord.lord_id, "BELOVED WARWICK"):
        yields = {"militia": 5}                 # Y16: 5 Militia instead of the table
    else:
        yields = dict(static_data.stronghold_yields(here)["levy_troops"])
    if lord.side == "yorkist" and ratings.event_active(state, "THE COMMONS"):
        commons = int(action.get("commons_extra", 0))   # Y16 Event: up to +2 Militia
        _require(0 <= commons <= 2, "bad_commons", "The Commons adds 0-2 Militia (Y16)")
        if commons:
            yields["militia"] = yields.get("militia", 0) + commons
    sof = bool(action.get("soldiers_of_fortune"))        # Y12 Capability
    if sof:
        _require(ratings.has_capability(state, lord.lord_id, "SOLDIERS OF FORTUNE"),
                 "no_soldiers_of_fortune", f"{lord.lord_id} lacks Soldiers of Fortune (Y12)")
        _require(lord.assets.get("coin", 0) >= 1, "no_coin",
                 "Soldiers of Fortune costs 1 Coin (Y12)")
        yields["mercenaries"] = yields.get("mercenaries", 0) + 2
    forces_static = static_data.load_forces()
    added: dict[str, int] = {}
    for unit, amount in yields.items():
        pool = forces_static[unit].get("pool", 0)
        free = pool - _troops_in_play(state, unit)
        give = max(0, min(amount, free))   # "as able" (1.6): pool limits Muster
        if give:
            lord.forces[unit] = lord.forces.get(unit, 0) + give
            added[unit] = give
    if sof:
        lord.assets["coin"] = lord.assets.get("coin", 0) - 1
    # Deplete, or Exhaust if already Depleted -- unless a no-Deplete Capability
    # applies: Quartermasters (L9), Woodvilles (Y31), Chamberlains (L10) at a
    # Vassal's Seat (3.4.4 / 1.9.1).
    no_deplete = (ratings.has_capability(state, lord.lord_id, "QUARTERMASTERS")
                  or ratings.has_capability(state, lord.lord_id, "WOODVILLES")
                  or (ratings.has_capability(state, lord.lord_id, "CHAMBERLAINS")
                      and _is_own_vassal_seat(state, lord, here)))
    if not no_deplete:
        ls.depletion = "exhausted" if ls.depletion == "depleted" else "depleted"
    if stanley_free:
        lord.free_troops_used = True       # Thomas Stanley: 0 Lordship, once/Levy (L35)
    else:
        lord.lordship_spent += 1
    if rising_wages:
        lord.assets["coin"] = lord.assets.get("coin", 0) - 1
    return {"type": "levy_troops", "by_lord": lord.lord_id, "locale": here,
            "added": added, "depletion": ls.depletion, "stanley_free": stanley_free}


def _capabilities_in_play(state: GameState, side: str) -> set[str]:
    """Card ids whose Capability is currently on one of ``side``'s Lord mats."""
    out: set[str] = set()
    for v in state.lords.values():
        if v.side == side:
            out.update(v.capabilities)
    return out


def _capability_eligible(card_id: str, lord_id: str) -> bool:
    """Whether ``lord_id`` may Levy the Capability on ``card_id`` (Livery
    Badges, 3.4.6). 'Any' -> any Lord of the side; a Special-Vassal
    Capability -> its eligible Lords; otherwise match the Lord's base name."""
    cap = static_data.load_cards()[card_id]["capability"]
    lords_txt = cap.get("lords") or ""
    if "Any" in lords_txt:
        return True
    for v in static_data.load_vassals()["special"].values():
        if v.get("capability_card") == card_id:
            return lord_id in v.get("eligible_lords", [])
    if not lords_txt:
        return True   # eligibility not stated in the reference -> permit
    base = static_data.load_lords()[lord_id]["name"].split(" (")[0]
    return base in lords_txt


def _h_levy_capability(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Levy Capability (3.4.6): a Lord at a Friendly Locale obtains one unused
    Capability card it is eligible to Levy, to a maximum of two per mat and
    no two of the same name. The card is tracked on the mat; its mechanical
    effect is applied by the consumer until implemented in a later increment."""
    lord = _active_lord(state, action)
    _require(lord_at_friendly_locale(state, lord), "not_friendly_locale",
             "Levy Capability requires the acting Lord at a Friendly Locale (3.4.6)")
    card_id = action.get("card")
    cards = static_data.load_cards()
    _require(card_id in cards and cards[card_id]["side"] == lord.side, "unknown_card",
             f"{card_id!r} is not a {lord.side} Arts of War card")
    deck = static_data.scenario_card_deck(state.scenario, lord.side)
    _require(not deck or card_id in deck, "card_not_in_scenario",
             f"{card_id} is not in this scenario's deck (6.0)")
    _require(card_id not in _capabilities_in_play(state, lord.side), "card_in_play",
             f"{card_id} is already in play (3.4.6)")
    _require(_capability_eligible(card_id, lord.lord_id), "ineligible_lord",
             f"{lord.lord_id} may not Levy the {cards[card_id]['capability']['title']} "
             "Capability (3.4.6)")
    _require(len(lord.capabilities) < 2, "two_capabilities",
             "a Lord may hold only two Capability cards (3.4.6)")
    new_title = cards[card_id]["capability"]["title"]
    _require(all(cards[c]["capability"]["title"] != new_title for c in lord.capabilities),
             "duplicate_capability", f"{lord.lord_id} already has a {new_title} Capability (3.4.6)")
    lord.capabilities.append(card_id)
    lord.lordship_spent += 1
    sv = _muster_special_vassal(state, lord, card_id)
    return {"type": "levy_capability", "by_lord": lord.lord_id, "card": card_id,
            "title": new_title, "special_vassal": sv}


def _muster_special_vassal(state: GameState, lord, card_id: str) -> str | None:
    """If ``card_id`` is a Special-Vassal Capability, Muster the Vassal free to
    this Lord (1.5.4, 3.4.6) and apply any one-time Force addition (e.g.
    Hastings adds 2 Men-at-Arms, pool-limited)."""
    specials = static_data.load_vassals()["special"]
    for vid, sv in specials.items():
        if sv.get("capability_card") == card_id:
            if vid not in lord.special_vassals:
                lord.special_vassals.append(vid)
            add = sv.get("modifiers", {}).get("add_forces", {})
            forces_static = static_data.load_forces()
            for unit, amount in add.items():
                in_play = sum(v.forces.get(unit, 0) for v in state.lords.values())
                free = forces_static[unit].get("pool", 0) - in_play
                give = max(0, min(amount, free))
                if give:
                    lord.forces[unit] = lord.forces.get(unit, 0) + give
            return vid
    return None


# ------------------------------------------------------------- end_muster
def _h_end_muster(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = action.get("side")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's Muster")
    _require(state.levy_step == "muster", "wrong_step", "not in the Muster step")
    # Reset this side's per-Levy Muster bookkeeping.
    for v in state.lords.values():
        if v.side == side:
            v.mustered_this_segment = False
    rebel = [s for s, r in state.roles.items() if r == "rebel"][0]
    king = [s for s, r in state.roles.items() if r == "king"][0]
    if side == rebel:
        state.active_side = king
        return {"type": "end_muster", "next": "king_muster"}
    state.levy_step = "done"
    state.active_events = [e for e in state.active_events if e.get("scope") != "this_levy"]
    return {"type": "end_muster", "next": "levy_complete"}


def _campaign_handler(name):
    # Imported lazily to avoid a circular import (campaign imports actions).
    from plantagenet import campaign
    return getattr(campaign, name)


def _command_handler(name):
    from plantagenet import commands
    return getattr(commands, name)


def _parley_dispatch(state, action):
    # "Parley" exists in both phases (3.4.1 Levy / 4.6.4 Campaign).
    if state.phase == "campaign":
        from plantagenet import commands
        return commands.parley_campaign(state, action)
    return _h_parley(state, action)


_HANDLERS = {
    "begin_campaign": lambda st, a: _campaign_handler("begin_campaign")(st, a),
    "build_plan": lambda st, a: _campaign_handler("build_plan")(st, a),
    "forage": lambda st, a: _campaign_handler("forage")(st, a),
    "pass": lambda st, a: _campaign_handler("pass_command")(st, a),
    "end_activation": lambda st, a: _campaign_handler("end_activation")(st, a),
    "end_campaign": lambda st, a: _campaign_handler("end_campaign")(st, a),
    "march": lambda st, a: _command_handler("march")(st, a),
    "sail": lambda st, a: _command_handler("sail")(st, a),
    "tax": lambda st, a: _command_handler("tax")(st, a),
    "supply": lambda st, a: _command_handler("supply")(st, a),
    "agitators": lambda st, a: _command_handler("agitators")(st, a),
    "merchants": lambda st, a: _command_handler("merchants")(st, a),
    "heralds": lambda st, a: _command_handler("heralds")(st, a),
    "parley": _parley_dispatch,
    "levy_lord": _h_levy_lord,
    "levy_vassal": _h_levy_vassal,
    "levy_transport": _h_levy_transport,
    "levy_troops": _h_levy_troops,
    "levy_capability": _h_levy_capability,
    "end_muster": _h_end_muster,
    "pay": lambda st, a: __import__("plantagenet.pay", fromlist=["pay"]).pay(st, a),
    "draw": lambda st, a: __import__("plantagenet.arts_of_war", fromlist=["draw"]).draw(st, a),
}
