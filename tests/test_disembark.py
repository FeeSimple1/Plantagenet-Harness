"""Sailing into a Sea (4.6.1) and End-Campaign Disembark / Shipwreck (4.8.2)."""

from __future__ import annotations

from plantagenet import actions, campaign
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def _campaign_with_sailor(seed=1):
    s = build_initial_state("henry_vi", seed=seed)
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
    lid = lc[0]
    s.active_side = "lancastrian"
    s.campaign.active_lord = lid
    s.campaign.actions_remaining = 2
    lord = s.lords[lid]
    lord.location = "bristol"                       # Irish Sea Port
    s.locales["bristol"].favour = "lancastrian"
    lord.assets["ship"] = 5
    lord.forces = {"retinue": 1}
    return s, lid


def test_sail_into_an_adjacent_sea_leaves_the_lord_at_sea():
    s, lid = _campaign_with_sailor()
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "english_channel"})
    assert r["at_sea"] == "english_channel"
    assert s.lords[lid].at_sea == "english_channel" and s.lords[lid].location is None


def test_sail_from_at_sea_to_a_port():
    s, lid = _campaign_with_sailor()
    s.lords[lid].location = None
    s.lords[lid].at_sea = "english_channel"
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "dover"})
    assert r["to"] == "dover"
    assert s.lords[lid].location == "dover" and s.lords[lid].at_sea is None


def _at_sea(seed, sea="english_channel", lord="york"):
    s = build_initial_state("henry_vi", seed=seed)
    s.lords[lord].at_sea = sea
    s.lords[lord].location = None
    s.lords[lord].status = LordStatus.MUSTERED
    s.lords[lord].forces = {"retinue": 1}
    return s


def test_disembark_shipwreck_removes_lord_with_unpaid_penalty():
    seen = False
    for seed in range(1, 30):
        s = _at_sea(seed)
        res = campaign._disembark(s, {})
        roll = res["rolls"][0]
        if roll.get("shipwreck"):
            seen = True
            assert roll["roll"] <= 4
            assert s.lords["york"].status == LordStatus.REMOVED
            assert s.lords["york"].at_sea is None
            assert roll["influence_lost"] >= 1       # Unpaid penalty (3.2.1)
            break
    assert seen


def test_disembark_land_places_at_chosen_free_port_and_feeds():
    seen = False
    for seed in range(1, 30):
        s = _at_sea(seed)
        res = campaign._disembark(s, {"disembark_land": {"york": "dover"}})
        roll = res["rolls"][0]
        if roll.get("landed"):
            seen = True
            assert roll["roll"] >= 5
            assert s.lords["york"].location == "dover" and s.lords["york"].at_sea is None
            assert s.lords["york"].status == LordStatus.MUSTERED
            assert "lancastrian" in res["feed"] or "yorkist" in res["feed"]   # must Feed
            break
    assert seen


def test_disembark_land_without_a_free_port_disbands():
    for seed in range(1, 40):
        s = _at_sea(seed)
        res = campaign._disembark(s, {})            # no landing Port chosen
        roll = res["rolls"][0]
        if roll.get("disbanded"):
            assert roll["roll"] >= 5
            assert s.lords["york"].status == LordStatus.CALENDAR   # Disbanded to Calendar
            assert s.lords["york"].at_sea is None
            return
    raise AssertionError("no land-roll-without-port seed found")
