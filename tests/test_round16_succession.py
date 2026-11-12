"""War IIY withdraws York's Burgundians when March becomes Edward IV."""

import pytest

from plantagenet import actions, invariants
from plantagenet.legal_moves import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState


def _act(state, kind, **parameters):
    return actions.apply_action(state, {"type": kind, **parameters})


@pytest.mark.parametrize("remaining, legacy_save", [(0, False), (2, False), (0, True)])
def test_yorks_death_withdraws_burgundians_and_preserves_surviving_handgunners(
    remaining, legacy_save,
):
    state = build_initial_state("wars_of_the_roses", seed=1)
    state.phase, state.victory = "over", {"result": "yorkist", "rule": "5.2"}
    _act(state, "renew_war")
    while state.levy_step == "arts_of_war":
        _act(state, "draw", side=state.active_side)
    state.lords["march"].location = "lynn"
    state.locales["lynn"].favour = "yorkist"
    state.lords["warwick_lancastrian"].location = "st_albans"
    _act(state, "end_muster", side="lancastrian")
    _act(state, "levy_capability", side="yorkist", by_lord="march", card="Y14")
    _act(state, "end_muster", side="yorkist")
    _act(state, "begin_campaign")
    assert state.lords["march"].forces["handgunners"] == 2
    state.lords["march"].forces["handgunners"] = remaining
    cards_required = state.campaign.cards_required
    _act(state, "build_plan", side="lancastrian", plan=[{"pass": True}] * cards_required)
    _act(state, "build_plan", side="yorkist", plan=[
        {"lord": "york"}, {"lord": "march"}, *([{"pass": True}] * (cards_required - 2)),
    ])
    _act(state, "end_activation", side="lancastrian")
    battle = _act(
        state, "march", side="yorkist", by_lord="york", to="st_albans",
        decisions={"flee": ["york"]},
    )["approach"]["battle"]
    assert battle["deaths"] == ["york"]
    assert state.lords["edward_iv"].capabilities == []
    assert "Y23" in state.decks["yorkist"]["draw"]
    assert not state.flags.get("burgundians_edward_iv")
    _act(state, "end_activation", side="yorkist")
    _act(state, "end_activation", side="lancastrian")

    if legacy_save:
        # Older saves dropped York's source but retained the Capability on Edward's mat.
        state.lords["edward_iv"].capabilities.append("Y14")
        state.flags["burgundians_march"] = True
    restored = GameState.model_validate_json(state.model_dump_json())
    assert restored.lords["edward_iv"].capabilities == []
    assert restored.campaign.active_lord == "edward_iv"
    for destination in ("ely", "lynn"):
        move = {"type": "march", "side": "yorkist", "by_lord": "edward_iv", "to": destination}
        assert move in legal_moves(restored)
        actions.apply_action(restored, move)
    assert restored.lords["edward_iv"].forces.get("handgunners", 0) == remaining
    assert not invariants.board_invariant_violations(restored)
