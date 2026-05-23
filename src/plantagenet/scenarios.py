"""Scenario loader: build a fully-set-up ``GameState`` from scenario data.

Maps the structured scenario setup (`data/scenarios/*.json`) onto the
state model. This is deterministic data transformation, not game logic:
it places Lords (Mustered / on the Calendar / in Exile / available),
Vassals, Favour, the Influence track, Exile-box alignment, and Calendar
markers exactly as the Scenario Reference specifies.

The Wars of the Roses grand scenario is initialized at its first War
("Plantagenets Go to War"), whose setup is Scenario Ia per the reference.
The conditional Succession that selects later Wars' setups is game logic
deferred to a later phase; `grand_scenario` metadata records the current
War so that logic has what it needs.

Initial `active_side` is the Rebel side: the Levy sequence (cards, Pay,
Muster) proceeds "Rebel then King's" each Turn (3.1-3.4).
"""

from __future__ import annotations

from typing import Any

from plantagenet import static_data
from plantagenet.errors import DataError
from plantagenet.rng import DiceRoller
from plantagenet.state import (
    CalendarState,
    Favour,
    GameState,
    InfluenceState,
    LocaleState,
    LordState,
    LordStatus,
    Role,
    Side,
    StrongholdMarker,
    VassalState,
    VassalStatus,
)

SIDES = ("lancastrian", "yorkist")


def build_initial_state(scenario_id: str, seed: int = 1) -> GameState:
    """Build the initial GameState for a scenario id."""
    scn = static_data.load_scenario(scenario_id)
    if scn.get("is_grand_scenario"):
        return _build_grand(scn, seed)
    return _build_standalone(scn, seed, scenario_id, scn["title"])


# --------------------------------------------------------------------------


def _king_side(scn: dict[str, Any]) -> str:
    for side in SIDES:
        if scn["sides"][side]["role"] == "king":
            return side
    raise DataError(f"scenario {scn.get('id')} has no King side")


def _rebel_side(scn: dict[str, Any]) -> str:
    for side in SIDES:
        if scn["sides"][side]["role"] == "rebel":
            return side
    raise DataError(f"scenario {scn.get('id')} has no Rebel side")


def _placement_index(setup: dict[str, Any]) -> tuple[dict, dict]:
    """Return (on_map_by_lord, calendar_by_lord) from a setup block."""
    on_map = {e["lord"]: e for e in setup.get("on_map", [])
              if not str(e.get("lord", "")).isupper()  # skip tokens like "KING"
              and "_per_succession" not in str(e.get("lord", ""))}
    calendar: dict[str, dict] = {}
    for entry in setup.get("calendar", []):
        box = entry.get("box")
        for lord in entry.get("lords", []):
            calendar[lord["lord"]] = {**lord, "box": box}
    return on_map, calendar


def _vassal_service_boxes(setup: dict[str, Any]) -> dict[str, int]:
    boxes: dict[str, int] = {}
    for entry in setup.get("calendar", []):
        for vid in entry.get("vassals", []):
            boxes[vid] = entry.get("box")
    return boxes


