"""Held Event timing through native draws, player menus and saved games."""

import json

import pytest

from plantagenet import actions, legal_moves, ratings
from plantagenet.invariants import board_invariant_violations
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState
from tests._helpers import resolve_pending_events
from tests.test_llm_interface import attach, get_id, nv, quiet
from tests.test_round20_plantagenet import _play

YORK = "yorkist"
LANCASTER = "lancastrian"
Y24_LONDON = {"type": "play_held_event", "side": YORK, "card": "Y24",
              "decisions": {"target": "london"}}


def _draw_arts(state):
    while state.levy_step == "arts_of_war":
        if state.pending_events:
            resolve_pending_events(state)
        else:
            actions.apply_action(state, legal_moves.legal_moves(state)[0])


def _pay(state):
    while state.levy_step == "pay":
        actions.apply_action(state, {"type": "pay", "side": state.active_side})


def _end_muster(state):
    actions.apply_action(state, {"type": "end_muster", "side": state.active_side})


def _finish_muster(state):
    while state.levy_step == "muster":
        _end_muster(state)


def _start_campaign(state, *, first_yorkist=None):
    _finish_muster(state)
    actions.apply_action(state, {"type": "begin_campaign"})
    for side in (LANCASTER, YORK):
        plan = [{"pass": True} for _ in range(state.campaign.cards_required)]
        if side == YORK and first_yorkist is not None:
            plan[0] = {"lord": first_yorkist}
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})


def _finish_campaign(state):
    while state.campaign.step == "activation":
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    actions.apply_action(state, {"type": "end_campaign"})


def _second_levy(scenario, seed):
    state = build_initial_state(scenario, seed=seed)
    _draw_arts(state)
    _start_campaign(state)
    _finish_campaign(state)
    _draw_arts(state)
    return state


def _assert_replay(state):
    replay = build_initial_state(state.scenario, seed=state.seed)
    for entry in state.history:
        assert actions.apply_action(replay, entry["action"]) == entry["result"]
    assert replay.model_dump(mode="json") == state.model_dump(mode="json")
    assert not board_invariant_violations(state)


def _round_trip(state, path):
    before = state.model_dump(mode="json")
    quiet(nv.save, path)
    quiet(nv.load, path, perspective=YORK)
    restored = nv._state()
    assert restored.model_dump(mode="json") == before
    return restored


def _assert_rejected(state, action, code):
    before, stamp = state.model_dump_json(), nv.version()
    reply, _ = quiet(nv.apply, action, expected_version=stamp)
    assert reply["error"]["code"] == code
    assert state.model_dump_json() == before and nv.version() == stamp


def _y24_before_levy_choice():
    state = _second_levy("warwicks_rebellion", 5)
    assert "Y24" in state.decks[YORK]["held"]
    actions.apply_action(state, {"type": "pay", "side": LANCASTER})
    actions.apply_action(state, {"type": "pay", "side": YORK, "disband_lords": ["edward_iv"]})
    assert state.lords["edward_iv"].status == "calendar"
    assert state.lords["edward_iv"].calendar_box == 3
    return state


@pytest.mark.parametrize("play_during_lancastrian_muster", [False, True])
def test_sun_in_splendour_during_muster_summons_edward_without_lordship(
    tmp_path, play_during_lancastrian_muster
):
    state = _y24_before_levy_choice()
    if not play_during_lancastrian_muster:
        _end_muster(state)
    attach(state, YORK)
    _play("play_held_event", card="Y24", decisions={"target": "london"})
    edward = state.lords["edward_iv"]
    assert edward.location == "london" and edward.status == "mustered"
    assert state.decks[YORK]["discard"].count("Y24") == 1
    assert "Y24" not in state.decks[YORK]["held"]
    if play_during_lancastrian_muster:
        _end_muster(state)
    state = _round_trip(state, tmp_path / "late-muster.json")
    assert state.lords["edward_iv"].mustered_this_segment
    assert not any(m.get("by_lord") == "edward_iv" for m in legal_moves.legal_moves(state))
    _assert_rejected(state, {"type": "levy_transport", "side": YORK,
                             "by_lord": "edward_iv", "transport": "cart"},
                     "mustered_this_segment")
    _assert_replay(state)

    old_save = state.model_dump(mode="json")
    old_save["lords"]["edward_iv"]["mustered_this_segment"] = False
    assert GameState.model_validate(old_save).model_dump(mode="json") == state.model_dump(
        mode="json")


