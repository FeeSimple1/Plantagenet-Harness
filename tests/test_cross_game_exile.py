"""P2-1/P2-4: Exile reentry and owner allocation of Approach Spoils."""
from __future__ import annotations

import pytest

from plantagenet import actions, battle, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus
from tests.test_cross_game_sail import place, position


def pay_position(lid="henry_tudor", *, exile=True):
    state = build_initial_state("my_kingdom_for_a_horse", seed=1)
    side = state.lords[lid].side
    state.phase = "levy"
    state.levy_step = "pay"
    state.turn_box = 4
    state.active_side = side
    state.pending = []
    state.pending_events = []
    for other in state.lords.values():
        if other.side == side and other.lord_id != lid:
            other.status = LordStatus.CALENDAR
            other.location = other.exile_box = None
            other.calendar_box = 9
    lord = state.lords[lid]
    lord.status = LordStatus.MUSTERED
    lord.calendar_box = None
    lord.location = None if exile else "lynn"
    lord.exile_box = ("france" if side == "lancastrian" else "burgundy") if exile else None
    lord.forces = {"retinue": 1, "men_at_arms": 1}
    lord.assets = {}
    lord.vassals = []
    lord.special_vassals = []
    lord.capabilities = []
    if not exile:
        state.locales["lynn"].depletion = "exhausted"
    return state, lord


def net(state):
    track = state.influence["track"]
    return track.marker_at if track.marker_side == "lancastrian" else -track.marker_at


@pytest.mark.parametrize("lid", ["henry_tudor", "richard_iii"])
def test_unpaid_exile_keeps_marker_penalty_and_future_muster(lid):
    state, lord = pay_position(lid)
    side = lord.side
    before = net(state)
    rating = static_data.load_lords()[lid]["ratings"]["influence"]
    result = actions.apply_action(state, {"type": "pay", "side": side})
    assert result["troops"]["unpaid_disbanded"] == [lid]
    assert lord.status == LordStatus.CALENDAR and lord.calendar_exile is True
    assert lord.calendar_box == 4 + 6 - rating
    assert not lord.forces and not lord.assets and lord.exile_box is None
    assert net(state) - before == (rating if side == "yorkist" else -rating)
    state = GameState.model_validate_json(state.model_dump_json())
    state.turn_box = state.lords[lid].calendar_box
    state.levy_step = "muster"
    state.active_side = side
    assert any(m["type"] == "muster_exiles" and lid in m["lords"]
               for m in legal_moves.legal_moves(state))
    result = actions.apply_action(state, {"type": "muster_exiles", "side": side, "lords": [lid]})
    assert result["mustered"]
    assert state.lords[lid].exile_box == ("france" if side == "lancastrian" else "burgundy")
    assert state.lords[lid].calendar_exile is False


def test_unpaid_disband_at_a_stronghold_does_not_gain_an_exile_marker():
    state, lord = pay_position(exile=False)
    actions.apply_action(state, {"type": "pay", "side": lord.side})
    assert lord.status == LordStatus.CALENDAR and lord.calendar_exile is False


def test_enough_coin_in_exile_avoids_disband_and_pays_the_normal_lord_cost():
    state, lord = pay_position()
    lord.assets = {"coin": 1}
    result = actions.apply_action(state, {"type": "pay", "side": lord.side})
    assert result["troops"]["unpaid_disbanded"] == []
    assert result["lords"]["influence_paid"] == 2
    assert lord.status == LordStatus.MUSTERED and lord.exile_box == "france"


def approach_position(side="yorkist", favour="friendly", *, multiple=False, mixed=False):
    leader, ally, defender = (("york", "salisbury", "henry_vi") if side == "yorkist"
                              else ("henry_vi", "somerset_1", "york"))
    state = position(leader)
    state.lords[leader].location = "ely"
    state.lords[leader].assets = {}
    place(state, ally, "ely").assets = {}
    target = state.lords[defender]
    target.location = "cambridge"
    target.assets = {"cart": 2, "provender": 2, "coin": 3, "ship": 1}
    foe = "lancastrian" if side == "yorkist" else "yorkist"
    state.locales["cambridge"].favour = side if favour == "friendly" else (
        foe if favour == "enemy" else "neutral")
    responses = {defender: "exile"}
    if multiple:
        extra = place(state, "buckingham", "cambridge")
        extra.assets = {"cart": 1, "provender": 1}
        responses["buckingham"] = "exile"
    if mixed:
        fighter = place(state, "somerset_1", "cambridge")
        fighter.assets = {"cart": 4, "provender": 4}
        responses["somerset_1"] = "battle"
    return state, leader, ally, defender, responses


def march(case, **decisions):
    state, leader, ally, _, responses = case
    return actions.apply_action(state, {"type": "march", "side": state.lords[leader].side,
                                        "by_lord": leader, "to": "cambridge", "group": [ally],
                                        "decisions": {"responses": responses, **decisions}})


@pytest.mark.parametrize("side", ["yorkist", "lancastrian"])
@pytest.mark.parametrize("key", ["spoils_to", "exile_spoils_to"])
def test_no_battle_exile_honors_either_allocation_key_for_both_sides(side, key):
    case = approach_position(side)
    state, leader, ally, defender, _ = case
    result = march(case, **{key: {ally: {"cart": 2, "provender": 2}}})
    assert not any(state.lords[leader].assets.values())
    assert state.lords[ally].assets == {"cart": 2, "provender": 2}
    assert state.lords[defender].calendar_exile is True
    assert state.lords[defender].assets == {}
    assert result["approach"]["battle"] is None
    assert result["approach"]["exile_spoils_allocation"] == {ally: {"cart": 2, "provender": 2}}


