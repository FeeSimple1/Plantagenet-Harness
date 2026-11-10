"""Public-action regressions for Capture of the King and Tax Collectors."""

import pytest

from plantagenet import actions, influence
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus
from tests._helpers import apply_drawn_event
from tests.test_cross_game_battle_pools_and_death import capability, march, position
from tests.test_cross_game_sail import place


def _capture_position():
    state = position("henry_vi", "york", "ely")
    place(state, "henry_vi", "cambridge").forces = {"retinue": 1, "militia": 1}
    state.locales["cambridge"].favour = "yorkist"
    return state


def test_temporary_troops_last_until_capture_then_release_henry():
    state = _capture_position()
    york = state.lords["york"]
    henry = state.lords["henry_vi"]
    york.forces = {"retinue": 1}
    capability(state, "york", "Y3")
    action = march(state, "cambridge", flee=["henry_vi"])
    before = influence._net_lanc(state.influence["track"])
    replay = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, action)["approach"]["battle"]

    assert result["captured"] == [{"lord": henry.lord_id, "by": york.lord_id}]
    assert result["aftermath_disbands"] == [york.lord_id]
    assert result["losses"][york.lord_id] == {"recovered": 0, "lost": 0}
    assert york.status == henry.status == LordStatus.CALENDAR
    assert henry.captured_by is None
    after = influence._net_lanc(state.influence["track"])
    assert after == before - result["influence_award"]["yorkist"]
    assert actions.apply_action(replay, action)["approach"]["battle"] == result
    assert replay.model_dump_json() == state.model_dump_json()


def test_yorkists_can_choose_a_different_eligible_captor():
    state = _capture_position()
    place(state, "salisbury", "ely").forces = {"retinue": 1, "militia": 1}
    action = march(state, "cambridge", flee=["henry_vi"])
    action["group"] = ["salisbury"]
    before = state.model_dump_json()

    # A routed participant and an absent Yorkist cannot hold Henry.
    for invalid in ("salisbury", "march"):
        action["decisions"] = {"flee": ["henry_vi", "salisbury"], "capture_holder": invalid}
        with pytest.raises(IllegalAction, match="bad_capture_holder"):
            actions.apply_action(state, action)
        assert state.model_dump_json() == before

    action["decisions"] = {"flee": ["henry_vi"], "capture_holder": "salisbury"}
    result = actions.apply_action(state, action)["approach"]["battle"]
    assert result["captured"] == [{"lord": "henry_vi", "by": "salisbury"}]
    assert state.lords["henry_vi"].captured_by == "salisbury"


@pytest.mark.parametrize(("origin", "eligible"), [
    ("carlisle", False), ("cambridge", True), ("ely", True),
])
def test_tax_collectors_checks_own_seat_route_and_taxes_each_lord_once(origin, eligible):
    state = position("henry_vi", "york", origin)
    for locale in state.locales.values():
        locale.favour = "lancastrian"
    state.locales[origin].favour = state.locales["ely"].favour = "yorkist"
    state.locales["ely"].depletion = None
    york = state.lords["york"]
    result = apply_drawn_event(state, {"type": "play_event", "side": "yorkist", "card": "Y10",
                                      "decisions": {"lords": ["york", "york"],
                                                    "tax_targets": {"york": "ely"}}})
    if eligible:
        assert result["taxes"] == {"york": {"target": "ely", "coin": 4, "success": True,
                                            "auto": True, "roll": None, "spent": 0}}
        assert york.assets["coin"] == 4
        assert state.locales["ely"].depletion == "depleted"
    else:
        assert result["taxes"] == {}
        assert york.assets.get("coin", 0) == 0
        assert state.locales["ely"].depletion is None
