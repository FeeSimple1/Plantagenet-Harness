import pytest

from plantagenet.actions import apply_action
from plantagenet.errors import IllegalAction
from plantagenet.legal_moves import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _scots_pending():
    state = build_initial_state("henry_vi", seed=1)
    state.phase, state.levy_step = "levy", "arts_of_war"
    state.turn_box = state.calendar.first_box + 1
    state.active_side = "lancastrian"
    for pile in state.decks["lancastrian"].values():
        if "L14" in pile:
            pile.remove("L14")
    state.pending_events = [{"card": "L14", "side": "lancastrian"}]
    return state


@pytest.mark.parametrize(("decisions", "code"), [
    ({"lords": ["henry_vi", "henry_vi"]}, "duplicate_lords"),
    ({"lords": ["henry_vi", "york"]}, "bad_lord"),
    ({"lords": ["henry_vi", "exeter_1"]}, "bad_lord"),
    ({"lords": ["henry_vi", "unknown"]}, "bad_lord"),
    ({"lords": "henry_vi"}, "bad_event_decisions"),
    ({"reinforcements": {"henry_vi": {"militia": 2}}}, "bad_event_decisions"),
])
def test_scots_rejects_invalid_reinforcements_atomically(decisions, code):
    state = _scots_pending()
    action = legal_moves(state)[0]
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as error:
        apply_action(state, {**action, "decisions": decisions})
    assert error.value.code == code
    assert state.model_dump_json() == before


def test_scots_selects_each_troop_type_including_for_exiled_lords():
    state = _scots_pending()
    henry, exeter = (state.lords[lid] for lid in ("henry_vi", "exeter_1"))
    exeter.status = LordStatus.EXILE
    exeter.calendar_box = None
    exeter.exile_box = "scotland"
    exeter.forces = {"retinue": 1}
    before_henry = dict(henry.forces)
    action = legal_moves(state)[0]
    result = apply_action(state, {**action, "decisions": {"reinforcements": {
        "henry_vi": {"men_at_arms": 1},
        "exeter_1": {"militia": 1},
    }}})
    assert result["added"] == {
        "henry_vi": {"men_at_arms": 1, "militia": 0},
        "exeter_1": {"men_at_arms": 0, "militia": 1},
    }
    assert henry.forces == {**before_henry, "men_at_arms": before_henry["men_at_arms"] + 1}
    assert exeter.forces == {"retinue": 1, "militia": 1}
