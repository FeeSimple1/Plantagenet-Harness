"""Levy Pay step (3.2): Pay Troops, Pay Lords, Pay Vassals.

Runs Rebel then King on a rolled-over Turn (Pay is skipped on the
scenario's first Turn, 3.2). Reuses `campaign._pillage` and
`campaign._disband_lord`. Player choices are optional action args with
deterministic defaults:
  - ``disband_lords``: Lords to voluntarily Disband (3.2.2).
  - ``pillage_by``: {locale: lord_id} choosing the Pillaging Lord (3.2.1).
  - ``unpay_vassals``: due Vassals to NOT pay (they Disband, 3.2.3).
"""

from __future__ import annotations

from typing import Any

from plantagenet import campaign, influence, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus, VassalStatus

SIDES = ("lancastrian", "yorkist")


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _troop_pay_need(lord) -> int:
    return -(-campaign._troop_count(lord) // 6)   # 1 Coin per 6 Troops, rounded up


def _locale_key(lord) -> str | None:
    if lord.location is not None:
        return f"loc:{lord.location}"
    if lord.exile_box is not None:
        return f"exile:{lord.exile_box}"
    return None


def pay(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = action.get("side")
    _require(side in SIDES, "bad_side", "side must be a valid side")
    _require(state.phase == "levy" and state.levy_step == "pay", "wrong_step",
             "Pay runs in the Levy Pay step (3.2)")
    _require(side == state.active_side, "not_active_side",
             f"it is the {state.active_side} side's Pay (Rebel then King, 3.2)")

    # Madame La Grande (L37): +1 Coin each Pay if at/adjacent a Friendly English
    # Channel Port.
    madame = []
    for lid, lord in state.lords.items():
        if (lord.side == side and lord.status == LordStatus.MUSTERED
                and ratings.has_capability(state, lid, "MADAME LA GRANDE")
                and _at_adj_friendly_ec_port(state, lord)):
            lord.assets["coin"] = lord.assets.get("coin", 0) + 1
            madame.append(lid)

    result: dict[str, Any] = {"type": "pay", "side": side}
    if madame:
        result["madame_la_grande"] = madame
    result["troops"] = _pay_troops(state, side, action)
    result["lords"] = _pay_lords(state, side, action)
    result["vassals"] = _pay_vassals(state, side, action)

    rebel = [s for s, r in state.roles.items() if r == "rebel"][0]
    king = [s for s, r in state.roles.items() if r == "king"][0]
    if side == rebel:
        state.active_side = king
        result["next"] = "king_pay"
    else:
        returned = campaign.ready_vassals(state)   # 3.3.2 Ready Vassals
        state.levy_step = "muster"
        state.active_side = rebel
        result["ready_vassals"] = returned
        result["next"] = "muster"
    return result


# --------------------------------------------------------- 3.2.1 Pay Troops
def _drain_coin(lords: list, amount: int) -> None:
    """Remove ``amount`` Coin from a co-located group (Sharing, 1.5.3)."""
    for lord in lords:
        if amount <= 0:
            break
        take = min(lord.assets.get("coin", 0), amount)
        lord.assets["coin"] = lord.assets.get("coin", 0) - take
        amount -= take


def _at_adj_friendly_ec_port(state: GameState, lord) -> bool:
    from plantagenet.commands import _adjacency
    ec = set(static_data.load_seas()["zones"]["english_channel"]["ports"])
    here = lord.location
    if here in ec and state.locales[here].favour == lord.side:
        return True
    return any(n in ec and state.locales[n].favour == lord.side
               for n, _t in _adjacency().get(here, []))


def _percys_power_free_north(state: GameState, side: str) -> bool:
    """Percy's Power (L14, Northumberland): Lancastrian Pay in the North is
    free while Northumberland (with the Capability) is in the North."""
    if side != "lancastrian":
        return False
    locales = static_data.load_locales()
    return any(lord.status == LordStatus.MUSTERED
               and locales.get(lord.location, {}).get("region") == "north"
               and ratings.has_capability(state, lid, "PERCY'S POWER")
               for lid, lord in state.lords.items() if lord.side == side)


def _pay_troops(state: GameState, side: str, action: dict[str, Any]) -> dict[str, Any]:
    pillage_by = action.get("pillage_by", {})
    # 3.2.1: on a shortfall the player chooses which Lords go unpaid; honour an
    # explicit ``unpay_lords`` list, else default to paying smallest-need first.
    choose_unpaid = set(action.get("unpay_lords", []))
    groups: dict[str, list] = {}
    for lord in state.lords.values():
        if lord.side == side and lord.status in (LordStatus.MUSTERED, LordStatus.EXILE):
            key = _locale_key(lord)
            if key:
                groups.setdefault(key, []).append(lord)

    free_north = _percys_power_free_north(state, side)
    locales_static = static_data.load_locales()
    paid_groups, pillaged, disbanded = [], [], []
    for key, lords in groups.items():
        is_stronghold = key.startswith("loc:")
        locale_id = key.split(":", 1)[1] if is_stronghold else None
        if (free_north and is_stronghold
                and locales_static.get(locale_id, {}).get("region") == "north"):
            paid_groups.append(key)             # Percy's Power: Pay is free here (L14)
            continue
        need = {lord.lord_id: _troop_pay_need(lord) for lord in lords}
        total_need = sum(need.values())
        pool = sum(lord.assets.get("coin", 0) for lord in lords)

        if pool >= total_need:
            _drain_coin(lords, total_need)
            paid_groups.append(key)
            continue

        # Shortfall: Pillage an Unexhausted Stronghold (3.2.1), then re-Pay.
        if (is_stronghold and state.locales[locale_id].depletion != "exhausted"):
            chooser = pillage_by.get(locale_id)
            pillager = next((lord for lord in lords if lord.lord_id == chooser), None)
            if pillager is None:   # default: the Lord with the most Troops
                pillager = max(lords, key=lambda x: campaign._troop_count(x))
            campaign._pillage(state, pillager, locale_id)
            pillaged.append(locale_id)
            pool = sum(lord.assets.get("coin", 0) for lord in lords)

        # Fully Pay as many Lords as possible; the rest Disband (3.2.1). If the
        # player named Lords to leave unpaid, Pay the others first (then ascending
        # need); otherwise default to ascending need.
        order = sorted(lords, key=lambda x: (x.lord_id in choose_unpaid, need[x.lord_id]))
        available = pool
        unpaid = []
        for lord in order:
            if lord.lord_id not in choose_unpaid and available >= need[lord.lord_id]:
                available -= need[lord.lord_id]
            else:
                unpaid.append(lord)
        _drain_coin(lords, pool - available)
        for lord in unpaid:
            inf = static_data.load_lords()[lord.lord_id]["ratings"]["influence"]
            influence.spend_influence(state, side, inf + len(lord.vassals))  # 3.2.1 penalty
            campaign._disband_lord(state, lord)
            disbanded.append(lord.lord_id)

    return {"paid_groups": paid_groups, "pillaged": pillaged, "unpaid_disbanded": disbanded}


# ---------------------------------------------------------- 3.2.2 Pay Lords
def _pay_lords(state: GameState, side: str, action: dict[str, Any]) -> dict[str, Any]:
    voluntary = action.get("disband_lords", [])
    disbanded = []
    for lid in voluntary:
        lord = state.lords.get(lid)
        _require(lord is not None and lord.side == side and lord.status == LordStatus.MUSTERED,
                 "bad_disband", f"{lid} is not a Mustered {side} Lord")
        campaign._disband_lord(state, lord, from_exile=lord.exile_box is not None)
        disbanded.append(lid)
    # Pay 1 Influence per Lord at a Stronghold, 2 per Lord in an Exile box (3.2.2).
    cost = 0
    for lord in state.lords.values():
        if lord.side != side or lord.status not in (LordStatus.MUSTERED, LordStatus.EXILE):
            continue
        cost += 2 if lord.exile_box is not None else 1
    if cost:
        influence.spend_influence(state, side, cost)
    return {"voluntary_disbanded": disbanded, "influence_paid": cost}


# -------------------------------------------------------- 3.2.3 Pay Vassals
def _pay_vassals(state: GameState, side: str, action: dict[str, Any]) -> dict[str, Any]:
    unpay = set(action.get("unpay_vassals", []))
    paid, disbanded = [], []
    vassals_static = static_data.load_vassals()["regular"]
    for vid, vs in state.vassals.items():
        if vs.status != VassalStatus.MUSTERED or vs.service_box != state.turn_box:
            continue
        lord = state.lords.get(vs.on_lord)
        if lord is None or lord.side != side:
            continue
        if vid in unpay:
            campaign._disband_vassal(state, vid)
            if vid in lord.vassals:
                lord.vassals.remove(vid)
            disbanded.append(vid)
        else:
            influence.spend_influence(state, side, 1)
            vs.service_box += 1     # shift the Vassal marker one box right (3.2.3)
            paid.append(vid)
    _ = vassals_static
    return {"paid": paid, "disbanded": disbanded}
