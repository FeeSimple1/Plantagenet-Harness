"""Human/LLM-readable renderings of a GameState.

Pure read-only formatting. `render_summary` is the compact view an LLM
uses for routine decisions (kept terse); `render_verbose` is the complete
state as pretty JSON; `render_focused` zooms into a single Lord mat,
Locale, the Calendar, or the Influence track.

No prescriptive language (no "should"/"recommend"): these functions
describe state only (BRIEF: "No Agent in the Harness").
"""

from __future__ import annotations

from plantagenet import static_data
from plantagenet.state import GameState, LordStatus

SIDE_LABEL = {"lancastrian": "Lancastrian", "yorkist": "Yorkist"}


def render_summary(state: GameState) -> str:
    lines: list[str] = []
    lines.append(f"{state.title or state.scenario}")
    cal = state.calendar
    box_range = ""
    if cal.first_box and cal.last_box:
        box_range = f" (boxes {cal.first_box}-{cal.last_box})"
    lines.append(f"Turn box {state.turn_box}{box_range} | phase: {state.phase} "
                 f"| active: {SIDE_LABEL.get(state.active_side, state.active_side)}")
    if state.grand_scenario:
        lines.append(f"Grand scenario — current war: {state.grand_scenario.get('current_war')}")
    roles = " / ".join(f"{SIDE_LABEL[s]}: {r}" for s, r in state.roles.items())
    if roles:
        lines.append(roles)

    for side in ("lancastrian", "yorkist"):
        side_lords = [v for v in state.lords.values() if v.side == side]
        if not side_lords:
            continue
        lines.append(f"\n{SIDE_LABEL[side]} Lords ({len(side_lords)}):")
        for v in sorted(side_lords, key=lambda x: x.lord_id):
            lines.append(f"  {_lord_line(v)}")

    if state.influence:
        lines.append("\nInfluence:")
        for _, inf in state.influence.items():
            mk = ", ".join(f"{k} {m.side[:1].upper()}{m.at}"
                           for k, m in inf.stronghold_markers.items())
            vc = f", VC {inf.victory_check}" if inf.victory_check is not None else ""
            lines.append(f"  marker {inf.marker_at} ({SIDE_LABEL[inf.marker_side]})"
                         + (f"; {mk}" if mk else "") + vc)

    # Favour tally
    fav = {"lancastrian": 0, "yorkist": 0, "neutral": 0}
    for ls in state.locales.values():
        fav[ls.favour] = fav.get(ls.favour, 0) + 1
    lines.append(f"\nFavour: Lancastrian {fav['lancastrian']}, "
                 f"Yorkist {fav['yorkist']}, Neutral {fav['neutral']}")
    return "\n".join(lines)


def _lord_line(v) -> str:
    where = ""
    if v.status == LordStatus.MUSTERED:
        where = f"@ {v.location}" if v.location else "(mat)"
    elif v.status == LordStatus.CALENDAR:
        where = f"cal box {v.calendar_box}" + (" [Exile]" if v.calendar_exile else "")
    elif v.status == LordStatus.EXILE:
        where = f"exile: {v.exile_box}"
    ring = f" ({v.ring} ring)" if v.ring else ""
    extra = ""
    if v.capabilities:
        extra += f" caps={v.capabilities}"
    if v.special_vassals:
        extra += f" sv={v.special_vassals}"
    return f"{v.lord_id}: {v.status} {where}{ring}{extra}".rstrip()


def render_verbose(state: GameState) -> str:
    return state.to_json()


def render_focused(state: GameState, target: str) -> str:
    if target == "calendar":
        return _focus_calendar(state)
    if target == "influence":
        return _focus_influence(state)
    if target in state.lords:
        return _focus_lord(state, target)
    if target in state.locales:
        return _focus_locale(state, target)
    return (f"Unknown focus target: {target!r} "
            "(use a lord id, locale id, 'calendar', or 'influence')")


