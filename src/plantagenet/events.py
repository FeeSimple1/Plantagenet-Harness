"""Immediate Arts of War Event effects (1.9.1), resolved via the ``play_event``
action with a ``decisions`` payload for any targeting choices.

Each resolver is keyed by card id and takes (state, side, decisions) -> dict.
Hold and This-Levy/This-Campaign Events are handled elsewhere (held pile /
active_events + per-handler hooks); this module covers the "immediate" type.
"""

from __future__ import annotations

from typing import Any

from plantagenet import influence, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import Favour, GameState, LordStatus

_OTHER = {"yorkist": "lancastrian", "lancastrian": "yorkist"}


def _require(cond, code, msg):
    if not cond:
        raise IllegalAction(code, msg)


def _on_map(state, side):
    return [(lid, ls) for lid, ls in state.lords.items()
            if ls.side == side and ls.status == LordStatus.MUSTERED]


def _pool_add(state, lord, unit, amount):
    from plantagenet.actions import _troops_in_play
    pool = static_data.load_forces()[unit].get("pool", 0)
    give = max(0, min(amount, pool - _troops_in_play(state, unit)))
    if give:
        lord.forces[unit] = lord.forces.get(unit, 0) + give
    return give


def _region_locales(region):
    return [k for k, v in static_data.load_locales().items()
            if isinstance(v, dict) and v.get("region") == region]


# --------------------------------------------------------------- resolvers
def _charles_the_bold(state, side, d):                       # Y23
    for _lid, ls in _on_map(state, "yorkist"):
        ls.assets["coin"] = ls.assets.get("coin", 0) + 1
        ls.assets["provender"] = ls.assets.get("provender", 0) + 1
    return {"granted": "1 Coin + 1 Provender to each Yorkist Lord"}


def _french_war_loans(state, side, d):                       # L30
    for _lid, ls in _on_map(state, "lancastrian"):
        ls.assets["coin"] = ls.assets.get("coin", 0) + 1
        ls.assets["provender"] = ls.assets.get("provender", 0) + 1
    return {"granted": "1 Coin + 1 Provender to each Lancastrian Lord"}


def _earl_rivers(state, side, d):                            # Y31: up to 2 Militia each
    add = {}
    per = d.get("militia", {})
    for lid, ls in _on_map(state, "yorkist"):
        n = int(per.get(lid, 2))
        _require(0 <= n <= 2, "bad_militia", "Earl Rivers adds 0-2 Militia per Lord (Y31)")
        g = _pool_add(state, ls, "militia", n)
        if g:
            add[lid] = g
    return {"militia_added": add}


def _scots(state, side, d):                                  # L14: up to 1 MaA + 1 Militia
    add = {}
    sel = d.get("lords", [lid for lid, _ in _on_map(state, "lancastrian")])
    for lid in sel:
        ls = state.lords[lid]
        a = _pool_add(state, ls, "men_at_arms", 1) + 0
        b = _pool_add(state, ls, "militia", 1)
        add[lid] = {"men_at_arms": a, "militia": b}
    return {"added": add}


def _french_troops(state, side, d):                          # L22: a Lord at a Port (optional)
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
    _require(ls.location in locales and bool(locales[ls.location].get("port")),
             "not_port", "French Troops reinforce a Lancastrian Lord at a Port (L22)")
    a = _pool_add(state, ls, "men_at_arms", min(2, int(d.get("men_at_arms", 2))))
    b = _pool_add(state, ls, "militia", min(2, int(d.get("militia", 2))))
    return {"lord": lid, "men_at_arms": a, "militia": b}


def _yorkist_north(state, side, d):                          # Y27
    north = _region_locales("north")
    strongholds = sum(1 for loc in north if state.locales[loc].favour == "yorkist")
    lords = sum(1 for lid, ls in _on_map(state, "yorkist") if ls.location in north)
    influence.gain_influence(state, "yorkist", strongholds + lords)
    return {"influence": strongholds + lords}


def _henry_pressures_parliament(state, side, d):             # L15
    from plantagenet.state import LordStatus, VassalStatus
    n = sum(1 for v in state.vassals.values() if v.status == VassalStatus.MUSTERED
            and state.lords.get(v.on_lord) is not None
            and state.lords[v.on_lord].side == "yorkist")
    # Special Vassals (e.g. Hastings Y24) live on the Lord's mat, not state.vassals.
    n += sum(len(ld.special_vassals) for ld in state.lords.values()
             if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED)
    influence.spend_influence(state, "yorkist", n)
    return {"yorkist_influence_lost": n}