def test_owner_can_split_each_asset_differently_among_approachers():
    case = approach_position()
    state, leader, ally, _, _ = case
    result = march(case, spoils_to={leader: {"cart": 2}, ally: {"provender": 2}})
    assert state.lords[leader].assets.get("cart", 0) == 2
    assert state.lords[leader].assets.get("provender", 0) == 0
    assert state.lords[ally].assets == {"provender": 2}
    assert result["approach"]["exile_spoils"] == {"cart": 2, "provender": 2}


@pytest.mark.parametrize("favour,taken", [("friendly", 2), ("neutral", 2), ("enemy", 0)])
def test_multiple_exiles_round_each_lords_neutral_spoils_separately(favour, taken):
    case = approach_position(favour=favour, multiple=True)
    state, _, ally, defender, _ = case
    state.lords[defender].assets = {"cart": 1, "provender": 1}
    result = march(case, spoils_to={ally: {"cart": taken, "provender": taken}})
    assert result["approach"]["exile_spoils"] == {"cart": taken, "provender": taken}
    assert state.lords[ally].assets.get("cart", 0) == taken
    assert state.lords[ally].assets.get("provender", 0) == taken


def test_mixed_exile_and_battle_have_independent_spoils_allocations(monkeypatch):
    case = approach_position(mixed=True)
    state, leader, ally, defender, _ = case
    original = battle.resolve_battle
    seen = []

    def observe(*args, **kwargs):
        seen.append((dict(state.lords[ally].assets), state.lords[defender].calendar_exile))
        return original(*args, **kwargs)

    monkeypatch.setattr(battle, "resolve_battle", observe)
    result = march(case, exile_spoils_to={ally: {"cart": 2, "provender": 2}},
                   spoils_to={leader: {"cart": 4, "provender": 4}}, flee=["somerset_1"])
    assert seen == [({"cart": 2, "provender": 2}, True)]
    assert result["approach"]["battle"]["spoils"] == {"cart": 4, "provender": 4}
    assert state.lords[leader].assets == {"cart": 4, "provender": 4}
    assert state.lords[ally].assets == {"cart": 2, "provender": 2}


def test_mixed_case_preserves_existing_battle_key_and_default_exile_recipient():
    case = approach_position(mixed=True)
    state, leader, ally, _, _ = case
    march(case, spoils_to={ally: {"cart": 4, "provender": 4}}, flee=["somerset_1"])
    assert state.lords[leader].assets == {"cart": 2, "provender": 2}
    assert state.lords[ally].assets == {"cart": 4, "provender": 4}


def test_default_exile_distribution_still_uses_the_first_approaching_lord():
    case = approach_position()
    state, leader, ally, _, _ = case
    march(case)
    assert state.lords[leader].assets == {"cart": 2, "provender": 2}
    assert state.lords[ally].assets == {}


def test_england_is_my_home_still_gives_neither_exile_marker_nor_spoils():
    case = approach_position("lancastrian")
    state, leader, ally, defender, _ = case
    state.lords[defender].capabilities = ["Y8"]
    before = net(state)
    result = march(case)
    assert state.lords[defender].status == LordStatus.CALENDAR
    assert state.lords[defender].calendar_box == state.turn_box + 1
    assert state.lords[defender].calendar_exile is False
    assert result["approach"]["exile_spoils"] == {"cart": 0, "provender": 0}
    assert not any(state.lords[leader].assets.values())
    assert not any(state.lords[ally].assets.values())
    assert net(state) == before


@pytest.mark.parametrize("split", [
    {"henry_vi": {"cart": 2, "provender": 2}},
    {"march": {"cart": 2, "provender": 2}},
    {"salisbury": {"cart": 1, "provender": 2}},
    {"salisbury": {"cart": 3, "provender": 2}},
    {"york": {"cart": -1}, "salisbury": {"cart": 3, "provender": 2}},
    {"salisbury": {"cart": 2.0, "provender": 2}},
    {"salisbury": {"cart": True, "provender": 2}},
    {"salisbury": {"cart": 2, "provender": 2, "coin": 0}},
    {"salisbury": []}, ["salisbury"],
])
def test_invalid_exile_splits_reject_without_movement_influence_history_or_rng_changes(split):
    case = approach_position()
    state = case[0]
    before = state.model_dump_json()
    with pytest.raises(IllegalAction):
        march(case, spoils_to=split)
    assert state.model_dump_json() == before


def test_high_admiral_sail_approach_honors_exile_allocation():
    state = position("exeter_1")
    state.lords["exeter_1"].capabilities = ["L29"]
    state.lords["york"].location = "newcastle"
    state.lords["york"].assets = {"cart": 1, "provender": 1}
    state.locales["newcastle"].favour = "lancastrian"
    result = actions.apply_action(state, {
        "type": "sail", "side": "lancastrian", "by_lord": "exeter_1", "to": "newcastle",
        "decisions": {"responses": {"york": "exile"},
                      "exile_spoils_to": {"exeter_1": {"cart": 1, "provender": 1}}}})
    assert result["approach"]["exile_spoils_allocation"] == {
        "exeter_1": {"cart": 1, "provender": 1}}


def test_battle_uses_the_same_nonnegative_allocation_validation_and_full_rollback():
    case = approach_position(mixed=True)
    state = case[0]
    before = state.model_dump_json()
    with pytest.raises(IllegalAction, match="nonnegative"):
        march(case, flee=["somerset_1"], spoils_to={
            "york": {"cart": -1}, "salisbury": {"cart": 5, "provender": 4}})
    assert state.model_dump_json() == before