def _focus_lord(state: GameState, lord_id: str) -> str:
    v = state.lords[lord_id]
    static = static_data.load_lords().get(lord_id, {})
    r = static.get("ratings", {})
    lines = [f"Lord {lord_id} ({SIDE_LABEL.get(v.side, v.side)}) — {static.get('name', '')}"]
    if static.get("title"):
        lines.append(f"  Title: {static['title']}"
                     + (f" | Heir #{static['heir']}" if static.get("heir") else ""))
    lines.append(f"  Ratings: Influence {r.get('influence')} / Lordship {r.get('lordship')}"
                 f" / Command {r.get('command')} / Valour {r.get('valour')}")
    lines.append(f"  Seat: {static.get('seat')}")
    where = ""
    if v.status == LordStatus.MUSTERED and v.location:
        where = f"@ {v.location}"
    elif v.status == LordStatus.CALENDAR:
        where = f"Calendar box {v.calendar_box}" + (" [Exile]" if v.calendar_exile else "")
    elif v.status == LordStatus.EXILE:
        where = f"Exile box {v.exile_box}"
    lines.append(f"  Status: {v.status} {where}".rstrip()
                 + (f" ({v.ring} ring)" if v.ring else ""))
    if v.status == LordStatus.MUSTERED:
        lines.append(f"  Forces: {v.forces or '(none)'}")
        lines.append(f"  Assets: {v.assets or '(none)'}")
    if v.capabilities:
        lines.append(f"  Capabilities: {v.capabilities}")
    if v.special_vassals:
        lines.append(f"  Special Vassals: {v.special_vassals}")
    on_mat = [vid for vid, vs in state.vassals.items() if vs.on_lord == lord_id]
    if on_mat:
        lines.append(f"  Vassals on mat: {on_mat}")
    return "\n".join(lines)


def _focus_locale(state: GameState, loc_id: str) -> str:
    static = static_data.load_locales().get(loc_id, {})
    ls = state.locales[loc_id]
    lines = [f"Locale {loc_id} — {static.get('name', '')}"]
    lines.append(f"  Type: {static.get('type')}"
                 + ("  [Port]" if static.get("port") else "")
                 + (f"  region: {static['region']}" if static.get("region") else ""))
    lines.append(f"  Favour: {ls.favour}")
    if static.get("lord_seats"):
        lines.append(f"  Lord Seats: {static['lord_seats']}")
    if static.get("vassal_seats"):
        lines.append(f"  Vassal Seats: {static['vassal_seats']}")
    adj = [f"{w['to'] if w['from'] == loc_id else w['from']} ({w['type']})"
           for w in static_data.load_ways() if loc_id in (w["from"], w["to"])]
    if adj:
        lines.append(f"  Ways: {', '.join(sorted(adj))}")
    here = [v.lord_id for v in state.lords.values() if v.location == loc_id]
    if here:
        lines.append(f"  Lords here: {here}")
    return "\n".join(lines)


def _focus_calendar(state: GameState) -> str:
    cal = state.calendar
    lines = ["Calendar:"]
    lines.append(f"  Levy marker: box {cal.levy_box} | End marker: box {cal.end_box}")
    by_box: dict[int, list[str]] = {}
    for v in state.lords.values():
        if v.status == LordStatus.CALENDAR and v.calendar_box is not None:
            tag = f"{v.lord_id} ({v.side[:1].upper()})" + (" [Exile]" if v.calendar_exile else "")
            by_box.setdefault(v.calendar_box, []).append(tag)
    for vid, vs in state.vassals.items():
        if vs.service_box is not None:
            by_box.setdefault(vs.service_box, []).append(f"vassal:{vid}")
    for box in sorted(by_box):
        lines.append(f"  Box {box}: {', '.join(sorted(by_box[box]))}")
    return "\n".join(lines)


def _focus_influence(state: GameState) -> str:
    if not state.influence:
        return "No Influence track in this scenario."
    lines = ["Influence track:"]
    for _key, inf in state.influence.items():
        lines.append(f"  marker at {inf.marker_at} on the {SIDE_LABEL[inf.marker_side]} side")
        for k, m in inf.stronghold_markers.items():
            lines.append(f"    {k}: {SIDE_LABEL[m.side]} at {m.at}")
        if inf.victory_check is not None:
            lines.append(f"    Victory Check: {inf.victory_check}")
    return "\n".join(lines)
