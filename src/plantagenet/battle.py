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

from plantagenet import campaign, influence, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus

_ABSORB_DEFAULT = ["militia", "mercenaries", "longbow", "handgunners",
                   "men_at_arms", "vassal", "retinue"]
_TROOP_TYPES = {"men_at_arms", "longbow", "militia", "mercenaries", "handgunners"}
_FILL_ORDER = [1, 0, 2]   # center, left, right (4.4.1)


def _require(cond: bool, code: str, msg: str) -> None:
    if not cond:
        raise IllegalAction(code, msg)


def _strike_profile() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fid, f in static_data.load_forces().items():
        if fid.startswith("_"):
            continue
        missile = sum(s["count"] for s in f["strikes"] if s["kind"] in ("archery", "gun"))
        melee = sum(s["count"] for s in f["strikes"] if s["kind"] == "melee")
        out[fid] = {"missile": missile, "melee": melee, "prot": f["protection"]}
    return out



CULVERINS = "CULVERINS AND FALCONETS"
LEEWARD = "LEEWARD BATTLE LINE"
CALTROPS = "CALTROPS"
RAVINE = "RAVINE"
BARRICADES = "BARRICADES"
BLOCKED_FORD = "BLOCKED FORD"
REGROUP = "REGROUP"
ESCAPE_SHIP = "ESCAPE SHIP"
FLANK_ATTACK = "FLANK ATTACK"
SUSPICION = "SUSPICION"
BARDED_HORSE = "BARDED HORSE"
CHEVALIERS = "CHEVALIERS"
PIQUIERS = "PIQUIERS"
YEOMEN = "YEOMEN OF THE CROWN"
FINAL_CHARGE = "FINAL CHARGE"
BLOODY_THOU_ART = "BLOODY THOU ART"
VANGUARD = "VANGUARD"
SWIFT_MANEUVER = "SWIFT MANEUVER"


def _lord_has_capability(state: GameState, lord_id: str, title: str) -> str | None:
    for cid in state.lords[lord_id].capabilities:
        if static_data.load_cards()[cid]["capability"]["title"] == title:
            return cid
    return None


def _side_held_event(state: GameState, side: str, title: str) -> str | None:
    for cid in state.decks.get(side, {}).get("held", []):
        if static_data.load_cards()[cid]["event"]["title"] == title:
            return cid
    return None


def _discard_capability(state: GameState, lord_id: str, card_id: str) -> None:
    lord = state.lords[lord_id]
    if card_id in lord.capabilities:
        lord.capabilities.remove(card_id)
    state.decks.setdefault(lord.side, {}).setdefault("discard", []).append(card_id)


def _use_held_event(state: GameState, side: str, card_id: str) -> None:
    held = state.decks.get(side, {}).get("held", [])
    if card_id in held:
        held.remove(card_id)
    state.decks.setdefault(side, {}).setdefault("discard", []).append(card_id)


def _escape_route(state: GameState, locale: str, side: str) -> bool:
    """Whether ``side`` can trace from ``locale`` to a Friendly Port — at it
    or via an overland Friendly Route (Escape Ship, 4.5.1)."""
    from plantagenet import commands
    locs = static_data.load_locales()
    for p, lc in locs.items():
        if lc.get("port") and state.locales[p].favour == side:
            if p == locale or commands._supply_route_cost(state, locale, p, side) is not None:
                return True
    return False


def _apply_special_vassal_armour(state, forces):
    """Special-Vassal Armour mods (e.g. Montagu gives Warwick's Retinue
    Armour 1-5, 1.5.4)."""
    special = static_data.load_vassals()["special"]
    for f in forces.values():
        for sv in state.lords[f.lord_id].special_vassals:
            ra = special.get(sv, {}).get("modifiers", {}).get("retinue_armour")
            if ra and "retinue" in f.prof:
                f.prof["retinue"]["prot"] = list(ra)


