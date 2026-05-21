"""Levy Muster action handlers (Rules 3.4)."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus, VassalStatus


def test_turn_order_rebel_then_king():
    # 3.4: Rebel then King's Lords. Ia: Yorkist Rebel acts first.
    s = build_initial_state("henry_vi")
    assert s.active_side == "yorkist"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "guildford"})
    assert e.value.code == "not_active_side"


def test_parley_neutral_to_friendly_on_success_and_spends_lordship():
    s = build_initial_state("henry_vi", seed=1)
    r = actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "lynn"})
    assert r["way_cost"] == 1  # ely-lynn is one Way (Road)
    assert s.lords["york"].lordship_spent == 1
    if r["success"]:
        assert s.locales["lynn"].favour == "yorkist"


def test_parley_rejects_already_friendly_location():
    s = build_initial_state("henry_vi")
    # Yorkist favour already at ely (York's seat). Parley there is pointless.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "ely"})
    assert e.value.code == "already_friendly"


def test_parley_no_route_when_target_unreachable_friendly_chain():
    s = build_initial_state("henry_vi")
    # London Favours Lancastrian; York at Ely cannot Route to a distant Enemy
    # Stronghold through non-Friendly intermediates.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "london"})
    assert e.value.code == "no_route"


def test_lordship_exhausts_after_rating_actions():
    s = build_initial_state("henry_vi")
    rating = actions._lordship("march")  # March Lordship = 2
    for _ in range(rating):
        actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                                 "by_lord": "march", "transport": "cart"})
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                                 "by_lord": "march", "transport": "cart"})
    assert e.value.code == "lordship_exhausted"


def test_levy_transport_cart_adds_two():
    s = build_initial_state("henry_vi")
    before = s.lords["york"].assets.get("cart", 0)
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "cart"})
    assert s.lords["york"].assets["cart"] == before + 2


def test_levy_lord_requires_ready_target():
    s = build_initial_state("henry_vi")
    # Salisbury is on the Calendar at box 2 (> Turn 1): not Ready.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_lord", "side": "yorkist",
                                 "by_lord": "york", "target": "salisbury"})
    assert e.value.code == "target_not_ready"


def test_levy_lord_musters_ready_target_at_seat():
    s = build_initial_state("henry_vi", seed=4)
    # Make Salisbury Ready (cylinder in the current Turn box).
    s.lords["salisbury"].calendar_box = 1
    # Keep trying until the Influence check succeeds (York rating 5).
    for _ in range(20):
        if s.lords["salisbury"].status == LordStatus.MUSTERED:
            break
        if s.lords["york"].lordship_spent >= actions._lordship("york"):
            s.lords["york"].lordship_spent = 0  # allow more attempts for the test
        actions.apply_action(s, {"type": "levy_lord", "side": "yorkist",
                                 "by_lord": "york", "target": "salisbury"})
    assert s.lords["salisbury"].status == LordStatus.MUSTERED
    assert s.lords["salisbury"].location == "york"  # Salisbury's Seat
    assert s.lords["salisbury"].mustered_this_segment is True
    assert s.lords["salisbury"].forces  # got a mat


def test_levy_vassal_needs_friendly_enemyfree_seat():
    s = build_initial_state("henry_vi")
    # Suffolk's Seat is Ipswich (Neutral at start) -> not Friendly.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                 "by_lord": "york", "target": "suffolk"})
    assert e.value.code == "seat_not_friendly"


def test_levy_vassal_musters_with_service_marker():
    s = build_initial_state("henry_vi", seed=2)
    # Make Suffolk's Seat (Ipswich) Friendly to Yorkist.
    s.locales["ipswich"].favour = "yorkist"
    for _ in range(20):
        if s.vassals["suffolk"].status == VassalStatus.MUSTERED:
            break
        if s.lords["york"].lordship_spent >= actions._lordship("york"):
            s.lords["york"].lordship_spent = 0
        actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                 "by_lord": "york", "target": "suffolk"})
    v = s.vassals["suffolk"]
    assert v.status == VassalStatus.MUSTERED
    assert v.on_lord == "york"
    assert v.service_box == 1 + 3  # Turn 1 + Suffolk Service 3
    assert "suffolk" in s.lords["york"].vassals


def test_levy_troops_deferred_to_strongholds_table():
    s = build_initial_state("henry_vi")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert e.value.code == "needs_strongholds_table"


def test_levy_capability_deferred_to_phase_4():
    s = build_initial_state("henry_vi")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_capability", "side": "yorkist", "by_lord": "york"})
    assert e.value.code == "deferred_phase_4"


def test_end_muster_passes_rebel_to_king_then_completes():
    s = build_initial_state("henry_vi")
    r1 = actions.apply_action(s, {"type": "end_muster", "side": "yorkist"})
    assert r1["next"] == "king_muster"
    assert s.active_side == "lancastrian"
    r2 = actions.apply_action(s, {"type": "end_muster", "side": "lancastrian"})
    assert r2["next"] == "levy_complete"
    assert s.levy_step == "done"


def test_exile_box_lord_may_levy_transport_but_not_troops():
    # III: Henry Tudor is Mustered in the France Exile box (Lancastrian Rebel).
    s = build_initial_state("my_kingdom_for_a_horse")
    assert s.active_side == "lancastrian"
    r = actions.apply_action(s, {"type": "levy_transport", "side": "lancastrian",
                                 "by_lord": "henry_tudor", "transport": "cart"})
    assert r["added"] == "2 cart"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "lancastrian",
                                 "by_lord": "henry_tudor"})
    assert e.value.code == "needs_strongholds_table"
