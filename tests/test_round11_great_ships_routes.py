"""Great Ships reach in Campaign Parley and Exile Supply (Y6/L6)."""

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.legal_moves import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState


def _shipping_command(active, *, in_exile, great_ships=True):
    state = build_initial_state("henry_vi", seed=2)
    state.levy_step, state.active_side = "muster", "yorkist"
    state.locales["bristol"].favour = "yorkist"
    if in_exile:
        state.locales["dover"].favour = "yorkist"
    for lid in {"york", active}:
        lord = state.lords[lid]
        lord.location = None if in_exile else "bristol"
        lord.exile_box = "ireland" if in_exile else None
    if great_ships:
        actions.apply_action(state, {"type": "levy_capability", "side": "yorkist",
                                     "by_lord": "york", "card": "Y6"})
    for _ in range(2):
        actions.apply_action(state, {"type": "levy_transport", "side": "yorkist",
                                     "by_lord": "york", "transport": "ship"})
    for side in ("yorkist", "lancastrian"):
        actions.apply_action(state, {"type": "end_muster", "side": side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side, lid in (("yorkist", active), ("lancastrian", "henry_vi")):
        plan = [{"lord": lid}] + [{"pass": True}] * (state.campaign.cards_required - 1)
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
    return state


@pytest.mark.parametrize("command", ["parley", "supply"])
@pytest.mark.parametrize("owner", ["self", "ally", "ordinary"])
def test_campaign_can_use_the_selected_ship_owners_cross_sea_reach(command, owner):
    active = "march" if owner == "ally" else "york"
    state = _shipping_command(active, in_exile=command == "supply",
                              great_ships=owner != "ordinary")
    params = {"source": "dover", "use_ships": True} if command == "supply" else {"target": "dover"}
    action = {"type": command, "side": "yorkist", "by_lord": active, **params}
    if owner == "ally":
        action["share"] = ["york"]
    matches = [m for m in legal_moves(state) if all(m.get(key) == v for key, v in action.items())]
    checkpoint = state.model_dump_json()
    if owner == "ordinary":
        assert not matches
        with pytest.raises(IllegalAction) as exc:
            actions.apply_action(state, action)
        code = "exile_needs_ship_port" if command == "supply" else "out_of_reach"
        assert exc.value.code == code
        assert state.model_dump_json() == checkpoint
    else:
        move, = matches
        restored = GameState.model_validate_json(checkpoint)
        result = actions.apply_action(state, move)
        assert result == actions.apply_action(restored, move)
        assert state.model_dump_json() == restored.model_dump_json()
        assert state.lords["york"].assets["ship"] == 2
        if command == "supply":
            assert result["provender_added"] == 4 and result["via"] == "ship"
            assert state.locales["dover"].depletion is None
        else:
            assert result["spent"] == 2
            if owner == "self":
                assert result["success"]
