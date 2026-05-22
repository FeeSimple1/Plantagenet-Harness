"""Influence points and the Influence check (Rules 1.4.1, 1.4.2).

Influence is tracked as a single net value on the edge track: a marker at
``marker_at`` showing ``marker_side``'s colour. The net total never
exceeds 45 (1.4.1). Spending Influence always moves the marker *toward the
opponent*; gaining moves it toward the gaining side (1.4.1 NOTE).

The Influence check (1.4.2): the acting Lord's side spends 1 point; it may
spend 1 more (+1 to the rating) or 3 more (+2); a Vassal Levy modifies the
rating by the Vassal's Loyalty (added if its colour matches the Levying
side, subtracted if it opposes); Parley adds 1 point per Way of distance.
Roll a d6 — success if roll <= modified rating, with a "1" always
succeeding and a "6" always failing.
"""

from __future__ import annotations

from typing import Any

from plantagenet import ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, InfluenceState, Side

INFLUENCE_CAP = 45
_RATING_BONUS = {0: 0, 1: 1, 3: 2}   # additional points spent -> rating bonus


def _track(state: GameState) -> InfluenceState:
    track = state.influence.get("track")
    if track is None:
        raise IllegalAction("no_influence_track",
                            "this scenario has no Influence track (1.4.1)")
    return track


def _net_lanc(track: InfluenceState) -> int:
    return track.marker_at if track.marker_side == Side.LANCASTRIAN.value else -track.marker_at


def _write_net(track: InfluenceState, net: int) -> None:
    net = max(-INFLUENCE_CAP, min(INFLUENCE_CAP, net))   # 1.4.1: never exceed 45
    if net >= 0:
        track.marker_side = Side.LANCASTRIAN.value
        track.marker_at = net
    else:
        track.marker_side = Side.YORKIST.value
        track.marker_at = -net


def _toward(track: InfluenceState, side: str, points: int) -> None:
    """Move the marker ``points`` toward ``side``."""
    net = _net_lanc(track)
    net += points if side == Side.LANCASTRIAN.value else -points
    _write_net(track, net)


def spend_influence(state: GameState, side: str, points: int) -> None:
    """Spend Influence: move the marker ``points`` toward the opponent."""
    other = Side.YORKIST.value if side == Side.LANCASTRIAN.value else Side.LANCASTRIAN.value
    _toward(_track(state), other, points)


def gain_influence(state: GameState, side: str, points: int) -> None:
    """Gain Influence: move the marker ``points`` toward ``side``."""
    _toward(_track(state), side, points)


def lord_influence_rating(lord_id: str) -> int:
    return static_data.load_lords()[lord_id]["ratings"]["influence"]


def check_influence(
    state: GameState,
    lord_id: str,
    side: str,
    *,
    extra_spend: int = 0,
    loyalty_mod: int = 0,
    way_cost: int = 0,
    action: str | None = None,
) -> dict[str, Any]:
    """Perform an Influence check for ``lord_id``; returns the outcome.

    Spends 1 + ``extra_spend`` + ``way_cost`` Influence points (toward the
    opponent), rolls a d6 from the seeded dice, and reports success.
    ``extra_spend`` must be 0, 1, or 3 (1.4.2: "never two").
    """
    if extra_spend not in _RATING_BONUS:
        raise IllegalAction("bad_extra_spend",
                            "added Influence spend must be 0, 1, or 3 (1.4.2)")
    rating = (ratings.rating(state, lord_id, "influence", action=action)
              + _RATING_BONUS[extra_spend] + loyalty_mod)
    total_spend = 1 + extra_spend + way_cost
    spend_influence(state, side, total_spend)

    roller = state.dice()
    roll = roller.d6()
    state.store_dice(roller)

    success = roll == 1 or (roll != 6 and roll <= rating)
    return {"success": success, "roll": roll, "rating": rating, "spent": total_spend}
