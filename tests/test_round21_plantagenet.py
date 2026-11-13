"""Round 21 regressions through the player menu and saved continuations."""

import json

import pytest

from plantagenet import actions, legal_moves
from plantagenet.invariants import board_invariant_violations
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState
from tests._helpers import to_muster
from tests.test_bosworth_setup import complete_setup
from tests.test_cross_game_sail import position as sail_position
from tests.test_llm_interface import attach, complete_battle_choices, get_id, nv, quiet
from tests.test_round20_plantagenet import _march, _play, _york_campaign


def _flank_position():
    state = _york_campaign(seed=192)
    actions.apply_action(state, _march("cambridge"))
    while state.campaign.step == "activation":
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    actions.apply_action(state, {"type": "end_campaign"})
    while state.levy_step == "arts_of_war" or state.levy_step == "pay":
        actions.apply_action(state, legal_moves.legal_moves(state)[0])
    for _ in range(2):
        actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side, lord in (("yorkist", "york"), ("lancastrian", "henry_vi")):
        slots = state.campaign.cards_required
        actions.apply_action(state, {"type": "build_plan", "side": side,
                                     "plan": [{"lord": lord}] + [{"pass": True}] * (slots - 1)})
    assert state.turn_box == 2
    assert set(state.decks["lancastrian"]["held"]) == {"L2", "L11"}
    assert "Y12" in state.decks["yorkist"]["held"]
    return state


@pytest.mark.parametrize("outcome", ["truce", "exile", "battle"])
def test_native_flank_attack_preserves_approach_and_reverses_only_battle(tmp_path, outcome):
    state = _flank_position()
    base = state.model_copy(deep=True)
    attach(state, "yorkist")
    assert _play("march", by_lord="york", to="st_albans")["type"] == "pending_intercept"
    quiet(nv.set_perspective, "lancastrian")
    rng = state.rng_state
    result = _play("respond_intercept", lord="somerset_1", flank_attack=True)
    assert result["type"] == "pending_reactions"
    assert result["intercept"]["roll"] is None and state.rng_state == rng
    assert "L2" not in state.decks["lancastrian"]["held"]
    assert not nv.all_actions()
    path = tmp_path / "approach_reaction.json"
    quiet(nv.save, path)
    quiet(nv.load, path, perspective="yorkist")
    if outcome == "truce":
        result = _play("react", play="Y12")
        assert result["approach_cancelled"] == "parliaments_truce"
        assert nv._state().lords["york"].location == "cambridge"
        assert "L11" in nv._state().decks["lancastrian"]["held"]
    else:
        assert _play("react", **{"pass": True})["awaiting"]["side"] == "lancastrian"
        quiet(nv.set_perspective, "lancastrian")
        result = _play("react", play="L11") if outcome == "battle" else _play(
            "react", **{"pass": True})
        assert result["type"] == "pending_approach"
        assert result["awaiting_side"] == "lancastrian" and result["lord"] == "somerset_1"
        if outcome == "battle":
            assert {row["action"]["response"] for row in nv.all_actions()} == {"battle"}
            assert _play("respond_approach", lord="somerset_1", response="battle")[
                "awaiting_side"] == "yorkist"
            result = complete_battle_choices()["result"]
            assert result["approach"]["blocked_ford"]
            assert result["approach"]["battle"]["attackers"] == ["somerset_1"]
            assert result["approach"]["battle"]["defenders"] == ["york"]
            assert "L11" not in nv._state().decks["lancastrian"]["held"]
        else:
            result = _play("respond_approach", lord="somerset_1", response="exile")
            assert result["approach"]["exiles"] == ["somerset_1"]
            assert result["approach"]["battle"] is None
            assert nv._state().lords["york"].location == "st_albans"
    final = nv._state()
    assert not final.pending and not board_invariant_violations(final)
    for row in final.history[len(base.history):]:
        assert actions.apply_action(base, row["action"]) == row["result"]
    assert base.model_dump_json() == final.model_dump_json()


def test_legacy_flank_save_returns_exile_choice_to_the_approached_lord():
    state = _flank_position()
    attach(state, "yorkist")
    _play("march", by_lord="york", to="st_albans")
    quiet(nv.set_perspective, "lancastrian")
    _play("respond_intercept", lord="somerset_1", flank_attack=True)
    quiet(nv.set_perspective, "yorkist")
    _play("react", **{"pass": True})
    quiet(nv.set_perspective, "lancastrian")
    _play("react", **{"pass": True})
    saved = json.loads(state.model_dump_json())
    saved["pending"][0].update(side="yorkist", lords=["york"], attackers=["somerset_1"])
    restored = GameState.model_validate(saved)
    attach(restored, "lancastrian")
    assert _play("respond_approach", lord="somerset_1", response="exile")[
        "approach"]["exiles"] == ["somerset_1"]
    assert restored.lords["york"].location == "st_albans"
    assert not restored.pending and not board_invariant_violations(restored)


