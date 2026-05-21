"""Battle engine (4.4) and Approach/Exile (4.3.5) — multi-Lord (3b-ii).

Handles any number of Lords per side. Each Round (4.4.2): Flee ->
Reposition (Rout removal, Reserve Advance, Center fill) -> Engage (with
Flanking) -> Strike (Missiles then Melee, per Engagement) -> Lord Rout,
until at least one side's Lords all Rout. Ending (4.4.3): winner Influence,
Spoils, Losses, Death/Disband.

Array positions are indexed 0=left, 1=center, 2=right; the Defender fills
center first then left/right, and the Attacker places opposite each Front
Defender (4.4.1). A Front Lord with no Lord directly opposite Engages the
nearest enemy Front Lord (Flanking).

Player choices use an optional ``decisions`` payload with deterministic
defaults: ``flee`` (lord ids), ``attacker_positions``/``defender_positions``
({index: lord_id}), ``absorb_order`` (unit-type priority), ``valour`` (bool).
"""

from __future__ import annotations

from math import ceil
from typing import Any

from plantagenet import campaign, influence, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus

_ABSORB_DEFAULT = ["militia", "mercenaries", "longbow", "handgunners",
                   "men_at_arms", "vassal", "retinue"]
_TROOP_TYPES = {"men_at_arms", "longbow", "militia", "mercenaries", "handgunners"}
_FILL_ORDER = [1, 0, 2]   # center, left, right (4.4.1)


def _strike_profile() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fid, f in static_data.load_forces().items():
        if fid.startswith("_"):
            continue
        missile = sum(s["count"] for s in f["strikes"] if s["kind"] in ("archery", "gun"))
        melee = sum(s["count"] for s in f["strikes"] if s["kind"] == "melee")
        out[fid] = {"missile": missile, "melee": melee, "prot": f["protection"]}
    return out


class _Force:
    """Mutable battle state for one Lord's Forces (counts + Routed counts)."""

    def __init__(self, state: GameState, lord_id: str):
        self.lord_id = lord_id
        lord = state.lords[lord_id]
        self.prof = _strike_profile()
        self.count: dict[str, int] = {"retinue": lord.forces.get("retinue", 1) or 1}
        if lord.vassals:
            self.count["vassal"] = len(lord.vassals)
        for t in _TROOP_TYPES:
            if lord.forces.get(t):
                self.count[t] = lord.forces[t]
        self.routed: dict[str, int] = {t: 0 for t in self.count}
        self.valour = static_data.load_lords()[lord_id]["ratings"]["valour"]
        self.fled = False
        self.lord_routed = False

    def avail(self, t: str) -> int:
        return self.count.get(t, 0) - self.routed.get(t, 0)

    def raw_hits(self, kind: str) -> float:
        return sum(self.prof[t][kind] * self.avail(t) for t in self.count)

    def hits(self, kind: str) -> int:
        return ceil(self.raw_hits(kind))

    def is_lord_routed(self) -> bool:
        if self.avail("retinue") == 0:
            return True
        troops = [t for t in self.count if t in _TROOP_TYPES]
        return bool(troops) and all(self.avail(t) == 0 for t in troops)


def _absorb_side(side_forces: list[_Force], n_hits: int, dice, order: list[str],
                 use_valour: bool, log: list) -> None:
    """Apply ``n_hits`` to a side's Forces in an Engagement: each Hit -> a
    unit (owner's priority order, across the side's Lords) -> Protection roll
    (Valour reroll) -> Rout on failure (4.4.2)."""
    types = order + [t for f in side_forces for t in f.count if t not in order]
    for _ in range(n_hits):
        hit_force = hit_type = None
        for t in types:
            for f in side_forces:
                if f.avail(t) > 0:
                    hit_force, hit_type = f, t
                    break
            if hit_force:
                break
        if hit_force is None:
            break
        lo, hi = hit_force.prof[hit_type]["prot"]
        roll = dice.d6()
        saved = lo <= roll <= hi
        entry = {"lord": hit_force.lord_id, "unit": hit_type, "roll": roll}
        if not saved and use_valour and hit_force.valour > 0:
            hit_force.valour -= 1
            roll2 = dice.d6()
            saved = lo <= roll2 <= hi
            entry["valour_reroll"] = roll2
        entry["saved"] = saved
        log.append(entry)
        if not saved:
            hit_force.routed[hit_type] += 1


# ----------------------------------------------------------------- 4.4.1 Array
def _initial_array(attackers: list[str], defenders: list[str],
                   decisions: dict[str, Any]) -> tuple[dict, dict]:
    if "defender_positions" in decisions:
        dpos = dict(decisions["defender_positions"])
        res_def = [d for d in defenders if d not in dpos.values()]
    else:
        dpos = {idx: lid for idx, lid in zip(_FILL_ORDER, defenders[:3], strict=False)}
        res_def = defenders[3:]
    occupied = [i for i in _FILL_ORDER if i in dpos]
    if "attacker_positions" in decisions:
        apos = dict(decisions["attacker_positions"])
        res_atk = [a for a in attackers if a not in apos.values()]
    else:
        apos = {idx: lid for idx, lid in zip(occupied, attackers[:len(occupied)], strict=False)}
        res_atk = attackers[len(occupied):]
    return ({"attacker": apos, "defender": dpos},
            {"attacker": res_atk, "defender": res_def})