def _apply_barricades(state, forces, locale):
    """Barricades (Y9 Capability): at a Friendly Stronghold, this Lord's
    Men-at-Arms gain Armour 1-4 and Longbowmen/Militia Armour 1-2 (4.4.2).
    Does not apply to Losses rolls (handled in _losses)."""
    fav = state.locales[locale].favour
    for f in forces.values():
        lord = state.lords[f.lord_id]
        if fav == lord.side and any(
                static_data.load_cards()[c]["capability"]["title"] == BARRICADES
                for c in lord.capabilities):
            if "men_at_arms" in f.prof:
                f.prof["men_at_arms"]["prot"] = [1, 4]
            if "longbow" in f.prof:
                f.prof["longbow"]["prot"] = [1, 2]
            if "militia" in f.prof:
                f.prof["militia"]["prot"] = [1, 2]


def _english_channel_ports() -> set[str]:
    return set(static_data.load_seas()["zones"]["english_channel"]["ports"])


def _at_friendly_stronghold(state, lid, locale):
    return state.locales[locale].favour == state.lords[lid].side


def _in_region_fn(*regions):
    def f(state, lid, locale):
        return static_data.load_locales().get(locale, {}).get("region") in regions
    return f


def _route_to_carlisle(state, lid, locale):
    from plantagenet import commands
    side = state.lords[lid].side
    return locale == "carlisle" or \
        commands._supply_route_cost(state, locale, "carlisle", side) is not None


def _adj_friendly_ec_port(state, lid, locale):
    from plantagenet.commands import _adjacency
    side = state.lords[lid].side
    ec = _english_channel_ports()
    if locale in ec and state.locales[locale].favour == side:
        return True
    return any(nbr in ec and state.locales[nbr].favour == side
               for nbr, _t in _adjacency().get(locale, []))


# Battle troop-add Capabilities (1.9.1), keyed by *card id* (PERCY'S NORTH has
# two different texts: Y27 in the North, Y37 with a Route to Carlisle).
# Each entry: (condition(state, lord_id, locale) -> bool, {force_type: count}).
# Added units are battle-local (removed after Battle automatically).
_BATTLE_TROOP_CAPS = {
    "Y3": (_at_friendly_stronghold, {"men_at_arms": 2, "longbow": 1}),  # Muster'd My Soldiers
    "L3": (_at_friendly_stronghold, {"men_at_arms": 2, "longbow": 1}),
    "Y25": (_in_region_fn("wales"), {"longbow": 2}),                    # Pembroke
    "L25": (_in_region_fn("wales"), {"longbow": 2}),                    # Welsh Lord
    "Y27": (_in_region_fn("north"), {"militia": 4}),                    # Percy's North (Y27)
    "Y37": (_route_to_carlisle, {"men_at_arms": 2}),                    # Percy's North (Y37)
    "Y35": (_in_region_fn("north", "south", "wales"), {"militia": 3}),  # Kingdom United
    "L33": (_adj_friendly_ec_port, {"men_at_arms": 2}),                 # Philibert de Chandee
}


def _apply_battle_troop_caps(state, forces, locale):
    for lid, f in forces.items():
        for cid in state.lords[lid].capabilities:
            spec = _BATTLE_TROOP_CAPS.get(cid)
            if spec and spec[0](state, lid, locale):
                for t, n in spec[1].items():
                    f.count[t] = f.count.get(t, 0) + n
                    f.routed.setdefault(t, 0)


def _apply_armour_caps(state, forces):
    """Uniform (all-phase) Armour Capabilities. Church Blessing (L5): this
    Lord's Men-at-Arms have Armour 1-4 (1.9.1)."""
    for f in forces.values():
        if _lord_has_capability(state, f.lord_id, "CHURCH BLESSING") and "men_at_arms" in f.prof:
            f.prof["men_at_arms"]["prot"] = [1, 4]


