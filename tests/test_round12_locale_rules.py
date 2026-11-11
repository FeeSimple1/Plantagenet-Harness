"""P12-01 and P12-02. Locale identity in group movement and Tides scoring."""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus


def _muster(scenario, side, *, turn=4, seed=1):
    state = build_initial_state(scenario, seed=seed)
    state.turn_box = turn
    state.levy_step = "muster"
    state.active_side = side
    return state


def _act(state, kind, **args):
    return actions.apply_action(state, {"type": kind, **args})


def _muster_exiles(state, *lords):
    for lid in lords:
        lord = state.lords[lid]
        lord.status = LordStatus.CALENDAR
        lord.calendar_box = state.turn_box
        lord.calendar_exile = True
        lord.location = lord.exile_box = lord.at_sea = None
        lord.forces = {}
        lord.assets = {}
    _act(state, "muster_exiles", side=state.active_side, lords=list(lords))


def _end_activation(state):
    _act(state, "end_activation", side=state.active_side)


def _start_campaign(state, side, *lords):
    while state.levy_step == "muster":
        _act(state, "end_muster", side=state.active_side)
    _act(state, "begin_campaign")
    for player in ("yorkist", "lancastrian"):
        plan = [{"lord": lid} for lid in lords] if player == side else []
        plan += [{"pass": True}] * (state.campaign.cards_required - len(plan))
        _act(state, "build_plan", side=player, plan=plan)
    if state.active_side != side:
        _end_activation(state)


def _move_in_menu(state, kind, destination, group):
    moves = legal_moves.validated_legal_moves(state)["moves"]
    return next(move for move in moves if move["type"] == kind
                and move["to"] == destination and move.get("group") == group)


def _reject_unchanged(state, action, code):
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as rejected:
        actions.apply_action(state, action)
    assert rejected.value.code == code
    assert state.model_dump_json() == before


def test_scotland_group_march_is_listed_and_uses_the_whole_card():
    state = _muster("henry_vi", "lancastrian")
    _muster_exiles(state, "henry_vi", "somerset_1")
    _start_campaign(state, "lancastrian", "henry_vi")
    state = GameState.model_validate_json(state.model_dump_json())
    move = _move_in_menu(state, "march", "carlisle", ["somerset_1"])

    remote = state.model_copy(deep=True)
    remote.lords["somerset_1"].exile_box = "ireland"
    _reject_unchanged(remote, move, "bad_group_member")

    result = actions.apply_action(state, move)
    assert result["way"] == "path" and result["whole_card"]
    assert state.campaign.actions_remaining == 0
    for lid in ("henry_vi", "somerset_1"):
        lord = state.lords[lid]
        assert lord.location == "carlisle" and lord.exile_box is None and lord.moved_fought


def _captain_in_burgundy(edward_destination):
    state = _muster("warwicks_rebellion", "yorkist")
    _muster_exiles(state, "pembroke", "devon")
    state.lords["edward_iv"].location = "newcastle"
    state.locales["newcastle"].favour = "yorkist"
    _act(state, "levy_capability", side="yorkist", by_lord="pembroke", card="Y30")
    for lid in ("pembroke", "devon", "edward_iv", "edward_iv"):
        _act(state, "levy_transport", side="yorkist", by_lord=lid, transport="ship")
    _start_campaign(state, "yorkist", "edward_iv", "pembroke")
    _act(state, "sail", side="yorkist", by_lord="edward_iv", to=edward_destination)
    _end_activation(state)
    _end_activation(state)
    return state


@pytest.mark.parametrize("edward_destination", ["north_sea", "scarborough"])
def test_captain_can_lead_group_sail_from_burgundy_with_remote_marshal(edward_destination):
    state = _captain_in_burgundy(edward_destination)
    state = GameState.model_validate_json(state.model_dump_json())
    move = _move_in_menu(state, "sail", "lynn", ["devon"])
    result = actions.apply_action(state, move)
    assert result["group"] == ["devon"]
    for lid in ("pembroke", "devon"):
        lord = state.lords[lid]
        assert lord.location == "lynn" and lord.exile_box is None and lord.moved_fought


@pytest.mark.parametrize("same_box", [True, False])
def test_captain_cannot_lead_with_a_marshal_in_its_box_or_from_at_sea(same_box):
    state = _captain_in_burgundy("scarborough")
    if same_box:
        edward = state.lords["edward_iv"]
        edward.location, edward.exile_box = None, "burgundy"
    else:
        for lid in ("pembroke", "devon"):
            lord = state.lords[lid]
            lord.exile_box, lord.at_sea = None, "north_sea"
    action = {"type": "sail", "side": "yorkist", "by_lord": "pembroke",
              "to": "lynn", "group": ["devon"]}
    assert not any(move["type"] == "sail" and move.get("group")
                   for move in legal_moves.legal_moves(state))
    _reject_unchanged(state, action, "not_group_leader")


@pytest.mark.parametrize(("destination", "influence"), [("north_sea", 2), ("newcastle", 7)])
def test_gain_lords_influence_uses_position_before_disembark(destination, influence):
    state = _muster("henry_vi", "yorkist", seed=3)
    state.lords["york"].location = "lynn"
    state.locales["lynn"].favour = "yorkist"
    for _ in range(2):
        _act(state, "levy_transport", side="yorkist", by_lord="york", transport="ship")
    _start_campaign(state, "yorkist", "york")
    _act(state, "sail", side="yorkist", by_lord="york", to=destination)
    while state.campaign.step == "activation":
        _end_activation(state)

    result = _act(state, "end_campaign")
    assert f"yorkist +{influence} Lords' Influence" in result["tides_of_war"]["detail"]
    if destination == "north_sea":
        assert result["disembark"]["rolls"] == [
            {"lord": "york", "roll": 2, "shipwreck": True, "influence_lost": 5}]
    else:
        assert result["disembark"]["rolls"] == []


@pytest.mark.parametrize(("scenario", "side", "lid", "card", "box", "title"), [
    ("warwicks_rebellion", "yorkist", "edward_iv", "Y28", "burgundy", "First Son"),
    ("henry_vi", "lancastrian", "somerset_1", "L18", "scotland", "Council Member"),
])
def test_tides_capability_requires_a_locale(scenario, side, lid, card, box, title):
    state = _muster(scenario, side, turn=3)
    lord = state.lords[lid]
    lord.location = "newcastle"
    state.locales["newcastle"].favour = side
    _act(state, "levy_capability", side=side, by_lord=lid, card=card)
    detail = f"{side} +1 {title}"
    assert detail in campaign.tides_of_war(state)["detail"]
    lord.location, lord.exile_box = None, box
    assert detail in campaign.tides_of_war(state)["detail"]
    lord.exile_box, lord.at_sea = None, "north_sea"
    assert detail not in campaign.tides_of_war(state)["detail"]
