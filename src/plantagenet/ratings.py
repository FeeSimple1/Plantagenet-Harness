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

from plantagenet import static_data

_MUSTERED = "mustered"


# ----------------------------------------------------------------------------
# board-context helpers (used by conditional Capability mods)
# ----------------------------------------------------------------------------
def _loc(state, lord_id: str):
    ls = state.lords.get(lord_id)
    if ls is None or ls.status != _MUSTERED or ls.location is None:
        return None
    return ls.location


def _loc_friendly(state, lord_id: str) -> bool:
    """Lord is at a Locale whose Favour matches the Lord's own side (1.5)."""
    where = _loc(state, lord_id)
    if where is None:
        return False
    loc = state.locales.get(where)
    return loc is not None and loc.favour == state.lords[lord_id].side


def _other_lord_at(state, other_id: str, location: str) -> bool:
    o = state.lords.get(other_id)
    return o is not None and o.status == _MUSTERED and o.location == location


def _named_lord_at(state, name_prefix: str, location: str) -> bool:
    """A Mustered Lord whose printed name starts with ``name_prefix`` (e.g.
    "Warwick") is at ``location`` -- resolves either side's copy."""
    lords = static_data.load_lords()
    for lid, ls in state.lords.items():
        if ls.status != _MUSTERED or ls.location != location:
            continue
        if lords.get(lid, {}).get("name", "").startswith(name_prefix):
            return True
    return False


def _lord_removed(state, lord_id: str) -> bool:
    o = state.lords.get(lord_id)
    return o is not None and o.status == "removed"


# ----------------------------------------------------------------------------
# Capability rating modifiers (Arts of War, 1.9.1).  Keyed by Capability title.
# Each entry is a callable (state, lord_id, action) -> {rating_name: delta}.
# ----------------------------------------------------------------------------
def _cap_thomas_bourchier(state, lid, action):      # Y5: +1 Command at a Friendly City
    where = _loc(state, lid)
    if where is None:
        return {}
    loc = state.locales.get(where)
    typ = static_data.load_locales().get(where, {}).get("type")
    if loc is not None and loc.favour == state.lords[lid].side and typ == "city":
        return {"command": 1}
    return {}


def _cap_yorks_favoured_son(state, lid, action):    # Y20
    return {"influence": 1, "command": 1}


def _cap_fair_arbiter(state, lid, action):          # Y22 (Salisbury)
    return {"influence": 1, "lordship": 1} if _loc_friendly(state, lid) else {}


def _cap_fallen_brother(state, lid, action):        # Y26 (Gloucester/Richard III)
    return {"influence": 2, "lordship": 1} if _lord_removed(state, "clarence") else {}


def _cap_in_the_name_of_the_king(state, lid, action):   # L11
    return {"influence": 1} if action == "parley" else {}


def _cap_expert_counsellors(state, lid, action):    # L13
    return {"valour": 2}


def _cap_veteran_of_french_wars(state, lid, action):    # L20
    return {"valour": 2}


def _cap_married_to_a_neville(state, lid, action):  # L24 (Clarence)
    where = _loc(state, lid)
    if where and _loc_friendly(state, lid) and _named_lord_at(state, "Warwick", where):
        return {"influence": 2, "command": 1}
    return {}


def _cap_loyal_somerset(state, lid, action):        # L28 (Somerset)
    where = _loc(state, lid)
    if where and _other_lord_at(state, "margaret", where):
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
def _ev_richard_of_york(state, ev, lid, action):    # Y14: this Levy +1 Influence for Parley
    return {"influence": 1} if action == "parley" else {}


def _ev_privy_council(state, ev, lid, action):      # Y35: this Levy +1 all Influence ratings
    return {"influence": 1}


def _ev_yorkist_parade(state, ev, lid, action):     # Y20: this Levy +2 Yorkist Influence
    return {"influence": 2}


def _ev_loyalty_and_trust(state, ev, lid, action):  # Y22: a chosen Yorkist Lord Lordship +3
    return {"lordship": 3} if ev.get("target") == lid else {}


def _ev_edward_v(state, ev, lid, action):           # Y33: Gloucester (not Richard III) +3 Lordship
    return {"lordship": 3} if lid in ("gloucester_1", "gloucester_2") else {}


def _event_rating_fn(title):
    return {
        "RICHARD OF YORK": _ev_richard_of_york,
        "PRIVY COUNCIL": _ev_privy_council,
        "YORKIST PARADE": _ev_yorkist_parade,
        "LOYALTY AND TRUST": _ev_loyalty_and_trust,
        "EDWARD V": _ev_edward_v,
    }.get(title)


def _capability_mod(state, lord_id: str, name: str, action) -> int:
    cards = static_data.load_cards()
    total = 0
    for c in state.lords[lord_id].capabilities:
        title = cards[c]["capability"]["title"]
        fn = _CAP_RATING_MODS.get(title)
        if fn is not None:
            total += fn(state, lord_id, action).get(name, 0)
    return total


def _event_mod(state, lord_id: str, name: str, action) -> int:
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


def rating(state, lord_id: str, name: str, *, action: str | None = None) -> int:
    base = static_data.load_lords()[lord_id]["ratings"][name]
    special = static_data.load_vassals()["special"]
    mod = sum(special.get(sv, {}).get("modifiers", {}).get(name, 0)
              for sv in state.lords[lord_id].special_vassals)
    mod += _capability_mod(state, lord_id, name, action)
    mod += _event_mod(state, lord_id, name, action)
    return base + mod


def has_capability(state, lord_id: str, title: str) -> bool:
    """Whether a Capability with ``title`` is on ``lord_id``'s mat."""
    cards = static_data.load_cards()
    return any(cards[c]["capability"]["title"] == title
               for c in state.lords[lord_id].capabilities)


def event_active(state, title: str):
    """Active This-Levy / This-Campaign Events with the given Event title."""
    cards = static_data.load_cards()
    return [e for e in state.active_events
            if cards[e["card"]]["event"]["title"] == title]


def event_against(state, title: str, side: str) -> bool:
    """Whether an active Event titled ``title`` is in effect against ``side``
    (i.e. played by the opposing side)."""
    return any(e["side"] != side for e in event_active(state, title))
