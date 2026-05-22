"""Succession (6.2-6.3) for the Wars of the Roses grand scenario.

This module implements the *general* Succession mechanic (6.2.2): when an Heir
is removed by Death or Shipwreck (NOT mere Disband or Exile), the next-ranked
still-available Heir of that side enters at the next Calendar box.

The per-War *scripted* parts (specific Arts of War card add/remove, the free
mandatory Capability assignments such as L26 EDWARD to Margaret, and the
Renewed-War setup transitions) are stored as verbatim prose in
``wars_of_the_roses.json`` and are tracked as a structured-encoding follow-up
(see RULES_QUESTIONS Q-005); they are not auto-applied here.
"""

from __future__ import annotations

from typing import Any

from plantagenet import static_data
from plantagenet.state import GameState, LordState, LordStatus


def _heir_table(state: GameState, side: str) -> list[dict[str, Any]]:
    scn = static_data.load_scenario("wars_of_the_roses")
    return scn.get("heirs", {}).get(side, [])


def heir_rank(state: GameState, side: str, lord_id: str) -> int | None:
    for entry in _heir_table(state, side):
        if lord_id in entry.get("lord_ids", []):
            return entry["rank"]
    return None


def on_heir_removed(state: GameState, lord_id: str) -> dict[str, Any] | None:
    """Apply the general Succession step when ``lord_id`` is removed by Death or
    Shipwreck during the grand scenario. Adds the next-ranked still-available
    Heir of the same side to the next Calendar box (6.2.2). Returns a log dict
    or None if nothing happened."""
    if not state.grand_scenario:
        return None
    side = state.lords[lord_id].side
    rank = heir_rank(state, side, lord_id)
    if rank is None:
        return None                       # not an Heir -> no Succession effect
    lords_static = static_data.load_lords()
    for entry in sorted(_heir_table(state, side), key=lambda e: e["rank"]):
        if entry["rank"] <= rank:
            continue
        if entry.get("third_war_only") and not _is_third_war(state):
            continue
        for cand in entry["lord_ids"]:
            ls = state.lords.get(cand)
            if ls is not None and ls.status in (LordStatus.AVAILABLE, LordStatus.REMOVED):
                if ls.status != LordStatus.AVAILABLE:
                    continue                              # Dead Heirs never return (6.2.2)
                ls.status = LordStatus.CALENDAR
                ls.calendar_box = state.turn_box + 1
                return {"succession": cand, "after": lord_id, "to_box": ls.calendar_box}
            if ls is None and cand in lords_static:       # ADD a not-yet-present Heir (6.2)
                state.lords[cand] = LordState(
                    lord_id=cand, side=side, status=LordStatus.CALENDAR,
                    calendar_box=state.turn_box + 1)
                return {"succession": cand, "after": lord_id,
                        "to_box": state.turn_box + 1, "added": True}
    return None


def _is_third_war(state: GameState) -> bool:
    gs = state.grand_scenario or {}
    return str(gs.get("war_id", "")).startswith("war_iii")
