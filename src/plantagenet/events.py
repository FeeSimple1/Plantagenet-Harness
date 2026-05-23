"""Immediate Arts of War Event effects (1.9.1), resolved via the ``play_event``
action with a ``decisions`` payload for any targeting choices.

Each resolver is keyed by card id and takes (state, side, decisions) -> dict.
Hold and This-Levy/This-Campaign Events are handled elsewhere (held pile /
active_events + per-handler hooks); this module covers the "immediate" type.
"""

from __future__ import annotations

from typing import Any

from plantagenet import influence, static_data
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


def _french_troops(state, side, d):                          # L22: a Lord at a Port
    lid = d.get("lord")
    ls = state.lords.get(lid)
    _require(ls is not None and ls.side == "lancastrian"
             and ls.status == LordStatus.MUSTERED, "bad_lord", "name a Lancastrian Lord (L22)")
    _require(bool(static_data.load_locales()[ls.location].get("port")),
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
    from plantagenet.state import VassalStatus
    n = sum(1 for v in state.vassals.values() if v.status == VassalStatus.MUSTERED
            and state.lords.get(v.on_lord) is not None
            and state.lords[v.on_lord].side == "yorkist")
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
    if lon.favour == "yorkist":
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
            v.service_box = min(15, v.service_box + 1)
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
    _require(ed is not None and ed.status == LordStatus.MUSTERED,
             "no_edward", "Dubious Clarence needs Edward IV on the map (Y26)")
    clar = state.lords.get("clarence")
    _require(clar is not None and clar.status == LordStatus.MUSTERED,
             "no_clarence", "Clarence is not on the map (Y26)")
    chk = influence.check_influence(state, "edward_iv", "yorkist",
                                    extra_spend=int(d.get("extra_spend", 0)))
    if chk["success"]:
        from plantagenet import campaign
        campaign._disband_lord(state, clar)
    return {"disbanded": chk["success"], **chk}


def _luniverselle_aragne(state, side, d):                    # L27
    from plantagenet import campaign
    targets = d.get("vassals", [])
    _require(1 <= len(targets) <= 2, "bad_targets",
             "L'Universelle Aragne targets up to 2 Yorkist Mustered Vassals (L27)")
    out = []
    for vid in targets:
        v = state.vassals.get(vid)
        _require(v is not None and v.on_lord is not None, "bad_vassal", f"{vid} not Mustered")
        lord = state.lords[v.on_lord]
        chk = influence.check_influence(state, lord.lord_id, lord.side)
        if not chk["success"]:
            campaign._disband_vassal(state, vid)
            lord.vassals = [x for x in lord.vassals if x != vid]
        out.append({"vassal": vid, "disbanded": not chk["success"], **chk})
    return {"checks": out}


def _warwicks_propaganda(state, side, d):                    # L23/L24
    choices = d.get("strongholds", {})   # {locale: "pay" | "remove"}
    _require(len(choices) == 3, "bad_count",
             "Warwick's Propaganda selects 3 Yorkist Strongholds (L23/L24)")
    out = []
    for loc, how in choices.items():
        _require(state.locales[loc].favour == "yorkist", "not_yorkist",
                 f"{loc} must Favour Yorkist (L23/L24)")
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
    _require(ht is not None and ht.status == LordStatus.MUSTERED,
             "no_henry_tudor", "Henry Tudor must be on the map (L32)")
    _require(state.locales[ht.location].favour == "lancastrian", "not_friendly",
             "Henry Tudor must be at a Friendly Stronghold (L32)")
    york = {ls.location for _lid, ls in _on_map(state, "yorkist")}
    marked = []
    for n, _t in _adjacency().get(ht.location, []):
        if n not in york:
            state.locales[n].favour = "lancastrian"
            marked.append(n)
    return {"marked": marked}


def _tax_collectors(state, side, d):                         # Y10
    sel = d.get("lords", [])
    out = {}
    for lid in sel:
        ls = state.lords.get(lid)
        if ls is None or ls.side != "yorkist" or ls.status != LordStatus.MUSTERED:
            continue
        loc = ls.location
        st = state.locales[loc]
        if st.favour == "yorkist" and st.depletion != "exhausted":
            coin = static_data.stronghold_yields(loc).get("tax", {}).get("coin", 0) * 2
            ls.assets["coin"] = ls.assets.get("coin", 0) + coin
            st.depletion = "exhausted" if st.depletion == "depleted" else "depleted"
            out[lid] = coin
    return {"coin_added": out}


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
    state.campaign.actions_remaining += 1       # a free (March) action
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
    """Resolve an immediate Event card's effect (1.9.1)."""
    cid = action.get("card")
    side = action.get("side")
    cards = static_data.load_cards()
    if cid in _PERSIST:
        _require(cards[cid]["side"] == side, "wrong_side", f"{cid} is not a {side} card")
        state.active_events.append({"card": cid, "side": side, "scope": "this_campaign"})
        return {"type": "play_event", "card": cid, "side": side, "active": True}
    _require(cid in _IMMEDIATE, "not_immediate_event",
             f"{cid} is not a coded immediate Event")
    _require(cards[cid]["side"] == side, "wrong_side", f"{cid} is not a {side} card")
    # Henry Released (L26): cannot occur while L26 is on a mat / set aside (Succession).
    if cid == "L26":
        d = state.decks.get(side, {})
        in_deck = any("L26" in d.get(pile, []) for pile in ("draw", "discard", "held"))
        _require(in_deck, "event_suppressed",
                 "Henry Released cannot occur: L26 EDWARD is assigned/set aside (6.2)")
    res = _IMMEDIATE[cid](state, side, action.get("decisions", {}))
    state.decks.setdefault(side, {}).setdefault("discard", []).append(cid)
    return {"type": "play_event", "card": cid, "side": side, **res}