def _build_standalone(scn: dict, seed: int, scenario_id: str, title: str) -> GameState:
    lords_static = static_data.load_lords()
    vassals_static = static_data.load_vassals()
    locales_static = static_data.load_locales()

    battle_only = bool(scn.get("battle_only"))
    setup = scn.get("setup", {})
    on_map, calendar = _placement_index(setup)

    roles = {s: Role(scn["sides"][s]["role"]) for s in SIDES}

    # ---- Lords ----
    lords: dict[str, LordState] = {}
    for side in SIDES:
        block = scn["sides"][side]
        mustered = set(block.get("mustered", []))
        for lord_id in block["lord_cards"]:
            if lord_id not in lords_static:
                raise DataError(f"{scenario_id}: unknown lord {lord_id}")
            ls = _lord_state(lord_id, side, lords_static[lord_id],
                             on_map.get(lord_id), calendar.get(lord_id),
                             is_mustered_hint=lord_id in mustered,
                             battle_only=battle_only)
            lords[lord_id] = ls

    # ---- Vassals ----
    vassals = _build_vassals(setup, vassals_static)

    # ---- Locales / Favour ----
    locales: dict[str, LocaleState] = {lid: LocaleState() for lid in locales_static}
    if not battle_only:
        for side in SIDES:
            for loc in setup.get("favour", {}).get(side, []):
                if loc not in locales:
                    raise DataError(f"{scenario_id}: favour locale {loc!r} unknown")
                locales[loc] = LocaleState(favour=Favour(side))

    # ---- Influence ----
    influence: dict[str, InfluenceState] = {}
    inf = setup.get("influence")
    if inf and "marker_at" in inf:
        influence["track"] = _influence_state(inf)

    # ---- Exile alignment ----
    exile_alignment = {box: Side(side) for box, side in
                       setup.get("exile_alignment", {}).items()}

    # ---- Calendar ----
    turns = scn.get("turns", {})
    end_box = turns.get("end_marker_box")
    if end_box is None:
        for entry in setup.get("calendar", []):
            if "end" in entry.get("markers", []):
                end_box = entry["box"]
    cal = CalendarState(levy_box=turns.get("levy_box"), end_box=end_box,
                        first_box=turns.get("first_box"), last_box=turns.get("last_box"))

    # Levy proceeds Rebel side then King's side (3.1-3.4); Rebel acts first.
    first = _rebel_side(scn) if not battle_only else _king_side(scn)
    state = GameState(
        scenario=scenario_id,
        title=title,
        seed=seed,
        active_side=Side(first),
        turn_box=turns.get("levy_box", turns.get("first_box", 1)) or 1,
        phase="battle" if battle_only else "levy",
        roles=roles,
        lords=lords,
        vassals=vassals,
        locales=locales,
        exile_alignment=exile_alignment,
        influence=influence,
        calendar=cal,
        arts_of_war={"description": scn.get("arts_of_war", "")},
    )
    roller = DiceRoller(seed)
    if not battle_only:
        state.levy_step = "arts_of_war"      # the Levy begins with the Arts of War draw (3.1)
        in_play = {c for ls in lords.values() for c in ls.capabilities}
        for s_side in SIDES:
            draw = [cid for cid in static_data.scenario_card_deck(scenario_id, s_side)
                    if cid not in in_play]
            roller.shuffle(draw)
            state.decks[s_side] = {"draw": draw, "discard": [], "held": []}
    state.store_dice(roller)
    return state


def _lord_state(lord_id, side, static, on_map_entry, cal_entry,
                is_mustered_hint, battle_only) -> LordState:
    forces: dict[str, int] = {}
    assets: dict[str, int] = {}
    caps: list[str] = []
    special_vassals: list[str] = []
    ring = None
    status = LordStatus.AVAILABLE
    location = exile_box = calendar_box = None
    calendar_exile = False

    if battle_only:
        status = LordStatus.MUSTERED
        forces = dict(static.get("forces", {}))
        assets = dict(static.get("assets", {}))
    elif on_map_entry is not None:
        ring = on_map_entry.get("ring")
        # A Lord set up in an Exile box is Mustered there (has a mat and may
        # take Levy actions except Levy Troops, 3.4); the Exile box is just
        # its location. A bare Exile cylinder lives on the Calendar instead
        # (handled via cal_entry with calendar_exile).
        status = LordStatus.MUSTERED
        forces = dict(static.get("forces", {}))
        assets = dict(static.get("assets", {}))
        if on_map_entry.get("exile_box"):
            exile_box = on_map_entry["exile_box"]
        else:
            location = on_map_entry.get("locale")
        if on_map_entry.get("capability"):
            caps.append(on_map_entry["capability"])
        if on_map_entry.get("special_vassal"):
            special_vassals.append(on_map_entry["special_vassal"])
    elif cal_entry is not None:
        status = LordStatus.CALENDAR
        calendar_box = cal_entry.get("box")
        calendar_exile = bool(cal_entry.get("exile"))
        ring = cal_entry.get("ring")

    return LordState(
        lord_id=lord_id, side=Side(side), status=status, location=location,
        exile_box=exile_box, calendar_box=calendar_box, calendar_exile=calendar_exile,
        ring=ring, forces=forces, assets=assets, capabilities=caps,
        special_vassals=special_vassals,
    )


