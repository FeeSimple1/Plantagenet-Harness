"""Sailing into a Sea (4.6.1) and End-Campaign Disembark / Shipwreck (4.8.2)."""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign, invariants
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus
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


def test_disembark_lands_at_default_port_when_choice_omitted():
    # 4.8.2: a Lord that rolls 5-6 and CAN reach a free Port lands -- it must not
    # be Disbanded merely because the consumer omitted the landing-Port choice.
    for seed in range(1, 40):
        s = _at_sea(seed)
        res = campaign._disembark(s, {})            # no landing Port chosen
        roll = res["rolls"][0]
        if roll["roll"] >= 5:
            assert roll.get("landed")               # landed at a default free Port
            assert s.lords["york"].status == LordStatus.MUSTERED
            assert s.lords["york"].location in ("truro", "plymouth", "exeter", "dorchester",
                                                "southampton", "hastings", "dover", "calais")
            assert s.lords["york"].at_sea is None
            return
    raise AssertionError("no land roll found")


def test_disembark_disbands_only_when_no_free_port():
    # All Irish-Sea Ports occupied by Enemy (Lancastrian) Lords -> no free Port,
    # so a Yorkist Lord that rolls 5-6 Disbands (4.8.2).
    for seed in range(1, 40):
        s = _at_sea(seed, sea="irish_sea")
        for lid, port in zip(("somerset_1", "northumberland_lancastrian", "exeter_1"),
                             ("bristol", "pembroke", "harlech"), strict=True):
            s.lords[lid].status = LordStatus.MUSTERED
            s.lords[lid].location = port
        res = campaign._disembark(s, {})            # no free Port to land at
        roll = res["rolls"][0]
        if roll.get("disbanded"):
            assert roll["roll"] >= 5
            assert s.lords["york"].status == LordStatus.CALENDAR
            assert s.lords["york"].at_sea is None
            return
    raise AssertionError("no land-roll-without-port seed found")


def _war_iiy_fleet(seed: int) -> GameState:
    state = build_initial_state("wars_of_the_roses", seed=seed)
    state.phase = "over"
    state.victory = {"result": "yorkist", "rule": "5.2"}
    actions.apply_action(state, {"type": "renew_war"})

    # Stage York and March at a Friendly port for their joint Sail.
    state.levy_step, state.active_side = "muster", "yorkist"
    state.locales["lynn"].favour = "yorkist"
    for lid in ("york", "march"):
        state.lords[lid].location = "lynn"
    for lid in ("york", "york", "march"):
        actions.apply_action(state, {"type": "levy_transport", "side": "yorkist",
                                     "by_lord": lid, "transport": "ship"})
    while state.levy_step == "muster":
        actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side in ("yorkist", "lancastrian"):
        plan = [{"lord": "york"}] if side == "yorkist" else []
        plan += [{"pass": True}] * (state.campaign.cards_required - len(plan))
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
    if state.active_side != "yorkist":
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    actions.apply_action(state, {"type": "sail", "side": "yorkist", "by_lord": "york",
                                 "to": "north_sea", "group": ["march"]})
    while state.campaign.step == "activation":
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    assert not invariants.board_invariant_violations(state)
    return state


@pytest.mark.parametrize("seed,dice", [(2, [1, 2]), (7, [2, 5])])
def test_shipwreck_disembarks_the_living_successor_once(seed, dice):
    state = _war_iiy_fleet(seed)
    restored = GameState.model_validate_json(state.model_dump_json())
    # The owner submits the landing choice while March still holds the mat.
    action = {"type": "end_campaign",
              "decisions": {"disembark_land": {"march": "scarborough"}}}
    result = actions.apply_action(state, action)
    assert actions.apply_action(restored, action) == result
    assert restored.model_dump() == state.model_dump()

    rolls = result["disembark"]["rolls"]
    assert [roll["lord"] for roll in rolls] == ["york", "edward_iv"]
    assert [roll["roll"] for roll in rolls] == dice
    assert rolls[0]["shipwreck"]
    assert state.grand_scenario["replaced_cards"]["march"] == "edward_iv"
    assert state.lords["march"].status == LordStatus.REMOVED
    assert all(lord.at_sea is None for lord in state.lords.values())
    if seed == 2:
        assert rolls[1]["shipwreck"] and rolls[1]["influence_lost"] == 5
        assert state.lords["edward_iv"].status == LordStatus.REMOVED
    else:
        assert rolls[1]["landed"] == "scarborough"
        assert state.lords["edward_iv"].location == "scarborough"
        assert result["disembark"]["feed"]["yorkist"]["fed"][0]["lord"] == "edward_iv"
    assert not invariants.board_invariant_violations(state)


def test_successor_feeds_when_the_mat_landed_before_the_shipwreck():
    state = _war_iiy_fleet(1)
    # Resolve March before York to exercise a replacement after landing.
    state.lords = dict(sorted(state.lords.items()))
    action = {"type": "end_campaign",
              "decisions": {"disembark_land": {"march": "scarborough"}}}
    result = actions.apply_action(state, action)
    rolls = result["disembark"]["rolls"]
    assert [roll["lord"] for roll in rolls] == ["march", "york"]
    assert rolls[0]["landed"] == "scarborough" and rolls[1]["shipwreck"]
    assert state.lords["edward_iv"].location == "scarborough"
    assert [record["lord"] for record in result["disembark"]["feed"]["yorkist"]["fed"]] == [
        "edward_iv"]
    assert not invariants.board_invariant_violations(state)
