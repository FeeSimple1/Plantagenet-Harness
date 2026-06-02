"""Legal-move enumeration for the Levy Muster segment (3.4).

Emits the palette of currently-permissible actions for the active side.
Every option mirrors a handler pre-check in `actions.py`; the goal is that
nothing emitted here is rejected by `apply_action` (the round-trip
discipline from CROSS_PROJECT_LESSONS). When a pre-check depends on
static data, it is wrapped so a data hiccup suppresses the option rather
than crashing the enumerator (bias: miss a legal move over offering a
phantom-legal one).

All Muster actions (incl. levy_capability and muster_exiles) and the
Campaign Command actions are enumerated, each mirroring its handler check.
"""

from __future__ import annotations

from typing import Any

from plantagenet import actions, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus, VassalStatus


def _reaction_moves(state: GameState) -> list[dict[str, Any]]:
    """The only legal moves while a reaction is pending (Q-004): the awaiting
    reactor may play its card or decline. ``apply_action`` rejects all else."""
    inter = state.pending[0]
    offers = inter.get("offers", [])
    idx = inter.get("idx", 0)
    if idx >= len(offers):
        return []
    offer = offers[idx]
    side = offer.get("side")
    return [{"type": "react", "side": side, "play": offer.get("card")},
            {"type": "react", "side": side, "pass": True}]


def _pending_event_moves(state: GameState) -> list[dict[str, Any]]:
    """While immediate Events drawn during Arts of War (3.1.3) await resolution,
    the only legal move is to play each (the consumer supplies any ``decisions``;
    some Events are deterministic). ``apply_action`` rejects all else."""
    side = state.active_side
    return [{"type": "play_event", "side": side, "card": pe["card"]}
            for pe in state.pending_events if pe.get("side") == side]


def legal_moves(state: GameState) -> list[dict[str, Any]]:
    if state.phase == "over":
        return []
    if state.pending:                 # a reaction window is open: only react/pass
        return _reaction_moves(state)
    if state.pending_events:          # drawn immediate Events await resolution (3.1.3)
        return _pending_event_moves(state)
    if state.phase == "campaign":
        return _campaign_moves(state)
    if state.phase == "levy" and state.levy_step == "done":
        return [{"type": "begin_campaign"}]
    if state.phase == "levy" and state.levy_step == "arts_of_war":
        return [{"type": "draw", "side": state.active_side}]
    if state.phase == "levy" and state.levy_step == "pay":
        return [{"type": "pay", "side": state.active_side}]
    if state.levy_step != "muster":
        return []
    side = state.active_side
    out: list[dict[str, Any]] = []
    for lord_id, lord in state.lords.items():
        if lord.side != side or lord.status != LordStatus.MUSTERED:
            continue
        if actions.lord_location(lord) is None or lord.mustered_this_segment:
            continue
        free_only = lord.lordship_spent >= ratings.rating(state, lord_id, "lordship")
        out.extend(_moves_for_lord(state, lord_id, lord, side, free_only=free_only))
    # Muster Exiles (3.3.1): each Exile-marked Lord ready in the current/earlier box
    # with a designated Exile box.
    try:
        net = {lid for _box, lids in actions._allied_networks(state).items() for lid in lids}
        for lid, ls in state.lords.items():
            if (ls.side == side and ls.status == LordStatus.CALENDAR and ls.calendar_exile
                    and ls.calendar_box is not None and ls.calendar_box <= state.turn_box
                    and lid in net):
                out.append({"type": "muster_exiles", "side": side, "lords": [lid]})
    except (KeyError, AttributeError):
        pass
    # The active side may always end its Muster segment.
    out.append({"type": "end_muster", "side": side})
    return out


