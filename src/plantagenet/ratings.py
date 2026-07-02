"""Effective Lord ratings = printed rating + active card/Special-Vassal mods.

Sums, in order: printed rating (lords.json) + Special-Vassal modifiers
(``LordState.special_vassals``) + Arts of War **Capability** modifiers
(``LordState.capabilities``) + active **Event** rating modifiers
(``state.active_events``).  Use this instead of reading ``lords.json``
ratings directly anywhere a rating could be modified in play.

Some Capability mods are conditional (location/board context) or scoped to a
particular action (e.g. "Influence +1 for Parley"); pass ``action`` so those
fire only when relevant.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from plantagenet import static_data
from plantagenet.state import GameState

_MUSTERED = "mustered"


# ----------------------------------------------------------------------------
# board-context helpers (used by conditional Capability mods)
# ----------------------------------------------------------------------------
def _loc(state: GameState, lord_id: str) -> str | None:
    ls = state.lords.get(lord_id)
    if ls is None or ls.status != _MUSTERED or ls.location is None:
        return None
    return ls.location


def _loc_friendly(state: GameState, lord_id: str) -> bool:
    """Lord is at a Locale whose Favour matches the Lord's own side (1.5)."""
    where = _loc(state, lord_id)
    if where is None:
        return False
    loc = state.locales.get(where)
    return loc is not None and cast(str, loc.favour) == cast(str, state.lords[lord_id].side)


def _other_lord_at(state: GameState, other_id: str, location: str) -> bool:
    o = state.lords.get(other_id)
    return o is not None and o.status == _MUSTERED and o.location == location


def _named_lord_at(state: GameState, name_prefix: str, location: str) -> bool:
    """A Mustered Lord whose printed name starts with ``name_prefix`` (e.g.
    "Warwick") is at ``location`` -- resolves either side's copy."""
    lords = static_data.load_lords()
    for lid, ls in state.lords.items():
        if ls.status != _MUSTERED or ls.location != location:
            continue
        if lords.get(lid, {}).get("name", "").startswith(name_prefix):
            return True
    return False


def _lord_removed(state: GameState, lord_id: str) -> bool:
    o = state.lords.get(lord_id)
    return o is not None and o.status == "removed"


