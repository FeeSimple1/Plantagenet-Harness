"""Battle engine (4.4) and Approach/Exile (4.3.5).

Phase 3b-i scope: ONE Lord per side (the common case). With a single Front
Lord each, the Array, Flanking, and Reposition steps are trivial, so this
implements the full Round loop and Ending for a 1v1 Engagement:

  Round (4.4.2): Flee -> Strike (Missiles then Melee) -> Lord Rout, repeated
  until at least one side's Lord Routs.
    - Total Hits per side per Strike type from the Forces table (sum of
      per-unit Strike counts, rounded up). Missile = archery + gun; Melee =
      melee.
    - Each Hit is absorbed by a unit (owner's choice); a Protection roll
      within the unit's range negates it, else the unit Routs. A Lord may
      spend Valour markers to reroll its own failed Protection.
    - A Lord Routs if all its Troops Rout or its Retinue Routs.
  Ending (4.4.3): winner Influence (sum of losers' printed Influence + 1 per
  Vassal); Spoils (Favour-based Carts/Provender transfer); Losses (Unrouted
  Lords recover/lose their Routed Troops; Disband if all own Troops Lost);
  Death check (Routed Lord Dies on 3-6, -2 if Fled) then Disband.

Multi-Lord Arrays (Front left/center/right, Reserve, Flanking, Reposition)
and Intercept (4.3.4) are Phase 3b-ii.

Player choices use an optional ``decisions`` payload with deterministic
defaults (no Flee; absorb Hits weakest-first; spend Valour greedily), so
nothing is silently auto-decided where the consumer wants control.
"""

from __future__ import annotations

from math import ceil
from typing import Any

from plantagenet import campaign, influence, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus

# Default Hit-absorption order: cheapest/weakest Troops first, Retinue last.
_ABSORB_DEFAULT = ["militia", "mercenaries", "longbow", "handgunners",
                   "men_at_arms", "vassal", "retinue"]
_TROOP_TYPES = {"men_at_arms", "longbow", "militia", "mercenaries", "handgunners"}


def _strike_profile() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
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
        prof = _strike_profile()
        self.prof = prof
        self.count: dict[str, int] = {}
        self.count["retinue"] = lord.forces.get("retinue", 1) or 1
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

    def hits(self, kind: str) -> int:
        total = sum(self.prof[t][kind] * self.avail(t) for t in self.count)
        return ceil(total)

    def is_lord_routed(self) -> bool:
        if self.avail("retinue") == 0:
            return True
        troops = [t for t in self.count if t in _TROOP_TYPES]
        return bool(troops) and all(self.avail(t) == 0 for t in troops)


def _absorb(force: _Force, n_hits: int, dice, order: list[str], use_valour: bool,
            log: list) -> None:
    """Apply ``n_hits`` to ``force``: each Hit -> Protection roll (Valour
    reroll) -> Rout on failure (4.4.2)."""
    pri = [t for t in order if t in force.count] + [t for t in force.count if t not in order]
    for _ in range(n_hits):
        target = next((t for t in pri if force.avail(t) > 0), None)
        if target is None:
            break
        lo, hi = force.prof[target]["prot"]
        roll = dice.d6()
        saved = lo <= roll <= hi
        if not saved and use_valour and force.valour > 0:
            force.valour -= 1
            roll2 = dice.d6()
            saved = lo <= roll2 <= hi
            log.append({"unit": target, "roll": roll, "valour_reroll": roll2, "saved": saved})
        else:
            log.append({"unit": target, "roll": roll, "saved": saved})
        if not saved:
            force.routed[target] += 1