def _apply_phase_caps(state, forces, decisions):
    """Phase-dependent Armour and Melee-Strike Capabilities (1.9.1):
    Barded Horse (L27), Chevaliers (L36), Piquiers (L34), Yeomen of the Crown
    (L31, opt-in via decisions['yeomen'])."""
    yeomen_optin = set(decisions.get("yeomen", []))
    for f in forces.values():
        if _lord_has_capability(state, f.lord_id, BARDED_HORSE):
            for t in ("retinue", "vassal"):
                if t in f.prof:
                    f.prof[t]["prot_missile"] = [1, 3]
                    f.prof[t]["prot_melee"] = [1, 5]
        if _lord_has_capability(state, f.lord_id, CHEVALIERS) and "men_at_arms" in f.prof:
            lo, hi = f.prof["men_at_arms"]["prot"]
            f.prof["men_at_arms"]["prot_missile"] = [lo, max(lo - 1, hi - 1)]  # -1 Armour
            f.melee_mult["men_at_arms"] = 2                                    # Melee Strike x2
        if _lord_has_capability(state, f.lord_id, PIQUIERS):
            f.piquiers = True
        if (_lord_has_capability(state, f.lord_id, YEOMEN)
                and (f.lord_id in yeomen_optin or yeomen_optin == {True})):
            f.yeomen = True


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
        self.valour = ratings.rating(state, lord_id, "valour")
        self.fled = False
        self.lord_routed = False
        self.melee_mult: dict[str, int] = {}   # unit -> melee Strike multiplier (Chevaliers)
        self.piquiers = False                  # MaA+Militia Armour 1-4 until 3 Rout (L34)
        self.yeomen = False                    # Retinue fail -> may Rout a MaA instead (L31)

    def avail(self, t: str) -> int:
        return self.count.get(t, 0) - self.routed.get(t, 0)

    def raw_hits(self, kind: str) -> float:
        total = 0.0
        for t in self.count:
            mult = self.melee_mult.get(t, 1) if kind == "melee" else 1
            total += self.prof[t][kind] * self.avail(t) * mult
        return total

    def prot_range(self, t: str, phase: str):
        """Protection range for unit ``t`` in the given Strike ``phase``,
        honouring phase-specific overrides (Barded Horse, Chevaliers) and the
        dynamic Piquiers (L34) Armour 1-4 until 3 Men-at-Arms/Militia Rout."""
        if self.piquiers and t in ("men_at_arms", "militia"):
            routed_pm = self.routed.get("men_at_arms", 0) + self.routed.get("militia", 0)
            if routed_pm < 3:
                return [1, 4]
        return self.prof[t].get(f"prot_{phase}", self.prof[t]["prot"])

    def hits(self, kind: str) -> int:
        return ceil(self.raw_hits(kind))

    def is_lord_routed(self) -> bool:
        if self.avail("retinue") == 0:
            return True
        troops = [t for t in self.count if t in _TROOP_TYPES]
        return bool(troops) and all(self.avail(t) == 0 for t in troops)


def _absorb_side(side_forces: list[_Force], n_hits: int, dice, order: list[str],
                 use_valour: bool, log: list, phase: str = "melee") -> None:
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
        lo, hi = hit_force.prot_range(hit_type, phase)
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
            # Yeomen of the Crown (L31): a failed Retinue save may instead Rout
            # one of this Lord's Unrouted Men-at-Arms units.
            if (hit_type == "retinue" and hit_force.yeomen
                    and hit_force.avail("men_at_arms") > 0):
                hit_force.routed["men_at_arms"] += 1
                entry["yeomen_redirect"] = "men_at_arms"
            else:
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
def _resolve_suspicion(state, locale, attackers, defenders, forces, decisions):
    """Suspicion (Y5/L5): a participating Lord checks Influence; on success
    Disband one Enemy Lord at the Battle with a lower PRINTED Influence (no
    Influence-point loss). The Disbanded Lord leaves the Battle (4.4.1)."""
    sp = decisions.get("suspicion")
    if not sp:
        return None
    by, target = sp.get("by"), sp.get("target")
    _require(by in forces and target in forces, "bad_suspicion",
             "Suspicion must name a Friendly and an Enemy Lord in the Battle (4.4.1)")
    bside = state.lords[by].side
    _require(state.lords[target].side != bside, "bad_suspicion", "target must be an Enemy Lord")
    cid = _side_held_event(state, bside, SUSPICION)
    _require(cid is not None, "no_suspicion", f"{bside} has no Suspicion Held Event (4.4.1)")
    lords_static = static_data.load_lords()
    _require(lords_static[by]["ratings"]["influence"]
             > lords_static[target]["ratings"]["influence"], "suspicion_influence",
             "the Friendly Lord must have a higher PRINTED Influence than the Enemy (Y5 errata)")
    _use_held_event(state, bside, cid)
    chk = influence.check_influence(state, by, bside)
    if chk["success"]:
        campaign._disband_lord(state, state.lords[target])   # no Influence-point loss (Y5)
        for lst in (attackers, defenders):
            if target in lst:
                lst.remove(target)
        forces.pop(target, None)
    return {"by": by, "target": target, **chk}


