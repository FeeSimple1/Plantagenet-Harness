"""Regression coverage for Arts of War, Rebel Supply Depot, and Pay (October audit)."""

from __future__ import annotations

import pytest

from plantagenet import actions, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def _later_events():
    s = build_initial_state("warwicks_rebellion", seed=1)
    s.turn_box = (s.calendar.first_box or s.turn_box) + 1
    deck = s.decks["lancastrian"]["draw"]
    for cid in ("L30", "L26"):
        deck.remove(cid)
    deck[:0] = ["L30", "L26"]
    actions.apply_action(s, {"type": "draw", "side": "lancastrian"})
    return s


def test_immediate_event_requires_draw_and_cannot_replay():
    """Rules 3.1.3: an immediate Event resolves once for each actual draw."""
    s = _later_events()
    action = {"type": "play_event", "side": "lancastrian", "card": "L30"}
    before = s.lords["warwick_lancastrian"].assets.get("coin", 0)
    actions.apply_action(s, action)
    assert s.lords["warwick_lancastrian"].assets["coin"] == before + 1
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(s, action)
    assert exc.value.code == "event_not_pending"
    assert s.decks["lancastrian"]["draw"].count("L30") == 1
    assert s.lords["warwick_lancastrian"].assets["coin"] == before + 1


def test_immediate_events_resolve_in_draw_order():
    """Rules 3.1.3 requires implementing Events in the order drawn."""
    s = _later_events()
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(s, {"type": "play_event", "side": "lancastrian", "card": "L26"})
    assert exc.value.code == "event_order"
    assert [pe["card"] for pe in s.pending_events] == ["L30", "L26"]


@pytest.mark.parametrize(("change", "code"), [
    ({"phase": "campaign"}, "wrong_step"),
    ({"levy_step": "muster"}, "wrong_step"),
    ({"active_side": "yorkist"}, "not_active_side"),
    ({"turn_box": 1}, "first_levy"),
])
def test_immediate_event_obeys_draw_window(change, code):
    """Rules 3.1.2-.3: Events need the active side's later-Levy draw window."""
    s = _later_events()
    for attr, value in change.items():
        setattr(s, attr, value)
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(s, {"type": "play_event", "side": "lancastrian", "card": "L30"})
    assert exc.value.code == code


def test_undrawn_event_is_rejected_even_if_in_deck():
    """Rules 3.1.3: unused deck membership alone never authorizes Event play."""
    s = build_initial_state("warwicks_rebellion", seed=1)
    s.turn_box = 2
    s.active_side = "yorkist"
    assert "Y23" in s.decks["yorkist"]["draw"]
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(s, {"type": "play_event", "side": "yorkist", "card": "Y23"})
    assert exc.value.code == "event_not_pending"


def _pay_state():
    s = build_initial_state("henry_vi", seed=1)
    s.turn_box = 2
    s.levy_step = "pay"
    for lid in ("york", "march"):
        s.lords[lid].forces = {"retinue": 1, "men_at_arms": 6}
        s.lords[lid].assets["coin"] = 1
    return s


def test_pay_spends_partial_coin_before_pillage_then_owes_full_pay_again():
    """Rules 3.2.1: initial partial Coin is spent; after Pillage full Pay is due."""
    s = _pay_state()
    york = s.lords["york"]
    york.forces = {"retinue": 1, "men_at_arms": 7, "longbow": 6}
    york.assets["coin"] = 1
    s.locales["ely"].depletion = None
    result = actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert result["troops"]["pillaged"] == ["ely"]
    assert result["troops"]["unpaid_disbanded"] == ["york"]
    assert s.lords["york"].status == "calendar"


def test_pay_uses_own_coin_before_sharing():
    """Rules 3.2.1 SHARING: each Lord pays his own Troops from his own mat first."""
    s = _pay_state()
    for lid in ("york", "march"):
        s.lords[lid].location = "ely"
        s.lords[lid].assets["coin"] = 2
    actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert s.lords["york"].assets["coin"] == 1
    assert s.lords["march"].assets["coin"] == 1


