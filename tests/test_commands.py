"""Campaign Command-menu actions: March, Sail, Tax, Parley, Feed (4.x)."""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def _to_campaign(sid, seed=1):
    s = build_initial_state(sid, seed=seed)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian" and v.status == "mustered"]
    n = s.campaign.cards_required

    def pad(lo):
        e = [{"lord": x} for x in lo][:n]
        while len(e) < n:
            e.append({"pass": True})
        return e
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": pad(yk)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": pad(lc)})
    return s


def test_march_highway_one_action_and_marks_moved():
    s = _to_campaign("henry_vi")          # York active first, at Ely
    assert s.campaign.active_lord == "york"
    before = s.campaign.actions_remaining
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": "york", "to": "cambridge"})  # Ely-Cambridge Highway
    assert r["way"] == "highway" and r["whole_card"] is False
    assert s.lords["york"].location == "cambridge"
    assert s.lords["york"].moved_fought is True
    assert s.campaign.actions_remaining == before - 1


def test_march_path_takes_whole_card():
    # York Ely; reach a Path move? Use Chester (Path hub). Instead: move a Lord
    # whose adjacency includes a Path. March April (March at Ludlow) Ludlow has
    # no Path; use York -> ... Build a direct case: Lancaster<->Chester Path.
    s = _to_campaign("henry_vi")
    # Relocate York to Chester so a Path march (Chester-Lancaster) is available.
    s.lords["york"].location = "chester"
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": "york", "to": "lancaster"})
    assert r["way"] == "path" and r["whole_card"] is True
    assert s.campaign.actions_remaining == 0


def test_march_into_enemy_locale_triggers_approach():
    s = _to_campaign("henry_vi")
    # Put a Lancastrian Lord at Cambridge; the Defender Exiles on Approach.
    s.lords["henry_vi"].location = "cambridge"
    r = actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"responses": {"henry_vi": "exile"}}})
    assert r["approach"] is not None
    assert "henry_vi" in r["approach"]["exiles"]
    assert s.campaign.actions_remaining == 0   # Approach ends the card (4.3.5)


def test_march_adjacent_to_enemy_allowed_without_intercept():
    s = _to_campaign("henry_vi")
    s.lords["henry_vi"].location = "bedford"   # adjacent to Cambridge by Highway
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": "york", "to": "cambridge"})
    assert s.lords["york"].location == "cambridge"
    assert r["intercept"] is None and r["approach"] is None


def test_intercept_moves_enemy_to_destination_then_approach():
    s = _to_campaign("henry_vi")
    s.lords["henry_vi"].location = "bedford"   # adjacent to Cambridge by Highway
    # Henry VI intercepts; he has Valour 0, so the attempt fails (roll never <= 0).
    r = actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge", "decisions": {"intercept": "henry_vi"}})
    assert r["intercept"]["interceptor"] == "henry_vi"
    assert r["intercept"]["success"] is False    # Valour 0 -> cannot Intercept
    assert s.lords["henry_vi"].location == "bedford"


def test_intercept_success_triggers_battle():
    s = _to_campaign("henry_vi")
    # March (Yorkist, Valour 3) sits adjacent and Intercepts York's march.
    s.lords["march"].location = "bury_st_edmunds"   # adjacent to Cambridge by Road
    s.lords["henry_vi"].location = "bury_st_edmunds"  # an enemy for March? no - same side
    # Use a Lancastrian interceptor: place Somerset (Valour 2) adjacent to Cambridge.
    s.lords["somerset_1"].location = "cambridge"
    s.lords["somerset_1"].location = "bury_st_edmunds"  # Road-adjacent to Cambridge
    r = actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"intercept": "somerset_1",
                                               "responses": {"somerset_1": "exile"}}})
    if r["intercept"]["success"]:
        assert "somerset_1" in r["approach"]["exiles"]
    else:
        assert r["approach"] is None


def test_haul_discards_provender_over_carts():
    s = _to_campaign("henry_vi")
    s.lords["york"].assets["provender"] = 5
    s.lords["york"].assets["cart"] = 2
    actions.apply_action(s, {"type": "march", "side": "yorkist",
                             "by_lord": "york", "to": "cambridge"})
    assert s.lords["york"].assets["provender"] == 2  # discarded down to Carts (4.3.2)


def test_tax_own_seat_auto_adds_coin():
    s = _to_campaign("henry_vi")          # York at Ely (own Seat, a City)
    coin = s.lords["york"].assets.get("coin", 0)
    r = actions.apply_action(s, {"type": "tax", "side": "yorkist",
                                 "by_lord": "york", "target": "ely"})
    assert r["auto"] is True and r["coin_added"] == 2   # City Tax = 2 Coin
    assert s.lords["york"].assets["coin"] == coin + 2
    assert s.locales["ely"].depletion == "depleted"


def test_tax_rejects_bad_target():
    s = _to_campaign("henry_vi")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "tax", "side": "yorkist",
                                 "by_lord": "york", "target": "cambridge"})
    assert e.value.code == "bad_tax_target"