def resolve_battle(state: GameState, locale: str, attacker, defender,
                   decisions: dict[str, Any] | None = None) -> dict[str, Any]:
    decisions = decisions or {}
    attackers = [attacker] if isinstance(attacker, str) else list(attacker)
    defenders = [defender] if isinstance(defender, str) else list(defender)
    flee = set(decisions.get("flee", []))
    order = decisions.get("absorb_order", _ABSORB_DEFAULT)
    use_valour = decisions.get("valour", True)
    dice = state.dice()

    aside = state.lords[attackers[0]].side
    dside = state.lords[defenders[0]].side
    # Card plays (4.4.1 Event step): Leeward Battle Line (Hold Event) and
    # Culverins and Falconets (Capability discarded at Round 1).
    culverins = set(decisions.get("culverins", []))
    for lid in culverins:
        _require(lid in attackers + defenders and _lord_has_capability(state, lid, CULVERINS),
                 "no_culverins", f"{lid} has no Culverins and Falconets Capability (4.4.1)")
    leeward = set()
    for sd in decisions.get("leeward", []):
        cid = _side_held_event(state, sd, LEEWARD)
        _require(sd in (aside, dside) and cid is not None, "no_leeward",
                 f"{sd} has no Leeward Battle Line Held Event to play (4.4.1)")
        _use_held_event(state, sd, cid)
        leeward.add(sd)
    both_leeward = {aside, dside} <= leeward    # both played -> neither has effect

    caltrops = set()                            # Caltrops (Y19): +2 Melee Hits/Round
    for sd in decisions.get("caltrops", []):
        cid = _side_held_event(state, sd, CALTROPS)
        _require(sd in (aside, dside) and cid is not None, "no_caltrops",
                 f"{sd} has no Caltrops Held Event to play (4.4.1)")
        _use_held_event(state, sd, cid)
        caltrops.add(sd)
    ravine_target = decisions.get("ravine")     # Ravine (L12): ignore an enemy Lord Round 1
    if ravine_target is not None:
        _require(ravine_target in attackers + defenders, "bad_ravine",
                 "Ravine must target a Lord in the Battle (4.4.1)")
        player_side = dside if ravine_target in attackers else aside
        cid = _side_held_event(state, player_side, RAVINE)
        _require(cid is not None, "no_ravine",
                 f"{player_side} has no Ravine Held Event to play (4.4.1)")
        _use_held_event(state, player_side, cid)

    regroup_lord = regroup_round = None
    rg = decisions.get("regroup")
    if rg:
        regroup_lord = rg["lord"]
        regroup_round = rg.get("round", 2)
        _require(regroup_lord in attackers + defenders, "bad_regroup",
                 "Regroup must name a Lord in the Battle (4.4.2)")
        rside = state.lords[regroup_lord].side
        cid = _side_held_event(state, rside, REGROUP)
        _require(cid is not None, "no_regroup",
                 f"{rside} has no Regroup Held Event to play (4.4.2)")
        _use_held_event(state, rside, cid)

    vanguard_lord = decisions.get("vanguard")
    if vanguard_lord is not None:
        _require(vanguard_lord in attackers + defenders
                 and _lord_has_capability(state, vanguard_lord, VANGUARD), "no_vanguard",
                 f"{vanguard_lord} has no Vanguard Capability in this Battle (Y36)")
    swift = None
    sm_side = decisions.get("swift_maneuver")
    if sm_side:
        cid = _side_held_event(state, sm_side, SWIFT_MANEUVER)
        _require(cid is not None, "no_swift",
                 f"{sm_side} has no Swift Maneuver Held Event to play (Y36)")
        _use_held_event(state, sm_side, cid)
        swift = sm_side
    final_charge = set(decisions.get("final_charge", []))
    for lid in final_charge:
        _require(lid in attackers + defenders and lid == "richard_iii"
                 and _lord_has_capability(state, lid, FINAL_CHARGE), "no_final_charge",
                 f"{lid} cannot use Final Charge (Richard III only, Y32)")

    forces = {lid: _Force(state, lid) for lid in attackers + defenders}
    _apply_battle_troop_caps(state, forces, locale)
    _apply_barricades(state, forces, locale)
    _apply_special_vassal_armour(state, forces)
    _apply_armour_caps(state, forces)
    _apply_phase_caps(state, forces, decisions)

    susp = _resolve_suspicion(state, locale, attackers, defenders, forces, decisions)
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
        if regroup_lord is not None and n == regroup_round:    # Regroup: recover Troops
            f = forces[regroup_lord]
            for t in [x for x in f.count if x in _TROOP_TYPES]:
                rec = 0
                for _ in range(f.routed.get(t, 0)):
                    lo, hi = f.prof[t]["prot"]                  # modified Protection
                    if lo <= dice.d6() <= hi:
                        rec += 1
                f.routed[t] -= rec
        engs = _engagements(positions, forces)
        if n == 1 and ravine_target is not None:               # Ravine: ignore Lord Round 1
            for eng in engs:
                eng["attacker"] = [x for x in eng["attacker"] if x != ravine_target]
                eng["defender"] = [x for x in eng["defender"] if x != ravine_target]
            engs = [e for e in engs if e["attacker"] and e["defender"]]
        if n == 1 and vanguard_lord is not None:               # Vanguard: only his Engagement
            engs = [e for e in engs
                    if vanguard_lord in e["attacker"] or vanguard_lord in e["defender"]]
        # Swift Maneuver (Y36): snapshot Lancastrian Retinue Routs to detect new ones.
        lanc_ret_before = {lid: forces[lid].routed.get("retinue", 0)
                           for lid in forces if state.lords[lid].side == "lancastrian"}
        caltrops_done = set()
        for eng in engs:                                       # ENGAGE + STRIKE
            elog = {"attacker": eng["attacker"], "defender": eng["defender"], "strikes": []}
            a_forces = [forces[lid] for lid in eng["attacker"]]
            d_forces = [forces[lid] for lid in eng["defender"]]
            for phase in ("missile", "melee"):
                a_hits = ceil(sum(f.raw_hits(phase) for f in a_forces))
                d_hits = ceil(sum(f.raw_hits(phase) for f in d_forces))
                if phase == "melee":                # Caltrops: +2 Melee/Round (one Engagement)
                    if aside in caltrops and aside not in caltrops_done:
                        a_hits += 2
                        caltrops_done.add(aside)
                    if dside in caltrops and dside not in caltrops_done:
                        d_hits += 2
                        caltrops_done.add(dside)
                    for lid in final_charge:           # Final Charge (Y32): +3 Hits, +1 self
                        if lid in eng["attacker"]:
                            a_hits += 3
                        elif lid in eng["defender"]:
                            d_hits += 3
                        else:
                            continue
                        fc = forces[lid]
                        if fc.avail("retinue") > 0:    # Retinue suffers +1 Hit
                            lo, hi = fc.prot_range("retinue", "melee")
                            saved = lo <= dice.d6() <= hi
                            if not saved and use_valour and fc.valour > 0:
                                fc.valour -= 1
                                saved = lo <= dice.d6() <= hi
                            if not saved:
                                fc.routed["retinue"] += 1
                if phase == "missile":
                    if n == 1:                      # Culverins: +1 d6 Missile Hit, Round 1
                        for lid in eng["attacker"]:
                            if lid in culverins:
                                a_hits += dice.d6()
                                _discard_capability(state, lid,
                                                    _lord_has_capability(state, lid, CULVERINS))
                                culverins.discard(lid)
                        for lid in eng["defender"]:
                            if lid in culverins:
                                d_hits += dice.d6()
                                _discard_capability(state, lid,
                                                    _lord_has_capability(state, lid, CULVERINS))
                                culverins.discard(lid)
                    if not both_leeward:            # Leeward: halve incoming Missile Hits
                        if dside in leeward:
                            a_hits = ceil(a_hits / 2)
                        if aside in leeward:
                            d_hits = ceil(d_hits / 2)
                dlog: list = []
                alog: list = []
                _absorb_side(d_forces, a_hits, dice, order, use_valour, dlog, phase)
                _absorb_side(a_forces, d_hits, dice, order, use_valour, alog, phase)
                elog["strikes"].append({"phase": phase, "attacker_hits": a_hits,
                                        "defender_hits": d_hits,
                                        "defender_rolls": dlog, "attacker_rolls": alog})
            rlog["engagements"].append(elog)
            if swift == "yorkist" and any(
                    forces[lid].routed.get("retinue", 0) > lanc_ret_before.get(lid, 0)
                    and forces[lid].avail("retinue") == 0
                    for lid in lanc_ret_before):
                break                                          # Swift Maneuver: end Round
        for f in forces.values():                              # LORD ROUT
            f.lord_routed = f.is_lord_routed()
        rounds.append(rlog)

    state.store_dice(dice)
    res = _ending(state, locale, forces, attackers, defenders, rounds,
                  decisions.get("escape_ship", []))
    if susp is not None:
        res["suspicion"] = susp
    return res


