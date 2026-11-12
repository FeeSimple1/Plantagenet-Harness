"""A living card swap preserves the mat's Muster and Battle obligations."""

import pytest

from plantagenet import actions, invariants, ratings
from plantagenet.errors import IllegalAction
from plantagenet.legal_moves import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus

CROWN = {"type": "crown_richard", "side": "yorkist"}


def _act(state, kind, **args):
    return actions.apply_action(state, {"type": kind, **args})


def _first_muster(state):
    while state.levy_step == "arts_of_war":
        _act(state, "draw", side=state.active_side)
    assert state.levy_step == "muster"


def _reject_crown(state, action, code):
    before = state.model_dump_json()
    for position in (state, GameState.model_validate_json(before)):
        assert action not in legal_moves(position)
        with pytest.raises(IllegalAction) as rejected:
            actions.apply_action(position, action)
        assert rejected.value.code == code
        assert position.model_dump_json() == before


def test_king_richard_is_available_at_native_setup_and_after_reload():
    state = build_initial_state("my_kingdom_for_a_horse", seed=1)
    restored = GameState.model_validate_json(state.model_dump_json())
    for position in (state, restored):
        assert CROWN in legal_moves(position)
        assert actions.apply_action(position, CROWN)["with"] == "richard_iii"
        assert position.lords["richard_iii"].location == "london"
        assert position.lords["gloucester_2"].status == LordStatus.REMOVED
        assert any(move["type"] == "draw" for move in legal_moves(position))
        assert not invariants.board_invariant_violations(position)
    assert state.model_dump_json() == restored.model_dump_json()


def test_king_richard_setup_window_closes_at_the_first_draw():
    state = build_initial_state("my_kingdom_for_a_horse", seed=1)
    _act(state, "draw", side="lancastrian")
    assert state.levy_step == "arts_of_war"
    _reject_crown(state, CROWN, "wrong_step")
    _first_muster(state)
    _reject_crown(state, CROWN, "not_active_side")
    _act(state, "end_muster", side="lancastrian")
    assert CROWN in legal_moves(state)


@pytest.mark.parametrize("side", ["lancastrian", None])
def test_only_york_can_choose_to_crown_richard(side):
    state = build_initial_state("my_kingdom_for_a_horse", seed=1)
    _first_muster(state)
    _act(state, "end_muster", side="lancastrian")
    _reject_crown(state, {**CROWN, "side": side}, "wrong_side")
    assert CROWN in legal_moves(state)


def test_king_richard_cannot_rewrite_a_campaign_plan():
    state = build_initial_state("my_kingdom_for_a_horse", seed=1)
    _first_muster(state)
    for side in ("lancastrian", "yorkist"):
        _act(state, "end_muster", side=side)
    _act(state, "begin_campaign")
    for side, lord in (("lancastrian", "henry_tudor"), ("yorkist", "gloucester_2")):
        plan = [{"lord": lord}] + [{"pass": True}] * (state.campaign.cards_required - 1)
        _act(state, "build_plan", side=side, plan=plan)
    assert state.campaign.active_lord == "henry_tudor"
    _reject_crown(state, CROWN, "wrong_step")
    assert state.campaign.plans["yorkist"][0] == {"lord": "gloucester_2"}
    _act(state, "end_activation", side="lancastrian")
    assert state.campaign.active_lord == "gloucester_2"
    _reject_crown(state, CROWN, "wrong_step")