def _london_position():
    state = build_initial_state("henry_vi", seed=1)
    to_muster(state)
    for _ in range(2):
        actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side, lord in (("yorkist", "york"), ("lancastrian", "henry_vi")):
        actions.apply_action(state, {"type": "build_plan", "side": side,
                                     "plan": [{"lord": lord}] * 3 + [{"pass": True}]})
    attach(state, "yorkist")
    _play("march", by_lord="york", to="cambridge")
    _play("march", by_lord="york", to="st_albans")
    quiet(nv.set_perspective, "lancastrian")
    _play("respond_intercept", **{"pass": True})
    quiet(nv.set_perspective, "yorkist")
    _play("end_activation")
    quiet(nv.set_perspective, "lancastrian")
    _play("end_activation")
    quiet(nv.set_perspective, "yorkist")
    return state


def _london_approach():
    assert _play("march", by_lord="york", to="london")["type"] == "pending_approach"
    quiet(nv.set_perspective, "lancastrian")


def _london_battle():
    _play("respond_approach", lord="henry_vi", response="battle")
    assert _play("respond_approach", lord="somerset_1", response="battle") == {
        "type": "pending_battle_choices", "awaiting_side": "lancastrian",
        "locale": "london", "role": "defender",
    }


def _valour_rolls(battle, role):
    return {roll["lord"] for rnd in battle["rounds"] for engagement in rnd["engagements"]
            for strike in engagement["strikes"] for roll in strike[f"{role}_rolls"]
            if "valour_reroll" in roll}


def test_native_players_control_battle_array_and_valour_after_reload(tmp_path):
    state = _london_position()
    base = state.model_copy(deep=True)
    stamp, before = nv.version(), state.model_dump_json()
    march = get_id("march", by_lord="york", to="london")
    front = {"1": "somerset_1", "0": "henry_vi"}
    for decisions in ({"defender_positions": front}, {"valour": ["york"]}, {"valour": False}):
        with pytest.raises(PermissionError, match="choose_battle_tactics"):
            quiet(nv.apply, march, parameters={"decisions": decisions})
        assert nv.version() == stamp and state.model_dump_json() == before
    _london_approach()
    rng = state.rng_state
    _london_battle()
    move = get_id("choose_battle_tactics")
    info, _ = quiet(nv.describe, move)
    assert info["options"]["lords"] == ["henry_vi", "somerset_1"]
    before, stamp = state.model_dump_json(), nv.version()
    for parameters, error in (
        ({"positions": {"1": "york", "0": "henry_vi"}}, "bad_battle_array"),
        ({"positions": {"0": "henry_vi", "2": "somerset_1"}}, "bad_battle_array"),
        ({"valour": ["york"]}, "bad_valour_owner"),
    ):
        reply, _ = quiet(nv.apply, move, parameters=parameters)
        assert reply["error"]["code"] == error
        assert state.model_dump_json() == before and nv.version() == stamp
    quiet(nv.set_perspective, "yorkist")
    assert not nv.all_actions()
    reply, _ = quiet(nv.apply, {"type": "choose_battle_tactics", "valour": True},
                     expected_version=nv.version())
    assert reply["error"]["code"] == "wrong_battle_side"
    assert state.model_dump_json() == before
    quiet(nv.set_perspective, "lancastrian")
    move = get_id("choose_battle_tactics")
    before_choices = tmp_path / "before_choices.json"
    quiet(nv.save, before_choices)
    result = _play("choose_battle_tactics", parameters={"positions": front, "valour": True})
    assert result["awaiting_side"] == "yorkist" and state.rng_state == rng
    assert not nv.all_actions()
    after_defender = tmp_path / "after_defender.json"
    quiet(nv.save, after_defender)
    expected = None
    for _ in range(2):
        quiet(nv.load, after_defender, perspective="yorkist")
        with pytest.raises(nv.StaleSelectionError):
            quiet(nv.apply, move)
        move = get_id("choose_battle_tactics")
        info, _ = quiet(nv.describe, move)
        assert info["options"]["defender_front"] == front
        assert "valour_lords" not in info["options"]
        before = nv._state().model_dump_json()
        bad, _ = quiet(nv.apply, move, parameters={"positions": {"0": "york"}})
        assert bad["error"]["code"] == "bad_battle_array"
        assert nv._state().model_dump_json() == before
        result = _play("choose_battle_tactics", parameters={"positions": {"1": "york"}})
        final = nv._state()
        assert not final.pending and not board_invariant_violations(final)
        battle = result["approach"]["battle"]
        assert battle["rounds"][0]["engagements"][0]["defender"] == ["somerset_1", "henry_vi"]
        assert battle["losses"] == {"henry_vi": {"recovered": 1, "lost": 4},
                                    "somerset_1": {"recovered": 0, "lost": 2}}
        if expected is None:
            expected = final.model_dump_json()
            for row in final.history[len(base.history):]:
                assert actions.apply_action(base, row["action"]) == row["result"]
            assert base.model_dump_json() == expected
        else:
            assert final.model_dump_json() == expected

    # A list from one player adds to the other player's elected permissions.
    quiet(nv.load, before_choices, perspective="lancastrian")
    battle = complete_battle_choices(attacker={"valour": ["york"]})["result"]["approach"]["battle"]
    assert _valour_rolls(battle, "defender") == {"somerset_1"}
    assert _valour_rolls(battle, "attacker") == {"york"}
    quiet(nv.load, before_choices, perspective="lancastrian")
    reply, _ = quiet(nv.apply, {"type": "choose_battle_tactics", "valour": False},
                     expected_version=nv.version())
    assert reply["result"]["awaiting_side"] == "yorkist"
    quiet(nv.set_perspective, "yorkist")
    battle = _play("choose_battle_tactics")["approach"]["battle"]
    assert not _valour_rolls(battle, "defender")
    assert _valour_rolls(battle, "attacker") == {"york"}