def _ending(state: GameState, locale: str, forces: dict, attackers: list[str],
            defenders: list[str], rounds: list, escape_ship: list[str]) -> dict[str, Any]:
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
    # Escape Ship (4.4.3): selected Routed Lords with a Friendly Route to a Port
    # go into Exile (4.3.5) instead of rolling Death.
    escaped: set[str] = set()
    used_escape_side: set[str] = set()
    for lid in set(escape_ship):
        f = forces.get(lid)
        if f is None or not f.lord_routed:
            continue
        side = state.lords[lid].side
        cid = _side_held_event(state, side, ESCAPE_SHIP)
        if cid is not None and _escape_route(state, locale, side):
            if side not in used_escape_side:
                _use_held_event(state, side, cid)
                used_escape_side.add(side)
            escaped.add(lid)

    # Bloody Thou Art (Y33): if Richard III wins, skip Death checks -- all Routed
    # losing (Lancastrian) Lords Die.
    bloody = ("richard_iii" in win_ids
              and _lord_has_capability(state, "richard_iii", BLOODY_THOU_ART))
    deaths, disbands, exiles = [], [], []                # DEATH CHECK + DISBAND
    for lid in defenders + attackers:                    # Defenders first
        f = forces[lid]
        if not f.lord_routed:
            continue
        if lid in escaped:                               # Exile instead of Death (4.3.5)
            ld = state.lords[lid]
            influence.spend_influence(state, ld.side,
                                      static_data.load_lords()[lid]["ratings"]["influence"]
                                      + len(ld.vassals))
            campaign._disband_lord(state, ld, from_exile=True)
            exiles.append(lid)
            continue
        if bloody and lid in lose_ids:                   # Bloody Thou Art: certain Death
            _kill_lord(state, lid)
            deaths.append(lid)
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
    result["exiles"] = exiles
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
    base_prot = {fid: f["protection"] for fid, f in static_data.load_forces().items()
                 if not fid.startswith("_")}
    for t in [x for x in winner.count if x in _TROOP_TYPES]:
        for _ in range(winner.routed.get(t, 0)):
            lo, hi = base_prot[t]            # unmodified Protection for Losses (4.4.3)
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
    dside = state.lords[defenders[0]].side if defenders else None
    # Blocked Ford (Y11/L11): either side may play to forbid Exile (all Battle, 4.3.5).
    blocked_ford = False
    for sd in decisions.get("blocked_ford", []):
        cid = _side_held_event(state, sd, BLOCKED_FORD)
        _require(sd in (aside, dside) and cid is not None, "no_blocked_ford",
                 f"{sd} has no Blocked Ford Held Event to play (4.3.5)")
        _use_held_event(state, sd, cid)
        blocked_ford = True
    result: dict[str, Any] = {"locale": locale, "exiles": [], "battle": None,
                              "blocked_ford": blocked_ford}
    battling: list[str] = []
    for d in defenders:
        if not blocked_ford and responses.get(d, "battle") == "exile":
            _exile(state, locale, d, attackers[0])
            result["exiles"].append(d)
        else:
            battling.append(d)
    if battling:
        result["battle"] = resolve_battle(state, locale, attackers, battling, decisions)
    return result


def _exile(state: GameState, locale: str, lord_id: str, attacker_id: str) -> None:
    lord = state.lords[lord_id]
    if _lord_has_capability(state, lord_id, "ENGLAND IS MY HOME"):   # Y8
        campaign._disband_lord(state, lord)          # plain Disband, no Influence loss
        lord.calendar_box = state.turn_box + 1       # to the next Calendar box
        lord.calendar_exile = False
        return
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