@pytest.mark.parametrize("already_spent", [0, 1, 3])
def test_crowning_richard_keeps_the_remaining_muster_budget(already_spent):
    state = build_initial_state("my_kingdom_for_a_horse", seed=1)
    _first_muster(state)
    _act(state, "end_muster", side="lancastrian")
    transport = {"type": "levy_transport", "side": "yorkist", "transport": "cart"}
    for _ in range(already_spent):
        actions.apply_action(state, {**transport, "by_lord": "gloucester_2"})
    assert CROWN in legal_moves(state)
    restored = GameState.model_validate_json(state.model_dump_json())
    for position in (state, restored):
        actions.apply_action(position, CROWN)
        for _ in range(3 - already_spent):
            actions.apply_action(position, {**transport, "by_lord": "richard_iii"})
        richard = position.lords["richard_iii"]
        assert richard.assets["cart"] == 8
        assert richard.lordship_spent == 3
        assert not any(move["type"] == "levy_transport" and move.get("by_lord") == "richard_iii"
                       for move in legal_moves(position))
        before = position.model_dump_json()
        with pytest.raises(IllegalAction) as rejected:
            actions.apply_action(position, {**transport, "by_lord": "richard_iii"})
        assert rejected.value.code == "lordship_exhausted"
        assert position.model_dump_json() == before
    assert restored.model_dump() == state.model_dump()


def _war_iiy_encounter(seed, march_in_battle):
    state = build_initial_state("wars_of_the_roses", seed=seed)
    # Start from War IIY after a Yorkist victory. Stage the encounter by
    # moving intact native mats, with the normal RNG and Campaign actions.
    state.phase, state.victory = "over", {"result": "yorkist", "rule": "5.2"}
    _act(state, "renew_war")
    assert state.grand_scenario["current_war"] == "war_iiy"
    _first_muster(state)
    state.lords["march"].location = "london"
    state.lords["warwick_lancastrian"].location = "st_albans"
    assert not invariants.board_invariant_violations(state)
    while state.levy_step == "muster":
        _act(state, "end_muster", side=state.active_side)
    _act(state, "begin_campaign")
    for side, lid in (("lancastrian", "warwick_lancastrian"), ("yorkist", "york")):
        plan = [{"lord": lid}] + [{"pass": True}] * (state.campaign.cards_required - 1)
        _act(state, "build_plan", side=side, plan=plan)
    _act(state, "end_activation", side="lancastrian")
    return state, ["march"] if march_in_battle else []


@pytest.mark.parametrize("seed, order, deaths, disbands, edward_status", [
    (1, ["york", "march"], ["york"], ["edward_iv"], LordStatus.CALENDAR),
    (24, ["york", "march"], ["york", "edward_iv"], [], LordStatus.REMOVED),
    (2, ["york", "march"], [], ["york", "march"], None),
    (1, ["march", "york"], ["march"], ["york"], None),
    (1, ["york"], ["york"], [], LordStatus.MUSTERED),
])
def test_battle_death_checks_follow_the_living_mat(seed, order, deaths, disbands, edward_status):
    state, group = _war_iiy_encounter(seed, "march" in order)
    restored = GameState.model_validate_json(state.model_dump_json())
    dice = state.dice()
    dice.roll(len(order))  # Immediate Flee leaves only the elected Death checks.
    march = {"type": "march", "side": "yorkist", "by_lord": "york", "to": "st_albans",
             "group": group, "decisions": {"flee": ["york", *group],
                                           "death_order": {"yorkist": order}}}
    receipt = actions.apply_action(state, march)
    assert actions.apply_action(restored, march) == receipt
    assert restored.model_dump() == state.model_dump()
    result = receipt["approach"]["battle"]
    assert result["death_order"] == order
    assert result["deaths"] == deaths
    assert result["disbands"] == disbands
    assert result["winner_side"] == "lancastrian"
    assert state.dice().get_state() == dice.get_state()
    if edward_status is not None:
        edward = state.lords["edward_iv"]
        assert edward.status == edward_status
        assert state.lords["march"].status == LordStatus.REMOVED
        assert edward.location == ("london" if edward_status == LordStatus.MUSTERED else None)
        if edward_status == LordStatus.CALENDAR:
            assert edward.calendar_box == state.turn_box + 6 - ratings.rating(
                state, "edward_iv", "influence")
            assert not edward.forces
    assert not invariants.board_invariant_violations(state)