def _reposition(positions: dict, reserves: dict, forces: dict) -> None:
    for side in ("defender", "attacker"):
        pos = positions[side]
        for idx in list(pos):                                  # Rout removal
            if pos[idx] is None or forces[pos[idx]].lord_routed:
                pos.pop(idx, None)
        reserves[side] = [r for r in reserves[side] if not forces[r].lord_routed]
        for idx in _FILL_ORDER:                                # Advance reserves
            if idx not in pos and reserves[side]:
                pos[idx] = reserves[side].pop(0)
        if 1 not in pos:                                       # Center fill
            for i in (0, 2):
                if i in pos:
                    pos[1] = pos.pop(i)
                    break


def _engagements(positions: dict, forces: dict) -> list[dict]:
    atk = {i: lid for i, lid in positions["attacker"].items()
           if lid and not forces[lid].lord_routed}
    dfn = {i: lid for i, lid in positions["defender"].items()
           if lid and not forces[lid].lord_routed}
    parent = {lid: lid for lid in list(atk.values()) + list(dfn.values())}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    def target(i, enemy):
        if not enemy:
            return None
        if i in enemy:
            return enemy[i]
        best = min(enemy, key=lambda j: (abs(j - i), j))   # nearest; tie -> left
        return enemy[best]

    for i, lid in atk.items():
        t = target(i, dfn)
        if t:
            union(lid, t)
    for i, lid in dfn.items():
        t = target(i, atk)
        if t:
            union(lid, t)
    aset = set(atk.values())
    comps: dict[str, list[str]] = {}
    for lid in parent:
        comps.setdefault(find(lid), []).append(lid)
    engs = []
    for members in comps.values():
        a = [m for m in members if m in aset]
        d = [m for m in members if m not in aset]
        if a and d:
            engs.append({"attacker": a, "defender": d})
    return engs


