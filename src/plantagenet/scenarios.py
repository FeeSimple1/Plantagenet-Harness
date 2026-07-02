"""Scenario loader: build a fully-set-up ``GameState`` from scenario data.

Maps the structured scenario setup (`data/scenarios/*.json`) onto the
state model. This is deterministic data transformation, not game logic:
it places Lords (Mustered / on the Calendar / in Exile / available),
Vassals, Favour, the Influence track, Exile-box alignment, and Calendar
markers exactly as the Scenario Reference specifies.

The Wars of the Roses grand scenario is initialized at its first War
("Plantagenets Go to War"), whose setup is Scenario Ia per the reference.
The conditional Succession that selects and builds later Wars' setups is
implemented in `succession.py` and `renew_war`; `grand_scenario` metadata
records the current War.

Initial `active_side` is the Rebel side: the Levy sequence (cards, Pay,
Muster) proceeds "Rebel then King's" each Turn (3.1-3.4).
"""

from __future__ import annotations

from typing import Any, cast

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


def _placement_index(
        setup: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Return (on_map_by_lord, calendar_by_lord) from a setup block."""
    on_map = {e["lord"]: e for e in setup.get("on_map", [])
              if not str(e.get("lord", "")).isupper()  # skip tokens like "KING"
              and "_per_succession" not in str(e.get("lord", ""))}
    calendar: dict[str, dict[str, Any]] = {}
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


def _setup_special_rule_names(scn: dict[str, Any]) -> set[str]:
    rules = scn.get("setup", {}).get("special_rules") or scn.get("special_rules") or []
    return {r["name"] for r in rules if isinstance(r, dict) and "name" in r}


def _apply_setup_special_rules(state: GameState, scn: dict[str, Any]) -> None:
    """Apply setup-time scenario special rules that the generic builder does not
    express in data (e.g. a Capability + Special Vassal assigned at setup)."""
    names = _setup_special_rule_names(scn)
    # Montagu (Somerset's Return): the Yorkist Warwick sets up with the
    # Lancastrian MONTAGU Capability (L23) and its Special Vassal.
    if "Montagu" in names:
        wk = state.lords.get("warwick_yorkist")
        if wk is not None and "L23" in static_data.load_cards():
            if "L23" not in wk.capabilities:
                wk.capabilities.append("L23")
            if "montagu" not in wk.special_vassals:
                wk.special_vassals.append("montagu")


def _build_standalone(scn: dict[str, Any], seed: int, scenario_id: str,
                      title: str) -> GameState:
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
    # A regular Vassal set up on a Lord's mat (e.g. Fauconberg on March at Towton)
    # must also appear in that Lord's ``.vassals`` list -- the book every Vassal
    # mechanic reads (Battle Array unit, Exile/Unfed +1-per-Vassal penalties,
    # Vassal disbands, Tax via the Vassal's Seat).
    for _vid, _vs in vassals.items():
        if (_vs.status == VassalStatus.MUSTERED and _vs.on_lord
                and _vs.on_lord in lords and _vid not in lords[_vs.on_lord].vassals):
            lords[_vs.on_lord].vassals.append(_vid)

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
    _apply_setup_special_rules(state, scn)
    state.store_dice(roller)
    return state


def _lord_state(lord_id: str, side: str, static: dict[str, Any],
                on_map_entry: dict[str, Any] | None, cal_entry: dict[str, Any] | None,
                is_mustered_hint: bool, battle_only: bool) -> LordState:
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


def _build_vassals(setup: dict[str, Any],
                   vassals_static: dict[str, Any]) -> dict[str, VassalState]:
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


def _influence_state(inf: dict[str, Any]) -> InfluenceState:
    markers = {k: StrongholdMarker(side=Side(v["side"]), at=v["at"])
               for k, v in inf.get("stronghold_markers", {}).items()}
    return InfluenceState(marker_at=inf["marker_at"], marker_side=Side(inf["marker_side"]),
                          stronghold_markers=markers, victory_check=inf.get("victory_check"))


def _build_grand(scn: dict[str, Any], seed: int) -> GameState:
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
def _war_deck(war: dict[str, Any], side: str) -> list[str]:
    """A side's base Arts of War deck for a War (all no-rose + adds - excepts).
    Succession then layers further cards on top (deck_sources)."""
    spec = war.get("arts_of_war_spec", {}).get(side, {})
    cards = static_data.load_cards()
    base = {cid for cid, c in cards.items()
            if c.get("side") == side and c.get("rose") == 0}
    return sorted((base | set(spec.get("add", []))) - set(spec.get("except", [])))


def _war_as_scenario(war: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": war["title"],
        "sides": {s: {"role": war["sides"][s]["role"],
                      "lord_cards": war.get("lord_cards", {}).get(s, []),
                      "mustered": []} for s in SIDES},
        "setup": war.get("setup", {}),
        "turns": war.get("turns", {}),
    }


def _resolve_kings(state: GameState, war: dict[str, Any],
                   removed: set[str]) -> dict[str, str]:
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


def _apply_lost_heir_influence(state: GameState, removed: set[str]) -> int:
    """Each Heir (not Warwick) removed in an earlier War costs that side -8
    Influence (E2 / 6.x). Returns total points spent."""
    from plantagenet import influence, succession
    total = 0
    statics = static_data.load_lords()
    for lid in removed:
        if "warwick" in lid:
            continue
        # A Heir removed in an earlier War may be absent from this War's roster
        # (e.g. Henry VI in IIIY), so fall back to the static Lord's side.
        side = (state.lords[lid].side if lid in state.lords
                else statics.get(lid, {}).get("side"))
        if side and succession.is_global_heir(side, lid):   # 6.2.1 global Heir list
            influence.spend_influence(state, side, 8)
            total += 8
    return total


def _place_lord(state: GameState, lord_id: str, side: str, *, location: str | None = None,
                calendar_box: int | None = None, calendar_exile: bool = False,
                exile_box: str | None = None, ring: str | None = None) -> LordState:
    """Place (or relocate) a Lord with its static Forces/Assets. ``location`` ->
    Mustered on the map; ``exile_box`` -> Mustered in an Exile box; ``calendar_box``
    -> on the Calendar (Exile-marked if ``calendar_exile``). Used by the
    Succession-driven War setups (6.2.2)."""
    statics = static_data.load_lords()[lord_id]
    ls = state.lords.get(lord_id)
    if ls is None:
        ls = LordState(lord_id=lord_id, side=Side(side), status=LordStatus.AVAILABLE)
        state.lords[lord_id] = ls
    if location is not None:
        ls.status = LordStatus.MUSTERED
        ls.location = location
        ls.exile_box = None
        ls.calendar_box = None
    elif exile_box is not None:
        ls.status = LordStatus.MUSTERED          # Mustered in an Exile box (has a mat)
        ls.location = None
        ls.exile_box = exile_box
        ls.calendar_box = None
    else:
        ls.status = LordStatus.CALENDAR
        ls.location = None
        ls.exile_box = None
        ls.calendar_box = calendar_box
    ls.calendar_exile = calendar_exile
    ls.ring = ring
    ls.forces = dict(statics.get("forces", {}))
    ls.assets = dict(statics.get("assets", {}))
    return ls


def _unplace_lord(state: GameState, lord_id: str) -> None:
    """Remove a Lord from the board back to AVAILABLE (not REMOVED): used when a
    Succession setup supersedes a base-scenario placement (e.g. Margaret yields
    box 9 to a surviving Henry VI)."""
    ls = state.lords.get(lord_id)
    if ls is not None and ls.status != LordStatus.REMOVED:
        ls.status = LordStatus.AVAILABLE
        ls.location = ls.exile_box = ls.calendar_box = None
        ls.calendar_exile = False
        ls.ring = None
        ls.forces = {}
        ls.assets = {}


# Yorkist Heir slots for IIY (highest -> lowest), by the present "form" Lord.
# Slot 2's march becomes Edward IV, slot 4's gloucester_1 becomes Richard III,
# when that slot is King -- handled in place by succession.apply_setup.
_IIY_YORKIST_SLOTS = ["york", "march", "rutland", "gloucester_1"]


def _recompute_stronghold_markers(state: GameState) -> None:
    """Set the City/Town/Fortress favour markers on the Influence track to match
    the current Favour layout (E4 "slide Yorkist Cities marker", E6 "adjust City,
    Town, Fortress markers per Favour"). Marker side = the side leading that
    Stronghold type; ``at`` = the favour-count margin (0 on a tie)."""
    locs = static_data.load_locales()
    track = state.influence["track"]
    for typ in ("city", "town", "fortress"):
        counts = {side: sum(1 for lid, lc in locs.items()
                            if lc.get("type") == typ and state.locales[lid].favour == side)
                  for side in ("yorkist", "lancastrian")}
        diff = counts["yorkist"] - counts["lancastrian"]
        leader = "yorkist" if diff >= 0 else "lancastrian"      # tie -> at 0, default Yorkist
        track.stronghold_markers[typ] = StrongholdMarker(side=Side(leader), at=abs(diff))


def apply_iiy_setup(state: GameState, removed: set[str]) -> dict[str, Any]:
    """War IIY succession-driven roster (Scenario Reference E4 / Rules 6.2.2).

    The base build is standalone Scenario II ("Warwick's Rebellion"), whose
    Yorkist roster assumes Edward IV is King. The grand IIY instead suppresses
    the base Yorkist setup and places the roster by who survived War I:
    King = highest surviving Heir at London; March at Ludlow when York is King;
    Rutland at Canterbury (when not King); Gloucester (1) in box 9; Devon box 1
    and Northumberland (1) box 9 always; Pembroke at Pembroke only once two or
    fewer Heirs remain. Lancastrian: a surviving Henry VI / Somerset (1) lead
    from box 9 (Exile), displacing Margaret / Somerset (2). Card and King-form
    triggers are applied afterwards by ``succession.apply_setup``."""
    present = [slot for slot in _IIY_YORKIST_SLOTS if slot not in removed]
    log: dict[str, Any] = {"present_heirs": list(present)}
    # Clear the base Scenario II Yorkist heir-line + Pembroke; re-place below.
    for lid in ("york", "march", "edward_iv", "rutland", "gloucester_1",
                "richard_iii", "pembroke"):
        _unplace_lord(state, lid)
    if present:                                  # King at London (highest Heir)
        king = present[0]
        _place_lord(state, king, "yorkist", location="london")
        log["king"] = king
        for slot in present[1:]:                 # supporting present Heirs
            if slot == "march":                  # York is King -> March at Ludlow
                _place_lord(state, "march", "yorkist", location="ludlow")
            elif slot == "rutland":              # Rutland (not King) at Canterbury
                _place_lord(state, "rutland", "yorkist", location="canterbury")
            elif slot == "gloucester_1":         # Gloucester (1) silver ring, box 9
                _place_lord(state, "gloucester_1", "yorkist", calendar_box=9, ring="silver")
    _place_lord(state, "devon", "yorkist", calendar_box=1)
    _place_lord(state, "northumberland_1", "yorkist", calendar_box=9)
    if len(present) <= 2:                         # Pembroke joins (heir_count<=2)
        _place_lord(state, "pembroke", "yorkist", location="pembroke")
        log["pembroke"] = True
    # Yorkist Favour at Canterbury
    state.locales["canterbury"].favour = cast(Favour, Favour.YORKIST.value)

    if "henry_vi" not in removed:                 # Henry VI leads from box 9 Exile
        _place_lord(state, "henry_vi", "lancastrian", calendar_box=9, calendar_exile=True)
        _unplace_lord(state, "margaret")
        log["lancastrian_lead"] = "henry_vi"
    if "somerset_1" not in removed:               # Somerset (1) replaces Somerset (2)
        _place_lord(state, "somerset_1", "lancastrian", calendar_box=9, calendar_exile=True)
        _unplace_lord(state, "somerset_2")
    _recompute_stronghold_markers(state)          # E4: slide Yorkist Cities marker
    return log


_IIIY_YORKIST_SLOTS = {
    "york": ["york"],
    "march": ["march", "edward_iv"],
    "rutland": ["rutland"],
    "gloucester": ["gloucester_1", "gloucester_2", "richard_iii"],
}
_IIIY_SLOT_ORDER = ["york", "march", "rutland", "gloucester"]


def _iiiy_card(state: GameState, side: str, cid: str, source: str) -> None:
    from plantagenet import succession
    succession._register_source(state, side, cid, source)


def _place_iiiy_yorkist(state: GameState, slot: str, role: str, king_slot: str) -> str:
    """Place a Yorkist Heir slot in its IIIY position (E6) with role cards and
    return the form Lord placed. ``role`` is "king" or "heir"; ``king_slot`` is
    the slot that is King (for Heir-to-York vs Heir-to-Edward IV)."""
    def c(cid: str, src: str) -> None:
        _iiiy_card(state, "yorkist", cid, src)
    if slot == "york":                                   # York is always King when present
        _place_lord(state, "york", "yorkist", location="london")
        c("Y14", "york")
        c("Y21", "york")
        return "york"
    if slot == "march":
        if role == "king":                               # York removed -> Edward IV King
            _place_lord(state, "edward_iv", "yorkist", location="london")
            c("Y23", "edward_iv")
            c("Y24", "edward_iv")
            return "edward_iv"
        _place_lord(state, "march", "yorkist", location="ludlow")   # York King -> March@Ludlow
        c("Y20", "march")
        return "march"
    if slot == "rutland":
        if role == "king":                               # Rutland & Gloucester remain -> King
            _place_lord(state, "rutland", "yorkist", location="london")
            c("Y20", "rutland")
            c("Y21", "rutland")
            return "rutland"
        _place_lord(state, "rutland", "yorkist", location="canterbury")
        c("Y31" if king_slot == "march" else "Y20", "rutland")   # Heir to Edward IV / to York
        return "rutland"
    # slot == "gloucester"
    if role == "king":                                   # Gloucester King -> Richard III
        _place_lord(state, "richard_iii", "yorkist", location="london", ring="gold")
        c("Y32", "richard_iii")
        c("Y33", "richard_iii")
        return "richard_iii"
    if king_slot == "rutland":                           # Rutland King -> Gloucester (2) gold
        _place_lord(state, "gloucester_2", "yorkist", location="london", ring="gold")
        c("Y34", "gloucester_2")
        return "gloucester_2"
    _place_lord(state, "gloucester_1", "yorkist", location="gloucester", ring="silver")
    c("Y34", "gloucester_1")
    if king_slot == "march":                             # with Edward IV -> also Y28
        c("Y28", "gloucester_1")
    return "gloucester_1"


def _apply_succession_favour(state: GameState, king_side: str) -> None:
    """E6/E7 Map: suppress base Favour; London to the King's side, and each
    in-play Lord's (other) marked Seat to that Lord's side."""
    for lid in state.locales:
        state.locales[lid].favour = cast(Favour, Favour.NEUTRAL.value)
    statics = static_data.load_lords()
    in_play = (LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE)
    for lid, ls in state.lords.items():
        if ls.status in in_play:
            seat = statics.get(lid, {}).get("seat")
            if seat and seat != "london" and seat in state.locales:
                state.locales[seat].favour = cast(Favour, ls.side)
    state.locales["london"].favour = cast(Favour, Favour(king_side).value)


def apply_iiiy_setup(state: GameState, removed: set[str]) -> dict[str, Any]:
    """War IIIY succession-driven roster (Scenario Reference E6 / 6.2.2). The
    base build (Scenario III) supplies only board structure; all Lords, Seats
    and Favour are placed here per surviving Heirs. All set-up Lords are
    Mustered (none on the Calendar)."""
    from plantagenet import succession
    log: dict[str, Any] = {}
    present = [slot for slot in _IIIY_SLOT_ORDER
               if not any(lid in removed for lid in _IIIY_YORKIST_SLOTS[slot])]
    glos_set_aside = bool((state.grand_scenario or {}).get("gloucester_as_heir_played"))
    if glos_set_aside and "rutland" in present and "gloucester" in present:
        present.remove("rutland")                        # E6: Y28 set aside displaces Rutland
        log["rutland_removed_by_y28"] = True

    # E6: "hold off setting up any Lords" -- clear the entire base Scenario III
    # roster (keeping earlier-War removals) and place exactly the IIIY roster.
    for lid in list(state.lords):
        _unplace_lord(state, lid)

    king = None
    if present == ["rutland"]:                           # Rutland sole Heir -> Yorkist Warwick King
        present = []
        _place_lord(state, "warwick_yorkist", "yorkist", location="london")
        _place_lord(state, "salisbury", "yorkist", location="york")
        for cid in ("Y16", "Y17", "Y22"):
            _iiiy_card(state, "yorkist", cid, "warwick_yorkist")
        king = "warwick_yorkist"
        log["warwick_king"] = True
    elif present:
        kept = present[:2]                               # King + next Heir; remove the rest
        king = _place_iiiy_yorkist(state, kept[0], "king", kept[0])
        if len(kept) > 1:
            _place_iiiy_yorkist(state, kept[1], "heir", kept[0])
        log["king"] = king
        log["kept_heirs"] = kept
    log["present_after_removals"] = list(present)

    seniors = [s for s in present if s in ("york", "march", "gloucester")]
    if len(seniors) == 1:                                # one senior Heir -> Northumberland (2)
        _place_lord(state, "northumberland_2", "yorkist", location="carlisle")
        _iiiy_card(state, "yorkist", "Y37", "northumberland_2")
        log["northumberland_2"] = True
    _place_lord(state, "norfolk", "yorkist", location="arundel")        # always

    # Lancastrian Heir (exactly one) + Oxford / Jasper Tudor (2).
    king_is_edward = (king == "edward_iv")
    in_france = True
    if "margaret" not in removed:
        _place_lord(state, "margaret", "lancastrian", exile_box="france")
        _iiiy_card(state, "lancastrian", "L27", "margaret")
        _iiiy_card(state, "lancastrian", "L31", "margaret")
        succession.on_muster_lord(state, "margaret")     # L26 EDWARD (free, mandatory)
        log["lancastrian_lead"] = "margaret"
    elif "henry_tudor" not in removed and not king_is_edward:
        _place_lord(state, "henry_tudor", "lancastrian", exile_box="france")
        _iiiy_card(state, "lancastrian", "L32", "henry_tudor")
        _iiiy_card(state, "lancastrian", "L35", "henry_tudor")
        log["lancastrian_lead"] = "henry_tudor"
    else:
        _place_lord(state, "warwick_lancastrian", "lancastrian", location="calais")
        _iiiy_card(state, "lancastrian", "L23", "warwick_lancastrian")
        _iiiy_card(state, "lancastrian", "L30", "warwick_lancastrian")
        in_france = False
        log["lancastrian_lead"] = "warwick_lancastrian"
    for lid in ("oxford", "jasper_tudor_2"):
        if in_france:
            _place_lord(state, lid, "lancastrian", exile_box="france")
        else:
            _place_lord(state, lid, "lancastrian", location="calais")

    _apply_succession_favour(state, "yorkist")
    _recompute_stronghold_markers(state)          # E6: adjust markers per Favour
    return log


_IIIL_LANC_HEIRS = ["henry_vi", "margaret", "somerset_1", "somerset_2"]
_IIIL_LANC_KING_CARDS = {
    "henry_vi": ["L15", "L17"],
    "margaret": ["L27", "L31"],
    "somerset_1": ["L18", "L20", "L27"],
}
_IIIL_YORKIST_SLOTS = {
    "york": ["york"],
    "march": ["march", "edward_iv"],
    "rutland": ["rutland"],
    "gloucester": ["gloucester_1", "gloucester_2", "richard_iii"],
}
_IIIL_SLOT_ORDER = ["york", "march", "rutland", "gloucester"]


def apply_iiil_setup(state: GameState, removed: set[str]) -> dict[str, Any]:
    """War IIIL succession-driven roster (Scenario Reference E7 / 6.2.2). The
    Lancastrians are King (highest surviving L Heir at London; Somerset (2)
    yields to Somerset (1)), with Oxford and Jasper Tudor (2). The Yorkist
    Rebels are placed by Succession in the Burgundy Exile box -- or at Calais if
    a Yorkist Warwick is the Heir -- with Norfolk and (when only one Heir)
    Salisbury. Favour = London Lancastrian + each in-play Lord's marked Seat."""
    from plantagenet import succession
    log: dict[str, Any] = {}
    for lid in list(state.lords):                       # clear base build; re-place per E7
        _unplace_lord(state, lid)

    # ---- Lancastrian King (highest surviving L Heir) ----
    l_present = [h for h in _IIIL_LANC_HEIRS if h not in removed]
    king = l_present[0] if l_present else None
    if king == "somerset_2":                            # Somerset (2) yields to Somerset (1)
        king = "somerset_1"
    if king is not None:
        _place_lord(state, king, "lancastrian", location="london")
        for c in _IIIL_LANC_KING_CARDS.get(king, []):
            succession._register_source(state, "lancastrian", c, king)
        if king == "margaret":
            succession.on_muster_lord(state, "margaret")      # L26 EDWARD (free, mandatory)
        log["lancastrian_king"] = king
    _place_lord(state, "oxford", "lancastrian", location="oxford")
    _place_lord(state, "jasper_tudor_2", "lancastrian", location="pembroke")

    # ---- Yorkist Rebels (Succession; forms revert to non-King) ----
    present = [slot for slot in _IIIL_SLOT_ORDER
               if not any(lid in removed for lid in _IIIL_YORKIST_SLOTS[slot])]
    glos_set_aside = bool((state.grand_scenario or {}).get("gloucester_as_heir_played"))
    heirs: list[tuple[str, list[str]]] = []        # (lord_id, [cards])
    warwick_heir = False
    if present and ((glos_set_aside and "gloucester" in present) or present[0] == "gloucester"):
        heirs = [("gloucester_2", ["Y35"])]             # Gloucester (2) the sole Heir
    elif "york" in present:
        heirs = [("york", ["Y14", "Y18"])]
        rest = [slot for slot in present if slot != "york"]
        nxt = rest[0] if rest else None
        if nxt in ("march", "rutland"):
            heirs.append((nxt, ["Y20"]))
        elif nxt == "gloucester":
            heirs.append(("gloucester_1", ["Y34"]))
    else:
        warwick_heir = True                             # highest is March/Rutland, or none
    if not heirs and not warwick_heir:
        warwick_heir = True
    if warwick_heir:
        heirs = [("warwick_yorkist", ["Y16"])]
    salisbury = len(heirs) == 1                          # exactly one Heir -> Salisbury + Y17/Y22

    # Placement: Burgundy Exile box, or Calais if the Yorkist Warwick is Heir.
    y_at: dict[str, Any] = ({"location": "calais"} if warwick_heir
                            else {"exile_box": "burgundy"})
    for lord_id, cards in heirs:
        _place_lord(state, lord_id, "yorkist", **y_at)
        for c in cards:
            succession._register_source(state, "yorkist", c, lord_id)
    if salisbury:
        _place_lord(state, "salisbury", "yorkist", **y_at)
        for c in ("Y17", "Y22"):
            succession._register_source(state, "yorkist", c, "salisbury")
    _place_lord(state, "norfolk", "yorkist", **y_at)    # Norfolk always
    log["yorkist_heirs"] = [h for h, _ in heirs]
    log["salisbury"] = salisbury

    _apply_succession_favour(state, "lancastrian")      # London Lancastrian + marked Seats
    _recompute_stronghold_markers(state)
    return log


def apply_natural_causes(state: GameState) -> dict[str, Any]:
    """Natural Causes (E4/E5 special rule): after victory in a second War (IIY
    or IIL), roll for aging Heirs still present. Henry VI and York: roll two
    dice -- a roll (sum) less than the last Turn box played removes that Heir.
    Edward IV (IIY only, not March): roll one die -- removed on a '6'. Removed
    Heirs are permanently out (6.2.2) and incur the -8 Influence penalty in the
    next War's setup. Operates on the *won* state before the next War is built.
    "Last Turn played" = the final Calendar Turn box reached (Rules 2.2)."""
    gs = state.grand_scenario or {}
    war = {w["war_id"]: w for w in static_data.load_scenario("wars_of_the_roses")["wars"]}.get(
        gs.get("current_war"))
    spec = (war or {}).get("natural_causes")
    if not spec:
        return {"applied": False}
    last_turn = state.turn_box
    roller = state.dice()
    removed, rolls = [], []
    alive = (LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE)
    for entry in spec:
        lid = entry["lord"]
        ls = state.lords.get(lid)
        if ls is None or ls.status not in alive:
            continue
        dice = entry.get("dice", 1)
        roll = sum(roller.d6() for _ in range(dice))
        cond = entry["remove_if"]
        gone = (roll < last_turn) if cond == "sum_lt_last_turn" else (roll == 6)
        rolls.append({"lord": lid, "roll": roll, "removed": gone})
        if gone:
            ls.status = LordStatus.REMOVED
            ls.location = ls.exile_box = ls.calendar_box = None
            removed.append(lid)
    state.store_dice(roller)
    return {"applied": True, "last_turn": last_turn, "rolls": rolls, "removed": removed}


def next_war_id(scn_grand: dict[str, Any], current_war: str, winner: str) -> str | None:
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
    _wars_by_id = {w["war_id"]: w for w in scn_grand["wars"]}
    from_order = _wars_by_id.get(gs["current_war"], {}).get("order")
    # The Y28 "Gloucester As Heir" set-aside is referenced only by IIIY, and only
    # if it occurred in the second War (E6); carry it forward only from order 2.
    glos_flag = gs.get("gloucester_as_heir_played", False) if from_order == 2 else False
    nxt = next_war_id(scn_grand, gs["current_war"], winner)
    if nxt is None:
        raise IllegalAction("game_over", "the final War is concluded; no Renewed War (6.1)")
    war = {w["war_id"]: w for w in scn_grand["wars"]}[nxt]

    apply_natural_causes(state)          # E4/E5: aging-Heir removals before carry-over
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
        "allied_networks": war.get("allied_networks") or gs.get("allied_networks", {}),
        "victory_threshold": war.get("victory_threshold"),
        "deck_sources": {}, "succession_fired": [], "current_king": {},
        "set_aside_on_disband": set_aside_keep,
        "gloucester_as_heir_played": glos_flag,
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
    if nxt == "war_iiy":                                # E4: succession-driven roster
        apply_iiy_setup(new, removed_prior)
    elif nxt == "war_iiiy":                             # E6: succession-driven roster
        apply_iiiy_setup(new, removed_prior)
    elif nxt == "war_iiil":                             # E7: succession-driven roster
        apply_iiil_setup(new, removed_prior)
    succession.apply_setup(new)                         # setup-time Succession (6.2)
    new.levy_step = "arts_of_war"
    return new