def _henry_released(state, side, d):                         # L26
    gained = 0
    if state.locales["london"].favour == "lancastrian":
        influence.gain_influence(state, "lancastrian", 5)
        gained = 5
    return {"lancastrian_influence": gained}


def _london_for_york(state, side, d):                        # Y15
    lon = state.locales["london"]
    added = False
    if lon.favour == "yorkist" and lon.favour_extra == 0:   # "If already two, no effect"
        lon.favour_extra += 1
        added = True
    return {"second_favour": added}


def _sir_richard_leigh(state, side, d):                      # Y21
    lon = state.locales["london"]
    if lon.favour == "lancastrian":
        if lon.favour_extra > 0:
            lon.favour_extra -= 1
        else:
            lon.favour = Favour.NEUTRAL.value
        return {"london": "lancastrian favour removed"}
    if lon.favour == Favour.NEUTRAL.value:
        lon.favour = "yorkist"
        return {"london": "yorkist favour placed"}
    return {"london": "no change"}


def _she_wolf(state, side, d):                               # Y17: shift Yorkist Vassals +1
    from plantagenet.state import VassalStatus
    shifted = []
    for vid, v in state.vassals.items():
        if (v.status == VassalStatus.MUSTERED and v.service_box is not None
                and state.lords.get(v.on_lord) is not None
                and state.lords[v.on_lord].side == "yorkist"):
            v.service_box = v.service_box + 1   # may go off-calendar past box 15 (2.2.3)
            shifted.append(vid)
    return {"shifted": shifted}


def _henrys_proclamation(state, side, d):                    # L19: Yorkist Vassals -> current Turn
    from plantagenet.state import VassalStatus
    shifted = []
    for vid, v in state.vassals.items():
        if (v.status == VassalStatus.MUSTERED and v.service_box is not None
                and state.lords.get(v.on_lord) is not None
                and state.lords[v.on_lord].side == "yorkist"):
            v.service_box = state.turn_box
            shifted.append(vid)
    return {"shifted": shifted}


def _dubious_clarence(state, side, d):                       # Y26
    ed = state.lords.get("edward_iv")
    clar = state.lords.get("clarence")
    if not (ed is not None and ed.status == LordStatus.MUSTERED
            and clar is not None and clar.status == LordStatus.MUSTERED):
        return {"no_effect": "requires Edward IV and Clarence on the map (Y26)"}
    chk = influence.check_influence(state, "edward_iv", "yorkist",
                                    extra_spend=int(d.get("extra_spend", 0)))
    if chk["success"]:
        from plantagenet import campaign
        campaign._disband_lord(state, clar)
    return {"disbanded": chk["success"], **chk}


def _luniverselle_aragne(state, side, d):                    # L27
    from plantagenet import campaign
    from plantagenet.state import LordStatus, VassalStatus
    owner: dict[str, str] = {}                               # vid -> Yorkist Lord id
    for vid, v in state.vassals.items():
        if (v.status == VassalStatus.MUSTERED and v.on_lord is not None
                and state.lords.get(v.on_lord) is not None
                and state.lords[v.on_lord].side == "yorkist"):
            owner[vid] = v.on_lord
    for lid, ld in state.lords.items():                      # Special Vassals (Hastings)
        if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED:
            for vid in ld.special_vassals:
                owner[vid] = lid
    if not owner:                                            # "No effect if no ... Vassals"
        return {"no_effect": "no Yorkist Mustered Vassals (L27)"}
    need = min(2, len(owner))                                # "Select 2 ... or fewer if fewer"
    targets = d.get("vassals", [])
    _require(len(targets) == need, "bad_targets",
             f"L'Universelle Aragne targets {need} Yorkist Mustered Vassals (L27)")
    out = []
    for vid in targets:
        _require(vid in owner, "bad_vassal", f"{vid} not a Yorkist Mustered Vassal")
        lord = state.lords[owner[vid]]
        chk = influence.check_influence(state, lord.lord_id, lord.side)
        if not chk["success"]:
            if vid in state.vassals:                         # regular Vassal -> Calendar (3.2.4)
                campaign._disband_vassal(state, vid)
                lord.vassals = [x for x in lord.vassals if x != vid]
            else:                                            # Special Vassal -> discard Y24
                campaign._disband_special_vassal(state, lord, vid)
        out.append({"vassal": vid, "disbanded": not chk["success"], **chk})
    return {"checks": out}