def resolve_battle(state: GameState, locale: str, attacker_id: str, defender_id: str,
                   decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    decisions = decisions or {}
    flee = set(decisions.get("flee", []))
    order = decisions.get("absorb_order", _ABSORB_DEFAULT)
    use_valour = decisions.get("valour", True)
    dice = state.dice()

    atk = _Force(state, attacker_id)
    dfn = _Force(state, defender_id)
    rounds: list[dict[str, Any]] = []

    n = 0
    while not atk.lord_routed and not dfn.lord_routed and n < 50:
        n += 1
        rlog: dict[str, Any] = {"round": n, "strikes": []}
        # FLEE (4.4.2): Defender then Attacker; a Fleeing Lord immediately Routs.
        for f in (dfn, atk):
            if f.lord_id in flee and not f.lord_routed:
                f.fled = True
                f.lord_routed = True
        if atk.lord_routed or dfn.lord_routed:
            rounds.append(rlog)
            break
        # STRIKE: Missiles then Melee (4.4.2).
        for phase in ("missile", "melee"):
            a_hits, d_hits = atk.hits(phase), dfn.hits(phase)
            dlog: list = []
            alog: list = []
            _absorb(dfn, a_hits, dice, order, use_valour, dlog)   # Defender absorbs first
            _absorb(atk, d_hits, dice, order, use_valour, alog)
            rlog["strikes"].append({"phase": phase, "attacker_hits": a_hits,
                                    "defender_hits": d_hits,
                                    "defender_rolls": dlog, "attacker_rolls": alog})
        # LORD ROUT check.
        atk.lord_routed = atk.is_lord_routed()
        dfn.lord_routed = dfn.is_lord_routed()
        rounds.append(rlog)

    state.store_dice(dice)
    return _ending(state, locale, atk, dfn, rounds, dice)


def _ending(state: GameState, locale: str, atk: _Force, dfn: _Force,
            rounds: list, dice) -> dict[str, Any]:
    a_out, d_out = atk.lord_routed, dfn.lord_routed
    if a_out and not d_out:
        winners, losers = [dfn], [atk]
    elif d_out and not a_out:
        winners, losers = [atk], [dfn]
    else:
        winners, losers = [], [atk, dfn]   # both Routed -> both lose (4.4.3)

    result: dict[str, Any] = {"type": "battle", "locale": locale, "rounds": rounds,
                              "attacker": atk.lord_id, "defender": dfn.lord_id,
                              "winner": winners[0].lord_id if winners else None}
    dice = state.dice()
    # INFLUENCE (4.4.3): winner gains sum of losers' Influence + 1 per Vassal.
    if winners:
        wside = state.lords[winners[0].lord_id].side
        gain = sum(static_data.load_lords()[f.lord_id]["ratings"]["influence"]
                   + len(state.lords[f.lord_id].vassals) for f in losers)
        influence.gain_influence(state, wside, gain)
        result["influence_award"] = {wside: gain}
        _spoils(state, locale, winners[0], losers, result)
    # LOSSES (4.4.3): Unrouted (winning) Lords recover/lose their Routed Troops.
    for w in winners:
        _losses(state, w, dice, result)
    # DEATH CHECK + DISBAND (4.4.3): Routed Lords Die (3-6, -2 if Fled) or Disband.
    deaths, disbands = [], []
    for f in (dfn, atk):           # Defenders first
        if not f.lord_routed:
            continue
        roll = dice.d6() - (2 if f.fled else 0)
        if roll >= 3:
            _kill_lord(state, f.lord_id)
            deaths.append(f.lord_id)
        else:
            campaign._disband_lord(state, state.lords[f.lord_id])
            disbands.append(f.lord_id)
    state.store_dice(dice)
    result["deaths"] = deaths
    result["disbands"] = disbands
    return result


def _spoils(state: GameState, locale: str, winner: _Force, losers: list,
            result: dict) -> None:
    fav = state.locales[locale].favour
    wside = state.lords[winner.lord_id].side
    if fav == wside:
        frac = 1.0
    elif fav == "neutral":
        frac = 0.5
    else:
        frac = 0.0   # Stronghold Favours the losers: transfer nothing (4.4.3)
    if frac == 0.0:
        return
    wmat = state.lords[winner.lord_id].assets
    taken = {"cart": 0, "provender": 0}
    for lf in losers:
        lassets = state.lords[lf.lord_id].assets
        for a in ("cart", "provender"):       # Ships are not taken (4.4.3)
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
            roll = dice.d6()
            if lo <= roll <= hi:
                recovered += 1               # pushed back above the line
            else:
                lord.forces[t] = max(0, lord.forces.get(t, 0) - 1)   # Lost to the pool
                lost += 1
    # An Unrouted Lord who Loses ALL its own Troops immediately Disbands (4.4.3).
    if not any(lord.forces.get(t, 0) for t in _TROOP_TYPES):
        campaign._disband_lord(state, lord)
        result.setdefault("loss_disbands", []).append(winner.lord_id)
    result.setdefault("losses", {})[winner.lord_id] = {"recovered": recovered, "lost": lost}


def _kill_lord(state: GameState, lord_id: str) -> None:
    """Death (4.4.3): the Lord Disbands and is permanently removed from play."""
    campaign._disband_lord(state, state.lords[lord_id])
    state.lords[lord_id].status = LordStatus.REMOVED
    state.lords[lord_id].calendar_box = None


# --------------------------------------------------------------- 4.3.5 Approach
def approach(state: GameState, locale: str, attacker_ids: list[str],
             decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve Approach (4.3.5): each Enemy Lord at ``locale`` chooses Exile or
    Battle; Exiles are resolved, then any Battle is fought (3b-i: 1v1)."""
    decisions = decisions or {}
    responses = decisions.get("responses", {})
    attackers = [a for a in attacker_ids
                 if state.lords[a].status == LordStatus.MUSTERED
                 and state.lords[a].location == locale]
    if len(attackers) != 1:
        raise IllegalAction("multi_lord_battle_phase_3b_ii",
                            "multi-Lord Battles/Approaches are Phase 3b-ii (4.4.1)")
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
        if len(battling) != 1:
            raise IllegalAction("multi_lord_battle_phase_3b_ii",
                                "multi-Lord Battles are Phase 3b-ii (4.4.1)")
        result["battle"] = resolve_battle(state, locale, attackers[0], battling[0], decisions)
    return result


def _exile(state: GameState, locale: str, lord_id: str, attacker_id: str) -> None:
    """A Lord chooses Exile upon Approach (4.3.5): lose Influence (rating + 1
    per Vassal), give Carts/Provender to the Approaching Lord as Spoils, then
    Disband to the Calendar marked Exile."""
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
