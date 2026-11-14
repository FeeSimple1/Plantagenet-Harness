"""Round 24 regressions for Muster eligibility and Campaign Truce timing."""

import json

import pytest

from plantagenet import actions, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState
from tests.test_cross_game_sail import place, position, sail
from tests.test_llm_interface import attach, campaign_reset_state, get_id, nv, quiet
from tests.test_round20_plantagenet import _play
from tests.test_round21_plantagenet import _flank_position
from tests.test_round23_plantagenet import (
    LANCASTER,
    YORK,
    _assert_replay,
    _draw_arts,
    _end_muster,
    _finish_campaign,
    _finish_muster,
    _pay,
    _second_levy,
)


def _jack_cade_muster(*, pillage):
    state = build_initial_state("somersets_return", seed=13)
    _draw_arts(state)
    _finish_muster(state)
    actions.apply_action(state, {"type": "begin_campaign"})
    for side in (LANCASTER, YORK):
        plan = [{"pass": True}] * state.campaign.cards_required
        if pillage and side == YORK:
            plan[:2] = [{"lord": "march"}, {"lord": "march"}]
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
    targets = iter(("oxford", "newbury"))
    while state.campaign.step == "activation":
        if pillage and state.campaign.active_lord == "march":
            actions.apply_action(state, {"type": "march", "side": YORK,
                                         "by_lord": "march", "to": next(targets)})
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    _finish_campaign(state)
    _draw_arts(state)
    _pay(state)
    if state.active_side == LANCASTER:
        _end_muster(state)
    assert (state.active_side, state.levy_step) == (YORK, "muster")
    assert any(event["card"] == "Y4" for event in state.active_events)
    return state


def _warwick_parley(state, target, *, extra_spend=0):
    return actions.apply_action(state, {"type": "parley", "side": YORK,
                                       "by_lord": "warwick_yorkist", "target": target,
                                       "extra_spend": extra_spend})


def test_jack_cade_does_not_gain_recipients_after_domination_is_completed():
    state = _jack_cade_muster(pillage=True)
    assert state.locales["salisbury"].favour == "neutral"
    first = _warwick_parley(state, "salisbury", extra_spend=3)
    assert first["success"] and first["spent"] == 7 and first["roll"] == 4
    assert state.locales["salisbury"].favour == YORK
    restored = GameState.model_validate_json(state.model_dump_json())
    second = _warwick_parley(state, "oxford")
    assert second["spent"] == 2 and second["roll"] is not None
    assert state.lords["warwick_yorkist"].lordship_spent == 2
    assert _warwick_parley(restored, "oxford") == second
    assert restored.model_dump_json() == state.model_dump_json()
    _assert_replay(state)


def test_jack_cade_restores_entry_from_older_muster_save():
    state = _jack_cade_muster(pillage=True)
    assert _warwick_parley(state, "salisbury", extra_spend=3)["success"]
    save = state.model_dump(mode="json")
    next(event for event in save["active_events"] if event["card"] == "Y4").pop(
        "eligible_lords", None)
    restored = GameState.model_validate(save)
    second = _warwick_parley(restored, "oxford")
    assert second["spent"] == 2 and second["roll"] is not None
    _assert_replay(restored)


def test_jack_cade_still_grants_two_free_parleys_when_eligible_at_entry():
    state = _jack_cade_muster(pillage=False)
    assert state.locales["salisbury"].favour == YORK
    rng = state.rng_state
    for target in ("oxford", "truro"):
        result = _warwick_parley(state, target)
        assert result["success"] and result["spent"] == 0 and result["roll"] is None
    assert state.rng_state == rng
    assert state.lords["warwick_yorkist"].lordship_spent == 0
    third = _warwick_parley(state, "st_albans")
    assert third["spent"] > 0 and third["roll"] is not None
    assert state.lords["warwick_yorkist"].lordship_spent == 1
    _assert_replay(state)


def test_jack_cade_also_snapshots_when_yorkists_muster_first():
    state = _second_levy("henry_vi", seed=13)
    _pay(state)
    assert state.roles[YORK] == "rebel" and state.active_side == YORK
    event = next(event for event in state.active_events if event["card"] == "Y4")
    assert event["eligible_lords"] == []


def _truce_action(side=YORK):
    return {"type": "play_held_event", "side": side,
            "card": "Y12" if side == YORK else "L20"}


def _assert_truce_active(state, side):
    card = _truce_action(side)["card"]
    assert not any(card in pile for pile in state.decks[side].values())
    assert [e for e in state.active_events if e["card"] == card] == [
        {"card": card, "side": side, "scope": "this_campaign"},
    ]


@pytest.mark.parametrize("during_intercept", [False, True])
def test_native_truce_allows_march_past_interceptors(tmp_path, during_intercept):
    state = _flank_position()
    attach(state, LANCASTER)
    assert not nv.all_actions()
    view, _ = quiet(nv.inspect, "state")
    assert "Y12" not in json.dumps(view["data"])
    quiet(nv.set_perspective, YORK)
    before = state.campaign.actions_remaining
    rng = state.rng_state
    if during_intercept:
        assert _play("march", by_lord="york", to="st_albans")["type"] == "pending_intercept"
        quiet(nv.set_perspective, LANCASTER)
        assert all(e["action"]["type"] == "respond_intercept" for e in nv.all_actions())
        with pytest.raises(ValueError, match="unknown selection"):
            quiet(nv.apply, f"{nv.version()}/{len(nv.all_actions())}")
        get_id("respond_intercept", flank_attack=True)
        path = tmp_path / "before-truce.json"
        quiet(nv.save, path)
        quiet(nv.load, path, perspective=YORK)
        state = nv._state()
    result = _play("play_held_event", card="Y12")
    if during_intercept:
        result = result["movement"]
    else:
        assert state.campaign.actions_remaining == before
        result = _play("march", by_lord="york", to="st_albans")
    assert result["intercept"] is None and result["approach"] is None
    assert state.lords["york"].location == "st_albans"
    assert state.lords["somerset_1"].location == "london"
    assert state.campaign.actions_remaining == before - 1
    assert state.rng_state == rng and not state.pending and "L2" in state.decks[LANCASTER]["held"]
    _assert_truce_active(state, YORK)
    assert not any(move.get("to") == "london" for move in legal_moves.legal_moves(state))
    _assert_replay(state)
    _finish_campaign(state)
    assert state.phase == "levy"
    assert state.decks[YORK]["discard"].count("Y12") == 1
    assert all(event["card"] != "Y12" for event in state.active_events)
    _assert_replay(state)


