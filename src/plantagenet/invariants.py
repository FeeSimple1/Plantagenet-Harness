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


def influence_violations(state: GameState) -> list[dict[str, Any]]:
    """The net Influence marker must sit within its track bounds (1.4.1)."""
    from plantagenet.influence import INFLUENCE_CAP
    out = []
    track = state.influence.get("track")
    if track is not None and not (0 <= track.marker_at <= INFLUENCE_CAP):
        out.append({"kind": "influence_marker_oob", "at": track.marker_at,
                    "cap": INFLUENCE_CAP})
    return out


def lord_status_violations(state: GameState) -> list[dict[str, Any]]:
    """A Lord's status and its position fields must agree. (Battle-only scenarios
    keep Lords Mustered with no map position -- they sit in a Battle Array.)"""
    from plantagenet import static_data
    battle_only = bool(static_data.load_scenario(state.scenario).get("battle_only"))
    out = []
    for lid, ls in state.lords.items():
        st = ls.status
        if (st == LordStatus.MUSTERED and not battle_only
                and not (ls.location or ls.exile_box or ls.at_sea)):
            out.append({"kind": "mustered_nowhere", "lord": lid})
        elif st == LordStatus.CALENDAR and ls.calendar_box is None:
            out.append({"kind": "calendar_no_box", "lord": lid})
        elif st == LordStatus.EXILE and ls.exile_box is None:
            out.append({"kind": "exile_no_box", "lord": lid})
        elif st == LordStatus.CAPTURED and ls.captured_by is None:
            out.append({"kind": "captured_no_holder", "lord": lid})
        # A Lord occupies exactly one position: at most one of these mutually
        # exclusive "where" fields may be set. (A Lord Mustered in an Exile box
        # uses exile_box alone; one on the map uses location alone; one at Sea
        # uses at_sea alone; etc.) Two at once -- e.g. an Exiled Lord still
        # carrying at_sea -- is an impossible dual location.
        occupied = [f for f in ("location", "exile_box", "at_sea",
                                "calendar_box", "captured_by")
                    if getattr(ls, f) is not None]
        if len(occupied) > 1:
            out.append({"kind": "incompatible_position", "lord": lid,
                        "fields": occupied})
    return out


def card_zone_violations(state: GameState) -> list[dict[str, Any]]:
    """An Arts of War card must occupy exactly one zone: no card in two of a
    side's deck piles, and no card both in a deck pile and on a Lord's mat."""
    out = []
    for side, deck in state.decks.items():
        piles_of: dict[str, list[str]] = {}
        for pile in ("draw", "discard", "held", "set_aside"):
            for c in deck.get(pile, []):
                piles_of.setdefault(c, []).append(pile)
        mat_caps = {c for ls in state.lords.values() if ls.side == side
                    for c in ls.capabilities}
        for c, piles in piles_of.items():
            if len(piles) > 1:
                out.append({"kind": "card_in_two_piles", "side": side, "card": c,
                            "piles": piles})
            if c in mat_caps:
                out.append({"kind": "card_in_deck_and_on_mat", "side": side, "card": c})
    return out


def board_invariant_violations(state: GameState) -> list[dict[str, Any]]:
    """All always-on invariants as one flat list of ``{kind, ...}`` (advisory
    §3). Empty == the board is in a legal configuration."""
    out = [{"kind": "co_location", **v} for v in co_location_violations(state)]
    out += influence_violations(state)
    out += lord_status_violations(state)
    out += card_zone_violations(state)
    return out
