"""Immediate Arts of War Event resolution integrated into the draw flow (3.1.3).

A 2nd-or-later Levy draws Events; immediate ones are queued on
``state.pending_events`` and resolved by ``play_event`` (with any decisions)
before the Levy advances. Each resolved card returns to the deck (3.1.3), and an
Event whose precondition is unmet has no effect rather than being rejected.
"""

from __future__ import annotations

import pytest

from plantagenet import actions, invariants, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from tests._helpers import resolve_pending_events


def _later_levy_with_top(scenario, seed, side_imm):
    """Build a later-Levy state and force two immediate Events to the top of the
    active (Rebel) side's draw pile. Returns (state, side, [cards])."""
    s = build_initial_state(scenario, seed=seed)
    s.turn_box = 2
    side = s.active_side
    cards = side_imm[side]
    deck = s.decks[side]["draw"]
    for c in cards:
        if c in deck:
            deck.remove(c)
    for c in reversed(cards):
        deck.insert(0, c)
    return s, side, cards


def test_draw_queues_immediates_and_blocks_advance():
    s, side, cards = _later_levy_with_top(
        "warwicks_rebellion", 1, {"lancastrian": ["L30", "L26"]})
    r = actions.apply_action(s, {"type": "draw", "side": side})
    assert r["next"] == "resolve_events"
    assert [pe["card"] for pe in s.pending_events] == cards
    # The Levy does not advance: active side unchanged, still arts_of_war.
    assert s.active_side == side and s.levy_step == "arts_of_war"
    assert invariants.board_invariant_violations(s) == []


def test_only_play_event_legal_while_pending():
    s, side, _ = _later_levy_with_top(
        "warwicks_rebellion", 1, {"lancastrian": ["L30", "L26"]})
    actions.apply_action(s, {"type": "draw", "side": side})
    moves = legal_moves.legal_moves(s)
    assert {m["type"] for m in moves} == {"play_event"}
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "draw", "side": side})
    assert e.value.code == "events_pending"


def test_resolution_returns_card_to_deck_and_advances():
    s, side, cards = _later_levy_with_top(
        "warwicks_rebellion", 1, {"lancastrian": ["L30", "L26"]})
    actions.apply_action(s, {"type": "draw", "side": side})
    resolve_pending_events(s)
    assert s.pending_events == []
    # Each immediate card is back in the deck exactly once (3.1.3, no duplication).
    for c in cards:
        piles = sum(s.decks[side][p].count(c) for p in ("draw", "discard", "held"))
        assert piles == 1, (c, piles)
    assert invariants.board_invariant_violations(s) == []
    # Rebel finished -> King draws next.
    assert s.active_side != side and s.levy_step == "arts_of_war"


def test_precondition_unmet_event_has_no_effect_not_rejected():
    # Tudor Banners (L32) has no effect unless Henry Tudor is at a Friendly
    # Stronghold; drawing it without him must resolve to no effect, not raise.
    s = build_initial_state("warwicks_rebellion", seed=1)
    s.turn_box = 2
    # Resolve as a pending event directly through play_event in a forced context.
    s.pending_events.append({"card": "L32", "side": "lancastrian"})
    s.active_side = "lancastrian"
    r = actions.apply_action(s, {"type": "play_event", "card": "L32",
                                 "side": "lancastrian"})
    assert "no_effect" in r
    assert invariants.board_invariant_violations(s) == []


def test_warwicks_propaganda_sizes_to_available():
    # Only 2 Yorkist Strongholds exist -> Warwick's Propaganda selects 2, not 3.
    s = build_initial_state("warwicks_rebellion", seed=1)
    for _loc, ls in s.locales.items():
        if ls.favour == "yorkist":
            ls.favour = "neutral"
    picks = list(s.locales)[:2]
    for loc in picks:
        s.locales[loc].favour = "yorkist"
    s.pending_events.append({"card": "L23", "side": "lancastrian"})
    s.active_side = "lancastrian"
    # Supplying 3 is now wrong (only 2 available); supplying 2 is correct.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_event", "card": "L23",
                                 "side": "lancastrian", "decisions": {
                                     "strongholds": {loc: "remove"
                                                     for loc in list(s.locales)[:3]}}})
    assert e.value.code == "bad_count"
    actions.apply_action(s, {"type": "play_event", "card": "L23",
                             "side": "lancastrian", "decisions": {
                                 "strongholds": {loc: "remove" for loc in picks}}})
    assert all(s.locales[loc].favour == "neutral" for loc in picks)