# ----------------------------------------------------------------------------
# Capability rating modifiers (Arts of War, 1.9.1).  Keyed by Capability title.
# Each entry is a callable (state, lord_id, action) -> {rating_name: delta}.
# ----------------------------------------------------------------------------
# Y5: +1 Command at a Friendly City
def _cap_thomas_bourchier(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    where = _loc(state, lid)
    if where is None:
        return {}
    loc = state.locales.get(where)
    typ = static_data.load_locales().get(where, {}).get("type")
    if (loc is not None and typ == "city"
            and cast(str, loc.favour) == cast(str, state.lords[lid].side)):
        return {"command": 1}
    return {}


# Y20
def _cap_yorks_favoured_son(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 1, "command": 1}


# Y22 (Salisbury)
def _cap_fair_arbiter(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 1, "lordship": 1} if _loc_friendly(state, lid) else {}


# Y26 (Gloucester/Richard III)
def _cap_fallen_brother(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 2, "lordship": 1} if _lord_removed(state, "clarence") else {}


# L11
def _cap_in_the_name_of_the_king(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 1} if action == "parley" else {}


# L13
def _cap_expert_counsellors(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    return {"valour": 2}


# L20
def _cap_veteran_of_french_wars(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    return {"valour": 2}


# L24 (Clarence)
def _cap_married_to_a_neville(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    where = _loc(state, lid)
    if where and _loc_friendly(state, lid) and _named_lord_at(state, "Warwick", where):
        return {"influence": 2, "command": 1}
    ls = state.lords.get(lid)                       # ... or in the same Exile box as Warwick
    if ls is not None and ls.exile_box is not None and any(
            o.lord_id != lid and o.exile_box == ls.exile_box
            and static_data.load_lords()[o.lord_id]["name"].startswith("Warwick")
            for o in state.lords.values()):
        return {"influence": 2, "command": 1}
    return {}


# L28 (Somerset)
def _cap_loyal_somerset(state: GameState, lid: str, action: str | None) -> dict[str, int]:
    where = _loc(state, lid)
    if where and _other_lord_at(state, "margaret", where):
        return {"influence": 1, "valour": 1}
    ls = state.lords.get(lid)                       # ... or in the same Exile box as Margaret
    mg = state.lords.get("margaret")
    if (ls is not None and ls.exile_box is not None
            and mg is not None and mg.exile_box == ls.exile_box):
        return {"influence": 1, "valour": 1}
    return {}


_CAP_RATING_MODS = {
    "THOMAS BOURCHIER": _cap_thomas_bourchier,
    "YORK'S FAVOURED SON": _cap_yorks_favoured_son,
    "FAIR ARBITER": _cap_fair_arbiter,
    "FALLEN BROTHER": _cap_fallen_brother,
    "IN THE NAME OF THE KING": _cap_in_the_name_of_the_king,
    "EXPERT COUNSELLORS": _cap_expert_counsellors,
    "VETERAN OF FRENCH WARS": _cap_veteran_of_french_wars,
    "MARRIED TO A NEVILLE": _cap_married_to_a_neville,
    "LOYAL SOMERSET": _cap_loyal_somerset,
}


# ----------------------------------------------------------------------------
# Active-Event rating modifiers (This Levy / This Campaign Events, 1.9.1).
# Keyed by Event title -> callable (state, ev, lord_id, action) -> {name: delta}
# where ``ev`` is the active_events entry (has "side", "card").
# The mod applies only to Lords on the Event-owner's side.
# ----------------------------------------------------------------------------
# Y14: this Levy +1 Influence for Parley
def _ev_richard_of_york(state: GameState, ev: dict[str, Any],
        lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 1} if action == "parley" else {}


# Y35: this Levy +1 all Influence ratings
def _ev_privy_council(state: GameState, ev: dict[str, Any],
        lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 1}


# Y20: this Levy +2 Yorkist Influence
def _ev_yorkist_parade(state: GameState, ev: dict[str, Any],
        lid: str, action: str | None) -> dict[str, int]:
    return {"influence": 2}


# Y22: a chosen Yorkist Lord Lordship +3
def _ev_loyalty_and_trust(state: GameState, ev: dict[str, Any],
        lid: str, action: str | None) -> dict[str, int]:
    return {"lordship": 3} if ev.get("target") == lid else {}


# Y33: Gloucester (not Richard III) +3 Lordship
def _ev_edward_v(state: GameState, ev: dict[str, Any],
        lid: str, action: str | None) -> dict[str, int]:
    return {"lordship": 3} if lid in ("gloucester_1", "gloucester_2") else {}


def _event_rating_fn(
        title: str,
) -> Callable[[GameState, dict[str, Any], str, str | None], dict[str, int]] | None:
    return {
        "RICHARD OF YORK": _ev_richard_of_york,
        "PRIVY COUNCIL": _ev_privy_council,
        "YORKIST PARADE": _ev_yorkist_parade,
        "LOYALTY AND TRUST": _ev_loyalty_and_trust,
        "EDWARD V": _ev_edward_v,
    }.get(title)


def _capability_mod(state: GameState, lord_id: str, name: str, action: str | None) -> int:
    cards = static_data.load_cards()
    total = 0
    for c in state.lords[lord_id].capabilities:
        title = cards[c]["capability"]["title"]
        fn = _CAP_RATING_MODS.get(title)
        if fn is not None:
            total += fn(state, lord_id, action).get(name, 0)
    return total


def _event_mod(state: GameState, lord_id: str, name: str, action: str | None) -> int:
    cards = static_data.load_cards()
    side = state.lords[lord_id].side
    total = 0
    for ev in state.active_events:
        if ev.get("side") != side:
            continue
        title = cards[ev["card"]]["event"]["title"]
        fn = _event_rating_fn(title)
        if fn is not None:
            total += fn(state, ev, lord_id, action).get(name, 0)
    return total


def rating(state: GameState, lord_id: str, name: str, *, action: str | None = None) -> int:
    base: int = static_data.load_lords()[lord_id]["ratings"][name]
    special = static_data.load_vassals()["special"]
    mod: int = sum(special.get(sv, {}).get("modifiers", {}).get(name, 0)
              for sv in state.lords[lord_id].special_vassals)
    mod += _capability_mod(state, lord_id, name, action)
    mod += _event_mod(state, lord_id, name, action)
    return base + mod


def has_capability(state: GameState, lord_id: str, title: str) -> bool:
    """Whether a Capability with ``title`` is on ``lord_id``'s mat."""
    cards = static_data.load_cards()
    return any(cards[c]["capability"]["title"] == title
               for c in state.lords[lord_id].capabilities)


def event_active(state: GameState, title: str) -> list[dict[str, Any]]:
    """Active This-Levy / This-Campaign Events with the given Event title."""
    cards = static_data.load_cards()
    return [e for e in state.active_events
            if cards[e["card"]]["event"]["title"] == title]


def event_against(state: GameState, title: str, side: str) -> bool:
    """Whether an active Event titled ``title`` is in effect against ``side``
    (i.e. played by the opposing side)."""
    return any(e["side"] != side for e in event_active(state, title))
