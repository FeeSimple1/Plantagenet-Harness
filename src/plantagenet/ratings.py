"""Effective Lord ratings = printed rating + active card/Special-Vassal mods.

Currently applies Special-Vassal rating modifiers (Command/Valour) tracked on
`LordState.special_vassals`; Arts of War Capability rating mods can hook in
here too. Use this instead of reading `lords.json` ratings directly anywhere
a rating could be modified in play.
"""

from __future__ import annotations

from plantagenet import static_data


def rating(state, lord_id: str, name: str) -> int:
    base = static_data.load_lords()[lord_id]["ratings"][name]
    special = static_data.load_vassals()["special"]
    mod = sum(special.get(sv, {}).get("modifiers", {}).get(name, 0)
              for sv in state.lords[lord_id].special_vassals)
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
