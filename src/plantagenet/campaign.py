"""Campaign phase: Plan, Activation, Commands, Feed, and End Campaign (4.x).

  - Plan (4.1): build per-side ordered stacks of Command cards (Lord
    activations + Pass), sized by the season.
  - Activation (4.2): Rebel then King alternate revealing their top card;
    the shown Lord takes up to its Command rating in Command actions.
  - Commands live in `commands.py` (March/Sail/Tax/Parley/Supply/...) and
    here: forage (4.6.2), pass (4.6.5).
  - Feed (4.7): Moved-Fought Lords feed after each card.
  - End Campaign (4.8): Tides of War (4.8.1), Disembark (4.8.2), Victory
    check (4.8.3 / 5.x), Grow (4.8.4), Waste (4.8.5), Reset / advance Turn
    (4.8.6). A rolled-over Turn re-enters the Levy at the Arts of War draw.

Combat (Approach/Battle) lives in `battle.py`.
"""

from __future__ import annotations

from typing import Any

from plantagenet import influence, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus, Side

SIDES = ("lancastrian", "yorkist")
AREAS = ("north", "south", "wales")
SPECIAL_TIDES = {"london": 2, "calais": 2, "harlech": 1}
MOST_FAVOUR_TIDES = {"city": 2, "town": 1, "fortress": 1}


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def season_info(box: int) -> dict[str, Any]:
    """Season facts for a Calendar box (4.1 card count, 4.8.1/.4/.5 flags)."""
    idx = (box - 1) % 5
    name, cards, gain = [
        ("Jan-Feb-Mar", 4, True),
        ("Apr-May", 6, False),
        ("Jun-Jul", 7, False),
        ("Aug-Sep", 6, True),
        ("Oct-Nov-Dec", 4, False),
    ][idx]
    return {"season": name, "cards": cards, "gain_lords_influence": gain,
            "grow": box in (4, 9, 14), "waste": box in (5, 10)}


def _rebel(state: GameState) -> str:
    return [s for s, r in state.roles.items() if r == "rebel"][0]


def _king(state: GameState) -> str:
    return [s for s, r in state.roles.items() if r == "king"][0]


def _command_rating(lord_id: str) -> int:
    return static_data.load_lords()[lord_id]["ratings"]["command"]