def _warwicks_propaganda(state, side, d):                    # L23/L24
    available = [loc for loc, ls in state.locales.items() if ls.favour == "yorkist"]
    if not available:                                        # "No effect if no ... Favour"
        return {"no_effect": "no Yorkist Favour to target (L23/L24)"}
    need = min(3, len(available))                            # "Select 3 ... or all if fewer"
    choices = d.get("strongholds", {})   # {locale: "pay" | "remove"}
    _require(len(choices) == need, "bad_count",
             f"Warwick's Propaganda selects {need} Yorkist Strongholds (L23/L24)")
    out = []
    for loc, how in choices.items():
        _require(loc in state.locales and state.locales[loc].favour == "yorkist",
                 "not_yorkist", f"{loc} must Favour Yorkist (L23/L24)")
        if how == "pay":
            influence.spend_influence(state, "yorkist", 2)
            out.append({loc: "paid 2 Influence"})
        else:
            if state.locales[loc].favour_extra > 0:
                state.locales[loc].favour_extra -= 1
            else:
                state.locales[loc].favour = Favour.NEUTRAL.value
            out.append({loc: "Favour removed"})
    return {"results": out}


def _welsh_rebellion(state, side, d):                        # L25
    wales = _region_locales("wales")
    yorkist_in_wales = [(lid, ls) for lid, ls in _on_map(state, "yorkist")
                        if ls.location in wales]
    if yorkist_in_wales:
        removed = {}
        for lid, ls in yorkist_in_wales:
            troops = [t for t in ls.forces if t in
                      {"men_at_arms", "longbow", "militia", "mercenaries", "handgunners"}]
            taken = 0
            for t in troops:
                while taken < 2 and ls.forces.get(t, 0) > 0:
                    ls.forces[t] -= 1
                    taken += 1
            removed[lid] = taken
        return {"troops_removed": removed}
    n = 0
    for loc in wales:
        if n >= 2:
            break
        if state.locales[loc].favour == "yorkist":
            state.locales[loc].favour = Favour.NEUTRAL.value
            n += 1
    return {"favour_removed": n}


def _to_wilful_disobedience(state, side, d):                 # L29
    from plantagenet.commands import _adjacency
    targets = d.get("strongholds", [])
    _require(len(targets) <= 2, "bad_count", "removes Yorkist Favour from up to 2 (L29)")
    lanc = {ls.location for _lid, ls in _on_map(state, "lancastrian")}
    york = {ls.location for _lid, ls in _on_map(state, "yorkist")}

    def near(locset, loc):
        return loc in locset or any(n in locset for n, _t in _adjacency().get(loc, []))
    removed = []
    for loc in targets[:2]:
        _require(state.locales[loc].favour == "yorkist", "not_yorkist", f"{loc} not Yorkist")
        _require(near(lanc, loc) and not near(york, loc), "bad_target",
                 f"{loc} must be at/adjacent a Lancastrian Lord and not a Yorkist one (L29)")
        state.locales[loc].favour = Favour.NEUTRAL.value
        removed.append(loc)
    return {"removed": removed}


def _robins_rebellion(state, side, d):                       # L31
    north = set(_region_locales("north"))
    ops = d.get("favour", [])             # [{locale, side|"neutral"}]
    _require(len(ops) <= 3, "too_many", "Robin's Rebellion places/removes up to 3 Favour (L31)")
    done = []
    for op in ops:
        loc = op["locale"]
        _require(loc in north, "not_north", f"{loc} is not in the North (L31)")
        state.locales[loc].favour = op.get("side", Favour.NEUTRAL.value)
        done.append(op)
    return {"changes": done}


def _tudor_banners(state, side, d):                          # L32
    from plantagenet.commands import _adjacency
    ht = state.lords.get("henry_tudor")
    if not (ht is not None and ht.status == LordStatus.MUSTERED
            and ht.location in state.locales
            and state.locales[ht.location].favour == "lancastrian"):
        return {"no_effect": "Henry Tudor not at a Friendly Stronghold (L32)"}
    york = {ls.location for _lid, ls in _on_map(state, "yorkist")}
    marked = []
    for n, _t in _adjacency().get(ht.location, []):
        if n not in york:
            state.locales[n].favour = "lancastrian"
            marked.append(n)
    return {"marked": marked}