def test_high_admiral_sail_hands_battle_choices_to_both_players():
    state = sail_position("exeter_1")
    for deck in state.decks.values():
        deck["draw"].extend(deck["held"])
        deck["held"].clear()
    for pile in state.decks["lancastrian"].values():
        if "L29" in pile:
            pile.remove("L29")
    state.lords["exeter_1"].capabilities = ["L29"]
    state.lords["york"].location = "newcastle"
    attach(state, "lancastrian")
    assert _play("sail", by_lord="exeter_1", to="newcastle")["awaiting_side"] == "yorkist"
    quiet(nv.set_perspective, "yorkist")
    assert _play("respond_approach", lord="york", response="battle")[
        "type"] == "pending_battle_choices"
    result = complete_battle_choices()["result"]
    assert result["type"] == "sail" and result["to"] == "newcastle"
    assert result["approach"]["battle"]["attackers"] == ["exeter_1"]
    assert result["approach"]["battle"]["defenders"] == ["york"]
    assert not state.pending and not board_invariant_violations(state)


def test_old_saved_approach_cannot_supply_the_other_players_tactics(tmp_path):
    _london_position()
    _london_approach()
    path = tmp_path / "old_approach.json"
    quiet(nv.save, path)
    data = json.loads(path.read_text())
    saved = json.loads(data["state_json"])
    saved["pending"][0]["attackers"] = ["york"]
    saved["pending"][0]["decisions"].update(
        defender_positions={"1": "somerset_1", "0": "henry_vi"}, valour=["york"])
    data["state_json"] = json.dumps(saved)
    path.write_text(json.dumps(data))
    quiet(nv.load, path, perspective="lancastrian")
    _london_battle()
    battle = complete_battle_choices()["result"]["approach"]["battle"]
    assert battle["rounds"][0]["engagements"][0]["defender"] == ["henry_vi", "somerset_1"]
    assert _valour_rolls(battle, "defender") == {"somerset_1"}
    assert _valour_rolls(battle, "attacker") == {"york"}


def test_fixed_bosworth_collects_both_valour_policies_with_locked_arrays(tmp_path):
    state = build_initial_state("bosworth", seed=731)
    complete_setup(state)
    joint = state.model_copy(deep=True)
    expected = actions.apply_action(joint, {"type": "resolve_battle", "decisions": {
        "valour": state.battle_setup.arrays["yorkist"],
    }})
    attach(state, state.active_side)
    assert _play("resolve_battle")["awaiting_side"] == "yorkist"
    quiet(nv.set_perspective, "yorkist")
    move = get_id("choose_battle_tactics")
    info, _ = quiet(nv.describe, move)
    assert info["options"]["array_locked"]
    before = state.model_dump_json()
    reply, _ = quiet(nv.apply, move, parameters={"positions": {"1": "richard_iii"}})
    assert reply["error"]["code"] == "battle_array_locked" and state.model_dump_json() == before
    assert _play("choose_battle_tactics")["awaiting_side"] == "lancastrian"
    path = tmp_path / "bosworth_tactics.json"
    quiet(nv.save, path)
    quiet(nv.load, path, perspective="lancastrian")
    assert _play("choose_battle_tactics", parameters={"valour": False}) == expected
    final = nv._state()
    assert final.battle_setup.arrays == state.battle_setup.arrays
    assert final.model_dump(exclude={"history"}) == joint.model_dump(exclude={"history"})
    assert not board_invariant_violations(final)
    replay = build_initial_state("bosworth", seed=731)
    for row in final.history:
        assert actions.apply_action(replay, row["action"]) == row["result"]
    assert replay.model_dump_json() == final.model_dump_json()
