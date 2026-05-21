"""Levy Muster action handlers (Rules 3.4)."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus, VassalStatus
from tests._helpers import to_muster


def test_turn_order_rebel_then_king():
    # 3.4: Rebel then King's Lords. Ia: Yorkist Rebel acts first.
    s = build_initial_state("henry_vi")
    to_muster(s)
    assert s.active_side == "yorkist"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "guildford"})
    assert e.value.code == "not_active_side"


def test_parley_neutral_to_friendly_on_success_and_spends_lordship():
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    r = actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "lynn"})
    assert r["way_cost"] == 1  # ely-lynn is one Way (Road)
    assert s.lords["york"].lordship_spent == 1
    if r["success"]:
        assert s.locales["lynn"].favour == "yorkist"


def test_parley_rejects_already_friendly_location():
    s = build_initial_state("henry_vi")
    to_muster(s)
    # Yorkist favour already at ely (York's seat). Parley there is pointless.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "ely"})
    assert e.value.code == "already_friendly"


def test_parley_no_route_when_target_unreachable_friendly_chain():
    s = build_initial_state("henry_vi")
    to_muster(s)
    # London Favours Lancastrian; York at Ely cannot Route to a distant Enemy
    # Stronghold through non-Friendly intermediates.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "london"})
    assert e.value.code == "no_route"


def test_lordship_exhausts_after_rating_actions():
    s = build_initial_state("henry_vi")
    to_muster(s)
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
    to_muster(s)
    before = s.lords["york"].assets.get("cart", 0)
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "cart"})
    assert s.lords["york"].assets["cart"] == before + 2


def test_levy_lord_requires_ready_target():
    s = build_initial_state("henry_vi")
    to_muster(s)
    # Salisbury is on the Calendar at box 2 (> Turn 1): not Ready.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_lord", "side": "yorkist",
                                 "by_lord": "york", "target": "salisbury"})
    assert e.value.code == "target_not_ready"


def test_levy_lord_musters_ready_target_at_seat():
    s = build_initial_state("henry_vi", seed=4)
    to_muster(s)
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
    to_muster(s)
    # Suffolk's Seat is Ipswich (Neutral at start) -> not Friendly.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                 "by_lord": "york", "target": "suffolk"})
    assert e.value.code == "seat_not_friendly"


def test_levy_vassal_musters_with_service_marker():
    s = build_initial_state("henry_vi", seed=2)
    to_muster(s)
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


def test_levy_troops_city_yields_and_depletes():
    # 3.4.4 + D-004: Ely is a City -> 1 Longbow + 1 Militia (Background Book
    # example), then Deplete; a second Levy Exhausts; a third is rejected.
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    lb = s.lords["york"].forces.get("longbow", 0)
    mil = s.lords["york"].forces.get("militia", 0)
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert r["added"] == {"longbow": 1, "militia": 1}
    assert s.lords["york"].forces["longbow"] == lb + 1
    assert s.lords["york"].forces["militia"] == mil + 1
    assert s.locales["ely"].depletion == "depleted"
    actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert s.locales["ely"].depletion == "exhausted"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert e.value.code == "exhausted"


def test_levy_troops_no_influence_check_spends_one_lordship():
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    track_before = (s.influence["track"].marker_side, s.influence["track"].marker_at)
    actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    # No Influence is spent for Levy Troops (3.4.4 NOTE).
    assert (s.influence["track"].marker_side, s.influence["track"].marker_at) == track_before
    assert s.lords["york"].lordship_spent == 1


def test_levy_troops_pool_limited():
    # 1.6: Muster no Troops beyond the pool. Drain the Militia pool, then a
    # Town (2 Militia) yields nothing for that type.
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    s.lords["york"].forces["militia"] = 45  # entire Militia pool on one mat
    s.locales["ely"].favour = "yorkist"
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert "militia" not in r["added"]      # none left in the pool
    assert r["added"].get("longbow") == 1   # Longbow still available


def test_end_muster_passes_rebel_to_king_then_completes():
    s = build_initial_state("henry_vi")
    to_muster(s)
    r1 = actions.apply_action(s, {"type": "end_muster", "side": "yorkist"})
    assert r1["next"] == "king_muster"
    assert s.active_side == "lancastrian"
    r2 = actions.apply_action(s, {"type": "end_muster", "side": "lancastrian"})
    assert r2["next"] == "levy_complete"
    assert s.levy_step == "done"


def test_exile_box_lord_may_levy_transport_but_not_troops():
    # III: Henry Tudor is Mustered in the France Exile box (Lancastrian Rebel).
    s = build_initial_state("my_kingdom_for_a_horse")
    to_muster(s)
    assert s.active_side == "lancastrian"
    r = actions.apply_action(s, {"type": "levy_transport", "side": "lancastrian",
                                 "by_lord": "henry_tudor", "transport": "cart"})
    assert r["added"] == "2 cart"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "lancastrian",
                                 "by_lord": "henry_tudor"})
    assert e.value.code == "in_exile_box"  # Exile-box Lords may not Levy Troops (3.4.4)


def test_levy_capability_attaches_eligible_card():
    s = build_initial_state("henry_vi")          # Yorkist Rebel; York at Ely (Friendly)
    to_muster(s)
    s.lords["york"].capabilities = []            # ignore any draw-deployed Capabilities
    r = actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                                 "by_lord": "york", "card": "Y1"})
    assert r["title"] == "CULVERINS AND FALCONETS"
    assert s.lords["york"].capabilities == ["Y1"]
    assert s.lords["york"].lordship_spent == 1


def test_levy_capability_blocks_duplicate_name_and_third_card():
    s = build_initial_state("henry_vi")
    to_muster(s)
    s.lords["york"].capabilities = []
    actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                             "by_lord": "york", "card": "Y1"})
    # Y2 shares the CULVERINS AND FALCONETS Capability name -> duplicate.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                                 "by_lord": "york", "card": "Y2"})
    assert e.value.code == "duplicate_capability"
    actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                             "by_lord": "york", "card": "Y3"})
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                                 "by_lord": "york", "card": "Y9"})
    assert e.value.code == "two_capabilities"


def test_levy_capability_rejects_card_not_in_scenario_deck():
    s = build_initial_state("henry_vi")          # Ia uses rose-1 cards, not rose-2/3
    to_muster(s)
    s.lords["york"].capabilities = []
    with pytest.raises(IllegalAction) as e:       # Y32 is a rose-3 (Scenario III) card
        actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                                 "by_lord": "york", "card": "Y32"})
    assert e.value.code == "card_not_in_scenario"


def test_levy_capability_eligibility_by_name():
    # L35 THOMAS STANLEY: eligible for Jasper Tudor or Henry Tudor only.
    s = build_initial_state("my_kingdom_for_a_horse")   # Lancastrian Rebel; Henry/Jasper in France
    to_muster(s)
    s.lords["jasper_tudor_2"].capabilities = []
    r = actions.apply_action(s, {"type": "levy_capability", "side": "lancastrian",
                                 "by_lord": "jasper_tudor_2", "card": "L35"})
    assert r["title"] == "THOMAS STANLEY"
    s2 = build_initial_state("my_kingdom_for_a_horse")
    to_muster(s2)
    with pytest.raises(IllegalAction) as e:        # Oxford is not eligible for L35
        actions.apply_action(s2, {"type": "levy_capability", "side": "lancastrian",
                                  "by_lord": "oxford", "card": "L35"})
    assert e.value.code == "ineligible_lord"
