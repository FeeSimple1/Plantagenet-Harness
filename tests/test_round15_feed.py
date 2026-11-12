"""End-of-card Feed elections belong to the Lords' owner (P15-01)."""

import pytest

from plantagenet import actions, invariants
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests.test_cross_game_repairs import feed_state
from tests.test_llm_interface import attach, get_id, nv, quiet


def _st_albans_battle():
    state = build_initial_state("wars_of_the_roses", seed=1)
    state.phase, state.victory = "over", {"result": "yorkist", "rule": "5.2"}
    actions.apply_action(state, {"type": "renew_war"})
    while state.levy_step == "arts_of_war":
        actions.apply_action(state, {"type": "draw", "side": state.active_side})
    # Native War IIY mats after earlier Provender expenditure.
    for lid, locale in (("york", "st_albans"), ("march", "st_albans"),
                        ("warwick_lancastrian", "london")):
        state.lords[lid].location = locale
        state.lords[lid].assets["provender"] = 0
    while state.levy_step == "muster":
        actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side, lid in (("lancastrian", "warwick_lancastrian"), ("yorkist", "york")):
        plan = [{"lord": lid}] + [{"pass": True}] * (state.campaign.cards_required - 1)
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
    result = actions.apply_action(state, {
        "type": "march", "side": "lancastrian", "by_lord": "warwick_lancastrian",
        "to": "st_albans", "decisions": {"flee": ["warwick_lancastrian"]},
    })
    assert result["approach"]["battle"]["winner_side"] == "yorkist"
    assert not invariants.board_invariant_violations(state)
    return state


@pytest.mark.parametrize("pillager,disbanded", [("york", "march"), ("march", "york")])
def test_defender_chooses_pillager_after_save_and_load(tmp_path, pillager, disbanded):
    state = _st_albans_battle()
    election = {"pillage_by": {"st_albans": pillager}}
    expected = state.model_copy(deep=True)
    expected_result = actions.apply_action(
        expected, {"type": "end_activation", "side": "lancastrian", **election})

    attach(state, "lancastrian")
    end_id = get_id("end_activation")
    start_plan = state.campaign.plan_index.copy()
    result, _ = quiet(nv.apply, end_id)
    assert result["result"]["type"] == "pending_feed"
    assert result["result"]["awaiting_side"] == "yorkist"
    assert list(result["result"]["feed"]) == ["lancastrian"]
    assert state.campaign.plan_index == start_plan
    assert not nv.all_actions()
    assert state.lords[pillager].moved_fought
    pending = state.model_dump_json()
    for action, code in [
        ({"type": "resolve_feed", "side": "lancastrian"}, "wrong_feed_side"),
        ({"type": "end_activation", "side": "lancastrian"}, "feed_pending"),
    ]:
        with pytest.raises(IllegalAction) as rejected:
            actions.apply_action(state, action)
        assert rejected.value.code == code
        assert state.model_dump_json() == pending

    save = tmp_path / "pending_feed.json"
    quiet(nv.save, save)
    quiet(nv.load, save, perspective="yorkist")
    assert nv._state().model_dump_json() == pending
    with pytest.raises(nv.StaleSelectionError):
        quiet(nv.apply, end_id)
    selection = get_id("resolve_feed")
    contract, _ = quiet(nv.describe, selection)
    assert set(contract["options"]["pillage_candidates"]["st_albans"]) == {"york", "march"}
    version = nv.version()
    wrong, _ = quiet(nv.apply, selection, parameters={
        "pillage_by": {"st_albans": "warwick_lancastrian"}})
    assert wrong["error"]["code"] == "wrong_feed_side"
    assert nv.version() == version and nv._state().model_dump_json() == pending

    final, _ = quiet(nv.apply, selection, parameters=election)
    actual = nv._state()
    assert final["result"] == expected_result
    assert actual.model_dump(exclude={"history"}) == expected.model_dump(exclude={"history"})
    assert actual.lords[disbanded].status == LordStatus.CALENDAR
    assert actual.lords[pillager].status == LordStatus.MUSTERED
    assert actual.campaign.plan_index["lancastrian"] == start_plan["lancastrian"] + 1
    assert not actual.pending and not invariants.board_invariant_violations(actual)


