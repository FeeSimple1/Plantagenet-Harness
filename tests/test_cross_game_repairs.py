"""Cross-game P1–P4: ordered Feed, full Pillage cost, Vassals and Warden."""
from __future__ import annotations

import pytest

from plantagenet import actions, battle, campaign, pay, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import CampaignState, LordStatus


def feed_state(*, troops=6, food=0, ally=False, exhausted=True):
    state = build_initial_state("henry_vi", seed=1)
    state.phase = "campaign"
    state.active_side = "yorkist"
    state.pending = []
    state.campaign = CampaignState(step="activation", cards_required=1,
        plans={"yorkist": [{"lord": "york"}], "lancastrian": [{"pass": True}]},
        plan_built={"yorkist": True, "lancastrian": True},
        plan_index={"yorkist": 0, "lancastrian": 1},
        active_lord="york", actions_remaining=0)
    york = state.lords["york"]
    york.forces = {"retinue": 1, "militia": troops}
    york.assets = {"provender": food}
    york.moved_fought = True
    state.locales["ely"].depletion = "exhausted" if exhausted else None
    if ally:
        salisbury = state.lords["salisbury"]
        salisbury.status = LordStatus.MUSTERED
        salisbury.location = "ely"
        salisbury.forces = {"retinue": 1, "militia": 6}
        salisbury.assets = {"provender": 1}
        salisbury.moved_fought = True
    return state


def end_feed(state, **choices):
    return actions.apply_action(state, {"type": "end_activation", "side": "yorkist",
                                        **choices})["feed"]["yorkist"]


def net(state):
    track = state.influence["track"]
    return track.marker_at if track.marker_side == "lancastrian" else -track.marker_at


def test_all_lords_feed_own_troops_before_any_sharing():
    state = feed_state(ally=True)
    result = end_feed(state)
    assert result["disbanded"] == ["york"]
    assert result["fed"] == [{"lord": "salisbury", "fed": 1, "needed": 1}]
    assert state.lords["salisbury"].status == "mustered"
    assert state.lords["salisbury"].assets["provender"] == 0
    assert not any(state.lords[lid].moved_fought for lid in ("york", "salisbury"))


def test_sharing_still_uses_food_of_lords_who_do_not_owe_feed():
    state = feed_state(ally=True)
    state.lords["salisbury"].moved_fought = False
    assert end_feed(state)["disbanded"] == []
    assert state.lords["york"].status == "mustered"
    assert state.lords["salisbury"].assets["provender"] == 0


@pytest.mark.parametrize("troops,food,survives", [(13, 1, False), (7, 1, True), (13, 3, True)])
def test_partial_food_is_spent_before_full_requirement_after_pillage(troops, food, survives):
    state = feed_state(troops=troops, food=food, exhausted=False)
    result = end_feed(state)
    assert (state.lords["york"].status == "mustered") is survives
    assert ("york" not in result["disbanded"]) is survives
    if food == 3:
        assert state.locales["ely"].depletion is None  # Enough initial food; no Pillage.
    else:
        assert state.locales["ely"].depletion == "exhausted"
    if survives:
        assert state.lords["york"].assets.get("provender", 0) == 0


def test_owner_selects_pillager_when_several_lords_are_unfed():
    state = feed_state(ally=True, exhausted=False)
    state.lords["salisbury"].assets = {}
    result = end_feed(state, pillage_by={"ely": "salisbury"})
    assert result["disbanded"] == []
    assert state.lords["salisbury"].assets["coin"] == 2
    assert state.lords["york"].assets.get("coin", 0) == 0


@pytest.mark.parametrize("first", ["york", "salisbury"])
def test_owner_controls_scarce_surplus_after_own_food_reserved(first):
    state = feed_state(ally=True)
    state.lords["salisbury"].assets = {}
    donor = state.lords["march"]
    donor.location = "ely"
    donor.assets = {"provender": 1}
    other = "salisbury" if first == "york" else "york"
    result = end_feed(state, feed_order={"yorkist": [first, other]})
    assert result["disbanded"] == [other]
    assert state.lords[first].status == "mustered"


