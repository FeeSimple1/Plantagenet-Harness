"""Immediate Arts of War Event effects (1.9.1), resolved via the ``play_event``
action with a ``decisions`` payload for any targeting choices.

Each resolver is keyed by card id and takes (state, side, decisions) -> dict.
Hold and This-Levy/This-Campaign Events are handled elsewhere (held pile /
active_events + per-handler hooks); this module covers the "immediate" type.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any, cast

from plantagenet import influence, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import Favour, GameState, LordState, LordStatus, VassalStatus

_OTHER = {"yorkist": "lancastrian", "lancastrian": "yorkist"}
EVENT_INFLUENCE_SPENDS = (0, 1, 3)


def _require(cond: object, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _on_map(state: GameState, side: str) -> list[tuple[str, LordState]]:
    return [(lid, ls) for lid, ls in state.lords.items()
            if ls.side == side and ls.status == LordStatus.MUSTERED]


def _pool_add(state: GameState, lord: LordState, unit: str, amount: int) -> int:
    from plantagenet.actions import _troops_in_play
    pool = static_data.load_forces()[unit].get("pool", 0)
    give: int = max(0, min(amount, pool - _troops_in_play(state, unit)))
    if give:
        lord.forces[unit] = lord.forces.get(unit, 0) + give
    return give


def _region_locales(region: str) -> list[str]:
    return [k for k, v in static_data.load_locales().items()
            if isinstance(v, dict) and v.get("region") == region]


# --------------------------------------------------------------- resolvers
# Y23
def _charles_the_bold(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    for _lid, ls in _on_map(state, "yorkist"):
        ls.assets["coin"] = ls.assets.get("coin", 0) + 1
        ls.assets["provender"] = ls.assets.get("provender", 0) + 1
    return {"granted": "1 Coin + 1 Provender to each Yorkist Lord"}


# L30
def _french_war_loans(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    for _lid, ls in _on_map(state, "lancastrian"):
        ls.assets["coin"] = ls.assets.get("coin", 0) + 1
        ls.assets["provender"] = ls.assets.get("provender", 0) + 1
    return {"granted": "1 Coin + 1 Provender to each Lancastrian Lord"}


# Y31: up to 2 Militia each
def _earl_rivers(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    add: dict[str, int] = {}
    per = d.get("militia", {})
    for lid, ls in _on_map(state, "yorkist"):
        n = int(per.get(lid, 2))
        _require(0 <= n <= 2, "bad_militia", "Earl Rivers adds 0-2 Militia per Lord (Y31)")
        g = _pool_add(state, ls, "militia", n)
        if g:
            add[lid] = g
    return {"militia_added": add}


# L14: up to 1 MaA + 1 Militia
def _scots(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    """Select each Mustered Lancastrian once, including Lords in Exile boxes.

    Use lords to request both types on the listed mats, or reinforcements to
    map Lord IDs to explicit 0 or 1 counts of men_at_arms and militia.
    Omit both fields to request both types for every eligible Lord.
    """
    _require(isinstance(d, dict), "bad_event_decisions", "decisions must be an object")
    eligible = {lid: lord for lid, lord in state.lords.items()
                if lord.side == side and lord.status in (LordStatus.MUSTERED, LordStatus.EXILE)}
    units = ("men_at_arms", "militia")
    if "reinforcements" in d:
        _require("lords" not in d, "bad_event_decisions",
                 "choose lords or reinforcements for Scots (L14)")
        requested = d.get("reinforcements")
        if not isinstance(requested, dict):
            raise IllegalAction("bad_event_decisions",
                                "reinforcements must map Lords to Troop counts (L14)")
    else:
        selected = d.get("lords", list(eligible))
        _require(isinstance(selected, list) and all(isinstance(lid, str) for lid in selected),
                 "bad_event_decisions", "lords must be a list of Lord IDs (L14)")
        _require(len(selected) == len(set(selected)), "duplicate_lords",
                 "name each Scots recipient only once (L14)")
        requested = {lid: dict.fromkeys(units, 1) for lid in selected}

    for lid, counts in requested.items():
        _require(lid in eligible, "bad_lord", "name a Mustered Lancastrian Lord (L14)")
        _require(isinstance(counts, dict) and all(
            unit in units and type(count) is int and count in (0, 1)
            for unit, count in counts.items()
        ), "bad_event_decisions", "Scots grants 0 or 1 of each listed Troop type (L14)")
    add = {lid: {unit: _pool_add(state, eligible[lid], unit, counts.get(unit, 0))
                 for unit in units}
           for lid, counts in requested.items()}
    return {"added": add}


# L22: a Lord at a Port (optional)
def _french_troops(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    locales = static_data.load_locales()
    at_port = [lid for lid, ls in _on_map(state, "lancastrian")
               if ls.location in locales and locales[ls.location].get("port")]
    if not at_port:                                          # "No effect if no ... at a Port"
        return {"no_effect": "no Lancastrian Lord at a Port (L22)"}
    lid = d.get("lord")
    if lid is None:                                          # Optional: declined
        return {"no_effect": "declined (L22 is optional)"}
    ls = state.lords.get(lid)
    _require(ls is not None and ls.side == "lancastrian"
             and ls.status == LordStatus.MUSTERED, "bad_lord", "name a Lancastrian Lord (L22)")
    assert ls is not None
    _require(ls.location in locales and bool(locales[ls.location].get("port")),
             "not_port", "French Troops reinforce a Lancastrian Lord at a Port (L22)")
    a = _pool_add(state, ls, "men_at_arms", min(2, int(d.get("men_at_arms", 2))))
    b = _pool_add(state, ls, "militia", min(2, int(d.get("militia", 2))))
    return {"lord": lid, "men_at_arms": a, "militia": b}


# Y27
def _yorkist_north(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    north = _region_locales("north")
    strongholds = sum(1 for loc in north if state.locales[loc].favour == "yorkist")
    lords = sum(1 for lid, ls in _on_map(state, "yorkist") if ls.location in north)
    influence.gain_influence(state, "yorkist", strongholds + lords)
    return {"influence": strongholds + lords}


# L15
def _henry_pressures_parliament(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    from plantagenet.state import LordStatus, VassalStatus
    n = sum(1 for v in state.vassals.values() if v.status == VassalStatus.MUSTERED
            and state.lords.get(v.on_lord or "") is not None
            and state.lords[cast(str, v.on_lord)].side == "yorkist")
    # Special Vassals (e.g. Hastings Y24) live on the Lord's mat, not state.vassals.
    n += sum(len(ld.special_vassals) for ld in state.lords.values()
             if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED)
    influence.spend_influence(state, "yorkist", n)
    return {"yorkist_influence_lost": n}


# L26
def _henry_released(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    gained = 0
    if state.locales["london"].favour == "lancastrian":
        influence.gain_influence(state, "lancastrian", 5)
        gained = 5
    return {"lancastrian_influence": gained}


# Y15
def _london_for_york(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    lon = state.locales["london"]
    added = False
    if lon.favour == "yorkist" and lon.favour_extra == 0:   # "If already two, no effect"
        lon.favour_extra += 1
        added = True
    return {"second_favour": added}


# Y21
def _sir_richard_leigh(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    lon = state.locales["london"]
    if lon.favour == "lancastrian":
        if lon.favour_extra > 0:
            lon.favour_extra -= 1
        else:
            lon.favour = cast(Favour, Favour.NEUTRAL.value)
        return {"london": "lancastrian favour removed"}
    if lon.favour == Favour.NEUTRAL.value:
        lon.favour = cast(Favour, "yorkist")
        return {"london": "yorkist favour placed"}
    return {"london": "no change"}


# Y17: shift Yorkist Vassals +1
def _she_wolf(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    from plantagenet.state import VassalStatus
    shifted: list[str] = []
    for vid, v in state.vassals.items():
        if (v.status == VassalStatus.MUSTERED and v.service_box is not None
                and state.lords.get(v.on_lord or "") is not None
                and state.lords[cast(str, v.on_lord)].side == "yorkist"):
            v.service_box = v.service_box + 1   # may go off-calendar past box 15 (2.2.3)
            shifted.append(vid)
    return {"shifted": shifted}


# L19: Yorkist Vassals -> current Turn
def _henrys_proclamation(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    from plantagenet.state import VassalStatus
    shifted: list[str] = []
    for vid, v in state.vassals.items():
        if (v.status == VassalStatus.MUSTERED and v.service_box is not None
                and state.lords.get(v.on_lord or "") is not None
                and state.lords[cast(str, v.on_lord)].side == "yorkist"):
            v.service_box = state.turn_box
            shifted.append(vid)
    return {"shifted": shifted}


def _at_stronghold_or_exile(lord: LordState | None) -> bool:
    return (lord is not None and lord.status in (LordStatus.MUSTERED, LordStatus.EXILE)
            and (lord.location is not None or lord.exile_box is not None))


def _event_extra_spend(extra: Any) -> int:
    if type(extra) is not int or extra not in EVENT_INFLUENCE_SPENDS:
        raise IllegalAction("bad_extra_spend", "choose 0, 1, or 3 extra Influence (1.4.2)")
    return extra


# Y26
def dubious_clarence_available(state: GameState) -> bool:
    return all(_at_stronghold_or_exile(state.lords.get(lid))
               for lid in ("edward_iv", "clarence"))


def _dubious_clarence(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    _require(d.keys() <= {"extra_spend"}, "bad_event_decisions",
             "use extra_spend to elect Edward IV's Influence check (Y26)")
    if not dubious_clarence_available(state):
        return {"no_effect": "requires Edward IV and Clarence on the map (Y26)"}
    if "extra_spend" not in d:
        return {"no_effect": "York declined the Influence check (Y26)"}
    chk = influence.check_influence(state, "edward_iv", side,
                                    extra_spend=_event_extra_spend(d.get("extra_spend")))
    if chk["success"]:
        from plantagenet import campaign
        clarence = state.lords["clarence"]
        campaign._disband_lord(state, clarence, from_exile=clarence.exile_box is not None)
    return {"disbanded": chk["success"], **chk}


# L27
def aragne_vassal_owners(state: GameState) -> dict[str, str]:
    lords = {lid: lord for lid, lord in state.lords.items()
             if lord.side == "yorkist" and lord.status in (LordStatus.MUSTERED, LordStatus.EXILE)}
    owners = {vid: v.on_lord for vid, v in state.vassals.items()
              if v.status == VassalStatus.MUSTERED and v.on_lord is not None
              and v.on_lord in lords}
    owners.update({vid: lid for lid, lord in lords.items() for vid in lord.special_vassals})
    return owners


def aragne_next_check(event: dict[str, Any]) -> dict[str, str]:
    response = event["aragne"]
    return cast(dict[str, str], response["targets"][len(response["checks"])])


def _luniverselle_aragne(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    if side == "yorkist":
        return _aragne_influence_check(state, side, d)

    _require(d.keys() <= {"vassals"}, "bad_event_decisions",
             "Lancaster selects the Vassals. York chooses spending for each check (L27)")
    owners = aragne_vassal_owners(state)
    need = min(2, len(owners))
    targets = d.get("vassals", [])
    _require(isinstance(targets, list) and all(isinstance(vid, str) for vid in targets)
             and len(targets) == len(set(targets)) == need, "bad_targets",
             f"L'Universelle Aragne requires {need} distinct Yorkist Mustered Vassals (L27)")
    _require(all(vid in owners for vid in targets), "bad_vassal",
             "select only Yorkist Mustered Vassals (L27)")
    if not targets:
        return {"no_effect": "no Yorkist Mustered Vassals (L27)"}
    state.pending_events[0]["aragne"] = {
        "targets": [{"vassal": vid, "lord": owners[vid]} for vid in targets],
        "checks": [],
    }
    return {"vassals": targets, "awaiting_side": "yorkist"}


def _aragne_influence_check(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    from plantagenet import actions, campaign

    _require(d.keys() <= {"vassal", "extra_spend"}, "bad_event_decisions",
             "name the pending Vassal and choose extra Influence (L27)")
    event = state.pending_events[0]
    response = event["aragne"]
    target = aragne_next_check(event)
    vid, lid = target["vassal"], target["lord"]
    _require(d.get("vassal") == vid, "bad_event_target", f"the pending check is for {vid} (L27)")
    regular = vid in state.vassals
    chk = influence.check_influence(
        state, lid, side, extra_spend=_event_extra_spend(d.get("extra_spend")),
        loyalty_mod=actions._loyalty_mod(vid, side) if regular else 0,
    )
    if not chk["success"]:
        lord = state.lords[lid]
        if regular:
            campaign._disband_vassal(state, vid)
            lord.vassals = [v for v in lord.vassals if v != vid]
        else:
            campaign._disband_special_vassal(state, lord, vid)
    checks = response["checks"]
    checks.append({"vassal": vid, "disbanded": not chk["success"], **chk})
    result: dict[str, Any] = {"checks": [dict(check) for check in checks]}
    if len(checks) < len(response["targets"]):
        result["awaiting_side"] = "yorkist"
    return result


# L23/L24
def propaganda_strongholds(state: GameState) -> list[str]:
    return sorted(loc for loc, ls in state.locales.items() if ls.favour == "yorkist")


def propaganda_next_stronghold(event: dict[str, Any]) -> str:
    response = event["propaganda"]
    return cast(str, response["targets"][len(response["results"])])


def _warwicks_propaganda(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    if side == "yorkist":
        return _propaganda_response(state, side, d)
    _require(d.keys() <= {"strongholds"}, "bad_event_decisions",
             "Lancaster selects Strongholds; York chooses whether to pay (L23/L24)")
    available = propaganda_strongholds(state)
    if not available:                                        # "No effect if no ... Favour"
        return {"no_effect": "no Yorkist Favour to target (L23/L24)"}
    need = min(3, len(available))                            # "Select 3 ... or all if fewer"
    targets = d.get("strongholds", [])
    _require(isinstance(targets, list) and all(isinstance(loc, str) for loc in targets)
             and len(targets) == len(set(targets)) == need, "bad_count",
             f"Warwick's Propaganda selects {need} distinct Yorkist Strongholds (L23/L24)")
    _require(all(loc in available for loc in targets), "not_yorkist",
             "select only Strongholds with Yorkist Favour (L23/L24)")
    state.pending_events[0]["propaganda"] = {"targets": list(targets), "results": []}
    return {"strongholds": targets, "awaiting_side": "yorkist"}


def _propaganda_response(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    _require(d.keys() <= {"stronghold", "choice"}, "bad_event_decisions",
             "York chooses pay or remove for the pending Stronghold (L23/L24)")
    response = state.pending_events[0]["propaganda"]
    loc = propaganda_next_stronghold(state.pending_events[0])
    _require(d.get("stronghold") == loc, "bad_event_target",
             f"Warwick's Propaganda awaits York's response for {loc} (L23/L24)")
    choice = d.get("choice")
    _require(choice in ("pay", "remove"), "bad_event_decisions",
             "choose pay or remove (L23/L24)")
    if choice == "pay":
        influence.spend_influence(state, side, 2)
        outcome = "paid 2 Influence"
    else:
        locale = state.locales[loc]
        if locale.favour_extra > 0:
            locale.favour_extra -= 1
        else:
            locale.favour = cast(Favour, Favour.NEUTRAL.value)
        outcome = "Favour removed"
    response["results"].append({loc: outcome})
    result: dict[str, Any] = {"results": list(response["results"])}
    if len(response["results"]) < len(response["targets"]):
        result["awaiting_side"] = "yorkist"
    return result


# L25
def welsh_rebellion_options(state: GameState) -> dict[str, Any]:
    """Return the eligible pieces and required counts for the current branch."""
    wales = _region_locales("wales")
    troop_types = [unit for unit, data in static_data.load_forces().items() if "pool" in data]
    troops = {}
    for lid, lord in _on_map(state, "yorkist"):
        if lord.location in wales:
            available = {unit: lord.forces[unit] for unit in troop_types
                         if lord.forces.get(unit, 0) > 0}
            troops[lid] = {"available": available, "remove": min(2, sum(available.values()))}
    if troops:
        return {"troops": troops}
    markers = {loc: 1 + state.locales[loc].favour_extra for loc in wales
               if state.locales[loc].favour == "yorkist"}
    return {"strongholds": {"available": markers, "remove": min(2, sum(markers.values()))}}


def _rebellion_default(available: dict[str, int]) -> list[str]:
    selected: list[str] = []
    for item, count in available.items():
        selected.extend([item] * min(count, 2 - len(selected)))
        if len(selected) == 2:
            break
    return selected


def _rebellion_removals(selection: Any, options: dict[str, Any], target: str) -> Counter[str]:
    _require(isinstance(selection, list) and all(isinstance(item, str) for item in selection),
             "bad_event_decisions", f"choose {target} as a list of IDs (L25)")
    need = options["remove"]
    _require(len(selection) == need, "bad_count", f"select {need} {target} (L25)")
    counts = Counter(selection)
    _require(all(count <= options["available"].get(item, 0) for item, count in counts.items()),
             "bad_event_target", f"select only available {target} (L25)")
    return counts


def _welsh_rebellion(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    options = welsh_rebellion_options(state)
    _require(isinstance(d, dict) and d.keys() <= options.keys(), "bad_event_decisions",
             "choose only the applicable Welsh Rebellion branch (L25)")
    if "troops" in options:
        eligible = options["troops"]
        requested = d.get("troops", {lid: _rebellion_default(spec["available"])
                                     for lid, spec in eligible.items()})
        _require(isinstance(requested, dict) and requested.keys() == eligible.keys(),
                 "bad_event_target", "select Troops for each Yorkist Lord in Wales (L25)")
        removals = {lid: _rebellion_removals(requested[lid], spec, f"Troops from {lid}")
                    for lid, spec in eligible.items()}
        for lid, units in removals.items():
            for unit, count in units.items():
                state.lords[lid].forces[unit] -= count

        # A Lord left with only Retinue and Vassals immediately Disbands.
        from plantagenet import campaign
        removed = {lid: sum(units.values()) for lid, units in removals.items()}
        disbanded = [lid for lid, spec in eligible.items()
                     if removed[lid] == sum(spec["available"].values())]
        for lid in disbanded:
            campaign._disband_lord(state, state.lords[lid])
        out: dict[str, Any] = {"troops_removed": removed}
        if disbanded:
            out["disbanded"] = disbanded
        return out

    markers = options["strongholds"]
    strongholds = d.get("strongholds", _rebellion_default(markers["available"]))
    removed_markers = _rebellion_removals(strongholds, markers, "Yorkist Favour markers in Wales")
    for loc, count in removed_markers.items():
        locale = state.locales[loc]
        if count > locale.favour_extra:
            locale.favour = cast(Favour, Favour.NEUTRAL.value)
        locale.favour_extra = max(0, locale.favour_extra - count)
    return {"favour_removed": len(strongholds)}


# L29
def wilful_disobedience_targets(state: GameState) -> list[str]:
    from plantagenet.actions import _adjacency

    adjacency = _adjacency()
    exile_boxes = static_data.load_exile_boxes()
    near: dict[str, set[str]] = {side: set() for side in _OTHER}
    for lord in state.lords.values():
        if not _at_stronghold_or_exile(lord):
            continue
        if lord.location is not None:
            near[lord.side].add(lord.location)
            near[lord.side].update(loc for loc, _kind in adjacency.get(lord.location, []))
        elif lord.exile_box is not None:
            near[lord.side].update(exile_boxes.get(lord.exile_box, {}).get("land_exits", []))
    return [loc for loc, locale in state.locales.items() if locale.favour == "yorkist"
            and loc in near["lancastrian"] and loc not in near["yorkist"]]


def _to_wilful_disobedience(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    _require(d.keys() <= {"strongholds"}, "bad_event_decisions",
             "choose only strongholds for the Favour removals (L29)")
    eligible = wilful_disobedience_targets(state)
    need = min(2, len(eligible))
    targets = d.get("strongholds", eligible if len(eligible) == need else None)
    if (not isinstance(targets, list) or not all(isinstance(loc, str) for loc in targets)
            or len(targets) != need or len(set(targets)) != need):
        raise IllegalAction("bad_count",
                            f"select {need} distinct eligible Yorkist Strongholds (L29)")
    _require(all(loc in eligible for loc in targets), "bad_target",
             "each Stronghold must have Yorkist Favour and be near Lancaster but not York (L29)")
    for loc in targets:
        state.locales[loc].favour = Favour.NEUTRAL
        state.locales[loc].favour_extra = 0
    if targets and "track" in state.influence:
        from plantagenet.scenarios import _recompute_stronghold_markers
        _recompute_stronghold_markers(state)
    return {"removed": targets}


# L31
def _robins_rebellion(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    """L31 ROBIN'S REBELLION: the playing side may, in the North only, remove the
    Enemy's Favour (-> neutral) and/or place its OWN Favour on a *neutral*
    Stronghold -- up to 3 markers total. It may not place the Enemy's Favour, nor
    flip an Enemy Stronghold straight to its own (that is two marker actions)."""
    north = set(_region_locales("north"))
    enemy = "yorkist" if side == "lancastrian" else "lancastrian"
    neutral = Favour.NEUTRAL.value
    ops = d.get("favour", [])             # [{locale, side|"neutral"}]
    _require(len(ops) <= 3, "too_many", "Robin's Rebellion places/removes up to 3 Favour (L31)")
    done: list[dict[str, Any]] = []
    for op in ops:
        loc = op["locale"]
        _require(loc in north, "not_north", f"{loc} is not in the North (L31)")
        target = op.get("side", neutral)
        cur: Any = state.locales[loc].favour
        cur = cur.value if hasattr(cur, "value") else cur
        if target in (neutral, "neutral"):           # remove Enemy Favour
            _require(cur == enemy, "not_enemy_favour",
                     f"{loc} does not hold {enemy} Favour to remove (L31)")
        elif target == side:                          # place own Favour on a neutral
            _require(cur in (neutral, "neutral"), "not_neutral",
                     f"{loc} is not neutral -- place Favour only on neutral Strongholds (L31)")
        else:                                         # placing Enemy Favour is illegal
            _require(False, "bad_favour_side",
                     "Robin's Rebellion may only remove Enemy Favour or place your own (L31)")
        state.locales[loc].favour = (Favour.NEUTRAL if target in (neutral, "neutral")
                                     else Favour(side))
        done.append(op)
    return {"changes": done}


# L32
def _tudor_banners(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    from plantagenet.actions import _adjacency
    ht = state.lords.get("henry_tudor")
    if not (ht is not None and ht.status == LordStatus.MUSTERED
            and ht.location in state.locales
            and state.locales[ht.location].favour == "lancastrian"):
        return {"no_effect": "Henry Tudor not at a Friendly Stronghold (L32)"}
    york = {ls.location for _lid, ls in _on_map(state, "yorkist")}
    marked: list[str] = []
    for n, _t in _adjacency().get(ht.location, []):
        if n not in york:
            state.locales[n].favour = cast(Favour, "lancastrian")
            marked.append(n)
    return {"marked": marked}


# Y10
def tax_collectors_targets(state: GameState) -> dict[str, list[str]]:
    """All qualifying Tax sources for every on-map Yorkist Lord (4.6.3)."""
    from plantagenet import commands

    statics = static_data.load_lords()
    regular = static_data.load_vassals()["regular"]
    available = {}
    for lid, lord in _on_map(state, "yorkist"):
        here = lord.location
        if here is None or here not in state.locales or state.locales[here].favour != "yorkist":
            continue
        candidates = {statics[lid]["seat"], "london", "calais", "harlech"}
        candidates.update(regular[v]["seat"] for v in lord.vassals if v in regular)
        # Sharing only qualifies the Route. Tax Collectors spends no Ships and
        # has no Lancastrian Naval Blockade reaction to choosing a fleet.
        owners = [lord, *commands._ship_donors(state, lord)]
        targets = []
        for target in sorted(candidates):
            locale = state.locales[target]
            if locale.depletion == "exhausted":
                continue
            if commands._tax_route_cost(state, ("stronghold", here), target,
                                        "yorkist", owners) is None:
                continue
            targets.append(target)
        if targets:
            available[lid] = targets
    return available


def _tax_collectors(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    """Each Yorkist Lord may immediately Tax (full 4.6.3 procedure: Influence check,
    a qualifying Stronghold reached by Route, Deplete) for DOUBLE the Coin.
    Decisions: ``lords``, ``tax_targets`` ({lord: Stronghold}), and optional
    ``extra_spend`` ({lord: 0, 1, or 3 Influence}), chosen before rolling."""
    from plantagenet import commands

    _require(d.keys() <= {"lords", "tax_targets", "extra_spend"}, "bad_event_decisions",
             "choose Lords, Tax targets, and each Lord's extra Influence (Y10)")
    lords = d.get("lords", [])
    targets = d.get("tax_targets", {})
    spending = d.get("extra_spend", {})
    _require(isinstance(lords, list) and all(isinstance(lid, str) for lid in lords)
             and isinstance(targets, dict) and isinstance(spending, dict),
             "bad_event_decisions", "lords is a list; tax_targets and extra_spend are maps (Y10)")
    extra = {lid: _event_extra_spend(value) for lid, value in spending.items()}
    out: dict[str, Any] = {}
    for lid in dict.fromkeys(lords):
        target = targets.get(lid)
        # Earlier elected Lords can Exhaust a shared source. Recheck live eligibility.
        if target not in tax_collectors_targets(state).get(lid, []):
            continue
        result = commands._resolve_tax_attempt(
            state, lid, target, auto=target == static_data.load_lords()[lid]["seat"],
            extra_spend=extra.get(lid, 0), coin_multiplier=2)
        coin = result.pop("coin_added")
        out[lid] = {"target": target, "coin": coin, **result}
    return {"taxes": out}


_IMMEDIATE: dict[str, Callable[[GameState, str, dict[str, Any]], dict[str, Any]]] = {
    "Y10": _tax_collectors, "Y15": _london_for_york, "Y17": _she_wolf,
    "Y21": _sir_richard_leigh, "Y23": _charles_the_bold, "Y26": _dubious_clarence,
    "Y27": _yorkist_north, "Y31": _earl_rivers,
    "L14": _scots, "L15": _henry_pressures_parliament, "L19": _henrys_proclamation,
    "L22": _french_troops, "L23": _warwicks_propaganda, "L24": _warwicks_propaganda,
    "L25": _welsh_rebellion, "L26": _henry_released, "L27": _luniverselle_aragne,
    "L29": _to_wilful_disobedience, "L30": _french_war_loans, "L31": _robins_rebellion,
    "L32": _tudor_banners,
}


def _held_card(state: GameState, side: str, title: str) -> str | None:
    cards = static_data.load_cards()
    for cid in state.decks.get(side, {}).get("held", []):
        if cards[cid]["event"]["title"] == title:
            return cid
    return None


def _use_held(state: GameState, side: str, cid: str) -> None:
    held = state.decks.get(side, {}).get("held", [])
    if cid in held:
        held.remove(cid)
    state.decks.setdefault(side, {}).setdefault("discard", []).append(cid)


def expire_scope(state: GameState, scope: str) -> list[str]:
    """Remove active Events of ``scope`` ("this_levy"/"this_campaign") and
    DISCARD any whose card is not already in a pile. A drawn This-Levy/This-
    Campaign Event lives only in ``active_events``; without this it would vanish
    from the game when the scope ends, silently shrinking the side's deck."""
    expired = [e for e in state.active_events if e.get("scope") == scope]
    state.active_events = [e for e in state.active_events if e.get("scope") != scope]
    discarded: list[str] = []
    for e in expired:
        cid = e.get("card")
        sd = e.get("side")
        if not cid or not sd:
            continue
        piles = state.decks.setdefault(sd, {"draw": [], "discard": [], "held": []})
        if not any(cid in piles.get(p, []) for p in ("draw", "discard", "held", "set_aside")):
            piles.setdefault("discard", []).append(cid)
            discarded.append(cid)
    return discarded