def test_scarce_shared_food_offers_the_owner_a_feed_order():
    state = feed_state(ally=True)
    state.lords["salisbury"].assets = {}
    donor = state.lords["march"]
    donor.location = "ely"
    donor.assets = {"provender": 1}
    attach(state, "active")
    result, _ = quiet(nv.apply, get_id("end_activation"))
    assert result["result"]["awaiting_side"] == "yorkist"
    selection = get_id("resolve_feed")
    contract, _ = quiet(nv.describe, selection)
    assert contract["options"]["sharing"] == [
        {"shortfalls": {"york": 1, "salisbury": 1}, "provender": 1}]
    result, _ = quiet(nv.apply, selection, parameters={
        "feed_order": {"yorkist": ["salisbury", "york"]}})
    assert result["result"]["feed"]["yorkist"]["disbanded"] == ["york"]
    assert state.lords["salisbury"].status == LordStatus.MUSTERED


def test_feed_order_can_choose_a_shared_mat_when_every_lord_can_feed():
    state = feed_state(ally=True)
    state.lords["salisbury"].assets = {"provender": 2}
    march = state.lords["march"]
    march.status = LordStatus.MUSTERED
    march.location = "ely"
    march.forces = {"retinue": 1, "militia": 1}
    march.assets = {"provender": 2}
    march.moved_fought = True
    attach(state, "active")
    result, _ = quiet(nv.apply, get_id("end_activation"))
    assert result["result"]["awaiting_side"] == "yorkist"
    result, _ = quiet(nv.apply, get_id("resolve_feed"), parameters={
        "feed_order": {"yorkist": ["march", "york", "salisbury"]}})
    assert result["result"]["feed"]["yorkist"]["disbanded"] == []
    assert march.assets["provender"] == 0
    assert state.lords["salisbury"].assets["provender"] == 1


def test_rebel_chooses_first_when_ending_the_kings_card():
    state = feed_state(ally=True, exhausted=False)
    state.lords["salisbury"].assets = {}
    assert state.roles == {"yorkist": "rebel", "lancastrian": "king"}
    kings_lords = [lord for lord in state.lords.values()
                   if lord.side == "lancastrian" and lord.status == LordStatus.MUSTERED][:2]
    assert len(kings_lords) == 2
    for lord in kings_lords:
        lord.location = "london"
        lord.exile_box = None
        lord.forces = {"retinue": 1, "militia": 1}
        lord.assets = {}
        lord.moved_fought = True
    state.active_side = "lancastrian"
    state.campaign.active_lord = kings_lords[0].lord_id
    state.campaign.plans["lancastrian"] = [{"lord": kings_lords[0].lord_id}]
    state.campaign.plan_index = {"lancastrian": 0, "yorkist": 1}
    attach(state, "active")
    first, _ = quiet(nv.apply, get_id("end_activation"))
    assert first["result"]["awaiting_side"] == "yorkist" and first["result"]["feed"] == {}
    second, _ = quiet(nv.apply, get_id("resolve_feed"))
    assert second["result"]["awaiting_side"] == "lancastrian"
    assert list(second["result"]["feed"]) == ["yorkist"]
    assert state.campaign.plan_index == {"lancastrian": 0, "yorkist": 1}
    final, _ = quiet(nv.apply, get_id("resolve_feed"))
    assert list(final["result"]["feed"]) == ["yorkist", "lancastrian"]
    assert not state.pending and state.campaign.step == "end"
    assert state.campaign.plan_index == {"lancastrian": 1, "yorkist": 1}


def test_forced_feed_advances_the_card_in_one_action():
    state = feed_state(food=1)
    attach(state, "active")
    result, _ = quiet(nv.apply, get_id("end_activation"))
    assert result["result"]["type"] == "end_activation"
    assert result["result"]["feed"]["yorkist"]["fed"] == [
        {"lord": "york", "fed": 1, "needed": 1}]
    assert not state.pending and state.campaign.plan_index["yorkist"] == 1