def _moves_for_lord(state: GameState, lord_id: str, lord, side: str,
                    free_only: bool = False) -> list[dict[str, Any]]:
    """Enumerate a Lord's Muster moves. ``free_only`` (set when the Lord has spent
    all Lordship) restricts output to actions that cost 0 Lordship: free-Lordship
    Parleys (Jack Cade Y4 / My Crown L17 / Gloucester Y28) and Thomas Stanley's
    free Levy Troops (L35)."""
    moves: list[dict[str, Any]] = []
    friendly_here = actions.lord_at_friendly_locale(state, lord)

    # --- Parley (3.4.1) ---
    try:
        moves.extend(_parley_moves(state, lord_id, lord, side, friendly_here,
                                   free_only=free_only))
    except (KeyError, AttributeError):
        pass

    if not friendly_here:
        return moves  # at an Enemy/Neutral Stronghold, only Parley is allowed (3.4)

    if free_only:
        # Lordship exhausted: only Thomas Stanley's free Levy Troops remains (L35).
        try:
            loc = actions.lord_location(lord)
            stanley_free = ("thomas_stanley" in lord.special_vassals
                            and not lord.free_troops_used)
            rising_wages = ratings.event_against(state, "RISING WAGES", side)
            if (stanley_free and loc[0] == "stronghold"
                    and state.locales[loc[1]].depletion != "exhausted"
                    and not (rising_wages and lord.assets.get("coin", 0) < 1)):
                moves.append({"type": "levy_troops", "side": side, "by_lord": lord_id})
        except (KeyError, AttributeError, IndexError):
            pass
        return moves

    # --- Levy Lord (3.4.2): Ready targets of this side ---
    try:
        seat_fallback = actions._friendly_enemyfree_seat_exists(state, side)
        for tid, t in state.lords.items():
            if (t.side == side and t.status == LordStatus.CALENDAR
                    and t.calendar_box is not None and t.calendar_box <= state.turn_box):
                seat = static_data.load_lords()[tid]["seat"]
                if not actions.enemy_lord_at(state, seat, side) or seat_fallback is not None:
                    moves.append({"type": "levy_lord", "side": side,
                                  "by_lord": lord_id, "target": tid})
    except (KeyError, AttributeError):
        pass

    # --- Levy Vassal (3.4.3): at-seat Vassals whose Seat is Friendly + Enemy-free ---
    # Yorkists Block Parliament (Y7): Lancastrians may not Levy Vassals (by Event).
    try:
        blocked = side == "lancastrian" and ratings.event_against(
            state, "YORKISTS BLOCK PARLIAMENT", "lancastrian")
        regular = static_data.load_vassals()["regular"]
        for vid, vs in (() if blocked else state.vassals.items()):
            if vs.status != VassalStatus.AT_SEAT:
                continue
            seat = regular[vid]["seat"]
            if (actions.is_friendly_stronghold(state, seat, side)
                    and not actions.enemy_lord_at(state, seat, side)):
                moves.append({"type": "levy_vassal", "side": side,
                              "by_lord": lord_id, "target": vid})
    except (KeyError, AttributeError):
        pass

    # --- Levy Troops (3.4.4): at a Friendly Stronghold (not Exile box), not Exhausted ---
    # Rising Wages (L9): this side pays 1 Coin per Levy Troops -- need the Coin.
    try:
        loc = actions.lord_location(lord)
        rising_wages = ratings.event_against(state, "RISING WAGES", side)
        if (loc[0] == "stronghold" and state.locales[loc[1]].depletion != "exhausted"
                and not (rising_wages and lord.assets.get("coin", 0) < 1)):
            moves.append({"type": "levy_troops", "side": side, "by_lord": lord_id})
    except (KeyError, AttributeError, IndexError):
        pass

    # --- Levy Capability (3.4.6): eligible, unused, not duplicating a held name ---
    try:
        if len(lord.capabilities) < 2:
            cards = static_data.load_cards()
            in_play = actions._capabilities_in_play(state, side)
            held_titles = {cards[c]["capability"]["title"] for c in lord.capabilities}
            deck = static_data.scenario_card_deck(state.scenario, side)
            pool = deck or [c for c in cards if cards[c]["side"] == side]
            for cid in pool:
                if (cid not in in_play and actions._capability_eligible(cid, lord_id)
                        and cards[cid]["capability"]["title"] not in held_titles):
                    moves.append({"type": "levy_capability", "side": side,
                                  "by_lord": lord_id, "card": cid})
    except (KeyError, AttributeError):
        pass

    # --- Levy Transport (3.4.5) ---
    moves.append({"type": "levy_transport", "side": side, "by_lord": lord_id, "transport": "cart"})
    try:
        loc = actions.lord_location(lord)
        at_port_or_exile = loc[0] == "exile" or static_data.load_locales()[loc[1]].get("port")
        if (at_port_or_exile and actions._ships_in_play(state) < 9
                and lord.assets.get("ship", 0) < 2):
            moves.append({"type": "levy_transport", "side": side,
                          "by_lord": lord_id, "transport": "ship"})
    except (KeyError, AttributeError, IndexError):
        pass
    return moves


