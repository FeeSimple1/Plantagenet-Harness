"""Levy Pay step (3.2): Pay Troops, Pay Lords, Pay Vassals."""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus, VassalStatus
from tests._helpers import to_muster


def _advance_to_turn2_pay(s):
    """Run a no-op Turn 1 (Levy + empty Campaign) to roll over to Turn 2 Pay."""
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    n = s.campaign.cards_required
    plan = [{"pass": True}] * n
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": plan})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": plan})
    while s.campaign.step == "activation":
        actions.apply_action(s, {"type": "end_activation", "side": s.active_side})
    actions.apply_action(s, {"type": "end_campaign"})
    to_muster(s)                       # Turn 2 begins with the Arts of War draw -> Pay
    assert s.levy_step == "pay" and s.turn_box == 2


def test_pay_is_skipped_on_first_turn():
    # Loader starts a scenario at the Muster step (Pay skipped on Turn 1, 3.2).
    s = build_initial_state("henry_vi")
    to_muster(s)                       # first Turn: Arts of War draw -> Muster (Pay skipped)
    assert s.levy_step == "muster"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert e.value.code == "wrong_step"


def test_pay_troops_one_coin_per_six():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    york = s.lords["york"]
    york.assets["coin"] = 5
    york.forces = {"retinue": 1, "men_at_arms": 6, "longbow": 6}   # 12 Troops -> 2 Coin
    actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert york.assets["coin"] == 3      # 5 - 2


def test_pay_order_is_rebel_then_king():
    s = build_initial_state("henry_vi")   # Yorkist Rebel
    _advance_to_turn2_pay(s)
    assert s.active_side == "yorkist"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "pay", "side": "lancastrian"})
    assert e.value.code == "not_active_side"
    r = actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert r["next"] == "king_pay" and s.active_side == "lancastrian"
    r2 = actions.apply_action(s, {"type": "pay", "side": "lancastrian"})
    assert r2["next"] == "muster" and s.levy_step == "muster"


def test_pay_lords_influence_cost():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    # York and March are Mustered at Strongholds -> 1 Influence each = 2 total.
    for lord in s.lords.values():
        if lord.side == "yorkist" and lord.status == LordStatus.MUSTERED:
            lord.assets["coin"] = 9   # ensure Troop Pay never disbands them
    r = actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert r["lords"]["influence_paid"] == 2


def test_unpaid_lord_at_exhausted_locale_disbands_with_penalty():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    york = s.lords["york"]
    york.forces = {"retinue": 1, "men_at_arms": 6}   # needs 1 Coin
    york.assets["coin"] = 0
    s.locales["ely"].depletion = "exhausted"          # cannot Pillage to recover
    actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert york.status == LordStatus.CALENDAR         # Unpaid -> Disbanded (3.2.4)


def test_unpaid_lord_pillages_unexhausted_stronghold():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    york = s.lords["york"]
    york.forces = {"retinue": 1, "men_at_arms": 6}   # needs 1 Coin
    york.assets["coin"] = 0
    s.locales["ely"].depletion = None                 # Ely (City) Pillage gives 2 Coin
    r = actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert "ely" in r["troops"]["pillaged"]
    assert york.status == LordStatus.MUSTERED          # Pillage funded the Pay
    assert s.locales["ely"].depletion == "exhausted"


def test_voluntary_disband_in_pay_lords():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    for lord in s.lords.values():
        if lord.side == "yorkist" and lord.status == LordStatus.MUSTERED:
            lord.assets["coin"] = 9
    actions.apply_action(s, {"type": "pay", "side": "yorkist", "disband_lords": ["march"]})
    assert s.lords["march"].status == LordStatus.CALENDAR


def test_pay_vassals_due_in_current_box_paid_shifts_or_disbands():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    # Attach a Vassal to York with a service marker due this Turn (box 2).
    york = s.lords["york"]
    york.assets["coin"] = 9
    york.vassals = ["suffolk"]
    s.vassals["suffolk"].status = VassalStatus.MUSTERED
    s.vassals["suffolk"].on_lord = "york"
    s.vassals["suffolk"].service_box = 2
    actions.apply_action(s, {"type": "pay", "side": "yorkist"})
    assert s.vassals["suffolk"].status == VassalStatus.MUSTERED
    assert s.vassals["suffolk"].service_box == 3      # paid -> shifted one box right


def test_unpaid_vassal_disbands():
    s = build_initial_state("henry_vi")
    _advance_to_turn2_pay(s)
    york = s.lords["york"]
    york.assets["coin"] = 9
    york.vassals = ["suffolk"]
    s.vassals["suffolk"].status = VassalStatus.MUSTERED
    s.vassals["suffolk"].on_lord = "york"
    s.vassals["suffolk"].service_box = 2
    actions.apply_action(s, {"type": "pay", "side": "yorkist", "unpay_vassals": ["suffolk"]})
    assert s.vassals["suffolk"].status == VassalStatus.DISBANDED


def test_ready_vassals_returns_disbanded_to_seat():
    s = build_initial_state("henry_vi")
    # A Disbanded Vassal due to return at Turn 2.
    s.vassals["fauconberg"].status = VassalStatus.DISBANDED
    s.vassals["fauconberg"].service_box = 2
    s.turn_box = 2
    returned = campaign.ready_vassals(s)
    assert "fauconberg" in returned
    assert s.vassals["fauconberg"].status == VassalStatus.AT_SEAT
    assert s.vassals["fauconberg"].location == "dover"   # Fauconberg's Seat
