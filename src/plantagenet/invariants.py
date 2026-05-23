"""Runtime board-state invariants (1.3, 4.3.5).

Unlike ``data_integrity`` (which validates the static reference data), these
assert that a *live* ``GameState`` is in a legal configuration. Plantagenet has
no Siege or Storm and no Retreat (4.4.3): opposing Lords never legitimately rest
in the same Locale -- entering an Enemy Lord's Locale forces Approach, which
resolves to Battle or Exile (4.3.5), and a Battle loser always leaves the Locale
(Die/Disband/Exile). So two opposing Mustered Lords sharing a ``location`` is an
illegal state. (Cross-project advisory: a "loser survives but never relocates"
class of bug; this invariant closes it for Plantagenet regardless of cause.)
"""

from __future__ import annotations

from typing import Any

from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus


def _pending_approach_dests(state: GameState) -> set[str]:
    """Locales with an Approach reaction window open (4.3.5 / Q-004): the
    Marching Lord is already at the dest while the defender's cancel/Battle
    is being resolved, so co-location there is a legal transient."""
    out: set[str] = set()
    for p in (state.pending or []):
        if p.get("trigger") == "on_approach":
            dest = (p.get("ctx") or {}).get("dest")
            if dest:
                out.add(dest)
    return out


def co_location_violations(state: GameState) -> list[dict[str, Any]]:
    """Locales where Mustered Lords of both sides share a position with no
    pending Approach to resolve it. Returns one entry per offending Locale:
    ``{"locale", "lords"}``. Empty list == legal."""
    exempt = _pending_approach_dests(state)
    by_locale: dict[str, dict[str, list[str]]] = {}
    for lid, ls in state.lords.items():
        if ls.status == LordStatus.MUSTERED and ls.location:
            by_locale.setdefault(ls.location, {}).setdefault(ls.side, []).append(lid)
    out = []
    for loc, sides in by_locale.items():
        if len(sides) > 1 and loc not in exempt:
            lords = sorted(lid for group in sides.values() for lid in group)
            out.append({"locale": loc, "lords": lords})
    return out


def assert_board_invariants(state: GameState) -> None:
    """Raise ``IllegalAction`` if the board holds any illegal co-location."""
    bad = co_location_violations(state)
    if bad:
        first = bad[0]
        raise IllegalAction(
            "co_located_enemies",
            f"opposing Lords {first['lords']} share Locale {first['locale']!r} with "
            f"no pending Approach (illegal: Plantagenet has no Siege/Retreat, 4.4.3)")