@pytest.mark.parametrize("choices,code", [
    ({"feed_order": {"yorkist": ["york", "york"]}}, "bad_feed_order"),
    ({"feed_order": {"yorkist": ["henry_vi"]}}, "bad_feed_order"),
    ({"feed_order": []}, "bad_feed_order"),
    ({"pillage_by": {"ely": "march"}}, "bad_pillager"),
])
def test_invalid_feed_choices_leave_public_state_unchanged(choices, code):
    state = feed_state(exhausted=False)
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as exc:
        end_feed(state, **choices)
    assert exc.value.code == code
    assert state.model_dump_json() == before


def special_state():
    state = build_initial_state("warwicks_rebellion", seed=1)
    lord = state.lords["edward_iv"]
    lord.forces = {"retinue": 1, "militia": 1}
    lord.assets = {}
    lord.vassals = []
    lord.special_vassals = ["hastings"]
    lord.capabilities = ["Y24"]
    state.locales[lord.location].depletion = "exhausted"
    return state, lord


@pytest.mark.parametrize("cause", ["unfed", "unpaid", "shipwreck"])
@pytest.mark.parametrize("regular", [False, True])
def test_penalties_count_special_and_regular_vassals(cause, regular):
    state, lord = special_state()
    if regular:
        lord.vassals = ["suffolk"]
        state.vassals["suffolk"].on_lord = lord.lord_id
    expected = static_data.load_lords()[lord.lord_id]["ratings"]["influence"] + 1 + regular
    before = net(state)
    if cause == "unfed":
        lord.moved_fought = True
        campaign._feed(state, "yorkist")
    elif cause == "unpaid":
        pay._pay_troops(state, "yorkist", {})
    else:
        lord.location = None
        lord.at_sea = "north_sea"
        result = campaign._disembark(state, {})
        assert result["rolls"][0]["shipwreck"] is True
        assert result["rolls"][0]["influence_lost"] == expected
    assert net(state) - before == expected
    assert lord.special_vassals == [] and lord.vassals == []


def test_warden_keeps_only_unrouted_troops_after_seeded_battle():
    state = build_initial_state("henry_vi", seed=1)
    for lid in ("york", "somerset_1"):
        lord = state.lords[lid]
        lord.location = "newcastle"
        lord.capabilities = []
        lord.vassals = []
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 3, "longbow": 3}
    state.lords["somerset_1"].forces = {
        "retinue": 1, "men_at_arms": 3, "longbow": 3, "militia": 3}
    state.locales["carlisle"].favour = "lancastrian"
    state.decks["lancastrian"]["held"] = ["L16"]
    result = battle.resolve_battle(state, "newcastle", "york", "somerset_1",
        {"warden": True, "valour": False,
         "absorb_plan": {"defender": [{"unit": "retinue"}] * 6}})
    routed = {}
    for rnd in result["rounds"]:
        for engagement in rnd["engagements"]:
            for strike in engagement["strikes"]:
                for roll in strike["defender_rolls"]:
                    if roll["lord"] == "somerset_1" and not roll["saved"]:
                        routed[roll["unit"]] = routed.get(roll["unit"], 0) + 1
    assert routed == {"retinue": 1, "militia": 3, "longbow": 3, "men_at_arms": 2}
    escaped = state.lords["somerset_1"]
    assert escaped.location == "carlisle" and escaped.status == "mustered"
    assert escaped.forces == {"retinue": 1, "men_at_arms": 1}
    assert "L16" in state.decks["lancastrian"]["discard"]


def test_feed_parameters_are_discoverable_and_player_cannot_override_opponent():
    from tests.test_llm_interface import nv, quiet
    state = feed_state(exhausted=False)
    quiet(nv.attach, state, perspective="yorkist")
    contract, _ = quiet(nv.describe, "end_activation")
    assert {"feed_order", "pillage_by"} <= contract["optional"].keys()
    stamp = nv.version()
    before = state.model_dump_json()
    for choices in ({"feed_order": {"lancastrian": ["henry_vi"]}},
                    {"pillage_by": {"ely": "henry_vi"}}):
        with pytest.raises(PermissionError):
            quiet(nv.apply, {"type": "end_activation", "side": "yorkist", **choices},
                  expected_version=stamp)
        assert state.model_dump_json() == before