def _tax_collectors(state, side, d):                         # Y10
    """Each Yorkist Lord may immediately Tax (full 4.6.3 procedure: Influence check,
    a qualifying Stronghold reached by Route, Deplete) for DOUBLE the Coin.
    Decisions: ``lords`` (electing Lords) and ``tax_targets`` ({lord: Stronghold})."""
    from plantagenet import commands
    statics = static_data.load_lords()
    regular = static_data.load_vassals()["regular"]
    targets = d.get("tax_targets", {})
    out = {}
    for lid in d.get("lords", []):
        ls = state.lords.get(lid)
        if ls is None or ls.side != "yorkist" or ls.status != LordStatus.MUSTERED:
            continue
        here = ls.location
        target = targets.get(lid)
        own_seat = statics[lid]["seat"]
        vassal_seats = {regular[v]["seat"] for v in ls.vassals if v in regular}
        if target is None or here is None:
            continue
        if not (target == own_seat or target in vassal_seats
                or target in {"london", "calais", "harlech"}):
            continue
        if state.locales[target].depletion == "exhausted":
            continue
        auto = (target == own_seat)
        if not auto:                                  # must trace a Route and pass the check
            gs = ratings.has_capability(state, lid, "GREAT SHIPS")
            way = commands._tax_route_cost(state, here, target, "yorkist",
                                           ls.assets.get("ship", 0) > 0, all_seas=gs)
            if way is None:
                continue
            chk = influence.check_influence(state, lid, "yorkist", action="tax")  # no per-Way
            if not chk["success"]:
                out[lid] = {"target": target, "success": False}
                continue
        coin = static_data.stronghold_yields(target).get("tax", {}).get("coin", 0) * 2
        ls.assets["coin"] = ls.assets.get("coin", 0) + coin
        st = state.locales[target]
        st.depletion = "exhausted" if st.depletion == "depleted" else "depleted"
        out[lid] = {"target": target, "coin": coin, "success": True}
    return {"taxes": out}


_IMMEDIATE = {
    "Y10": _tax_collectors, "Y15": _london_for_york, "Y17": _she_wolf,
    "Y21": _sir_richard_leigh, "Y23": _charles_the_bold, "Y26": _dubious_clarence,
    "Y27": _yorkist_north, "Y31": _earl_rivers,
    "L14": _scots, "L15": _henry_pressures_parliament, "L19": _henrys_proclamation,
    "L22": _french_troops, "L23": _warwicks_propaganda, "L24": _warwicks_propaganda,
    "L25": _welsh_rebellion, "L26": _henry_released, "L27": _luniverselle_aragne,
    "L29": _to_wilful_disobedience, "L30": _french_war_loans, "L31": _robins_rebellion,
    "L32": _tudor_banners,
}


def _held_card(state, side, title):
    cards = static_data.load_cards()
    for cid in state.decks.get(side, {}).get("held", []):
        if cards[cid]["event"]["title"] == title:
            return cid
    return None


def _use_held(state, side, cid):
    held = state.decks.get(side, {}).get("held", [])
    if cid in held:
        held.remove(cid)
    state.decks.setdefault(side, {}).setdefault("discard", []).append(cid)


def _hp_rebel_supply_depot(state, side, d):     # L28: after own March/Sail to a Port
    lids = d.get("lords", [])
    _require(lids, "no_lords", "name the Lord(s) that just reached the Port (L28)")
    locs = static_data.load_locales()
    for lid in lids:
        ls = state.lords[lid]
        _require(ls.location and locs.get(ls.location, {}).get("port"),
                 "not_at_port", f"{lid} is not at a Port (L28)")
        ls.assets["provender"] = ls.assets.get("provender", 0) + 4
        ls.ignore_next_feed = True
    return {"lords": lids, "provender_each": 4, "ignore_next_feed": True}


def _hp_surprise_landing(state, side, d):       # L33: after Sailing to a Port, free March
    _require(state.campaign is not None, "not_campaign", "Surprise Landing is a Campaign play")
    # "Play just after a Sail that ends at a Port (only)" (L33): the active Lord
    # must be at a Port. (The free action should be a non-Path March -- the
    # consumer is responsible for that constraint.)
    alid = state.campaign.active_lord
    al = state.lords.get(alid) if alid else None
    _require(al is not None and al.location is not None
             and static_data.load_locales().get(al.location, {}).get("port"),
             "not_at_port", "Surprise Landing is played just after Sailing to a Port (L33)")
    state.campaign.actions_remaining += 1       # a free March action ...
    state.flags["surprise_march_lord"] = alid   # ... which may NOT be a Path (L33)
    return {"free_action": True}