def _build_vassals(setup: dict, vassals_static: dict) -> dict[str, VassalState]:
    regular = vassals_static.get("regular", {})
    vmode = setup.get("vassals_on_map", {})
    mode = vmode.get("mode", "all")
    excepted = set(vmode.get("except", []))
    on_lord = {e["vassal"]: e["lord"] for e in vmode.get("on_lord_mat", [])}
    service_boxes = _vassal_service_boxes(setup)

    out: dict[str, VassalState] = {}
    for vid, vdata in regular.items():
        if vid in on_lord:
            out[vid] = VassalState(vassal_id=vid, status=VassalStatus.MUSTERED,
                                   on_lord=on_lord[vid], service_box=service_boxes.get(vid))
        elif mode == "all_except" and vid in excepted:
            out[vid] = VassalState(vassal_id=vid, status=VassalStatus.OFF_MAP)
        else:
            out[vid] = VassalState(vassal_id=vid, status=VassalStatus.AT_SEAT,
                                   location=vdata.get("seat"))
    return out


def _influence_state(inf: dict) -> InfluenceState:
    markers = {k: StrongholdMarker(side=Side(v["side"]), at=v["at"])
               for k, v in inf.get("stronghold_markers", {}).items()}
    return InfluenceState(marker_at=inf["marker_at"], marker_side=Side(inf["marker_side"]),
                          stronghold_markers=markers, victory_check=inf.get("victory_check"))


def _build_grand(scn: dict, seed: int) -> GameState:
    wars = {w["war_id"]: w for w in scn["wars"]}
    war1 = wars["war_i"]
    base_id = war1["base_scenario"]   # "henry_vi"
    base = static_data.load_scenario(base_id)
    state = _build_standalone(base, seed, "wars_of_the_roses", scn["title"])
    state.grand_scenario = {
        "current_war": "war_i",
        "war_title": war1["title"],
        "base_scenario": base_id,
        "allied_networks": war1.get("allied_networks", {}),
        "victory_threshold": war1.get("victory_threshold"),
        "deck_sources": {},
        "set_aside_on_disband": {},
        "note": "Initialized at War I (setup = Scenario Ia).",
    }
    # War I uses Scenario Ia's Arts of War decks; assemble them from the base.
    roller = state.dice()
    in_play = {c for ls in state.lords.values() for c in ls.capabilities}
    for s_side in SIDES:
        draw = [cid for cid in static_data.scenario_card_deck(base_id, s_side)
                if cid not in in_play]
        roller.shuffle(draw)
        state.decks[s_side] = {"draw": draw, "discard": [], "held": [], "set_aside": []}
    state.store_dice(roller)
    from plantagenet import succession
    succession.apply_setup(state)            # register while_remains deck sources (6.2)
    return state


# ---------------------------------------------------------------------------
# Renewed War (E1 6.1): on a War victory, transition the grand scenario to the
# next War -- select it by winner, rebuild the board/decks/favour from the new
# War's structured setup, carry forward removed Heirs (and their -8 Influence),
# resolve the King via Succession, then run setup-time Succession.
# ---------------------------------------------------------------------------
def _war_deck(war: dict, side: str) -> list[str]:
    """A side's base Arts of War deck for a War (all no-rose + adds - excepts).
    Succession then layers further cards on top (deck_sources)."""
    spec = war.get("arts_of_war_spec", {}).get(side, {})
    cards = static_data.load_cards()
    base = {cid for cid, c in cards.items()
            if c.get("side") == side and c.get("rose") == 0}
    return sorted((base | set(spec.get("add", []))) - set(spec.get("except", [])))


def _war_as_scenario(war: dict) -> dict:
    return {
        "title": war["title"],
        "sides": {s: {"role": war["sides"][s]["role"],
                      "lord_cards": war.get("lord_cards", {}).get(s, []),
                      "mustered": []} for s in SIDES},
        "setup": war.get("setup", {}),
        "turns": war.get("turns", {}),
    }


def _resolve_kings(state: GameState, war: dict, removed: set) -> dict[str, str]:
    """Seat the King token(s) in a War's setup.on_map as the highest surviving
    Heir of that side (6.2); fire its Muster Succession trigger."""
    from plantagenet import succession
    seated: dict[str, str] = {}
    for e in war.get("setup", {}).get("on_map", []):
        if str(e.get("lord", "")).upper() != "KING":
            continue
        side = "lancastrian" if e.get("color") == "red" else "yorkist"
        king = succession.highest_heir_for_setup(state, side, removed)
        if king is None:
            continue
        statics = static_data.load_lords()[king]
        ls = state.lords.get(king)
        if ls is None:
            ls = LordState(lord_id=king, side=Side(side), status=LordStatus.MUSTERED)
            state.lords[king] = ls
        ls.status = LordStatus.MUSTERED
        ls.location = e.get("locale")
        ls.exile_box = None
        ls.calendar_box = None
        ls.forces = dict(statics.get("forces", {}))
        ls.assets = dict(statics.get("assets", {}))
        seated[side] = king
        succession.on_muster_lord(state, king)        # e.g. Margaret -> L26 EDWARD
    return seated


