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

Initial `active_side` is set to the King's side as a provisional pointer;
turn-order enforcement per the Sequence of Play is a Phase 2 concern.
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

    king = _king_side(scn)
    state = GameState(
        scenario=scenario_id,
        title=title,
        seed=seed,
        active_side=Side(king),
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
    state.store_dice(DiceRoller(seed))
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
        if on_map_entry.get("exile_box"):
            status = LordStatus.EXILE
            exile_box = on_map_entry["exile_box"]
        else:
            status = LordStatus.MUSTERED
            location = on_map_entry.get("locale")
            forces = dict(static.get("forces", {}))
            assets = dict(static.get("assets", {}))
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
        "note": "Initialized at War I (setup = Scenario Ia). Later Wars' setups "
                "are selected by Succession (a later-phase concern).",
    }
    return state