def _hp_sun_in_splendour(state, side, d):       # Y24: Muster Edward IV in Levy, free
    from plantagenet.actions import enemy_lord_at
    _require(state.phase == "levy", "not_levy", "Sun in Splendour is played in the Levy (Y24)")
    ed = state.lords.get("edward_iv")
    _require(ed is not None and ed.status in (LordStatus.CALENDAR, LordStatus.EXILE),
             "edward_unavailable", "Edward IV must be on the Calendar/Exile (Y24)")
    target = d.get("target")
    in_box = target in static_data.load_exile_boxes()
    if in_box:                                          # a Yorkist-aligned Exile box
        _require(state.exile_alignment.get(target) == "yorkist", "bad_target",
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


def _hp_yorkist_parade(state, side, d):         # Y20: this Levy Yorkist Influence +2
    _require(state.locales["london"].favour == "yorkist", "london_not_friendly",
             "Yorkist Parade needs London Friendly (Y20)")
    here = {ls.location for lid, ls in state.lords.items()
            if lid in ("york", "warwick_yorkist") and ls.status == LordStatus.MUSTERED}
    _require("london" in here, "no_york_or_warwick",
             "York or Warwick must be at London (Y20)")
    state.active_events.append({"card": "Y20", "side": "yorkist", "scope": "this_levy"})
    return {"active": "Y20"}


def _hp_aspielles(state, side, d):              # Y13/L13: inspect Enemy Held cards (info)
    foe = "lancastrian" if side == "yorkist" else "yorkist"
    held = list(state.decks.get(foe, {}).get("held", []))
    return {"peek": {"enemy_side": foe, "enemy_held": held, "hidden_mat": d.get("mat")}}


_HELD_PLAYS = {
    "L28": _hp_rebel_supply_depot, "L33": _hp_surprise_landing,
    "Y24": _hp_sun_in_splendour, "Y20": _hp_yorkist_parade,
    "Y13": _hp_aspielles, "L13": _hp_aspielles,
}


def play_held_event(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Play a Held Event in one of its own-timing windows (1.9.1):
    Rebel Supply Depot (L28), Surprise Landing (L33), Sun in Splendour (Y24),
    Yorkist Parade (Y20)."""
    cid = action.get("card")
    side = action.get("side")
    _require(cid in _HELD_PLAYS, "not_held_play", f"{cid} is not a coded Held-play Event")
    held = _held_card(state, side, static_data.load_cards()[cid]["event"]["title"])
    _require(held == cid, "not_held", f"{side} is not holding {cid}")
    res = _HELD_PLAYS[cid](state, side, action.get("decisions", {}))
    _use_held(state, side, cid)
    return {"type": "play_held_event", "card": cid, "side": side, **res}


_PERSIST = {"Y34"}   # immediate Events that stay in effect (active_events)


def play_event(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    """Resolve an immediate Event card's effect (1.9.1 / 3.1.3).

    A drawn immediate Event sits in ``state.pending_events`` until resolved; on
    resolution it returns to the deck (3.1.3) and, once the side's queue empties,
    the Arts of War sequence advances. An Event whose precondition is unmet
    resolves to no effect (the card text's "No effect if ..."). Standalone calls
    (not from a draw) just apply the effect, leaving deck membership untouched."""
    cid = action.get("card")
    side = action.get("side")
    cards = static_data.load_cards()
    in_pending = any(pe.get("card") == cid and pe.get("side") == side
                     for pe in state.pending_events)
    if cid in _PERSIST:
        _require(cards[cid]["side"] == side, "wrong_side", f"{cid} is not a {side} card")
        state.active_events.append({"card": cid, "side": side, "scope": "this_campaign"})
        res: dict[str, Any] = {"active": True}
    else:
        _require(cid in _IMMEDIATE, "not_immediate_event",
                 f"{cid} is not a coded immediate Event")
        _require(cards[cid]["side"] == side, "wrong_side", f"{cid} is not a {side} card")
        # Henry Released (L26): cannot occur while L26 is on a mat / set aside.
        if cid == "L26":
            d = state.decks.get(side, {})
            # A just-drawn L26 is live by definition (in_pending); otherwise it is
            # suppressed when assigned to a mat / set aside (not in any deck pile).
            live = in_pending or any("L26" in d.get(pile, [])
                                     for pile in ("draw", "discard", "held"))
            _require(live, "event_suppressed",
                     "Henry Released cannot occur: L26 EDWARD is assigned/set aside (6.2)")
        res = _IMMEDIATE[cid](state, side, action.get("decisions", {}))
        # 3.1.3: a drawn immediate Event returns to the deck after resolving. Only
        # in the drawn (pending) context -- standalone calls leave the card alone.
        if in_pending:
            state.decks.setdefault(side, {}).setdefault("draw", []).append(cid)
    if in_pending:
        state.pending_events = [pe for pe in state.pending_events
                                if not (pe.get("card") == cid and pe.get("side") == side)]
        if not state.pending_events:
            from plantagenet.arts_of_war import advance_after_draw
            first_levy = state.turn_box == (state.calendar.first_box or state.turn_box)
            res["next"] = advance_after_draw(state, side, first_levy)
    return {"type": "play_event", "card": cid, "side": side, **res}