# ----------------------------------------------------------------- resolve
def resolve_battle(state: GameState, locale: str, attacker, defender,
                   decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    decisions = decisions or {}
    attackers = [attacker] if isinstance(attacker, str) else list(attacker)
    defenders = [defender] if isinstance(defender, str) else list(defender)
    flee = set(decisions.get("flee", []))
    order = decisions.get("absorb_order", _ABSORB_DEFAULT)
    use_valour = decisions.get("valour", True)
    dice = state.dice()

    forces = {lid: _Force(state, lid) for lid in attackers + defenders}
    positions, reserves = _initial_array(attackers, defenders, decisions)
    rounds: list[dict[str, Any]] = []

    def side_alive(ids):
        return any(not forces[x].lord_routed for x in ids)

    n = 0
    while side_alive(attackers) and side_alive(defenders) and n < 60:
        n += 1
        rlog: dict[str, Any] = {"round": n, "engagements": []}
        for f in [forces[d] for d in defenders] + [forces[a] for a in attackers]:  # FLEE
            if f.lord_id in flee and not f.lord_routed:
                f.fled = True
                f.lord_routed = True
        if not side_alive(attackers) or not side_alive(defenders):
            rounds.append(rlog)
            break
        _reposition(positions, reserves, forces)               # REPOSITION
        for eng in _engagements(positions, forces):            # ENGAGE + STRIKE
            elog = {"attacker": eng["attacker"], "defender": eng["defender"], "strikes": []}
            a_forces = [forces[lid] for lid in eng["attacker"]]
            d_forces = [forces[lid] for lid in eng["defender"]]
            for phase in ("missile", "melee"):
                a_hits = ceil(sum(f.raw_hits(phase) for f in a_forces))
                d_hits = ceil(sum(f.raw_hits(phase) for f in d_forces))
                dlog: list = []
                alog: list = []
                _absorb_side(d_forces, a_hits, dice, order, use_valour, dlog)
                _absorb_side(a_forces, d_hits, dice, order, use_valour, alog)
                elog["strikes"].append({"phase": phase, "attacker_hits": a_hits,
                                        "defender_hits": d_hits,
                                        "defender_rolls": dlog, "attacker_rolls": alog})
            rlog["engagements"].append(elog)
        for f in forces.values():                              # LORD ROUT
            f.lord_routed = f.is_lord_routed()
        rounds.append(rlog)

    state.store_dice(dice)
    return _ending(state, locale, forces, attackers, defenders, rounds)


def _ending(state: GameState, locale: str, forces: dict, attackers: list[str],
            defenders: list[str], rounds: list) -> dict[str, Any]:
    a_alive = any(not forces[a].lord_routed for a in attackers)
    d_alive = any(not forces[d].lord_routed for d in defenders)
    if a_alive and not d_alive:
        win_ids, lose_ids = attackers, defenders
    elif d_alive and not a_alive:
        win_ids, lose_ids = defenders, attackers
    else:
        win_ids, lose_ids = [], attackers + defenders   # both lose (4.4.3)

    winners = [forces[w] for w in win_ids if not forces[w].lord_routed]
    result: dict[str, Any] = {"type": "battle", "locale": locale, "rounds": rounds,
                              "attackers": attackers, "defenders": defenders,
                              "winner_side": (state.lords[win_ids[0]].side if win_ids else None)}
    dice = state.dice()
    if win_ids:
        wside = state.lords[win_ids[0]].side
        gain = sum(static_data.load_lords()[lid]["ratings"]["influence"]
                   + len(state.lords[lid].vassals) for lid in lose_ids)
        influence.gain_influence(state, wside, gain)
        result["influence_award"] = {wside: gain}
        _spoils(state, locale, winners, lose_ids, result)
    for w in winners:                                    # LOSSES (4.4.3)
        _losses(state, w, dice, result)
    deaths, disbands = [], []                            # DEATH CHECK + DISBAND
    for lid in defenders + attackers:                    # Defenders first
        f = forces[lid]
        if not f.lord_routed:
            continue
        roll = dice.d6() - (2 if f.fled else 0)
        if roll >= 3:
            _kill_lord(state, lid)
            deaths.append(lid)
        else:
            campaign._disband_lord(state, state.lords[lid])
            disbands.append(lid)
    state.store_dice(dice)
    result["deaths"] = deaths
    result["disbands"] = disbands
    return result


def _spoils(state: GameState, locale: str, winners: list[_Force], lose_ids: list[str],
            result: dict) -> None:
    if not winners:
        return
    fav = state.locales[locale].favour
    wside = state.lords[winners[0].lord_id].side
    frac = 1.0 if fav == wside else (0.5 if fav == "neutral" else 0.0)
    if frac == 0.0:
        return
    wmat = state.lords[winners[0].lord_id].assets   # piled on the first Unrouted winner
    taken = {"cart": 0, "provender": 0}
    for lid in lose_ids:
        lassets = state.lords[lid].assets
        for a in ("cart", "provender"):
            amt = lassets.get(a, 0)
            move = amt if frac == 1.0 else ceil(amt * 0.5)
            lassets[a] = amt - move
            wmat[a] = wmat.get(a, 0) + move
            taken[a] += move
    result["spoils"] = taken


def _losses(state: GameState, winner: _Force, dice, result: dict) -> None:
    lord = state.lords[winner.lord_id]
    recovered = lost = 0
    for t in [x for x in winner.count if x in _TROOP_TYPES]:
        for _ in range(winner.routed.get(t, 0)):
            lo, hi = winner.prof[t]["prot"]
            if lo <= dice.d6() <= hi:
                recovered += 1
            else:
                lord.forces[t] = max(0, lord.forces.get(t, 0) - 1)
                lost += 1
    if not any(lord.forces.get(t, 0) for t in _TROOP_TYPES):
        campaign._disband_lord(state, lord)
        result.setdefault("loss_disbands", []).append(winner.lord_id)
    result.setdefault("losses", {})[winner.lord_id] = {"recovered": recovered, "lost": lost}


def _kill_lord(state: GameState, lord_id: str) -> None:
    campaign._disband_lord(state, state.lords[lord_id])
    state.lords[lord_id].status = LordStatus.REMOVED
    state.lords[lord_id].calendar_box = None


# --------------------------------------------------------------- 4.3.5 Approach
def approach(state: GameState, locale: str, attacker_ids: list[str],
             decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    decisions = decisions or {}
    responses = decisions.get("responses", {})
    attackers = [a for a in attacker_ids
                 if state.lords[a].status == LordStatus.MUSTERED
                 and state.lords[a].location == locale]
    if not attackers:
        raise IllegalAction("no_attacker", "no Approaching Lord at the Locale")
    aside = state.lords[attackers[0]].side
    defenders = [lid for lid, v in state.lords.items()
                 if v.status == LordStatus.MUSTERED and v.location == locale and v.side != aside]
    result: dict[str, Any] = {"locale": locale, "exiles": [], "battle": None}
    battling: list[str] = []
    for d in defenders:
        if responses.get(d, "battle") == "exile":
            _exile(state, locale, d, attackers[0])
            result["exiles"].append(d)
        else:
            battling.append(d)
    if battling:
        result["battle"] = resolve_battle(state, locale, attackers, battling, decisions)
    return result


def _exile(state: GameState, locale: str, lord_id: str, attacker_id: str) -> None:
    lord = state.lords[lord_id]
    inf = static_data.load_lords()[lord_id]["ratings"]["influence"]
    influence.spend_influence(state, lord.side, inf + len(lord.vassals))
    fav = state.locales[locale].favour
    aside = state.lords[attacker_id].side
    frac = 1.0 if fav == aside else (0.5 if fav == "neutral" else 0.0)
    if frac > 0.0:
        wmat = state.lords[attacker_id].assets
        for a in ("cart", "provender"):
            amt = lord.assets.get(a, 0)
            move = amt if frac == 1.0 else ceil(amt * 0.5)
            lord.assets[a] = amt - move
            wmat[a] = wmat.get(a, 0) + move
    campaign._disband_lord(state, lord, from_exile=True)
