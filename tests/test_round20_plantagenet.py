"""Round 20 regressions for Levy Parley and player-owned Intercept."""

import pytest

from plantagenet import actions, legal_moves
from plantagenet.invariants import board_invariant_violations
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster
from tests.test_llm_interface import attach, complete_battle_choices, get_id, nv, quiet


def _york_campaign(seed=3):
    state = build_initial_state("henry_vi", seed=seed)
    to_muster(state)
    for _ in range(2):
        actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side, lord in (("yorkist", "york"), ("lancastrian", "henry_vi")):
        actions.apply_action(state, {"type": "build_plan", "side": side,
                                     "plan": [{"lord": lord}] + [{"pass": True}] * 3})
    return state


def _march(to):
    return {"type": "march", "side": "yorkist", "by_lord": "york", "to": to}


def _play(kind, *, parameters=None, **fields):
    reply, _ = quiet(nv.apply, get_id(kind, **fields), parameters=parameters)
    assert reply["kind"] == "result", dict(reply)
    return reply["result"]


def test_native_levy_parley_requires_a_friendly_origin_for_remote_targets():
    state = _york_campaign()
    actions.apply_action(state, _march("cambridge"))
    while state.campaign.step == "activation":
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    actions.apply_action(state, {"type": "end_campaign"})
    while state.levy_step != "muster":
        actions.apply_action(state, legal_moves.legal_moves(state)[0])
    assert state.turn_box == 2
    assert state.lords["york"].location == "cambridge"
    assert state.locales["cambridge"].favour == "neutral"
    attach(state, "yorkist")
    local = get_id("parley", by_lord="york", target="cambridge")
    before, stamp = state.model_dump_json(), nv.version()
    custom = {"type": "parley", "side": "yorkist", "by_lord": "york", "target": "st_albans"}
    for choice, kwargs in ((custom, {"expected_version": stamp}),
                           (local, {"parameters": {"target": "st_albans"}})):
        reply, _ = quiet(nv.apply, choice, **kwargs)
        assert reply["error"]["code"] == "not_friendly_locale"
        assert state.model_dump_json() == before and nv.version() == stamp
    local_result = _play("parley", by_lord="york", target="cambridge")
    remote = _play("parley", by_lord="york", target="st_albans")
    assert local_result["spent"] == 1 and remote["spent"] == 2
    assert state.locales["cambridge"].favour == state.locales["st_albans"].favour == "yorkist"
    assert state.lords["york"].lordship_spent == 2


@pytest.mark.parametrize("choice", ["decline", "attempt", "fail"])
def test_native_intercept_hands_off_and_replays_from_saved_declaration(tmp_path, choice):
    state = _york_campaign()
    attach(state, "yorkist")
    _play("march", by_lord="york", to="cambridge")
    before_march = state.model_copy(deep=True)
    move = get_id("march", by_lord="york", to="st_albans")
    before, stamp = state.model_dump_json(), nv.version()
    for decisions in ({"intercept": "somerset_1"}, {"intercept_group": ["henry_vi"]},
                      {"flank_attack": True}):
        with pytest.raises(PermissionError, match="respond_intercept"):
            quiet(nv.apply, move, parameters={"decisions": decisions})
        assert state.model_dump_json() == before and nv.version() == stamp
    prompt = _play("march", by_lord="york", to="st_albans")
    assert prompt["type"] == "pending_intercept" and prompt["awaiting_side"] == "lancastrian"
    assert state.lords["york"].location == "cambridge"
    assert state.campaign.actions_remaining == 1
    assert state.rng_state == before_march.rng_state
    assert state.lords["somerset_1"].location == "london"
    assert not nv.all_actions()
    pending, stamp = state.model_dump_json(), nv.version()
    rejected, _ = quiet(nv.apply, {"type": "respond_intercept", "pass": True},
                        expected_version=stamp)
    assert rejected["error"]["code"] == "wrong_intercept_side"
    rejected, _ = quiet(nv.apply, {"type": "end_activation", "side": "yorkist"},
                        expected_version=stamp)
    assert rejected["error"]["code"] == "intercept_pending"
    assert state.model_dump_json() == pending and nv.version() == stamp

    path = tmp_path / "intercept.json"
    quiet(nv.save, path)
    quiet(nv.set_perspective, "lancastrian")
    responses = [row["action"] for row in nv.all_actions()]
    assert {row.get("lord") for row in responses} == {None, "henry_vi", "somerset_1"}
    assert all(row["type"] == "respond_intercept" for row in responses)
    old_response = get_id("respond_intercept", **{"pass": True})
    expected = None
    for _ in range(2):
        quiet(nv.load, path, perspective="lancastrian")
        with pytest.raises(nv.StaleSelectionError):
            quiet(nv.apply, old_response)
        assert nv._state().model_dump_json() == pending
        if choice == "decline":
            reply = _play("respond_intercept", **{"pass": True})
            assert reply["intercept"] is None
        elif choice == "fail":
            reply = _play("respond_intercept", lord="henry_vi")
            assert reply["intercept"]["roll"] == 2
            assert reply["intercept"]["success"] is False
        else:
            reply = _play("respond_intercept", lord="somerset_1")
            assert reply["intercept"]["roll"] == 2
            assert reply["type"] == "pending_approach"
            assert nv._state().lords["somerset_1"].location == "st_albans"
            assert nv._state().lords["somerset_1"].moved_fought
            reply = _play("respond_approach", lord="somerset_1", response="exile")
            assert reply["approach"]["exiles"] == ["somerset_1"]
        resolved = nv._state()
        assert not resolved.pending and not board_invariant_violations(resolved)
        assert resolved.lords["york"].location == "st_albans"
        if choice != "attempt":
            assert resolved.lords["somerset_1"].location == "london"
            assert resolved.campaign.actions_remaining == 0
        if choice == "decline":
            assert resolved.rng_state == before_march.rng_state
        # Replay the recorded engine actions from before the March declaration.
        replay = before_march.model_copy(deep=True)
        for row in resolved.history[len(before_march.history):]:
            assert actions.apply_action(replay, row["action"]) == row["result"]
        assert replay.model_dump_json() == resolved.model_dump_json()
        if expected is None:
            expected = resolved.model_dump_json()
        else:
            assert resolved.model_dump_json() == expected