def _hold(state, side, card):
    for pile in state.decks[side].values():
        if card in pile:
            pile.remove(card)
    for lord in state.lords.values():
        if card in lord.capabilities:
            lord.capabilities.remove(card)
    state.decks[side]["held"].append(card)


def test_lancastrian_truce_cancels_declared_approach_and_rejects_forgery():
    state = _flank_position()
    _hold(state, LANCASTER, "L20")
    state.lords["henry_vi"].location = "st_albans"
    attach(state, YORK)
    assert _play("march", by_lord="york", to="st_albans")["type"] == "pending_intercept"
    quiet(nv.set_perspective, LANCASTER)
    before = state.model_dump_json()
    reply, _ = quiet(nv.apply, {**_truce_action(), "side": LANCASTER},
                     expected_version=nv.version())
    assert reply["error"]["code"] == "not_held" and state.model_dump_json() == before
    leader = state.lords["york"].model_dump()
    result = _play("play_held_event", card="L20")["movement"]
    assert result["approach_cancelled"] == "parliaments_truce"
    assert not state.pending and state.campaign.actions_remaining == 0
    assert state.lords["york"].model_dump() == leader
    assert state.lords["somerset_1"].location == "london"
    assert "L2" in state.decks[LANCASTER]["held"]
    _assert_truce_active(state, LANCASTER)


def test_high_admiral_approach_can_be_cancelled_by_truce():
    state = position("exeter_1")
    state.lords["exeter_1"].capabilities = ["L29"]
    place(state, "york", "newcastle")
    _hold(state, YORK, "Y12")
    assert sail(state, "newcastle")["awaiting"]["card"] == "Y12"
    restored = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(restored, {"type": "react", "side": YORK, "play": "Y12"})
    assert result["approach_cancelled"] == "parliaments_truce" and not restored.pending
    assert restored.lords["exeter_1"].location == "lynn"
    assert restored.lords["york"].location == "newcastle"
    _assert_truce_active(restored, YORK)


def test_truce_can_cancel_high_admiral_during_blockade_reaction():
    state = position("exeter_1")
    state.lords["exeter_1"].capabilities = ["L29"]
    place(state, "york", "newcastle")
    warwick = place(state, "warwick_yorkist", "scarborough")
    warwick.capabilities = ["Y15"]
    _hold(state, YORK, "Y12")
    assert sail(state, "newcastle")["awaiting"]["card"] == "Y15"
    rng = state.rng_state
    result = actions.apply_action(state, _truce_action())["movement"]
    assert result["approach_cancelled"] == "parliaments_truce"
    assert state.lords["exeter_1"].location == "lynn" and not state.pending
    assert state.rng_state == rng and warwick.capabilities == ["Y15"]
    _assert_truce_active(state, YORK)


def test_playing_truce_before_reset_preserves_other_staged_discards():
    state = campaign_reset_state()
    _hold(state, YORK, "Y12")
    attach(state, YORK)
    quiet(nv.stage_reset, {"discard_held": ["Y12", "Y13"]}, expected_version=nv.version())
    quiet(nv.set_perspective, LANCASTER)
    quiet(nv.stage_reset, {"discard_held": ["L11"]}, expected_version=nv.version())
    quiet(nv.set_perspective, YORK)
    _play("play_held_event", card="Y12")
    quiet(nv.set_perspective, LANCASTER)
    _play("end_campaign")
    assert state.decks[YORK]["discard"].count("Y12") == 1
    assert "Y13" in state.decks[YORK]["discard"] and "L11" in state.decks[LANCASTER]["discard"]


def test_truce_card_stays_reserved_after_late_reaction_and_legacy_load():
    state = _flank_position()
    march = {"type": "march", "side": YORK, "by_lord": "york", "to": "st_albans"}
    actions.apply_action(state, {**march, "_defer_approach": True})
    actions.apply_action(state, {"type": "respond_intercept", "side": LANCASTER,
                                 "lord": "somerset_1", "flank_attack": True})
    result = actions.apply_action(state, {"type": "react", "side": YORK, "play": "Y12"})
    assert result["approach_cancelled"] == "parliaments_truce"
    _assert_truce_active(state, YORK)
    save = state.model_dump(mode="json")
    save["decks"][YORK]["discard"].append("Y12")
    restored = GameState.model_validate(save)
    _assert_truce_active(restored, YORK)
    assert restored.model_dump_json() == state.model_dump_json()
    _assert_replay(restored)


def test_truce_is_not_playable_in_levy():
    state = build_initial_state("henry_vi")
    _hold(state, YORK, "Y12")
    before = state.model_dump_json()
    assert _truce_action() not in legal_moves.legal_moves(state)
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, _truce_action())
    assert error.value.code == "not_campaign" and state.model_dump_json() == before
