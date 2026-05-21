"""Campaign phase: Plan, Activation, Forage, Feed, End Campaign (4.x)."""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster


def _finish_levy(s):
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})


def _pad(lords, n):
    e = [{"lord": x} for x in lords][:n]
    while len(e) < n:
        e.append({"pass": True})
    return e


def test_season_card_counts():
    # 4.1: 4/6/7/6/4 by season; boxes cycle every 5.
    assert [campaign.season_info(b)["cards"] for b in (1, 2, 3, 4, 5)] == [4, 6, 7, 6, 4]
    assert campaign.season_info(7)["cards"] == 6        # Apr-May 1464 (Ic)
    assert campaign.season_info(3)["cards"] == 7        # Jun-Jul (III)


def test_season_flags():
    assert campaign.season_info(1)["gain_lords_influence"] is True   # Jan-Feb-Mar
    assert campaign.season_info(4)["grow"] is True                   # Aug-Sep Grow
    assert campaign.season_info(5)["waste"] is True                  # Oct-Nov-Dec Waste
    assert campaign.season_info(15)["waste"] is False                # last Turn, no Waste


def test_begin_requires_levy_done():
    s = build_initial_state("towton")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "begin_campaign"})
    assert e.value.code == "levy_not_done"


def test_plan_must_match_season_size():
    s = build_initial_state("towton")
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})  # box 1 -> 4 cards
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "build_plan", "side": "yorkist",
                                 "plan": [{"pass": True}]})
    assert e.value.code == "wrong_plan_size"


def test_plan_max_three_activations_per_lord():
    s = build_initial_state("towton")
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})
    bad = [{"lord": "march"}] * 4   # 4 > 3 Command cards
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": bad})
    assert e.value.code == "too_many_activations"


def test_activation_alternates_rebel_then_king():
    s = build_initial_state("towton")  # Yorkist Rebel, Lancastrian King
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian"]
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": _pad(yk, 4)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": _pad(lc, 4)})
    assert s.campaign.step == "activation"
    assert s.active_side == "yorkist"            # Rebel reveals first (4.2)
    actions.apply_action(s, {"type": "end_activation", "side": "yorkist"})
    assert s.active_side == "lancastrian"        # then King


def test_forage_friendly_auto_success_and_depletes():
    s = build_initial_state("towton")
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian"]
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": _pad(yk, 4)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": _pad(lc, 4)})
    lord_id = s.campaign.active_lord            # a Yorkist Lord at London (Friendly)
    prov = s.lords[lord_id].assets.get("provender", 0)
    r = actions.apply_action(s, {"type": "forage", "side": "yorkist", "by_lord": lord_id})
    assert r["success"] is True and r["roll"] is None    # Friendly + no enemy adj = automatic
    assert s.lords[lord_id].assets["provender"] == prov + 1
    assert s.locales[s.lords[lord_id].location].depletion == "depleted"


def test_command_actions_limited_by_command_rating():
    s = build_initial_state("towton")
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian"]
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": _pad(yk, 4)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": _pad(lc, 4)})
    lid = s.campaign.active_lord
    rating = campaign._command_rating(lid)
    for _ in range(rating):
        actions.apply_action(s, {"type": "pass", "side": "yorkist", "by_lord": lid})
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "pass", "side": "yorkist", "by_lord": lid})
    assert e.value.code == "no_actions_left"


def _run_campaign(s):
    """Build minimal Plans and run all Activations to the End step."""
    yk = [x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian" and v.status == "mustered"]
    n = s.campaign.cards_required
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": _pad(yk, n)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": _pad(lc, n)})
    while s.campaign.step == "activation":
        actions.apply_action(s, {"type": "end_activation", "side": s.active_side})


def test_scenario_end_victory_on_final_turn():
    # Towton is a one-Turn scenario: End Campaign resolves a 5.3 victory.
    s = build_initial_state("towton")
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})
    _run_campaign(s)
    r = actions.apply_action(s, {"type": "end_campaign"})
    assert r["victory"] is not None and r["victory"]["rule"] == "5.3"
    assert s.phase == "over"


def test_end_campaign_advances_turn_on_multi_turn_scenario():
    s = build_initial_state("henry_vi")  # 15 Turns
    _finish_levy(s)
    actions.apply_action(s, {"type": "begin_campaign"})
    _run_campaign(s)
    r = actions.apply_action(s, {"type": "end_campaign"})
    assert r["victory"] is None
    assert s.turn_box == 2
    # A rolled-over Turn begins at the Arts of War draw (3.1), Rebel first.
    assert s.phase == "levy" and s.levy_step == "arts_of_war"
    assert s.active_side == "yorkist"


def test_tides_of_war_awards_gain_lords_influence_in_jan_feb_mar():
    s = build_initial_state("towton", seed=1)
    tow = campaign.tides_of_war(s)
    # Box 1 is a Gain-Lords-Influence Turn: detail includes a Lords' Influence award.
    assert any("Lords' Influence" in d for d in tow["detail"])
    assert tow["points"]["lancastrian"] > 0 and tow["points"]["yorkist"] > 0


def test_waste_halves_transport_and_resets_coin():
    s = build_initial_state("henry_vi")
    york = s.lords["york"]
    york.assets["cart"] = 5
    york.assets["coin"] = 9
    york.forces["militia"] = 10
    campaign._waste(s)
    assert york.assets["cart"] == 3                       # 5 -> ceil(2.5)=3
    assert york.assets["coin"] == 2                       # reset to setup (York start 2 Coin)
    assert york.forces["militia"] == 2                    # reset to setup (York start 2 Militia)


def test_grow_recovers_depletion():
    s = build_initial_state("henry_vi")
    s.locales["ely"].depletion = "exhausted"
    s.locales["lynn"].depletion = "depleted"
    campaign._grow(s)
    assert s.locales["ely"].depletion == "depleted"       # exhausted -> depleted
    assert s.locales["lynn"].depletion is None            # depleted -> recovered