def _parley_moves(state, lord_id, lord, side, friendly_here,
                  free_only: bool = False) -> list[dict[str, Any]]:
    if free_only:                       # only free-Lordship Parleys survive (peek, no consume)
        if not actions._parley_event_mods(state, lord_id, side, commit=False)["free_lordship"]:
            return []
    loc = actions.lord_location(lord)
    kind, here = loc
    moves: list[dict[str, Any]] = []
    has_ship = lord.assets.get("ship", 0) > 0
    # Current location, if a Stronghold not yet Friendly to us.
    if kind == "stronghold" and state.locales[here].favour != side:
        moves.append({"type": "parley", "side": side, "by_lord": lord_id, "target": here})
    if not friendly_here:
        return moves
    # Reachable Strongholds that don't already Favour us.
    for tid, ls in state.locales.items():
        if tid == here or ls.favour == side:
            continue
        if actions._parley_route_cost(state, loc, tid, side, has_ship) is not None:
            moves.append({"type": "parley", "side": side, "by_lord": lord_id, "target": tid})
    return moves


def _campaign_moves(state: GameState) -> list[dict[str, Any]]:
    c = state.campaign
    if c is None:
        return []
    if c.step == "plan":
        # The Plan is a free construction (4.1); the consumer submits it via
        # build_plan. We surface the requirement rather than enumerate stacks.
        pending = [s for s in ("lancastrian", "yorkist") if not c.plan_built.get(s)]
        return [{"type": "build_plan", "side": s, "cards_required": c.cards_required}
                for s in pending]
    if c.step == "activation":
        side = state.active_side
        moves: list[dict[str, Any]] = []
        if c.active_lord is not None and c.actions_remaining > 0:
            moves.extend(_command_moves(state, side, c.active_lord))
        moves.append({"type": "end_activation", "side": side})
        return moves
    if c.step == "end":
        return [{"type": "end_campaign"}]
    return []