def test_sun_in_splendour_is_offered_during_arts_of_war_and_pay(tmp_path):
    state = _y24_before_levy_choice()
    _start_campaign(state)
    _finish_campaign(state)
    assert (state.turn_box, state.levy_step, state.active_side) == (3, "arts_of_war", LANCASTER)
    attach(state, YORK)
    get_id("play_held_event", card="Y24", decisions={"target": "london"})
    _draw_arts(state)
    assert state.levy_step == "pay" and state.active_side == LANCASTER
    id_for_york = get_id("play_held_event", card="Y24", decisions={"target": "london"})
    quiet(nv.set_perspective, LANCASTER)
    assert all(e["action"]["side"] == LANCASTER for e in nv.all_actions())
    _assert_rejected(state, {**Y24_LONDON, "side": LANCASTER}, "not_held")
    with pytest.raises(nv.StaleSelectionError):
        quiet(nv.apply, id_for_york)
    quiet(nv.set_perspective, YORK)

    state = _round_trip(state, tmp_path / "before-pay.json")
    _play("play_held_event", card="Y24", decisions={"target": "london"})
    assert state.active_side == LANCASTER and state.levy_step == "pay"
    _pay(state)
    _end_muster(state)
    assert state.levy_step == "muster" and state.active_side == YORK
    state = _round_trip(state, tmp_path / "early-muster.json")
    before = state.lords["edward_iv"].assets["cart"]
    _play("levy_transport", by_lord="edward_iv", transport="cart")
    assert state.lords["edward_iv"].assets["cart"] == before + 2
    _assert_replay(state)


def _assert_parade_reserved(state):
    assert sum(e["card"] == "Y20" for e in state.active_events) == 1
    assert all("Y20" not in pile for pile in state.decks[YORK].values())


def _assert_parade_expired(state):
    assert not any(e["card"] == "Y20" for e in state.active_events)
    assert state.decks[YORK]["discard"].count("Y20") == 1
    assert ratings.rating(state, "march", "influence") == 2


def test_yorkist_parade_reserves_card_and_waits_for_next_levy(tmp_path):
    state = _second_levy("somersets_return", 2)
    _pay(state)
    _start_campaign(state, first_yorkist="march")
    while state.active_side != YORK:
        actions.apply_action(state, {"type": "end_activation", "side": state.active_side})
    assert state.turn_box == 6 and state.campaign.active_lord == "march"
    attach(state, YORK)
    state = _round_trip(state, tmp_path / "parade-before-campaign-play.json")
    control = actions.apply_action(state.model_copy(deep=True),
                                   {"type": "parley", "side": YORK, "by_lord": "march",
                                    "target": "oxford"})
    assert (control["roll"], control["rating"], control["spent"]) == (3, 2, 2)
    assert not control["success"]

    assert _play("play_held_event", card="Y20")["levy_turn"] == 7
    _assert_parade_reserved(state)
    state = _round_trip(state, tmp_path / "parade-scheduled.json")
    assert _play("parley", by_lord="march", target="oxford") == control
    assert state.locales["oxford"].favour == "neutral"
    _finish_campaign(state)
    assert state.turn_box == 7 and ratings.rating(state, "march", "influence") == 4
    _draw_arts(state)
    _pay(state)
    _end_muster(state)
    _assert_parade_reserved(state)
    state = _round_trip(state, tmp_path / "parade-during-levy.json")
    assert ratings.rating(state, "march", "influence") == 4
    # Pay can Pillage London. Restore Yorkist Favour so the Capability denial
    # tests the card's availability with March at a Friendly Locale.
    assert state.locales["london"].favour == "lancastrian"
    for favour in ("neutral", YORK):
        assert _play("parley", by_lord="warwick_yorkist", target="london")["success"]
        assert state.locales["london"].favour == favour
    assert not any(m["type"] == "levy_capability" and m.get("card") == "Y20"
                   for m in legal_moves.legal_moves(state))
    _assert_rejected(state, {"type": "levy_capability", "side": YORK, "by_lord": "march",
                             "card": "Y20"}, "card_in_play")
    _finish_muster(state)
    _assert_parade_expired(state)
    _assert_replay(state)


def test_yorkist_parade_played_during_levy_applies_that_levy():
    state = _second_levy("somersets_return", 2)
    assert state.turn_box == 6 and state.levy_step == "pay"
    attach(state, YORK)
    assert _play("play_held_event", card="Y20")["levy_turn"] == 6
    assert ratings.rating(state, "march", "influence") == 4
    _assert_parade_reserved(state)
    _pay(state)
    _finish_muster(state)
    _assert_parade_expired(state)
    _assert_replay(state)


@pytest.mark.parametrize(("phase", "pile"), [("campaign", "discard"), ("levy", "draw")])
def test_legacy_yorkist_parade_save_reserves_card_on_reload(phase, pile):
    state = _second_levy("somersets_return", 2)
    if phase == "campaign":
        _pay(state)
        _start_campaign(state, first_yorkist="march")
    saved = state.model_dump(mode="json")
    saved["decks"][YORK]["held"].remove("Y20")
    saved["decks"][YORK][pile].append("Y20")
    saved["active_events"].append({"card": "Y20", "side": YORK, "scope": "this_levy"})
    loaded = GameState.model_validate_json(json.dumps(saved))
    _assert_parade_reserved(loaded)
    assert loaded.rng_state == state.rng_state and loaded.history == state.history
    if phase == "campaign":
        assert ratings.rating(loaded, "march", "influence") == 2
        _finish_campaign(loaded)
        _draw_arts(loaded)
    assert ratings.rating(loaded, "march", "influence") == 4
    _assert_parade_reserved(loaded)
    _pay(loaded)
    _finish_muster(loaded)
    _assert_parade_expired(loaded)
