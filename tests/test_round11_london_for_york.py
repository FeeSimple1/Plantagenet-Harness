"""Y15 double Favour through seeded draws, Parley and Pillage."""

import pytest

from plantagenet import actions, ratings
from plantagenet.errors import IllegalAction
from plantagenet.legal_moves import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState
from tests._helpers import resolve_pending_events

PARLEY = {"type": "parley", "side": "lancastrian", "by_lord": "henry_vi", "target": "london"}


def _london(seed=8, *, henry_at="london", pillage_at=None):
    state = build_initial_state("henry_vi", seed=seed)
    state.turn_box = 2
    state.locales["london"].favour = "yorkist"
    if pillage_at:
        state.lords["york"].location = pillage_at
        state.lords["york"].assets["coin"] = 0
        state.lords["henry_vi"].location = "coventry"
        state.lords["somerset_1"].location = "wells"
    elif henry_at != "london":
        state.lords["henry_vi"].location = henry_at
        state.locales[henry_at].favour = "lancastrian"
    draw = actions.apply_action(state, {"type": "draw", "side": "yorkist"})
    assert "Y15" in draw["drawn"]
    resolve_pending_events(state)
    actions.apply_action(state, {"type": "draw", "side": "lancastrian"})
    resolve_pending_events(state)
    assert state.locales["london"].favour_extra == 1
    return state


def _lancastrian_muster(state):
    for side in ("yorkist", "lancastrian"):
        actions.apply_action(state, {"type": "pay", "side": side})
    actions.apply_action(state, {"type": "end_muster", "side": "yorkist"})


def _henry_command(state):
    actions.apply_action(state, {"type": "end_muster", "side": "lancastrian"})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side, lord in (("yorkist", "york"), ("lancastrian", "henry_vi")):
        plan = [{"lord": lord}] + [{"pass": True}] * (state.campaign.cards_required - 1)
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
    actions.apply_action(state, {"type": "end_activation", "side": "yorkist"})
    assert state.campaign.active_lord == "henry_vi"


def _london_parleys(state):
    return [move for move in legal_moves(state) if all(move.get(k) == v for k, v in PARLEY.items())]


def _assert_rejected(state, action):
    before = state.model_dump_json()
    for position in (state, GameState.model_validate_json(before)):
        with pytest.raises(IllegalAction) as exc:
            actions.apply_action(position, action)
        assert exc.value.code == "london_for_york"
        assert position.model_dump_json() == before


@pytest.mark.parametrize("phase", ["levy", "campaign_here", "campaign_adjacent"])
def test_london_for_york_blocks_ordinary_parley(phase):
    state = _london(henry_at="st_albans" if phase == "campaign_adjacent" else "london")
    _lancastrian_muster(state)
    if phase != "levy":
        _henry_command(state)
    assert _london_parleys(state) == []
    _assert_rejected(state, PARLEY)

    # Only double Favour grants the protection.
    state.locales["london"].favour_extra = 0
    assert _london_parleys(state)
    actions.apply_action(state, PARLEY)


@pytest.mark.parametrize(("seed", "card"), [(70, "L18"), (107, "L17")])
def test_event_aided_parley_can_remove_both_yorkist_markers(seed, card):
    state = _london(seed=seed)
    _lancastrian_muster(state)
    henry = state.lords["henry_vi"]
    event = next(e for e in state.active_events if e["card"] == card)
    if card == "L18":
        decline = {**PARLEY, "use_parliament_votes": False}
        assert decline not in _london_parleys(state)
        _assert_rejected(state, decline)
    else:
        henry.lordship_spent = ratings.rating(state, "henry_vi", "lordship")
    spent_before = henry.lordship_spent

    move, = _london_parleys(state)
    restored = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, move)
    assert result == actions.apply_action(restored, move)
    assert state.model_dump_json() == restored.model_dump_json()
    assert result["success"]
    assert state.locales["london"].favour == "neutral"
    assert state.locales["london"].favour_extra == 0
    assert event["used"]["henry_vi"] == 1
    if card == "L18":
        assert result["roll"] is None and result["spent"] == 0
    else:
        assert result["roll"] == 4 and henry.lordship_spent == spent_before


@pytest.mark.parametrize(("site", "favour"), [("london", "lancastrian"), ("st_albans", "neutral")])
def test_pillage_that_changes_london_favour_removes_both_markers(site, favour):
    state = _london(pillage_at=site)
    action = {"type": "pay", "side": "yorkist"}
    restored = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, action)
    assert result == actions.apply_action(restored, action)
    assert state.model_dump_json() == restored.model_dump_json()
    assert site in result["troops"]["pillaged"]
    assert state.locales["london"].favour == favour
    assert state.locales["london"].favour_extra == 0
