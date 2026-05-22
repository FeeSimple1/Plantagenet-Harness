"""Influence/favour & active-event card effects: Rising Wages, New Act, Suspicion."""

from __future__ import annotations

import pytest

from plantagenet import actions, battle
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def test_rising_wages_charges_yorkist_one_coin_per_levy_troops():
    s = build_initial_state("henry_vi")
    to_muster(s)
    s.active_events = [{"card": "L9", "side": "lancastrian", "scope": "this_levy"}]
    york = s.lords["york"]
    york.assets["coin"] = 2
    actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert york.assets["coin"] == 1                     # paid 1 Coin (L9)
    york.assets["coin"] = 0
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert e.value.code == "rising_wages_no_coin"


def _campaign():
    s = build_initial_state("henry_vi")
    to_muster(s)
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


def test_new_act_of_parliament_makes_yorkist_parley_whole_card():
    s = _campaign()
    lid = s.campaign.active_lord                        # a Yorkist Lord (Rebel acts first)
    s.active_events = [{"card": "L10", "side": "lancastrian", "scope": "this_campaign"}]
    # Parley at the Lord's own (Friendly) location auto-succeeds and uses the whole card.
    s.lords[lid].location = "lynn"                       # Neutral, so Parley has an effect
    actions.apply_action(s, {"type": "parley", "side": "yorkist", "by_lord": lid, "target": "lynn"})
    assert s.campaign.actions_remaining == 0             # L10: whole Command card


def test_suspicion_disbands_lower_influence_enemy_on_success():
    success = False
    for seed in range(1, 12):
        s = build_initial_state("henry_vi", seed=seed)
        for lid in ("york", "exeter_1"):                # York Influence 5 > Exeter (1) 2
            s.lords[lid].location = "cambridge"
            s.lords[lid].capabilities = []
        s.lords["exeter_1"].status = LordStatus.MUSTERED
        s.lords["exeter_1"].forces = {"retinue": 1, "men_at_arms": 2}
        s.decks["yorkist"]["held"] = ["Y5"]
        r = battle.resolve_battle(s, "cambridge", "york", "exeter_1",
                                  {"suspicion": {"by": "york", "target": "exeter_1"}})
        assert r["suspicion"]["by"] == "york"
        if r["suspicion"]["success"]:
            success = True
            assert s.lords["exeter_1"].status == LordStatus.CALENDAR
            assert "exeter_1" not in r["defenders"]      # removed from the Battle
            break
    assert success                                       # at least one seed succeeded


def test_suspicion_requires_higher_printed_influence():
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):                     # both Influence 5 -> not higher
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
    s.decks["yorkist"]["held"] = ["Y5"]
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                              {"suspicion": {"by": "york", "target": "henry_vi"}})
    assert e.value.code == "suspicion_influence"
