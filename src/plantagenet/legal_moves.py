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
This includes the Event/Capability Command actions (Y8 Exile Pact, Y10
Agitators, L30 Merchants, L4 Heralds) and the scenario action crown_richard
(My Kingdom for a Horse, King Richard 6.2).

`concede` (6.1.1 Surrender) is deliberately NOT enumerated: its legal window
("just before the last Heir's Death roll") is not modeled in state, so it is a
manual-adjudication action the consumer submits as a raw action at the right
moment (see ACTIONS.md).
"""

from __future__ import annotations

from typing import Any, cast

from plantagenet import actions, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordState, LordStatus, VassalStatus


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


def _intercept_moves(state: GameState, pending: dict[str, Any]) -> list[dict[str, Any]]:
    from plantagenet import battle, commands

    side = pending["side"]
    base = {"type": "respond_intercept", "side": side}
    moves = [{**base, "pass": True}]
    flank = battle._side_held_event(state, side, battle.FLANK_ATTACK)
    dest = pending["locale"]
    for lid in commands._intercept_candidates(state, dest, side):
        lord = state.lords[lid]
        title = commands._effective_title(state, lid)
        group_options = [
            ally.lord_id for ally in state.lords.values()
            if title in ("marshal", "lieutenant") and ally.lord_id != lid
            and ally.status == LordStatus.MUSTERED and ally.side == side
            and ally.location == lord.location
            and not commands._shaky_allies_block(state, [lid, ally.lord_id], dest)
            and not (title == "lieutenant"
                     and static_data.load_lords()[ally.lord_id].get("title") == "marshal")
        ]
        move = {**base, "lord": lid, "valour": ratings.rating(state, lid, "valour")}
        if group_options:
            move["group_options"] = group_options
        moves.append(move)
        if flank:
            moves.append({**move, "flank_attack": True})
    return moves


def _pending_event_moves(state: GameState) -> list[dict[str, Any]]:
    """Offer only the current decision of the head drawn Event (3.1.3)."""
    from plantagenet import events

    pe = state.pending_events[0]
    if pe.get("side") != state.active_side:
        return []
    side = events.pending_event_side(pe)
    card = pe["card"]
    move: dict[str, Any] = {"type": "play_event", "side": side, "card": card}
    if card == "Y10":
        move["event_choices"] = {"tax_targets": events.tax_collectors_targets(state),
                                  "extra_spend": list(events.EVENT_INFLUENCE_SPENDS)}
    elif card == "Y22":
        targets = events.loyalty_and_trust_targets(state, side)
        if targets:
            return [{**move, "decisions": {"target": lid}} for lid in targets]
    elif card == "Y26":
        decline = {**move, "decisions": {}}
        if not events.dubious_clarence_available(state):
            return [decline]
        return [decline] + [{**move, "decisions": {"extra_spend": extra}}
                            for extra in events.EVENT_INFLUENCE_SPENDS]
    elif card in ("L23", "L24"):
        if side == "yorkist":
            stronghold = events.propaganda_next_stronghold(pe)
            move["event_choices"] = {"stronghold": stronghold}
            return [{**move, "decisions": {"stronghold": stronghold, "choice": choice}}
                    for choice in ("remove", "pay")]
        targets = events.propaganda_strongholds(state)
        move["event_choices"] = {"strongholds": {"available": targets,
                                                "select": min(3, len(targets))}}
        if len(targets) <= 3:
            move["decisions"] = {"strongholds": targets}
    elif card == "L25":
        move["event_choices"] = events.welsh_rebellion_options(state)
    elif card == "L27":
        if side == "yorkist":
            target = events.aragne_next_check(pe)
            move["event_choices"] = dict(target)
            return [{**move, "decisions": {"vassal": target["vassal"], "extra_spend": extra}}
                    for extra in events.EVENT_INFLUENCE_SPENDS]
        owners = events.aragne_vassal_owners(state)
        move["event_choices"] = {"vassals": {"available": owners, "select": min(2, len(owners))}}
        if len(owners) <= 1:
            move["decisions"] = {"vassals": list(owners)}
    elif card == "L29":
        targets = events.wilful_disobedience_targets(state)
        move["event_choices"] = {"strongholds": {"available": targets,
                                                "remove": min(2, len(targets))}}
        if len(targets) <= 2:
            move["decisions"] = {"strongholds": targets}
    return [move]


def legal_moves(state: GameState) -> list[dict[str, Any]]:
    if state.phase == "over":
        if state.grand_scenario and (state.victory or {}).get("result") in actions.SIDES:
            from plantagenet.scenarios import next_war_id
            winner = cast(str, (state.victory or {})["result"])
            if next_war_id(static_data.load_scenario("wars_of_the_roses"),
                           state.grand_scenario["current_war"], winner):
                return [{"type": "renew_war"}]
        return []
    if state.pending:
        pending = state.pending[0]
        if pending.get("kind") == "battle_choices":
            return [{"type": "choose_battle_tactics", "side": pending["side"]}]
        if pending.get("kind") == "feed":
            return [{"type": "resolve_feed", "side": pending["side"]}]
        if pending.get("kind") == "intercept":
            return _intercept_moves(state, pending)
        if pending.get("kind") == "approach":
            responses = ("battle",) if pending["decisions"].get("blocked_ford") else (
                "exile", "battle")
            return [{"type": "respond_approach", "side": pending["side"],
                     "lord": pending["lords"][0], "response": response}
                    for response in responses]
        return _reaction_moves(state)
    if state.phase == "battle":           # Bosworth: choose cards, Array, then Battle
        from plantagenet.battle_setup import legal_moves as setup_moves
        return setup_moves(state)
    if state.pending_events:          # drawn immediate Events await resolution (3.1.3)
        return _pending_event_moves(state)
    if state.phase == "campaign":
        return _campaign_moves(state)
    if state.phase == "levy" and state.levy_step == "done":
        return [{"type": "begin_campaign"}]
    if state.phase == "levy" and state.levy_step == "arts_of_war":
        first_levy = state.turn_box == (state.calendar.first_box or state.turn_box)
        if first_levy:
            from plantagenet.arts_of_war import capability_assignment_options
            side = state.active_side
            drawn = list(state.decks.get(side, {}).get("draw", [])[:2])
            moves = [{"type": "draw", "side": side, "assignments": assignment}
                     for assignment in capability_assignment_options(state, side, drawn)]
            return moves + _crown_richard_moves(state)
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
        for lid, ls in state.lords.items():
            bsf = side == "lancastrian" and ratings.event_active(state, "BE SENT FOR")
            if (ls.side == side and ls.status == LordStatus.CALENDAR and ls.calendar_exile
                    and ls.calendar_box is not None
                    and (bsf or ls.calendar_box <= state.turn_box)):
                boxes = actions._exile_destinations(state, lid)
                for box in boxes:
                    move: dict[str, Any] = {"type": "muster_exiles", "side": side, "lords": [lid]}
                    if len(boxes) > 1:
                        move["exile_boxes"] = {lid: box}
                    out.append(move)
    except (KeyError, AttributeError):
        pass
    out.extend(_crown_richard_moves(state))
    out.extend(_held_event_moves(state, side))   # own-timing Held Events (1.9.1)
    # The active side may always end its Muster segment.
    out.append({"type": "end_muster", "side": side})
    return out


def _moves_for_lord(state: GameState, lord_id: str, lord: LordState, side: str,
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
            stanley_free = ("thomas_stanley" in lord.special_vassals
                            and not lord.free_troops_used)
            if stanley_free:
                moves.extend(_troop_levy_moves(state, lord, side))
        except (KeyError, AttributeError, IndexError):
            pass
        return moves

    # --- Levy Lord (3.4.2): Ready targets of this side ---
    try:
        seat_fallback = actions._friendly_enemyfree_seat_exists(state, side)
        for tid, t in state.lords.items():
            if (t.side == side and t.status == LordStatus.CALENDAR and not t.calendar_exile
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
        moves.extend(_troop_levy_moves(state, lord, side))
    except (KeyError, AttributeError, IndexError):
        pass

    # --- Levy Capability (3.4.6): eligible, unused, not duplicating a held name ---
    try:
        if len(lord.capabilities) < 2:
            cards = static_data.load_cards()
            in_play = actions._capabilities_in_play(state, side)
            held_titles = {cards[c]["capability"]["title"] for c in lord.capabilities}
            deck = static_data.scenario_card_deck(state.scenario, side)
            if deck:
                pool = deck
            else:                        # grand scenario: only cards live this War
                pool = [c for pile in ("draw", "discard", "held", "set_aside")
                        for c in state.decks.get(side, {}).get(pile, [])]
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
        loc = cast(tuple[str, str], actions.lord_location(lord))
        at_port_or_exile = loc[0] == "exile" or static_data.load_locales()[loc[1]].get("port")
        if (at_port_or_exile and lord.assets.get("ship", 0) < 2
                and (lord.assets.get("ship", 0) > 0 or actions._ships_in_play(state) < 9)):
            moves.append({"type": "levy_transport", "side": side,
                          "by_lord": lord_id, "transport": "ship"})
    except (KeyError, AttributeError, IndexError):
        pass
    return moves


def _troop_levy_moves(state: GameState, lord: LordState, side: str) -> list[dict[str, Any]]:
    """All eligible own/adjacent recruitment locations, including free Levies."""
    if ratings.event_against(state, "RISING WAGES", side) and lord.assets.get("coin", 0) < 1:
        return []
    loc = actions.lord_location(lord)
    if loc is None:
        return []
    kind, here = loc
    base = {"type": "levy_troops", "side": side, "by_lord": lord.lord_id}
    if kind == "exile":
        if (here == "ireland" and state.exile_depletion.get(here) != "exhausted"
                and ratings.has_capability(state, lord.lord_id, "IRISHMEN")):
            return [base]
        return []
    moves = []
    if state.locales[here].depletion != "exhausted":
        moves.append(base)
    if ratings.has_capability(state, lord.lord_id, "COMMISSION OF ARRAY"):
        for target in sorted({n for n, _ in actions._adjacency().get(here, [])}):
            if (actions.is_friendly_stronghold(state, target, side)
                    and not actions.enemy_lord_at(state, target, side)
                    and state.locales[target].depletion != "exhausted"):
                moves.append({**base, "levy_target": target})
    return moves


def _parley_moves(state: GameState, lord_id: str, lord: LordState, side: str,
                  friendly_here: bool,
                  free_only: bool = False) -> list[dict[str, Any]]:
    from plantagenet.commands import _ship_donors

    mods = actions._parley_event_mods(state, lord_id, side, commit=False)
    if free_only and not mods["free_lordship"]:
        return []
    loc = cast(tuple[str, str], actions.lord_location(lord))
    kind, here = loc
    moves: list[dict[str, Any]] = []
    # Current location, if a Stronghold not yet Friendly to us.
    if kind == "stronghold" and state.locales[here].favour != side:
        moves.append({"type": "parley", "side": side, "by_lord": lord_id, "target": here})
    if friendly_here:
        # Reachable Strongholds that don't already Favour us.
        donors = _ship_donors(state, lord)
        donor_ids = [ally.lord_id for ally in donors]
        for tid, ls in state.locales.items():
            if tid == here or ls.favour == side:
                continue
            move = {"type": "parley", "side": side, "by_lord": lord_id, "target": tid}
            own_route = actions._route_with_ships(state, loc, tid, side, [lord])
            if own_route is not None:
                moves.append(move)
            if donors:
                shared_route = actions._route_with_ships(state, loc, tid, side, [lord, *donors])
                if shared_route is not None and (own_route is None or shared_route < own_route):
                    moves.append({**move, "share": donor_ids, "share_options": donor_ids})
    votes_available = (side == "lancastrian" and any(
        e.get("card") == "L18" and e.get("side") == side
        and e.get("used", {}).get(lord_id, 0) < 1 for e in state.active_events))
    offered = [mv for mv in moves
               if not actions._london_blocks_parley(state, mv["target"], side, mods)]
    if votes_available:
        # L18: announce which one Parley benefits before rolling. A normal
        # Parley may reserve Parliament Votes for a later target this Levy.
        without_votes = actions._parley_event_mods(
            state, lord_id, side, commit=False, use_parliament_votes=False)
        offered.extend({**mv, "use_parliament_votes": False} for mv in moves
                       if not actions._london_blocks_parley(
                           state, mv["target"], side, without_votes))
    return offered


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
        moves.extend(_held_event_moves(state, side))     # Held Events (1.9.1)
        moves.append({"type": "end_activation", "side": side})
        return moves
    if c.step == "end":
        held = {side: list(state.decks.get(side, {}).get("held", []))
                for side in ("lancastrian", "yorkist")
                if state.decks.get(side, {}).get("held", [])}
        move: dict[str, Any] = {"type": "end_campaign"}
        if held:
            # Informational template data: the concrete no-discard action remains
            # legal as-is; a player may instead submit decisions.discard_held.
            move["discard_held_options"] = held
        return [move]
    return []


def _sail_moves(state: GameState, lord_id: str, lord: LordState, side: str,
                from_sea: str | None, *, here: str | None,
                origin_at_sea: bool) -> list[dict[str, Any]]:
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
    allies = []
    for gid, ally in state.lords.items():
        if gid == lord_id or ally.side != side or ally.status != LordStatus.MUSTERED:
            continue
        same = (ally.at_sea == from_sea if origin_at_sea else
                ally.at_sea is None and (
                    ally.exile_box == here if lord.exile_box is not None
                    else ally.location == here))
        if same:
            allies.append(ally)
    donors = [ally for ally in allies if ally.assets.get("ship", 0) > 0]
    title = commands._effective_title(state, lord_id)
    group = [ally for ally in allies
             if title in ("marshal", "lieutenant")
             and not (title == "lieutenant"
                      and static_data.load_lords()[ally.lord_id].get("title") == "marshal")]
    # Concrete defaults plus complete group/share/discard parameter options.
    # Any feasible group also permits its leader to Sail solo using that
    # group's Shared Ships, so the shared entry keeps partial groups reachable
    # even when the full co-located group exceeds capacity.
    variants: list[tuple[list[LordState], list[LordState], dict[str, Any]]] = [
        ([lord], [lord], {})]
    if donors:
        variants.append(([lord], [lord, *donors], {"share": [a.lord_id for a in donors]}))
    if group:
        variants.append(([lord, *group], [lord, *group],
                         {"group": [a.lord_id for a in group]}))
    sail_args: list[dict[str, Any]] = []
    for movers, owners, params in variants:
        ships = commands._transport_capacity(state, owners, "ship")
        if sum(commands._forces_units(m) for m in movers) > 6 * ships:
            continue
        excess = commands._sail_excess(movers, ships)
        remaining = dict(excess)
        discards: dict[str, dict[str, int]] = {}
        options: dict[str, dict[str, int]] = {}
        for mover in movers:
            for asset in remaining:
                available = min(mover.assets.get(asset, 0), excess[asset])
                if available:
                    options.setdefault(mover.lord_id, {})[asset] = available
                drop = min(mover.assets.get(asset, 0), remaining[asset])
                if drop:
                    discards.setdefault(mover.lord_id, {})[asset] = drop
                    remaining[asset] -= drop
        if discards:
            params["discard"] = discards[lord_id] if len(movers) == 1 else discards
            params["discard_options"] = options
            params["discard_needed"] = {a: n for a, n in excess.items() if n}
        if group:
            params["group_options"] = [a.lord_id for a in group]
        if donors:
            params["share_options"] = [a.lord_id for a in donors]
        sail_args.append(params)
    if not sail_args:
        return moves
    owain = side == "lancastrian" and commands._active_event(state, "OWAIN GLYNDWR")
    locales = static_data.load_locales()
    for dest, dsea in port_sea.items():
        if dest == here:
            continue
        reachable = (dsea == from_sea or frozenset({from_sea, dsea}) in adj) \
            if origin_at_sea else (dsea == from_sea)
        enemy = actions.enemy_lord_at(state, dest, side)
        if not reachable or (enemy and (
                not ratings.has_capability(state, lord_id, "HIGH ADMIRAL")
                or commands._active_event(state, "PARLIAMENT'S TRUCE"))):
            continue
        if owain and locales.get(dest, {}).get("region") == "wales":   # Owain Glyndwr (Y25)
            continue
        for params in sail_args:
            if not commands._shaky_allies_block(state, [lord_id, *params.get("group", [])], dest):
                moves.append({"type": "sail", "side": side, "by_lord": lord_id,
                              "to": dest, **params})
    for z in zones:                                    # into the current or an adjacent Sea
        if z == from_sea or frozenset({from_sea, z}) in adj:
            moves.extend({"type": "sail", "side": side, "by_lord": lord_id,
                          "to": z, **params} for params in sail_args)
    return moves


def _capability_command_moves(state: GameState, side: str, lord_id: str,
                              lord: LordState,
                              loc: tuple[str, str] | None) -> list[dict[str, Any]]:
    """Command actions granted by Events/Capabilities -- Exile Pact (Y8),
    Agitators (Y10), Merchants (L30), Heralds (L4). Each mirrors its handler
    pre-check so nothing offered is rejected (round-trip discipline). Exile Pact
    is available whether the Active Lord is on a Locale or at Sea; the other
    three require the Lord at a Locale (their handlers read its location)."""
    import itertools

    from plantagenet import actions, commands
    out: list[dict[str, Any]] = []

    # Exile Pact (Y8 Event): a Yorkist Lord may enter a Friendly Exile box for
    # free (no Influence cost), this Campaign.
    try:
        if side == "yorkist" and commands._active_event(state, "EXILE PACT", "yorkist"):
            boxes = static_data.load_exile_boxes()
            for box, align in state.exile_alignment.items():
                if box not in boxes or align != "yorkist":
                    continue
                if (lord.status == LordStatus.MUSTERED and lord.exile_box == box
                        and lord.location is None):
                    continue          # already in this box -- a no-op (suppress)
                out.append({"type": "exile_pact", "side": side,
                            "by_lord": lord_id, "box": box})
    except (KeyError, AttributeError):
        pass

    if loc is None:
        return out                       # the remaining three need a Locale
    here = loc[1]

    # Agitators (Y10 Capability): Deplete an adjacent Neutral/Enemy Stronghold,
    # or flip a Depleted one there to Exhausted (never one already Exhausted).
    try:
        if ratings.has_capability(state, lord_id, "AGITATORS"):
            for tgt, _t in actions._adjacency().get(here, []):
                ls = state.locales.get(tgt)
                if ls is not None and ls.favour != side and ls.depletion != "exhausted":
                    out.append({"type": "agitators", "side": side,
                                "by_lord": lord_id, "target": tgt})
    except (KeyError, AttributeError):
        pass

    # Merchants (L30 Capability, Warwick): 1 Command action + Influence check
    # removes up to 2 Depletion markers at/adjacent to the Lord (must remove 2
    # if able, else 1). Offer every maximal target set so the menu matches the
    # rule's "remove 2 if able".
    try:
        if ratings.has_capability(state, lord_id, "MERCHANTS"):
            region = {here} | {n for n, _t in actions._adjacency().get(here, [])}
            markers = [t for t in region
                       if (ls := state.locales.get(t)) is not None
                       and ls.depletion in ("depleted", "exhausted")]
            k = min(2, len(markers))
            for combo in itertools.combinations(sorted(markers), k) if k else ():
                out.append({"type": "merchants", "side": side,
                            "by_lord": lord_id, "targets": list(combo)})
    except (KeyError, AttributeError):
        pass

    # Heralds (L4 Capability): at a Port, the full Command card buys an Influence
    # check that advances a Lord on the Calendar to the next Turn box.
    try:
        if (ratings.has_capability(state, lord_id, "HERALDS")
                and static_data.load_locales()[here].get("port")):
            for tid, tl in state.lords.items():
                if (tl.side == side and tl.status == LordStatus.CALENDAR
                        and tl.calendar_box is not None):
                    out.append({"type": "heralds", "side": side,
                                "by_lord": lord_id, "target": tid})
    except (KeyError, AttributeError):
        pass

    return out


def _crown_richard_moves(state: GameState) -> list[dict[str, Any]]:
    try:
        actions._crown_richard_target(state, "yorkist")
    except (IllegalAction, KeyError, AttributeError):
        return []
    return [{"type": "crown_richard", "side": "yorkist"}]


def _held_event_moves(state: GameState, side: str) -> list[dict[str, Any]]:
    """Enumerate own-timing Held Event plays (1.9.1, play_held_event) the active
    side may make now, each emitted fully-formed (decisions filled) so it is
    directly playable. Any-moment cards -- Aspielles (Y13/L13), Yorkist Parade
    (Y20), Sun in Splendour (Y24) -- are offered whenever held and their own
    preconditions hold; the movement-triggered cards -- Rebel Supply Depot (L28),
    Surprise Landing (L33) -- only while the Hold-event window opened by a
    qualifying March/Sail to a Port is open (mirrors each handler pre-check)."""
    out: list[dict[str, Any]] = []
    held = state.decks.get(side, {}).get("held", [])
    if not held:
        return out
    win = state.hold_window

    # Aspielles (Y13 / L13): inspect Enemy Held cards -- play at any moment.
    for cid in ("Y13", "L13"):
        if cid in held:
            out.append({"type": "play_held_event", "side": side, "card": cid})

    # Yorkist Parade (Y20): any time London Favours Yorkists with York/Warwick there.
    if side == "yorkist" and "Y20" in held:
        try:
            york_warwick_at_london = any(
                state.lords.get(lid) is not None
                and state.lords[lid].status == LordStatus.MUSTERED
                and state.lords[lid].location == "london"
                for lid in ("york", "warwick_yorkist"))
            if state.locales["london"].favour == "yorkist" and york_warwick_at_london:
                out.append({"type": "play_held_event", "side": side, "card": "Y20"})
        except (KeyError, AttributeError):
            pass

    # Sun in Splendour (Y24): any moment of the Levy, Muster Edward IV at a
    # Friendly Enemy-free Locale / Yorkist Exile box. One move per valid target.
    if side == "yorkist" and "Y24" in held and state.phase == "levy":
        try:
            ed = state.lords.get("edward_iv")
            if ed is not None and ed.status in (LordStatus.CALENDAR, LordStatus.EXILE):
                for box, align in state.exile_alignment.items():
                    if align == "yorkist":
                        out.append({"type": "play_held_event", "side": side,
                                    "card": "Y24", "decisions": {"target": box}})
                for tid, ls in state.locales.items():
                    if (ls.favour == "yorkist"
                            and not actions.enemy_lord_at(state, tid, "yorkist")):
                        out.append({"type": "play_held_event", "side": side,
                                    "card": "Y24", "decisions": {"target": tid}})
        except (KeyError, AttributeError):
            pass

    # Rebel Supply Depot (L28): just after a March/Sail to a Port (window movers).
    if ("L28" in held and win is not None and win.get("side") == side
            and win.get("action") in ("march", "sail") and win.get("lords")):
        movers = list(win["lords"])
        if len(movers) == 1:
            out.append({"type": "play_held_event", "side": side, "card": "L28",
                        "decisions": {"lords": movers}})
        else:
            # Four total Provender, with the allocation chosen by the consumer.
            import itertools
            for recipients in itertools.combinations_with_replacement(movers, 4):
                out.append({"type": "play_held_event", "side": side, "card": "L28",
                            "decisions": {"lords": movers, "provender":
                                          {lid: recipients.count(lid) for lid in movers}}})

    # Surprise Landing (L33): just after a Sail to a Port.
    if ("L33" in held and win is not None and win.get("side") == side
            and win.get("action") == "sail"):
        out.append({"type": "play_held_event", "side": side, "card": "L33"})

    return out


def _attach_battle_reactions(state: GameState, side: str,
                             moves: list[dict[str, Any]]) -> None:
    """Annotate each March/Sail move that would resolve a Battle (a destination
    holding an Enemy Lord) with the in-Battle reaction windows that would be
    playable there -- the catalog gated by location/capability (e.g. Warden only
    in the North, Patrick only with Culverins). A menu-driven player can then see
    which Held Events / Capabilities it may pass in the move's ``decisions``.
    Include potential Death-check priorities when either faction has a choice.
    Advisory metadata only: apply_action ignores the extra key."""
    from plantagenet import battle, reactions
    for mv in moves:
        if mv.get("type") not in ("march", "sail"):
            continue
        dest = mv.get("to")
        if dest not in state.locales or not actions.enemy_lord_at(state, dest, side):
            continue
        attackers = [mv["by_lord"], *mv.get("group", [])]
        defenders = [lid for lid, ls in state.lords.items()
                     if ls.side != side and ls.status == LordStatus.MUSTERED
                     and ls.location == dest]
        try:
            av = reactions.available_battle_reactions(state, attackers, defenders, locale=dest)
            if max(len(attackers), len(defenders)) > 1:
                mv["death_order_options"] = battle.death_order_options(state, attackers, defenders)
        except (KeyError, AttributeError):
            continue
        if av:
            mv["battle_reactions"] = av


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
        out.extend(_capability_command_moves(state, side, lord_id, lord, loc))
        _attach_battle_reactions(state, side, out)
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
                        and gl.status == LordStatus.MUSTERED and actions.lord_location(gl) == loc):
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
    if (kind == "stronghold" and state.locales[here].favour != side
            and not actions._london_blocks_parley(state, here, side)):
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

    # Event/Capability Command actions (Y8 Exile Pact, Y10 Agitators,
    # L30 Merchants, L4 Heralds) -- none require a Friendly Locale here.
    out.extend(_capability_command_moves(state, side, lord_id, lord, loc))
    _attach_battle_reactions(state, side, out)

    if not friendly_here:
        return out

    ship_donors = commands._ship_donors(state, lord)
    fleets: list[tuple[list[LordState], dict[str, Any]]] = [([lord], {})]
    if ship_donors:
        donor_ids = [ally.lord_id for ally in ship_donors]
        fleets.append(([lord, *ship_donors], {"share": donor_ids, "share_options": donor_ids}))

    # Tax (4.6.3): own Seat / Vassal Seats / Special Strongholds, reachable, not Exhausted.
    try:
        statics = static_data.load_lords()[lord_id]
        regular = static_data.load_vassals()["regular"]
        targets = {statics["seat"]}
        targets |= {regular[v]["seat"] for v in lord.vassals if v in regular}
        targets |= {"london", "calais", "harlech"}
        for t in sorted(targets):     # sorted: set order must not leak into move order
            if t not in state.locales or state.locales[t].depletion == "exhausted":
                continue
            move = {"type": "tax", "side": side, "by_lord": lord_id, "target": t}
            own_route = commands._tax_route_cost(state, loc, t, side, [lord])
            if own_route is not None:
                out.append(move)
            if ship_donors and own_route != 0:
                owners, params = fleets[-1]
                shared_route = commands._tax_route_cost(state, loc, t, side, owners)
                if shared_route is not None and (own_route is None or shared_route < own_route):
                    out.append({**move, **params})
    except (KeyError, AttributeError, IndexError):
        pass

    # Supply (4.5): Friendly non-Exhausted Stronghold Sources reachable with
    # enough Carts; Port Sources via Ship.
    try:
        carts = commands._transport_capacity(state, [lord], "cart")
        great_ships = commands._great_ships_available(state, [lord])
        for src in state.locales:
            if src == here:
                base = static_data.stronghold_yields(src).get("supply", {}).get("provender", 0)
                if base and state.locales[src].depletion != "exhausted":
                    out.append({"type": "supply", "side": side, "by_lord": lord_id,
                                "source": src})
                continue
            if state.locales[src].depletion == "exhausted":
                continue
            ways = commands._supply_route_cost(state, here, src, side, all_seas=great_ships)
            if ways is None:
                continue
            base = static_data.stronghold_yields(src).get("supply", {}).get("provender", 0)
            if base and (carts // ways) >= 1:
                out.append({"type": "supply", "side": side, "by_lord": lord_id,
                            "source": src})
        for owners, params in fleets:
            if not any(owner.assets.get("ship", 0) > 0 for owner in owners):
                continue
            ports = commands._reachable_ports(
                here, all_seas=commands._great_ships_available(state, owners))
            for src in sorted(ports):  # sorted: set order must not leak into move order
                if (actions.is_friendly_stronghold(state, src, side)
                        and not actions.enemy_lord_at(state, src, side)):
                    out.append({"type": "supply", "side": side, "by_lord": lord_id,
                                "source": src, "use_ships": True, **params})
    except (KeyError, AttributeError, IndexError):
        pass

    # Parley (4.6.4): adjacent Stronghold or a connected Port using Ships.
    try:
        reach = {n for n, _t in actions._adjacency().get(here, [])}
        for owners, params in fleets:
            ports = set()
            if any(owner.assets.get("ship", 0) > 0 for owner in owners):
                ports = commands._reachable_ports(
                    here, all_seas=commands._great_ships_available(state, owners))
            targets = ports - reach if params else reach | ports
            reach.update(ports)
            for t in sorted(targets):
                if (t in state.locales and state.locales[t].favour != side
                        and not actions._london_blocks_parley(state, t, side)
                        and not actions.enemy_lord_at(state, t, side)):
                    out.append({"type": "parley", "side": side, "by_lord": lord_id,
                                "target": t, **params})
    except (KeyError, AttributeError, IndexError):
        pass
    return out




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
    if mv.get("type") == "choose_battle_tactics":
        # The default resolution can fail for other tactical policies (such as
        # a Spoils allocation). Keep the template available for a custom Array.
        return True
    if mv.get("type") == "build_plan" and "plan" not in mv:
        return True
    return mv.get("type") == "play_event" and "decisions" not in mv