# --------------------------------------------------------------- begin
def begin_campaign(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    _require(state.phase == "levy" and state.levy_step == "done", "levy_not_done",
             "the Levy must be complete before the Campaign (4.0)")
    from plantagenet.state import CampaignState
    info = season_info(state.turn_box)
    state.phase = "campaign"
    state.campaign = CampaignState(step="plan", cards_required=info["cards"],
                                   plan_index={s: 0 for s in SIDES},
                                   plan_built={s: False for s in SIDES})
    from plantagenet import commands
    for _l in state.lords.values():                # Y14/Y23 Burgundians: Lords already at a Port
        commands._apply_burgundians(state, _l)
    for lid, lord in state.lords.items():        # L22 Stafford Estates (Buckingham)
        if lord.status == LordStatus.MUSTERED and \
                ratings.has_capability(state, lid, "STAFFORD ESTATES"):
            lord.assets["coin"] = lord.assets.get("coin", 0) + 1
            lord.assets["provender"] = lord.assets.get("provender", 0) + 1
    return {"type": "begin_campaign", "season": info["season"],
            "cards_required": info["cards"]}


# ---------------------------------------------------------------- 4.1 Plan
def build_plan(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = action.get("side")
    _require(side in SIDES, "bad_side", "side must be a valid side")
    c = state.campaign
    _require(c is not None and c.step == "plan", "wrong_step", "not in the Plan step (4.1)")
    _require(not c.plan_built.get(side), "plan_already_built", f"{side} already built its Plan")
    plan = action.get("plan")
    _require(isinstance(plan, list), "bad_plan", "plan must be a list of entries")
    _require(len(plan) == c.cards_required, "wrong_plan_size",
             f"Plan must use exactly {c.cards_required} cards this season (4.1)")
    per_lord: dict[str, int] = {}
    norm: list[dict[str, Any]] = []
    for entry in plan:
        if entry.get("pass"):
            norm.append({"pass": True})
            continue
        lid = entry.get("lord")
        _require(lid in state.lords and state.lords[lid].side == side, "bad_plan_lord",
                 f"{lid!r} is not a {side} Lord")
        _require(state.lords[lid].status == LordStatus.MUSTERED, "plan_lord_not_in_play",
                 f"{lid} is not Mustered -- a Plan is built from Lords in play (4.1)")
        per_lord[lid] = per_lord.get(lid, 0) + 1
        _require(per_lord[lid] <= 3, "too_many_activations",
                 f"each Lord has only three Command cards (4.1.1): {lid}")
        norm.append({"lord": lid})
    c.plans[side] = norm
    c.plan_built[side] = True
    if all(c.plan_built.get(s) for s in SIDES):
        c.step = "activation"
        state.active_side = _rebel(state)   # Rebels flip first (4.2)
        _reveal(state)
    return {"type": "build_plan", "side": side, "built": c.plan_built,
            "step": c.step}


# ------------------------------------------------------------ 4.2 Activation
def _reveal(state: GameState) -> None:
    """Reveal the active side's current top card and set up its Activation."""
    c = state.campaign
    side = state.active_side
    entry = c.plans[side][c.plan_index[side]]
    lid = entry.get("lord")
    on_map = (lid is not None and lid in state.lords
              and state.lords[lid].status == LordStatus.MUSTERED)
    if entry.get("pass") or not on_map:
        c.active_lord = None          # Pass card or off-map Lord -> do nothing (4.2.3)
        c.actions_remaining = 0
    else:
        c.active_lord = lid
        c.actions_remaining = ratings.rating(state, lid, "command")


def _active_command_lord(state: GameState, action: dict[str, Any]):
    side = action.get("side")
    c = state.campaign
    _require(c is not None and c.step == "activation", "wrong_step",
             "Command actions require the Activation step (4.2)")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's Activation")
    _require(c.active_lord is not None, "no_active_lord",
             "no Lord is Activated (Pass card or off-map); end the Activation")
    _require(c.actions_remaining > 0, "no_actions_left",
             "the Active Lord has no Command actions remaining (4.2.1)")
    by = action.get("by_lord", c.active_lord)
    _require(by == c.active_lord, "wrong_lord", f"the Active Lord is {c.active_lord}")
    return state.lords[c.active_lord]


def end_activation(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = action.get("side")
    c = state.campaign
    _require(c is not None and c.step == "activation", "wrong_step", "not Activating")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's Activation")
    state.flags.pop("surprise_march_lord", None)   # L33 grant does not carry over
    # 4.7 Feed at end of each card for BOTH sides, Rebel then King.
    feed = {s: _feed(state, s) for s in (_rebel(state), _king(state))}
    c.plan_index[side] += 1
    c.active_lord = None
    c.actions_remaining = 0
    other = _other(side)
    if c.plan_index[other] < c.cards_required:
        state.active_side = other
        _reveal(state)
    elif c.plan_index[side] < c.cards_required:
        _reveal(state)                        # other exhausted; continue this side
    else:
        c.step = "end"                        # both Plan stacks exhausted (4.8)
    return {"type": "end_activation", "side": side, "step": c.step, "feed": feed,
            "next_side": state.active_side if c.step == "activation" else None}


def _other(side: str) -> str:
    return Side.YORKIST.value if side == Side.LANCASTRIAN.value else Side.LANCASTRIAN.value


# ----------------------------------------------------------- 4.6.2 Forage
def forage(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = _active_command_lord(state, action)
    loc = _lord_locale(lord)
    _require(loc is not None, "lord_not_on_locale", "the Lord must be at a Locale to Forage")
    kind, here = loc
    if kind == "exile":
        ls = None  # Exile-box Depletion is tracked in state.exile_depletion, not LocaleState
        _require(state.exile_depletion.get(here) != "exhausted", "exhausted",
                 f"{here} (Exile box) is Exhausted and may not be Foraged (4.6.2)")
    else:
        ls = state.locales[here]
        _require(ls.depletion != "exhausted", "exhausted",
                 f"{here} is Exhausted and may not be Foraged (4.6.2)")
    fav = "friendly" if (kind == "exile" or ls.favour == lord.side) else (
        "enemy" if (kind == "stronghold" and ls.favour == _other(lord.side)) else "neutral")
    enemy_adjacent = _enemy_lord_adjacent(state, here, lord.side) if kind == "stronghold" else False

    roll = None
    if fav == "friendly" and not enemy_adjacent:
        success = True                              # automatic (4.6.2)
    else:
        roller = state.dice()
        roll = roller.d6()
        state.store_dice(roller)
        threshold = 3 if (fav == "enemy" or enemy_adjacent) else 4
        success = roll <= threshold
    state.campaign.actions_remaining -= 1
    added = 0
    if success:
        gain = 1 + (1 if ratings.has_capability(state, lord.lord_id, "SCOURERS") else 0)
        lord.assets["provender"] = lord.assets.get("provender", 0) + gain  # Y13 Scourers +1
        added = gain
        if ls is not None:
            ls.depletion = "exhausted" if ls.depletion == "depleted" else "depleted"
        elif kind == "exile":                       # Deplete, else Exhaust (4.6.2)
            cur = state.exile_depletion.get(here)
            state.exile_depletion[here] = "exhausted" if cur == "depleted" else "depleted"
    return {"type": "forage", "by_lord": lord.lord_id, "locale": here,
            "favour": fav, "enemy_adjacent": enemy_adjacent, "roll": roll,
            "success": success, "provender_added": added}


def pass_command(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    lord = _active_command_lord(state, action)
    state.campaign.actions_remaining -= 1
    return {"type": "pass", "by_lord": lord.lord_id}


# --------------------------------------------------------------- helpers
def _lord_locale(lord):
    if lord.location is not None:
        return ("stronghold", lord.location)
    if lord.exile_box is not None:
        return ("exile", lord.exile_box)
    return None


def _enemy_lord_adjacent(state: GameState, locale_id: str, side: str) -> bool:
    from plantagenet.actions import _adjacency, enemy_lord_at
    for nbr, _t in _adjacency().get(locale_id, []):
        if enemy_lord_at(state, nbr, side):
            return True
    return False


# ------------------------------------------------------- 3.2.1 Pillage
def _pillage(state: GameState, lord, locale_id: str) -> dict[str, Any]:
    """A Lord Pillages an Unexhausted Stronghold (3.2.1): gain Coin+Provender
    per the Strongholds table; the side loses 2x the Assets gained; Exhaust
    and set Enemy Favour; shift each Way-adjacent Stronghold one level toward
    Enemy Favour."""
    from plantagenet.actions import _adjacency
    yields = static_data.stronghold_yields(locale_id).get("pillage", {})
    gained = 0
    for asset, amt in yields.items():
        lord.assets[asset] = lord.assets.get(asset, 0) + amt
        gained += amt
    foe = _other(lord.side)
    influence.spend_influence(state, lord.side, 2 * gained)   # lose 2x Assets (toward foe)
    state.locales[locale_id].depletion = "exhausted"
    state.locales[locale_id].favour = foe
    for nbr, _t in _adjacency().get(locale_id, []):
        nb = state.locales[nbr]
        if nb.favour == lord.side:
            nb.favour = "neutral"
        elif nb.favour == "neutral":
            nb.favour = foe
    return {"locale": locale_id, "assets_gained": gained, "influence_lost": 2 * gained}


# ------------------------------------------------------- 3.2.4 Disband
def _release_captive(state: GameState, holder_id: str) -> None:
    """Capture of the King: if ``holder_id`` (a Yorkist Lord holding Henry VI)
    leaves play, place Henry VI on the Calendar as if just Disbanded and the
    Lancastrians gain +10 Influence."""
    for ls in state.lords.values():
        if ls.captured_by == holder_id and ls.status == LordStatus.CAPTURED:
            ls.captured_by = None
            ls.status = LordStatus.CALENDAR
            cap_inf = static_data.load_lords()[ls.lord_id]["ratings"]["influence"]
            ls.calendar_box = state.turn_box + (6 - cap_inf)   # "as if just Disbanded" (3.2.4)
            ls.location = ls.exile_box = None
            ls.calendar_exile = False
            influence.gain_influence(state, "lancastrian", 10)


def _disband_lord(state: GameState, lord, *, from_exile: bool = False) -> None:
    """Disband a Lord (3.2.4): Disband its Vassals, return Forces/Assets, and
    place the cylinder on the Calendar 6-minus-Influence boxes right of the
    current Turn (Exile-marked if Disbanding from an Exile box)."""
    _release_captive(state, lord.lord_id)        # Capture of the King: free any captive
    inf = static_data.load_lords()[lord.lord_id]["ratings"]["influence"]
    for vid in list(lord.vassals):
        _disband_vassal(state, vid)
    lord.vassals = []
    # Discard the Lord's Capability cards (or set aside per Succession, 6.2) and
    # release Special Vassals (1.5.3, 4.4.3).
    set_aside = set()
    if state.grand_scenario:
        from plantagenet import succession
        set_aside = set(succession.set_aside_cards(state, lord.lord_id))
    for cid in list(lord.capabilities):
        pile = "set_aside" if cid in set_aside else "discard"
        state.decks.setdefault(lord.side, {}).setdefault(pile, []).append(cid)
    lord.capabilities = []
    lord.special_vassals = []
    lord.forces = {}
    lord.assets = {}
    lord.location = None
    lord.exile_box = None
    lord.at_sea = None            # a Disbanded Lord goes to the Calendar -- clear
    lord.captured_by = None       # every map/sea position so it is in one place
    lord.status = LordStatus.CALENDAR
    lord.calendar_box = state.turn_box + (6 - inf)
    lord.calendar_exile = from_exile


def _disband_special_vassal(state: GameState, lord, vid: str) -> None:
    """Disband a Special Vassal (3.2.4): remove it from the Lord's mat. Special
    Vassals have no Seat/Service/Calendar, so they simply leave play; the
    Capability that Mustered it (e.g. Y24 Hastings) is discarded (1.5.4). The
    one-time Force addition (Hastings' 2 Men-at-Arms) is NOT removed here."""
    if vid in lord.special_vassals:
        lord.special_vassals.remove(vid)
    sv = static_data.load_vassals()["special"].get(vid, {})
    cap = sv.get("capability_card")
    if cap and cap in lord.capabilities:
        lord.capabilities.remove(cap)
        state.decks.setdefault(lord.side, {}).setdefault("discard", []).append(cap)


def _disband_vassal(state: GameState, vid: str) -> None:
    """Disband a Vassal (3.2.4): place it facedown on the Calendar
    6-minus-Service boxes right of the current Turn; it returns to its Seat
    when the Turn reaches that box (3.3.2)."""
    from plantagenet.state import VassalStatus
    vs = state.vassals.get(vid)
    if vs is None:
        return
    service = static_data.load_vassals()["regular"].get(vid, {}).get("service", 0)
    vs.status = VassalStatus.DISBANDED
    vs.on_lord = None
    vs.service_box = state.turn_box + (6 - service)


def ready_vassals(state: GameState) -> list[str]:
    """Ready Vassals (3.3.2): return Disbanded Vassals from the current Turn
    box to their Seat, face up."""
    from plantagenet.state import VassalStatus
    regular = static_data.load_vassals()["regular"]
    returned = []
    for vid, vs in state.vassals.items():
        if vs.status == VassalStatus.DISBANDED and vs.service_box == state.turn_box:
            vs.status = VassalStatus.AT_SEAT
            vs.location = regular[vid]["seat"]
            vs.service_box = None
            returned.append(vid)
    return returned


# ----------------------------------------------------------------- 4.7 Feed
def _co_located_group(state: GameState, lord) -> list:
    """Friendly Mustered Lords sharing ``lord``'s position (same Locale or Exile
    box), the Lord itself first -- the Sharing group for Assets (1.5.3)."""
    pos = (lord.location, lord.exile_box)
    if pos == (None, None):
        return [lord]
    group = [lord]
    for m in state.lords.values():
        if (m is not lord and m.side == lord.side and m.status == LordStatus.MUSTERED
                and (m.location, m.exile_box) == pos):
            group.append(m)
    return group


def _drain_provender(group: list, amount: int) -> None:
    """Remove ``amount`` Provender from a co-located group (Sharing, 1.5.3),
    drawing from the first Lord's mat before its allies'."""
    for m in group:
        if amount <= 0:
            break
        take = min(m.assets.get("provender", 0), amount)
        m.assets["provender"] = m.assets.get("provender", 0) - take
        amount -= take


def _feed(state: GameState, side: str) -> dict[str, Any]:
    """Moved-Fought Lords remove 1 Provender per 6 Troops, rounded up (4.7).
    A Lord short on Provender Pillages its Locale (if an Unexhausted
    Stronghold) and Feeds from the gain; if still short, it Unfed-Disbands,
    costing the side its Influence rating + 1 per Vassal (3.2.1)."""
    fed: list[dict[str, Any]] = []
    disbanded: list[str] = []
    for lid, lord in list(state.lords.items()):
        if lord.side != side or not lord.moved_fought:
            continue
        lord.moved_fought = False
        if lord.ignore_next_feed:           # Rebel Supply Depot (L28)
            lord.ignore_next_feed = False
            fed.append({"lord": lid, "skipped": "rebel_supply_depot"})
            continue
        need = -(-_troop_count(lord) // 6)  # ceil(troops / 6)
        # Sharing (1.5.3): a Lord Feeds from the Provender of all Friendly Lords
        # at its Locale, not just its own mat.
        group = _co_located_group(state, lord)
        have = sum(m.assets.get("provender", 0) for m in group)
        if have < need:
            loc = _lord_locale(lord)
            if (loc is not None and loc[0] == "stronghold"
                    and state.locales[loc[1]].depletion != "exhausted"):
                _pillage(state, lord, loc[1])
                have = sum(m.assets.get("provender", 0) for m in group)
        spend = min(need, have)
        _drain_provender(group, spend)   # own mat first, then co-located allies
        if spend < need:   # still Unfed -> Disband, with Influence penalty (3.2.1)
            inf = static_data.load_lords()[lid]["ratings"]["influence"]
            penalty = inf + len(lord.vassals)
            influence.spend_influence(state, side, penalty)
            _disband_lord(state, lord, from_exile=lord.exile_box is not None)
            disbanded.append(lid)
        else:
            fed.append({"lord": lid, "fed": spend, "needed": need})
    return {"fed": fed, "disbanded": disbanded}


def _troop_count(lord) -> int:
    forces_static = static_data.load_forces()
    return sum(n for f, n in lord.forces.items()
              if f != "retinue" and f in forces_static)  # Troops only (not Retinue/Vassal)


# ----------------------------------------------------------- 4.8.1 Tides
# Capability-based Tides effects (Arts of War, 1.9.1).
# Region-Domination overrides: holder Mustered in the area + >= N Friendly
# Strongholds there lets the side Dominate even without all-Favour.
_CAP_DOMINATION = {
    "WELSHMEN": ("wales", 3),
    "SOUTHERNERS": ("south", 5),
    "NORTHMEN": ("north", 3),
}


def _cap_holders(state: GameState, title: str) -> list[str]:
    cards = static_data.load_cards()
    return [lid for lid, ls in state.lords.items()
            if any(cards[c]["capability"]["title"] == title for c in ls.capabilities)]


def _cap_dominates(state: GameState, side: str, area: str, in_area: list[str]) -> bool:
    friendly = sum(1 for loc in in_area if state.locales[loc].favour == side)
    for title, (a, thr) in _CAP_DOMINATION.items():
        if a != area:
            continue
        for lid in _cap_holders(state, title):
            ls = state.lords[lid]
            if (ls.side == side and ls.status == LordStatus.MUSTERED
                    and ls.location in in_area and friendly >= thr):
                return True
    return False


def _foreign_haven_shift(state: GameState) -> None:
    """Foreign Haven (IIY / Warwick's Rebellion): when Warwick chooses Exile on
    Approach or dies as a defender, shift all Lancastrians on the Calendar left
    to the current Turn box and all Yorkists left to the next Turn box."""
    cur = state.turn_box
    for ls in state.lords.values():
        if ls.status == LordStatus.CALENDAR and ls.calendar_box is not None:
            if ls.side == "lancastrian" and ls.calendar_box > cur:
                ls.calendar_box = cur
            elif ls.side == "yorkist" and ls.calendar_box > cur + 1:
                ls.calendar_box = cur + 1


def _active_special_rules(state: GameState) -> set:
    """Names of the special rules in force for the current scenario or, in the
    grand scenario, the current War (read from the scenario data)."""
    if state.grand_scenario:
        wars = {w["war_id"]: w for w in static_data.load_scenario("wars_of_the_roses")["wars"]}
        rules = (wars.get(state.grand_scenario.get("current_war")) or {}).get("special_rules", [])
    else:
        scn = static_data.load_scenario(state.scenario)
        rules = scn.get("setup", {}).get("special_rules") or scn.get("special_rules") or []
    return {r["name"] for r in rules if isinstance(r, dict) and "name" in r}


def tides_of_war(state: GameState, decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    locales = static_data.load_locales()
    lords_static = static_data.load_lords()
    pts = {s: 0 for s in SIDES}
    detail: list[str] = []

    # Areas: +1 per side with a Lord present; +2 for Dominance (all Favour).
    for area in AREAS:
        in_area = [lid for lid in locales if locales[lid].get("region") == area]
        for side in SIDES:
            if any(v.status == LordStatus.MUSTERED and v.location in in_area
                   and v.side == side for v in state.lords.values()):
                pts[side] += 1
                detail.append(f"{side} +1 Lord in {area}")
            all_favour = bool(in_area) and all(
                state.locales[loc].favour == side for loc in in_area)
            if all_favour or _cap_dominates(state, side, area, in_area):
                pts[side] += 2
                detail.append(f"{side} +2 Dominates {area}")

    # Special Strongholds: individual Favour award unless an Enemy Lord occupies.
    for sp, amt in SPECIAL_TIDES.items():
        fav = state.locales[sp].favour
        if fav in SIDES:
            foe = _other(fav)
            occupied_by_enemy = any(v.status == LordStatus.MUSTERED and v.location == sp
                                    and v.side == foe for v in state.lords.values())
            if not occupied_by_enemy:
                pts[fav] += amt
                detail.append(f"{fav} +{amt} Favour at {sp}")

    # Most Favour by regular type: +2 city, +1 town, +1 fortress.
    for typ, amt in MOST_FAVOUR_TIDES.items():
        counts = {s: sum(1 for lid, lc in locales.items()
                         if lc["type"] == typ and state.locales[lid].favour == s)
                  for s in SIDES}
        if counts["lancastrian"] != counts["yorkist"]:
            leader = max(SIDES, key=lambda s: counts[s])
            pts[leader] += amt
            detail.append(f"{leader} +{amt} most Favour {typ}s ({counts})")

    # Gain Lords Influence (Jan-Feb-Mar and Aug-Sep Turns).
    if season_info(state.turn_box)["gain_lords_influence"]:
        for side in SIDES:
            tot = sum(lords_static[lid]["ratings"]["influence"]
                      for lid, v in state.lords.items()
                      if v.side == side
                      and v.status in (LordStatus.MUSTERED, LordStatus.EXILE))
            pts[side] += tot
            detail.append(f"{side} +{tot} Lords' Influence")

    # Queen Regent (Warwick's Rebellion special rule): Margaret at London -> +3.
    if "Queen Regent" in _active_special_rules(state):
        mg = state.lords.get("margaret")
        if mg is not None and mg.status == LordStatus.MUSTERED and mg.location == "london":
            pts["lancastrian"] += 3
            detail.append("lancastrian +3 Queen Regent")

    # Capability flat Influence bonuses (1.9.1).
    glos_set_aside = bool((state.grand_scenario or {}).get("gloucester_as_heir_played"))
    for lid in (() if glos_set_aside else _cap_holders(state, "FIRST SON")):   # Y28 (Edward IV)
        # Gloucester special rule: once Y28 GLOUCESTER AS HEIR is played/set aside,
        # the FIRST SON Capability becomes unavailable (IIY/IIL).
        if state.lords[lid].status == LordStatus.MUSTERED:
            sd = state.lords[lid].side
            pts[sd] += 1
            detail.append(f"{sd} +1 First Son")
    for lid in _cap_holders(state, "COUNCIL MEMBER"):      # L18 (anywhere on map incl. Exile)
        if state.lords[lid].status in (LordStatus.MUSTERED, LordStatus.EXILE):
            sd = state.lords[lid].side
            pts[sd] += 1
            detail.append(f"{sd} +1 Council Member")
    for lid in _cap_holders(state, "MARGARET TAKES THE REINS"):  # L17 (Henry VI)
        ls = state.lords[lid]
        # +2 while at a Stronghold outside London OR in an Exile box (1.3.1).
        on_map_outside_london = (ls.status == LordStatus.MUSTERED
                                 and ls.location not in (None, "london"))
        if ls.exile_box is not None or on_map_outside_london:
            pts[ls.side] += 2
            detail.append(f"{ls.side} +2 Margaret Takes the Reins")

    # We Done Deeds of Charity (Y4): pay 1 or 2 Provender for +1 Influence each.
    # (Sharing 1.5.3 is the consumer's job: move Provender onto the holder first.)
    charity = (decisions or {}).get("charity", {})
    for lid in _cap_holders(state, "WE DONE DEEDS OF CHARITY"):
        ls = state.lords[lid]
        if ls.status != LordStatus.MUSTERED:
            continue
        pay = int(charity.get(lid, 0))
        if pay not in (0, 1, 2):
            raise IllegalAction("bad_charity",
                                "We Done Deeds of Charity pays 0, 1, or 2 Provender (Y4)")
        if pay:
            have = ls.assets.get("provender", 0)
            if pay > have:
                raise IllegalAction("no_provender",
                                    f"{lid} lacks {pay} Provender for Deeds of Charity (Y4)")
            ls.assets["provender"] = have - pay
            pts[ls.side] += pay
            detail.append(f"{ls.side} +{pay} Deeds of Charity")

    return {"points": pts, "detail": detail}


# ----------------------------------------------------- 4.8.3 Victory check
def _side_influence(state: GameState, side: str) -> int:
    t = state.influence.get("track")
    if t is None:
        return 0
    return t.marker_at if t.marker_side == side else 0


def _current_threshold(state: GameState) -> int | None:
    from plantagenet.static_data import load_scenario
    if state.grand_scenario:                       # per-War flat threshold (5.2)
        return state.grand_scenario.get("victory_threshold")
    scn = load_scenario(state.scenario)
    best = None
    for vt in scn.get("victory_thresholds", []):
        turns = vt["turns"]
        if turns == "all":
            best = vt["influence"]
        else:
            lo, hi = (int(x) for x in turns.split("-"))
            if lo <= state.turn_box <= hi:
                best = vt["influence"]
    return best


def _victory_check(state: GameState) -> dict[str, Any] | None:
    # 5.1 Campaign Victory: a side with no Lords on map and no next-Turn Exiles loses.
    def has_presence(side: str) -> bool:
        # 5.1 counts a Lord as present if Mustered on the map OR sitting in an
        # Exile box ("including none in Exile boxes"), OR a cylinder marked Exile
        # arriving in the next Turn's Calendar box.
        on_map = any(v.side == side
                     and v.status in (LordStatus.MUSTERED, LordStatus.EXILE)
                     for v in state.lords.values())
        next_exile = any(v.side == side and v.status == LordStatus.CALENDAR
                         and v.calendar_exile and v.calendar_box == state.turn_box + 1
                         for v in state.lords.values())
        return on_map or next_exile
    l_pres, y_pres = has_presence("lancastrian"), has_presence("yorkist")
    if not l_pres or not y_pres:
        if not l_pres and not y_pres:
            return {"result": "draw", "rule": "5.1"}
        # The side WITHOUT presence loses; the other side wins (5.1).
        return {"result": "lancastrian" if l_pres else "yorkist", "rule": "5.1"}
    # 5.2 Threshold Victory.
    thr = _current_threshold(state)
    if thr is not None:
        for side in SIDES:
            if _side_influence(state, side) >= thr:
                return {"result": side, "rule": "5.2", "threshold": thr}
    # Test of Arms (Towton): at Campaign end, the side with Favour at York wins.
    if "Test of Arms" in _active_special_rules(state) \
            and state.turn_box >= (state.calendar.last_box or state.turn_box):
        fav = state.locales["york"].favour
        return {"result": fav if fav in SIDES else "draw", "rule": "Test of Arms"}
    # 5.3 Scenario End (final Turn).
    if state.turn_box >= (state.calendar.last_box or state.turn_box):
        li, yi = _side_influence(state, "lancastrian"), _side_influence(state, "yorkist")
        if li == yi:
            # Errata & Clarification FAQ #5: if a scenario is Tied (Influence
            # at 0) at Scenario End, victory goes to the King's side -- not a
            # draw. (Also keeps a grand-scenario War transitionable via 6.1.)
            return {"result": _king(state), "rule": "5.3",
                    "tie_break": "FAQ #5: tie goes to the King's side"}
        return {"result": "lancastrian" if li > yi else "yorkist", "rule": "5.3"}
    return None


# ------------------------------------------------------------ end_campaign
def _disembark(state: GameState, decisions: dict[str, Any] | None) -> dict[str, Any]:
    """4.8.2 Disembark: each Lord at Sea (first Rebel then King) rolls a die.
    Shipwreck (1-4): permanent removal with the Unpaid penalty (3.2.1, printed
    Influence + 1 per Vassal) and Succession (6.2.2). Land (5-6): to a chosen
    Enemy-free Port on that Sea, then it must immediately Feed (4.7); a Lord that
    cannot reach a free Port instead Disbands normally (3.2.4). No Events
    influence the roll (1.9.1)."""
    from plantagenet import battle
    from plantagenet.actions import enemy_lord_at
    decisions = decisions or {}
    land = decisions.get("disembark_land", {})         # lord_id -> chosen Port
    zones = static_data.load_seas()["zones"]
    roller = state.dice()
    rebel = next(s for s, r in state.roles.items() if r == "rebel")
    king = next(s for s, r in state.roles.items() if r == "king")
    rolls: list[dict[str, Any]] = []
    landed_sides: set[str] = set()
    for side in (rebel, king):
        for lid in [x for x, ls in state.lords.items()
                    if ls.side == side and ls.at_sea is not None]:
            ls = state.lords[lid]
            sea = ls.at_sea
            roll = roller.d6()
            if roll <= 4:                              # Shipwreck (permanent, like Death)
                inf = static_data.load_lords()[lid]["ratings"]["influence"]
                penalty = inf + len(ls.vassals)
                influence.spend_influence(state, side, penalty)   # Unpaid penalty (3.2.1)
                ls.at_sea = None
                battle._kill_lord(state, lid)                     # remove + Succession (6.2.2)
                rolls.append({"lord": lid, "roll": roll, "shipwreck": True,
                              "influence_lost": penalty})
            else:                                      # Land (5-6)
                free_ports = [p for p in zones[sea].get("ports", [])
                              if not enemy_lord_at(state, p, side)]
                choice = land.get(lid)
                if choice not in free_ports and free_ports:
                    choice = free_ports[0]   # default landing Port (overridable via disembark_land)
                if choice in free_ports:
                    ls.at_sea = None
                    ls.location = choice
                    ls.status = LordStatus.MUSTERED
                    ls.moved_fought = True             # must immediately Feed (4.7)
                    landed_sides.add(side)
                    rolls.append({"lord": lid, "roll": roll, "landed": choice})
                else:                                  # no free Port reachable -> Disband
                    ls.at_sea = None
                    _disband_lord(state, ls)
                    rolls.append({"lord": lid, "roll": roll, "disbanded": True})
    state.store_dice(roller)
    feed = {s: _feed(state, s) for s in (rebel, king) if s in landed_sides}
    return {"rolls": rolls, "feed": feed}


def end_campaign(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    c = state.campaign
    _require(c is not None and c.step == "end", "wrong_step",
             "the Campaign ends only after both Plan stacks are exhausted (4.8)")
    # 4.8.1 Tides of War
    tow = tides_of_war(state, action.get("decisions"))
    influence.gain_influence(state, "lancastrian", tow["points"]["lancastrian"])
    influence.gain_influence(state, "yorkist", tow["points"]["yorkist"])
    # 4.8.2 Disembark (Shipwreck may set an Automatic War Victory via Succession).
    disembark = _disembark(state, action.get("decisions"))
    # 4.8.3 Victory check
    victory = state.victory or _victory_check(state)
    info = season_info(state.turn_box)
    grown = wasted = False
    if victory is None:
        rules = _active_special_rules(state)
        ravaged = "Ravaged Land" in rules                 # IIIY/IIIL/My Kingdom: skip Grow+Waste
        skip_waste = ravaged or "Brief Rebellion" in rules  # Somerset's Return: skip Waste
        if info["grow"] and not ravaged:      # 4.8.4 Grow
            _grow(state)
            grown = True
        if info["waste"] and not skip_waste:  # 4.8.5 Waste
            _waste(state)
            wasted = True
        _reset_to_next_levy(state)            # 4.8.6
    else:
        state.phase = "over"
        state.victory = victory
    return {"type": "end_campaign", "tides_of_war": tow, "disembark": disembark,
            "victory": victory, "grow": grown, "waste": wasted,
            "turn_box": state.turn_box, "phase": state.phase}


def _grow(state: GameState) -> None:
    for ls in state.locales.values():
        if ls.depletion == "depleted":
            ls.depletion = None
        elif ls.depletion == "exhausted":
            ls.depletion = "depleted"
    for box, dep in list(state.exile_depletion.items()):   # Exile boxes recover too (4.8.4)
        if dep == "depleted":
            state.exile_depletion.pop(box, None)
        elif dep == "exhausted":
            state.exile_depletion[box] = "depleted"


def _waste(state: GameState) -> None:
    lords_static = static_data.load_lords()
    for lid, lord in state.lords.items():
        if lord.status != LordStatus.MUSTERED:
            continue
        for asset in ("provender", "cart", "ship"):
            if lord.assets.get(asset):
                lord.assets[asset] = -(-lord.assets[asset] // 2)  # halve, round up
        start = lords_static[lid]
        # Coin and Troops reset to setup; keep Mercenaries/Handgunners (4.8.5).
        lord.assets["coin"] = start["assets"].get("coin", 0)
        keep = {f: lord.forces[f] for f in ("mercenaries", "handgunners") if f in lord.forces}
        lord.forces = dict(start.get("forces", {}))
        for f, n in keep.items():
            lord.forces[f] = max(lord.forces.get(f, 0), n)


def _reset_to_next_levy(state: GameState) -> None:
    from plantagenet.events import expire_scope
    expire_scope(state, "this_campaign")  # discard expired This-Campaign Event cards (no leak)
    state.turn_box += 1
    state.phase = "levy"
    # A rolled-over Turn begins at the Arts of War draw (3.1), then Pay (3.2),
    # then the Muster window (Muster Exiles 3.3.1 + Muster 3.4).
    state.levy_step = "arts_of_war"
    state.campaign = None
    state.active_side = _rebel(state)
    for lord in state.lords.values():
        lord.lordship_spent = 0
        lord.mustered_this_segment = False
        lord.moved_fought = False
        lord.free_troops_used = False
