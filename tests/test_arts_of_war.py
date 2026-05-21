"""Arts of War draw (3.1)."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def test_levy_begins_at_arts_of_war_with_shuffled_decks():
    s = build_initial_state("henry_vi", seed=1)
    assert s.levy_step == "arts_of_war"
    assert len(s.decks["yorkist"]["draw"]) == 22     # Ia Yorkist deck
    assert len(s.decks["lancastrian"]["draw"]) == 22


def test_first_levy_draw_deploys_two_capabilities_rebel_then_king():
    s = build_initial_state("henry_vi", seed=1)     # Yorkist Rebel
    r = actions.apply_action(s, {"type": "draw", "side": "yorkist"})
    assert r["first_levy"] is True and len(r["drawn"]) == 2
    assert len(r["deployed"]) + len(r["discarded"]) == 2
    assert r["next"] == "king_draw" and s.active_side == "lancastrian"
    deployed_cards = {d["card"] for d in r["deployed"]}
    assert deployed_cards <= set(
        c for ls in s.lords.values() for c in ls.capabilities)
    r2 = actions.apply_action(s, {"type": "draw", "side": "lancastrian"})
    assert r2["next"] == "muster" and s.levy_step == "muster"


def test_draw_order_rebel_then_king():
    s = build_initial_state("henry_vi")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "draw", "side": "lancastrian"})
    assert e.value.code == "not_active_side"


def test_later_levy_draws_events_into_hold_active_or_deck():
    # Force a second Levy by claiming it is not the first Turn.
    s = build_initial_state("henry_vi", seed=2)
    s.turn_box = 2                                   # not the scenario's first Turn
    before = len(s.decks["yorkist"]["draw"])
    r = actions.apply_action(s, {"type": "draw", "side": "yorkist"})
    assert r["first_levy"] is False
    # Each drawn Event is held, active (This Levy/Campaign), or resolved-to-deck.
    assert len(r["held"]) + len(r["active"]) + len(r["resolved"]) == len(r["drawn"])
    # Held cards leave the draw pile; resolved/immediate return to it.
    assert len(s.decks["yorkist"]["draw"]) == before - 2 + len(r["resolved"])
    for cid in r["active"]:
        assert any(e["card"] == cid for e in s.active_events)