# L28: after own March/Sail to a Port
def _hp_rebel_supply_depot(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    # Timing (1.9.1): only just after a qualifying March/Sail to a Port -- the
    # Hold-event window names the mover(s). The named Lord(s) must be those movers.
    win = state.hold_window
    _require(win is not None and win.get("side") == side
             and win.get("action") in ("march", "sail"),
             "no_move_window",
             "Rebel Supply Depot is played just after a March or Sail to a Port (L28)")
    assert win is not None
    movers = set(win.get("lords", []))
    lids = d.get("lords", [])
    _require(isinstance(lids, list) and lids, "no_lords",
             "name the Lord(s) that just reached the Port (L28)")
    _require(all(isinstance(lid, str) for lid in lids) and len(set(lids)) == len(lids),
             "duplicate_lords", "name each moving Lord only once (L28)")
    locs = static_data.load_locales()
    for lid in lids:
        _require(lid in movers, "not_mover",
                 f"{lid} did not just March/Sail to the Port (L28)")
        ls = state.lords.get(lid)
        _require(ls is not None and ls.side == side and ls.status == LordStatus.MUSTERED,
                 "bad_lord", f"{lid} is not a Mustered {side} Lord (L28)")
        assert ls is not None
        _require(ls.location and locs.get(ls.location, {}).get("port"),
                 "not_at_port", f"{lid} is not at a Port (L28)")
    # L28 Tips: four Provender TOTAL, distributed among the movers as desired.
    distribution = d.get("provender", {lids[0]: 4} if len(lids) == 1 else None)
    _require(isinstance(distribution, dict), "provender_distribution_required",
             "distribute four Provender among the moving Lords (L28)")
    assert isinstance(distribution, dict)
    _require(all(lid in lids and type(n) is int and n >= 0
                 for lid, n in distribution.items()) and sum(distribution.values()) == 4,
             "bad_provender_distribution",
             "the distribution must assign exactly four Provender to named movers (L28)")
    for lid in lids:
        ls = state.lords[lid]
        ls.assets["provender"] = ls.assets.get("provender", 0) + distribution.get(lid, 0)
        ls.ignore_next_feed = True
    return {"lords": lids, "provender_added": distribution, "ignore_next_feed": True}


# L33: after Sailing to a Port, free March
def _hp_surprise_landing(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    _require(state.campaign is not None, "not_campaign", "Surprise Landing is a Campaign play")
    assert state.campaign is not None
    # Timing (1.9.1): only just after a Sail that ends at a Port -- the Hold-event
    # window must record a Sail for this side.
    win = state.hold_window
    _require(win is not None and win.get("action") == "sail" and win.get("side") == side,
             "no_sail_window",
             "Surprise Landing is played just after Sailing to a Port (L33)")
    alid = state.campaign.active_lord
    al = state.lords.get(alid) if alid else None
    _require(al is not None and al.location is not None
             and static_data.load_locales().get(al.location, {}).get("port"),
             "not_at_port", "Surprise Landing is played just after Sailing to a Port (L33)")
    state.campaign.surprise_march_lord = alid
    return {"free_action": True}


# Y24: Muster Edward IV in Levy, free
def _hp_sun_in_splendour(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    from plantagenet.actions import enemy_lord_at
    _require(state.phase == "levy", "not_levy", "Sun in Splendour is played in the Levy (Y24)")
    ed = state.lords.get("edward_iv")
    _require(ed is not None and ed.status in (LordStatus.CALENDAR, LordStatus.EXILE),
             "edward_unavailable", "Edward IV must be on the Calendar/Exile (Y24)")
    assert ed is not None
    target = d.get("target")
    in_box = target in static_data.load_exile_boxes()
    if in_box:                                          # a Yorkist-aligned Exile box
        _require(state.exile_alignment.get(cast(str, target)) == "yorkist", "bad_target",
                 "Muster Edward IV at a Yorkist Exile box (Y24)")
    else:                                               # a Friendly Stronghold, Enemy-free
        _require(target in state.locales and state.locales[target].favour == "yorkist"
                 and not enemy_lord_at(state, target, "yorkist"), "bad_target",
                 "Muster Edward IV at a Friendly Locale free of Enemy Lords (Y24)")
    statics = static_data.load_lords()["edward_iv"]
    ed.status = LordStatus.MUSTERED                     # validated; now place
    ed.exile_box = target if in_box else None
    ed.location = None if in_box else target
    ed.calendar_box = None
    ed.calendar_exile = False
    ed.forces = dict(statics.get("forces", {}))
    ed.assets = dict(statics.get("assets", {}))
    return {"mustered": "edward_iv", "at": target}


# Y20: this Levy Yorkist Influence +2
def _hp_yorkist_parade(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    _require(state.locales["london"].favour == "yorkist", "london_not_friendly",
             "Yorkist Parade needs London Friendly (Y20)")
    here = {ls.location for lid, ls in state.lords.items()
            if lid in ("york", "warwick_yorkist") and ls.status == LordStatus.MUSTERED}
    _require("london" in here, "no_york_or_warwick",
             "York or Warwick must be at London (Y20)")
    state.active_events.append({"card": "Y20", "side": "yorkist", "scope": "this_levy"})
    return {"active": "Y20"}


# Y13/L13: inspect Enemy Held cards (info)
def _hp_aspielles(state: GameState, side: str, d: dict[str, Any]) -> dict[str, Any]:
    foe = "lancastrian" if side == "yorkist" else "yorkist"
    held = list(state.decks.get(foe, {}).get("held", []))
    return {"peek": {"enemy_side": foe, "enemy_held": held, "hidden_mat": d.get("mat")}}


_HELD_PLAYS: dict[str, Callable[[GameState, str, dict[str, Any]], dict[str, Any]]] = {
    "L28": _hp_rebel_supply_depot, "L33": _hp_surprise_landing,
    "Y24": _hp_sun_in_splendour, "Y20": _hp_yorkist_parade,
    "Y13": _hp_aspielles, "L13": _hp_aspielles,
}


def play_held_event(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Play a Held Event in one of its own-timing windows (1.9.1):
    Rebel Supply Depot (L28), Surprise Landing (L33), Sun in Splendour (Y24),
    Yorkist Parade (Y20)."""
    cid = cast(str, action.get("card"))
    side = cast(str, action.get("side"))
    _require(cid in _HELD_PLAYS, "not_held_play", f"{cid} is not a coded Held-play Event")
    held = _held_card(state, side, static_data.load_cards()[cid]["event"]["title"])
    _require(held == cid, "not_held", f"{side} is not holding {cid}")
    res = _HELD_PLAYS[cid](state, side, action.get("decisions", {}))
    _use_held(state, side, cid)
    return {"type": "play_held_event", "card": cid, "side": side, **res}


def loyalty_and_trust_targets(state: GameState, side: str) -> list[str]:
    """Y22: any Yorkist Lord still in this scenario, including Calendar/Exile."""
    return sorted(lid for lid, lord in state.lords.items()
                  if lord.side == side == "yorkist" and lord.status != LordStatus.REMOVED)


_PERSIST = {"Y34"}   # immediate Events that stay in effect (active_events)


def pending_event_side(event: dict[str, Any]) -> str:
    """The owner of the head Event's current decision."""
    if ((event["card"] == "L27" and "aragne" in event)
            or (event["card"] in ("L23", "L24") and "propaganda" in event)):
        return "yorkist"
    return cast(str, event["side"])


def play_event(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Resolve the next decision of the head drawn Event (1.9.1 / 3.1.3)."""
    cid = cast(str, action.get("card"))
    side = cast(str, action.get("side"))
    cards = static_data.load_cards()
    _require(cid in _IMMEDIATE or cid in _PERSIST or cid == "Y22", "not_immediate_event",
             f"{cid} is not a coded pending Event")
    card_side = cards[cid]["side"]
    head = state.pending_events[0] if state.pending_events else {}
    actor = pending_event_side(head) if head.get("card") == cid else card_side
    _require(side == actor, "wrong_side", f"{cid} awaits a {actor} decision")
    _require(state.phase == "levy" and state.levy_step == "arts_of_war",
             "wrong_step", "drawn Events resolve during the Arts of War step (3.1.3)")
    _require(state.turn_box != (state.calendar.first_box or state.turn_box),
             "first_levy", "the first Levy draws Capabilities, not Events (3.1.2)")
    _require(card_side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's draw (3.1.3)")
    _require(any(pe.get("card") == cid and pe.get("side") == card_side
                 for pe in state.pending_events), "event_not_pending",
             f"{cid} has not been drawn for resolution (3.1.3)")
    _require(head.get("card") == cid and head.get("side") == card_side, "event_order",
             "resolve Events in the order drawn (3.1.3)")
    decisions = action.get("decisions", {})
    _require(isinstance(decisions, dict), "bad_event_decisions", "decisions must be an object")
    res: dict[str, Any]
    if cid == "Y22":
        targets = loyalty_and_trust_targets(state, side)
        target = decisions.get("target")
        _require((not targets and target is None) or target in targets, "bad_event_target",
                 "Loyalty and Trust requires selection of a Yorkist Lord still in the scenario")
        ev = {"card": cid, "side": side, "scope": "this_levy"}
        if target is not None:
            ev["target"] = target
        state.active_events.append(ev)
        res = {"active": True, "target": target, "no_effect": not targets}
    elif cid in _PERSIST:
        state.active_events.append({"card": cid, "side": side, "scope": "this_campaign"})
        res = {"active": True}
    else:
        res = _IMMEDIATE[cid](state, side, decisions)
        if res.get("awaiting_side"):
            return {"type": "play_event", "card": cid, "side": side, **res}
        state.decks.setdefault(card_side, {}).setdefault("draw", []).append(cid)
    state.pending_events.pop(0)
    if not state.pending_events:
        from plantagenet.arts_of_war import advance_after_draw
        res["next"] = advance_after_draw(state, card_side, first_levy=False)
    return {"type": "play_event", "card": cid, "side": side, **res}