def test_payment_preference_cannot_divert_another_lords_own_pay():
    """Rules 3.2.1: ownership takes precedence over chosen order or unpaid preference."""
    s = _pay_state()
    s.lords["march"].location = "ely"
    s.lords["york"].assets["coin"] = 0
    s.locales["ely"].depletion = "exhausted"
    result = actions.apply_action(s, {"type": "pay", "side": "yorkist",
                                     "unpay_lords": ["march"]})
    assert result["troops"]["unpaid_disbanded"] == ["york"]
    assert s.lords["march"].status == "mustered"


def test_pillage_does_not_charge_lords_already_paid():
    """Rules 3.2.1: only Unpaid Lords pay again following Pillage."""
    s = _pay_state()
    for lid in ("york", "march"):
        s.lords[lid].location = "london"
    s.lords["march"].assets["coin"] = 0
    s.locales["london"].depletion = None
    result = actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    coin = static_data.stronghold_yields("london")["pillage"]["coin"]
    assert result["troops"]["unpaid_disbanded"] == []
    assert s.lords["march"].assets["coin"] == coin - 1
    assert s.lords["york"].assets["coin"] == 0


def _supply_depot():
    s = build_initial_state("warwicks_rebellion", seed=1)
    lids = ["warwick_lancastrian", "clarence"]
    for lid in lids:
        s.lords[lid].location = "calais"
    s.decks["lancastrian"]["draw"].remove("L28")
    s.decks["lancastrian"]["held"].append("L28")
    s.hold_window = {"side": "lancastrian", "action": "sail", "lords": lids}
    return s, lids


def test_rebel_supply_depot_distributes_four_total_and_exempts_all_selected_movers():
    """L28 Tips: four total Provender distributed as desired; movers skip next Feed."""
    s, lids = _supply_depot()
    before = {lid: s.lords[lid].assets.get("provender", 0) for lid in lids}
    shares = {lids[0]: 1, lids[1]: 3}
    result = actions.apply_action(s, {"type": "play_held_event", "side": "lancastrian",
                                     "card": "L28", "decisions": {
                                         "lords": lids, "provender": shares}})
    assert result["provender_added"] == shares
    for lid in lids:
        assert s.lords[lid].assets["provender"] == before[lid] + shares[lid]
        assert s.lords[lid].ignore_next_feed


@pytest.mark.parametrize("decisions", [
    {"lords": ["clarence", "clarence"]},
    {"lords": ["warwick_lancastrian", "clarence"]},
    {"lords": ["warwick_lancastrian", "clarence"], "provender": {"clarence": 8}},
    {"lords": ["clarence"], "provender": {"edward_iv": 4}},
    {"lords": ["warwick_lancastrian", "clarence"],
     "provender": {"warwick_lancastrian": -1, "clarence": 5}},
])
def test_supply_depot_rejects_invalid_movers_or_distribution_before_grant(decisions):
    """L28 Tips: distinct qualifying movers share exactly four Provender."""
    s, lids = _supply_depot()
    before = {lid: s.lords[lid].assets.copy() for lid in lids}
    with pytest.raises(IllegalAction):
        actions.apply_action(s, {"type": "play_held_event", "side": "lancastrian",
                                 "card": "L28", "decisions": decisions})
    assert {lid: s.lords[lid].assets for lid in lids} == before
    assert not any(s.lords[lid].ignore_next_feed for lid in lids)
    assert "L28" in s.decks["lancastrian"]["held"]


def test_first_levy_hastings_deploys_special_vassal_and_troops():
    """Rules 3.1.2, 1.5.4 and Y24 Hastings: first-draw deployment has full effects."""
    s = build_initial_state("warwicks_rebellion", seed=1)
    actions.apply_action(s, {"type": "draw", "side": "lancastrian"})
    deck = s.decks["yorkist"]["draw"]
    deck.remove("Y24")
    deck.insert(0, "Y24")
    before = s.lords["edward_iv"].forces.get("men_at_arms", 0)
    actions.apply_action(s, {"type": "draw", "side": "yorkist"})
    ed = s.lords["edward_iv"]
    assert "Y24" in ed.capabilities
    assert ed.special_vassals == ["hastings"]
    assert ed.forces["men_at_arms"] == before + 2