def _apply_lost_heir_influence(state: GameState, removed: set) -> int:
    """Each Heir (not Warwick) removed in an earlier War costs that side -8
    Influence (E2 / 6.x). Returns total points spent."""
    from plantagenet import influence, succession
    total = 0
    for lid in removed:
        if "warwick" in lid:
            continue
        side = state.lords[lid].side if lid in state.lords else None
        if side and (succession.heir_rank(state, side, lid) is not None):
            influence.spend_influence(state, side, 8)
            total += 8
    return total


def next_war_id(scn_grand: dict, current_war: str, winner: str) -> str | None:
    wars = {w["war_id"]: w for w in scn_grand["wars"]}
    order = wars[current_war]["order"]
    rw = scn_grand["respite_and_war"]["renewed_war"]
    table = rw["after_first"] if order == 1 else rw["after_second"] if order == 2 else {}
    return table.get(f"{winner}_won")


def renew_war(state: GameState, seed: int | None = None) -> GameState:
    """Transition a won grand scenario to its next War (E1 6.1)."""
    from plantagenet import succession
    from plantagenet.errors import IllegalAction
    gs = state.grand_scenario
    if not gs:
        raise IllegalAction("not_grand", "Renewed War applies only to the grand scenario")
    winner = (state.victory or {}).get("result")
    if winner not in ("lancastrian", "yorkist"):
        raise IllegalAction("no_winner", "Renewed War needs a decisive War victory (6.1)")
    scn_grand = static_data.load_scenario("wars_of_the_roses")
    nxt = next_war_id(scn_grand, gs["current_war"], winner)
    if nxt is None:
        raise IllegalAction("game_over", "the final War is concluded; no Renewed War (6.1)")
    war = {w["war_id"]: w for w in scn_grand["wars"]}[nxt]

    removed_prior = {lid for lid, ls in state.lords.items()
                     if ls.status == LordStatus.REMOVED}
    set_aside_keep = dict(gs.get("set_aside_on_disband", {}))
    seed = state.seed if seed is None else seed

    if "lord_cards" in war and "setup" in war:          # structured War setup (IIL / IIIL)
        new = _build_standalone(_war_as_scenario(war), seed, "wars_of_the_roses", war["title"])
    else:                                               # base-scenario War (IIY / IIIY)
        base = static_data.load_scenario(war["base_scenario"])
        new = _build_standalone(base, seed, "wars_of_the_roses", war["title"])

    new.grand_scenario = {
        "current_war": nxt, "war_title": war["title"],
        "base_scenario": war.get("base_scenario"),
        "allied_networks": war.get("allied_networks", {}),
        "victory_threshold": war.get("victory_threshold"),
        "deck_sources": {}, "succession_fired": [], "current_king": {},
        "set_aside_on_disband": set_aside_keep,
    }
    new.victory = None
    new.phase = "levy"

    for lid in removed_prior:                           # Heirs removed earlier stay out (6.2.2)
        ls = new.lords.get(lid)
        if ls is not None:
            ls.status = LordStatus.REMOVED
            ls.location = ls.exile_box = ls.calendar_box = None

    in_play_caps = {c for ls in new.lords.values() for c in ls.capabilities}
    roller = new.dice()
    for side in SIDES:                                  # base decks from the War's spec
        draw = [c for c in _war_deck(war, side) if c not in in_play_caps]
        roller.shuffle(draw)
        prior_set_aside = state.decks.get(side, {}).get("set_aside", [])
        new.decks[side] = {"draw": draw, "discard": [], "held": [],
                           "set_aside": list(prior_set_aside)}
    new.store_dice(roller)

    _resolve_kings(new, war, removed_prior)
    _apply_lost_heir_influence(new, removed_prior)
    succession.apply_setup(new)                         # setup-time Succession (6.2)
    new.levy_step = "arts_of_war"
    return new
