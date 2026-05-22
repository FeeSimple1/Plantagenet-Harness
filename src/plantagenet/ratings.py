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
