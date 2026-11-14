"""Surprise Landing through the fixed Lancastrian player menu and saved state."""

import json

import pytest

from plantagenet import actions, legal_moves
from plantagenet.invariants import board_invariant_violations
from plantagenet.scenarios import build_initial_state
from tests.test_llm_interface import attach, nv, quiet
from tests.test_round20_plantagenet import _play

SIDE = "lancastrian"
LORD = "henry_tudor"


def _before_sail():
    state = build_initial_state("my_kingdom_for_a_horse", seed=2)
    for turn in range(2):
        while state.levy_step in ("arts_of_war", "pay"):
            actions.apply_action(state, legal_moves.legal_moves(state)[0])
        for _ in range(2):
            actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
        actions.apply_action(state, {"type": "begin_campaign"})
        for side in (SIDE, "yorkist"):
            plan = [{"pass": True} for _ in range(state.campaign.cards_required)]
            if turn and side == SIDE:
                plan[0] = {"lord": LORD}
            actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
        if not turn:
            while state.campaign.step == "activation":
                actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
            actions.apply_action(state, {"type": "end_campaign"})
    assert state.campaign.active_lord == LORD and state.decks[SIDE]["held"] == ["L33"]
    return state


def _assert_no_command(state, kind, **fields):
    before, stamp = state.model_dump_json(), nv.version()
    result, _ = quiet(nv.apply, {"type": kind, "side": SIDE, "by_lord": LORD, **fields},
                      expected_version=stamp)
    assert result["error"]["code"] == "no_actions_left"
    assert state.model_dump_json() == before and nv.version() == stamp


@pytest.mark.parametrize("take_march", [True, False])
def test_native_surprise_landing_allows_one_march_and_defers_feed(tmp_path, take_march):
    state = _before_sail()
    attach(state, SIDE)
    _play("sail", by_lord=LORD, to="southampton")
    assert state.campaign.actions_remaining == 0
    assert not any(row["action"]["type"] == "march" for row in nv.all_actions())
    _assert_no_command(state, "parley", target="southampton")
    _play("play_held_event", card="L33")
    assert "L33" not in state.decks[SIDE]["held"]

    checkpoint = tmp_path / "after_l33.json"
    quiet(nv.save, checkpoint)
    quiet(nv.load, checkpoint, perspective=SIDE)
    state = nv._state()
    assert state.campaign.actions_remaining == 0 and state.campaign.has_surprise_march
    moves = legal_moves.legal_moves(state)
    assert {move["type"] for move in moves} == {"march", "end_activation"}
    for kind, fields in (
        ("parley", {"target": "southampton"}), ("sail", {"to": "calais"}),
        ("forage", {}), ("supply", {"source": "southampton"}),
        ("tax", {"target": "southampton"}), ("pass", {}), ("heralds", {}),
    ):
        _assert_no_command(state, kind, **fields)
    if take_march:
        _play("march", by_lord=LORD, to="salisbury")
        assert not state.campaign.has_surprise_march
        assert state.lords[LORD].location == "salisbury"
        _assert_no_command(state, "march", to="southampton")
    assert state.lords[LORD].moved_fought and state.lords[LORD].assets["provender"] == 2
    _play("end_activation")
    assert state.campaign.surprise_march_lord is None
    assert not state.lords[LORD].moved_fought and state.lords[LORD].assets["provender"] == 1
    assert not board_invariant_violations(state)

    replay = build_initial_state(state.scenario, seed=state.seed)
    for entry in state.history:
        assert actions.apply_action(replay, entry["action"]) == entry["result"]
    assert replay.model_dump_json() == state.model_dump_json()


def test_surprise_landing_keeps_seamanship_command_and_loads_old_checkpoints(tmp_path):
    state = _before_sail()
    for pile in state.decks[SIDE].values():
        if "L6" in pile:
            pile.remove("L6")
    state.active_events.append({"card": "L6", "side": SIDE})
    attach(state, SIDE)
    _play("sail", by_lord=LORD, to="southampton")
    assert state.campaign.actions_remaining == 1
    _play("play_held_event", card="L33")
    assert state.campaign.actions_remaining == 1 and state.campaign.has_surprise_march

    checkpoint = tmp_path / "legacy.json"
    quiet(nv.save, checkpoint)
    saved = json.loads(checkpoint.read_text())
    board = json.loads(saved["state_json"])
    board["flags"]["surprise_march_lord"] = board["campaign"].pop("surprise_march_lord")
    board["campaign"]["actions_remaining"] += 1
    saved["state_json"] = json.dumps(board)
    checkpoint.write_text(json.dumps(saved))
    quiet(nv.load, checkpoint, perspective=SIDE)
    restored = nv._state()
    assert restored.model_dump_json() == state.model_dump_json()

    _play("march", by_lord=LORD, to="salisbury")
    assert restored.campaign.actions_remaining == 1 and not restored.campaign.has_surprise_march
    _play("forage", by_lord=LORD)
    assert restored.campaign.actions_remaining == 0


def test_surprise_landing_group_march_resumes_after_intercept_checkpoint(tmp_path):
    state = _before_sail()
    # Stage an ally at the Port and an enemy able to Intercept.
    ally = state.lords["jasper_tudor_2"]
    ally.location = "southampton"
    ally.exile_box = None
    state.lords["norfolk"].location = "winchester"
    attach(state, SIDE)
    group = [ally.lord_id]
    _play("sail", by_lord=LORD, to="southampton")
    _play("play_held_event", card="L33")
    assert _play("march", by_lord=LORD, to="salisbury", group=group)["type"] == "pending_intercept"
    assert state.campaign.has_surprise_march

    checkpoint = tmp_path / "intercept.json"
    quiet(nv.save, checkpoint)
    quiet(nv.load, checkpoint, perspective="yorkist")
    assert _play("respond_intercept", **{"pass": True})["type"] == "march"
    state = nv._state()
    assert not state.pending and not state.campaign.has_surprise_march
    assert state.campaign.actions_remaining == 0
    for lid in [LORD, *group]:
        assert state.lords[lid].location == "salisbury" and state.lords[lid].moved_fought
    assert not board_invariant_violations(state)