def test_flank_attack_and_intercept_group_belong_to_the_intercepting_player(tmp_path):
    state = _york_campaign()
    actions.apply_action(state, _march("cambridge"))
    # A stationary ally at the destination also Defends in the Flank Battle.
    salisbury = state.lords["salisbury"]
    salisbury.location = "st_albans"
    salisbury.status = LordStatus.MUSTERED
    salisbury.calendar_box = None
    salisbury.forces = {"retinue": 1}
    for pile in state.decks["lancastrian"].values():
        if "L2" in pile:
            pile.remove("L2")
    state.decks["lancastrian"]["held"].append("L2")
    attach(state, "yorkist")
    # The attacker's declaration cannot reveal or spend the enemy's Held Event.
    _play("march", by_lord="york", to="st_albans")
    details, _ = quiet(nv.describe, "respond_intercept")
    assert "group_options" not in details and not nv.all_actions()
    quiet(nv.set_perspective, "lancastrian")
    move = get_id("respond_intercept", lord="henry_vi", flank_attack=True)
    info, _ = quiet(nv.describe, move)
    assert info["group_options"] == ["somerset_1"]
    before, stamp = state.model_dump_json(), nv.version()
    for group in (["york"], ["somerset_1", "somerset_1"]):
        rejected, _ = quiet(nv.apply, move, parameters={"group": group})
        assert rejected["error"]["code"] in ("bad_group", "bad_group_member")
        assert state.model_dump_json() == before and nv.version() == stamp
    rejected, _ = quiet(nv.apply, move, parameters={"decisions": {"flee": ["york"]}})
    assert rejected["error"]["code"] == "wrong_flee_owner"
    assert state.model_dump_json() == before and nv.version() == stamp
    rng = state.rng_state
    out = _play("respond_intercept", lord="henry_vi", flank_attack=True, parameters={
        "group": ["somerset_1"], "decisions": {"flee_rounds": {"somerset_1": 1}},
    })
    assert out["type"] == "pending_approach" and out["awaiting_side"] == "lancastrian"
    assert out["intercept"]["flank_attack"] and out["intercept"]["roll"] is None
    assert state.rng_state == rng
    assert state.lords["henry_vi"].location == state.lords["somerset_1"].location == "st_albans"
    assert "L2" not in state.decks["lancastrian"]["held"]
    assert state.campaign.actions_remaining == 0
    assert not board_invariant_violations(state)
    path = tmp_path / "flank.json"
    quiet(nv.save, path)
    quiet(nv.load, path, perspective="lancastrian")
    _play("respond_approach", lord="henry_vi", response="battle")
    out = _play("respond_approach", lord="somerset_1", response="battle")
    assert out["type"] == "pending_battle_choices" and out["awaiting_side"] == "yorkist"
    battle = complete_battle_choices()["result"]["approach"]["battle"]
    assert battle["attackers"] == ["henry_vi", "somerset_1"]
    assert battle["defenders"] == ["york", "salisbury"]
    assert battle["rounds"][0]["fled"] == ["somerset_1"]
    assert not board_invariant_violations(nv._state())


def test_active_truce_skips_intercept_even_when_enemy_lords_are_adjacent():
    state = _york_campaign()
    actions.apply_action(state, _march("cambridge"))
    state.active_events.append({"card": "L20", "side": "lancastrian",
                                "scope": "this_campaign"})
    attach(state, "yorkist")
    out = _play("march", by_lord="york", to="st_albans")
    assert out["type"] == "march" and out["intercept"] is None
    assert state.lords["york"].location == "st_albans"
    assert state.lords["somerset_1"].location == "london"
    assert not state.pending


def test_intercept_can_reinforce_an_approach_before_reactions():
    state = _york_campaign()
    actions.apply_action(state, _march("cambridge"))
    state.lords["henry_vi"].location = "st_albans"
    for pile in state.decks["lancastrian"].values():
        if "L15" in pile:
            pile.remove("L15")
    state.lords["henry_vi"].capabilities.append("L15")
    attach(state, "yorkist")
    assert _play("march", by_lord="york", to="st_albans")["type"] == "pending_intercept"
    quiet(nv.set_perspective, "lancastrian")
    out = _play("respond_intercept", lord="somerset_1")
    assert out["type"] == "pending_reactions"
    assert out["intercept"]["success"]
    assert out["awaiting"]["card"] == "L15"
    assert not board_invariant_violations(state)
    out = _play("react", **{"pass": True})
    assert out["type"] == "pending_approach"
    for lord in ("henry_vi", "somerset_1"):
        out = _play("respond_approach", lord=lord, response="exile")
    assert set(out["approach"]["exiles"]) == {"henry_vi", "somerset_1"}
    assert state.campaign.actions_remaining == 0
    assert not state.pending and not board_invariant_violations(state)