def _sail_moves(state, lord_id, lord, side, from_sea, *, here, origin_at_sea):
    """Enumerate Sail destinations (4.6.1) for a Lord on ``from_sea``. A Lord at
    a Port/Exile box may Sail Port-to-Port only WITHIN a Sea; a Lord at Sea may
    also reach a Port on an adjacent Sea (FAQ #1: no direct cross-Sea Port hop).
    Either may Sail "into" the current or an adjacent Sea (ending at Sea)."""
    from plantagenet import commands
    seas = static_data.load_seas()
    zones = seas["zones"]
    port_sea = {p: z for z, zone in zones.items() for p in zone.get("ports", [])}
    adj = {frozenset(pr) for pr in seas["adjacency"]}
    moves: list[dict[str, Any]] = []
    if from_sea is None:
        return moves
    if side == "yorkist" and commands._active_event(state, "FRENCH FLEET"):
        return moves                                   # French Fleet bars Yorkist Sail (L21)
    ships = lord.assets.get("ship", 0)
    need = max(-(-commands._forces_units(lord) // 6),
               -(-lord.assets.get("provender", 0) // 2),
               -(-lord.assets.get("cart", 0) // 2))
    if ships < need:
        return moves
    owain = side == "lancastrian" and commands._active_event(state, "OWAIN GLYNDWR")
    locales = static_data.load_locales()
    for dest, dsea in port_sea.items():
        if dest == here:
            continue
        reachable = (dsea == from_sea or frozenset({from_sea, dsea}) in adj) \
            if origin_at_sea else (dsea == from_sea)
        if not reachable or actions.enemy_lord_at(state, dest, side):
            continue
        if owain and locales.get(dest, {}).get("region") == "wales":   # Owain Glyndwr (Y25)
            continue
        if commands._shaky_allies_block(state, [lord_id], dest):        # IIY Shaky Allies
            continue
        moves.append({"type": "sail", "side": side, "by_lord": lord_id, "to": dest})
    for z in zones:                                    # into the current or an adjacent Sea
        if z == from_sea or frozenset({from_sea, z}) in adj:
            moves.append({"type": "sail", "side": side, "by_lord": lord_id, "to": z})
    return moves


def _command_moves(state: GameState, side: str, lord_id: str) -> list[dict[str, Any]]:
    """Enumerate Command actions for the Active Lord (4.3-4.6), mirroring the
    handler pre-checks so nothing offered is rejected (round-trip discipline)."""
    from plantagenet import actions, commands
    lord = state.lords[lord_id]
    loc = actions.lord_location(lord)
    out: list[dict[str, Any]] = [{"type": "pass", "side": side, "by_lord": lord_id}]
    if loc is None:
        if lord.at_sea is not None:           # a Lord at Sea may only Sail (4.6.1) or Pass
            out.extend(_sail_moves(state, lord_id, lord, side, lord.at_sea,
                                   here=None, origin_at_sea=True))
        return out
    kind, here = loc
    # Forage (4.6.2): any Locale not yet Exhausted (Exile boxes are foragable and
    # Deplete/Exhaust too, tracked in state.exile_depletion).
    forage_ok = (state.exile_depletion.get(here) != "exhausted" if kind == "exile"
                 else state.locales[here].depletion != "exhausted")
    if forage_ok:
        out.append({"type": "forage", "side": side, "by_lord": lord_id})
    friendly_here = actions.lord_at_friendly_locale(state, lord)

    # March (4.3): destinations reachable in one action -- INCLUDING into enemy
    # contact, which resolves an Intercept (4.3.4) / Approach + Battle (4.3.5).
    # Only Parliament's Truce bars marching onto an Enemy Lord (Y12/L20).
    try:
        locs = static_data.load_locales()
        owain = side == "lancastrian" and commands._active_event(state, "OWAIN GLYNDWR")
        truce = commands._active_event(state, "PARLIAMENT'S TRUCE")
        # Group March (4.3.1): a Marshal (or Lieutenant, but not over a Marshal)
        # may lead co-located Friendly Lords. Offer the full eligible group;
        # partial groups remain available via a raw `group` list.
        title = commands._effective_title(state, lord_id)
        group: list[str] = []
        if title in ("marshal", "lieutenant"):
            for gid, gl in state.lords.items():
                if (gid != lord_id and gl.side == side
                        and gl.status == LordStatus.MUSTERED and gl.location == here):
                    if (title == "lieutenant" and static_data.load_lords()[gid]
                            .get("title") == "marshal"):
                        continue
                    group.append(gid)
        for dest in state.locales:
            if dest == here:
                continue
            if commands._march_cost(state, here, dest, kind, side=side) is None:
                continue
            if owain and locs.get(dest, {}).get("region") == "wales":  # Owain Glyndwr (Y25)
                continue
            if truce and actions.enemy_lord_at(state, dest, side):     # Parliament's Truce
                continue
            if not commands._shaky_allies_block(state, [lord_id], dest):  # IIY Shaky Allies
                out.append({"type": "march", "side": side, "by_lord": lord_id, "to": dest})
            if group and not commands._shaky_allies_block(state, [lord_id, *group], dest):
                out.append({"type": "march", "side": side, "by_lord": lord_id,
                            "to": dest, "group": group})
    except (KeyError, AttributeError, IndexError):
        pass

    # Parley at own location (4.6.4): automatic and free, allowed even when the
    # Lord stands on a non-Friendly Stronghold (the usual reason to Parley here).
    if kind == "stronghold" and state.locales[here].favour != side:
        out.append({"type": "parley", "side": side, "by_lord": lord_id, "target": here})

    # Sail (4.6.1): Port-to-Port within a Sea (cross-Sea moves transit at Sea).
    try:
        seas = static_data.load_seas()
        port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
        box_sea = {b: z for z, zone in seas["zones"].items() for b in zone.get("exile_boxes", [])}
        from_sea = box_sea.get(here) if kind == "exile" else port_sea.get(here)
        on_sea = kind == "exile" or static_data.load_locales()[here].get("port")
        if from_sea is not None and on_sea:
            out.extend(_sail_moves(state, lord_id, lord, side, from_sea,
                                   here=here, origin_at_sea=False))
    except (KeyError, AttributeError, IndexError):
        pass

    if not friendly_here:
        return out

    # Tax (4.6.3): own Seat / Vassal Seats / Special Strongholds, reachable, not Exhausted.
    try:
        statics = static_data.load_lords()[lord_id]
        regular = static_data.load_vassals()["regular"]
        targets = {statics["seat"]}
        targets |= {regular[v]["seat"] for v in lord.vassals if v in regular}
        targets |= {"london", "calais", "harlech"}
        has_ship = lord.assets.get("ship", 0) > 0
        for t in targets:
            if t not in state.locales or state.locales[t].depletion == "exhausted":
                continue
            if t == here or (t == statics["seat"] and here == statics["seat"]):
                out.append({"type": "tax", "side": side, "by_lord": lord_id, "target": t})
            elif commands._tax_route_cost(state, here, t, side, has_ship) is not None:
                out.append({"type": "tax", "side": side, "by_lord": lord_id, "target": t})
    except (KeyError, AttributeError, IndexError):
        pass

    # Supply (4.5): Friendly non-Exhausted Stronghold Sources reachable with
    # enough Carts; Port Sources via Ship.
    try:
        carts = lord.assets.get("cart", 0)
        for src in state.locales:
            if src == here:
                base = static_data.stronghold_yields(src).get("supply", {}).get("provender", 0)
                if base and state.locales[src].depletion != "exhausted":
                    out.append({"type": "supply", "side": side, "by_lord": lord_id,
                                "source": src})
                continue
            if state.locales[src].depletion == "exhausted":
                continue
            ways = commands._supply_route_cost(state, here, src, side)
            if ways is None:
                continue
            base = static_data.stronghold_yields(src).get("supply", {}).get("provender", 0)
            if base and (carts // ways) >= 1:
                out.append({"type": "supply", "side": side, "by_lord": lord_id,
                            "source": src})
        if lord.assets.get("ship", 0) > 0:
            seas = static_data.load_seas()
            ports = {p for zone in seas["zones"].values() for p in zone.get("ports", [])}
            for src in ports:
                if src != here and commands._same_sea_port_or_box(here, src):
                    out.append({"type": "supply", "side": side, "by_lord": lord_id,
                                "source": src, "use_ships": True})
    except (KeyError, AttributeError, IndexError):
        pass

    # Parley (4.6.4): own location (if not Friendly) or adjacent / same-Sea Port.
    try:
        has_ship = lord.assets.get("ship", 0) > 0
        reach = {n for n, _t in actions._adjacency().get(here, [])}
        if has_ship:
            reach |= {p for p in _same_sea_ports(here)}
        for t in reach:
            if (t in state.locales and state.locales[t].favour != side
                    and not actions.enemy_lord_at(state, t, side)):
                out.append({"type": "parley", "side": side, "by_lord": lord_id, "target": t})
    except (KeyError, AttributeError, IndexError):
        pass
    return out


def _same_sea_ports(here: str) -> set[str]:
    seas = static_data.load_seas()
    port_sea = {p: z for z, zone in seas["zones"].items() for p in zone.get("ports", [])}
    if here not in port_sea:
        return set()
    z = port_sea[here]
    return {p for p, zz in port_sea.items() if zz == z and p != here}


def validated_legal_moves(state: GameState) -> dict[str, Any]:
    """Agent-facing action palette (cross-harness advisory §2). Probe every move
    the enumerator emits on a deep copy of the state and drop any the handler
    rejects, returning the kept moves plus structured over-enumeration
    diagnostics. This is a safety net over the round-trip discipline, NOT a
    substitute for fixing the enumerator -- every drop is a logged bug.

    Safe because the RNG lives in the state (seed + rng_state): probing advances
    only the copy's dice, never the real game's. Use on the agent-facing path,
    not in hot loops. ``apply_action`` returning ``pending_reactions`` (a paused
    reaction) counts as legal -- the move is kept."""
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    unvalidated: list[dict[str, Any]] = []
    for mv in legal_moves(state):
        if _is_templated(mv):              # parameterized (e.g. build_plan): keep, don't probe
            kept.append(mv)
            unvalidated.append(mv)
            continue
        probe = state.model_copy(deep=True)
        try:
            actions.apply_action(probe, mv)
        except IllegalAction as e:
            rejected.append({"move": mv, "code": e.code, "reason": e.message})
            continue
        kept.append(mv)
    return {"active_side": state.active_side, "phase": state.phase,
            "levy_step": state.levy_step, "moves": kept, "rejected": rejected,
            "unvalidated": unvalidated}


def _is_templated(mv: dict[str, Any]) -> bool:
    """A move the consumer must parameterize before it can apply (4.1 Plan is a
    free construction): not directly probeable, so kept and flagged."""
    if mv.get("type") == "build_plan" and "plan" not in mv:
        return True
    return mv.get("type") == "play_event" and "decisions" not in mv