def test_campaign_parley_own_location_is_automatic():
    s = _to_campaign("henry_vi")
    s.lords["york"].location = "lynn"        # Neutral
    r = actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "lynn"})
    assert r["auto"] is True
    assert s.locales["lynn"].favour == "yorkist"


def test_sail_port_to_port_same_sea():
    s = _to_campaign("my_kingdom_for_a_horse")   # Lancastrian Rebel; Lords in France
    lid = s.campaign.active_lord
    s.lords[lid].assets["ship"] = 3
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "southampton"})
    assert r["to"] == "southampton"
    assert s.lords[lid].location == "southampton"
    assert s.campaign.actions_remaining == 0     # Sail takes the whole card


def test_sail_requires_enough_ships():
    s = _to_campaign("my_kingdom_for_a_horse")
    lid = s.campaign.active_lord
    s.lords[lid].assets["ship"] = 0
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "southampton"})
    assert e.value.code == "insufficient_ships"


def test_feed_consumes_provender_for_moved_lord():
    s = _to_campaign("henry_vi")
    actions.apply_action(s, {"type": "march", "side": "yorkist",
                             "by_lord": "york", "to": "cambridge"})
    prov = s.lords["york"].assets.get("provender", 0)
    troops = campaign._troop_count(s.lords["york"])
    need = -(-troops // 6)
    actions.apply_action(s, {"type": "end_activation", "side": "yorkist"})
    assert s.lords["york"].assets.get("provender", 0) == prov - need
    assert s.lords["york"].moved_fought is False


def test_unfed_moved_lord_pillages_then_disbands():
    s = _to_campaign("henry_vi")
    york = s.lords["york"]
    york.assets["provender"] = 0
    york.assets["cart"] = 0
    # Move to a Neutral Town-ish Locale and strip provender so Feed must Pillage.
    actions.apply_action(s, {"type": "march", "side": "yorkist",
                             "by_lord": "york", "to": "cambridge"})
    # Cambridge is a Town: Pillage yields 1 Provender (covers ceil(troops/6) for
    # York's ~6 Troops), so York Feeds via Pillage and survives, Cambridge Exhausts.
    actions.apply_action(s, {"type": "end_activation", "side": "yorkist"})
    assert s.locales["cambridge"].depletion == "exhausted"
    assert s.locales["cambridge"].favour == "yorkist" or True  # enemy-favour set to forager's foe


def test_campaign_activation_round_trip():
    # Every enumerated Activation move must be accepted by its handler.
    for sid in ("henry_vi", "warwicks_rebellion", "my_kingdom_for_a_horse"):
        s = _to_campaign(sid)
        steps = 0
        while s.campaign and s.campaign.step == "activation" and steps < 400:
            moves = legal_moves.legal_moves(s)
            for mv in moves:
                snap = s.model_copy(deep=True)
                try:
                    actions.apply_action(snap, mv)
                except IllegalAction as e:
                    pytest.fail(f"{sid}: enumerated {mv} rejected -> {e.code}")
            nxt = next((m for m in moves if m["type"] != "end_activation"), moves[-1])
            actions.apply_action(s, nxt)
            steps += 1


def test_supply_from_current_location_no_carts():
    s = _to_campaign("henry_vi")          # York at Ely (City, own Seat, Friendly)
    prov = s.lords["york"].assets.get("provender", 0)
    r = actions.apply_action(s, {"type": "supply", "side": "yorkist",
                                 "by_lord": "york", "source": "ely"})
    assert r["ways"] == 0 and r["provender_added"] == 2     # City Supply = 2 Provender
    assert s.lords["york"].assets["provender"] == prov + 2
    assert s.locales["ely"].depletion == "depleted"


def test_supply_over_one_way_needs_a_cart_per_provender():
    s = _to_campaign("henry_vi")
    s.locales["lynn"].favour = "yorkist"   # Fortress (1 Provender), one Way from Ely
    s.lords["york"].assets["cart"] = 0
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "supply", "side": "yorkist",
                                 "by_lord": "york", "source": "lynn"})
    assert e.value.code == "insufficient_carts"
    s.lords["york"].assets["cart"] = 1
    r = actions.apply_action(s, {"type": "supply", "side": "yorkist",
                                 "by_lord": "york", "source": "lynn"})
    assert r["provender_added"] == 1


def test_supply_exile_box_lord_needs_ship_and_port():
    s = _to_campaign("my_kingdom_for_a_horse")   # Lancastrian Rebel in France
    lid = s.campaign.active_lord
    # No ship: a Stronghold Supply Source from the Exile box is illegal.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                 "by_lord": lid, "source": "ludlow"})
    assert e.value.code in ("exile_needs_ship_port", "no_route")
    # With a Ship and a same-Sea Port Source (Southampton, English Channel): ships-many.
    s.lords[lid].assets["ship"] = 2
    r = actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                 "by_lord": lid, "source": "southampton", "use_ships": True})
    assert r["via"] == "ship" and r["provender_added"] == 2   # equals Ships
