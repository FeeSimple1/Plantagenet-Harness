"""Grand-campaign bug regressions, plus negative and cross-War controls.

See fixtures/grand_campaign_2026_10/README.md for snapshot provenance.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from plantagenet import (
    actions,
    battle,
    commands,
    events,
    invariants,
    legal_moves,
    ratings,
    scenarios,
    static_data,
    succession,
)
from plantagenet.errors import IllegalAction
from plantagenet.state import Favour, GameState, LocaleState, LordState, LordStatus, Side

DATA = Path(__file__).parent / "fixtures" / "grand_campaign_2026_10"
RECORDS = json.loads((DATA / "actions.json").read_text())


def before(step):
    return GameState.model_validate_json((DATA / f"before-{step}.json").read_text())


def recorded(step):
    return deepcopy(RECORDS[str(step)])


def reject_unchanged(state, move, code=None):
    old = state.model_dump(mode="json")
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, move)
    if code:
        assert error.value.code == code
    assert state.model_dump(mode="json") == old


# ---- G1: the final War is lost when its last Heir is removed, regardless of Influence.
def test_final_war_roster_recognizes_warwick_as_only_yorkist_heir():
    state = before(1099)
    assert succession._present_heirs(state, "yorkist") == ["warwick_yorkist"]
    assert succession._automatic_victory(state) is None


def test_last_heir_death_immediately_ends_final_war():
    state = before(1099)
    actions.apply_action(state, recorded(1099))
    assert state.lords["warwick_yorkist"].status == "removed"
    assert state.phase == "over" and state.victory["result"] == "lancastrian"
    assert legal_moves.legal_moves(state) == []
    reject_unchanged(state, {"type": "renew_war"})


def test_dead_dynasty_cannot_win_on_influence_counterexample():
    state = before(1099)
    # Controlled score variant, not the observed game score.
    state.influence["track"].marker_at = 25
    state.influence["track"].marker_side = "yorkist"
    for step in (1099, 1100, 1101):
        if state.phase == "over":
            break
        actions.apply_action(state, recorded(step))
    assert state.victory["result"] == "lancastrian"


def final_war(wid, removed=(), gloucester_as_heir=False):
    state = scenarios.build_initial_state("wars_of_the_roses", seed=1)
    state.grand_scenario["current_war"] = "war_iiy"
    state.grand_scenario["gloucester_as_heir_played"] = gloucester_as_heir
    state.turn_box = 1  # eliminate the Natural Causes sum<last-Turn condition
    for lid in removed:
        if lid not in state.lords:
            state.lords[lid] = LordState(lord_id=lid, side=static_data.load_lords()[lid]["side"],
                                        status=LordStatus.REMOVED)
        state.lords[lid].status = LordStatus.REMOVED
    state.victory = {"result": "yorkist" if wid == "war_iiiy" else "lancastrian"}
    state.phase = "over"
    new = scenarios.renew_war(state)
    assert new.grand_scenario["current_war"] == wid
    return new


@pytest.mark.parametrize("wid,removed,expected", [
    ("war_iiiy", [], ["york", "march"]),
    ("war_iiiy", ["york"], ["edward_iv", "rutland"]),
    ("war_iiiy", ["york", "march"], ["rutland", "gloucester_2"]),
    ("war_iiiy", ["york", "march", "rutland"], ["richard_iii"]),
    ("war_iiiy", ["york", "march", "gloucester_1"], ["warwick_yorkist"]),
    ("war_iiil", [], ["york", "march"]),
    ("war_iiil", ["march"], ["york", "rutland"]),
    ("war_iiil", ["march", "rutland"], ["york", "gloucester_1"]),
    ("war_iiil", ["york", "march", "rutland"], ["gloucester_2"]),
    ("war_iiil", ["york", "gloucester_1"], ["warwick_yorkist"]),
])
def test_complete_final_war_yorkist_rosters_and_last_heir_victory(wid, removed, expected):
    state = final_war(wid, removed)
    assert succession._present_heirs(state, "yorkist") == expected
    assert succession._automatic_victory(state) is None
    for i, lid in enumerate(expected):
        battle._kill_lord(state, lid)
        if i + 1 < len(expected):
            assert state.victory is None  # no false victory with the next Heir alive
        else:
            assert state.phase == "over" and state.victory["result"] == "lancastrian"


@pytest.mark.parametrize("wid,removed,expected", [
    ("war_iiiy", [], "margaret"),
    ("war_iiiy", ["margaret"], "henry_tudor"),
    ("war_iiiy", ["margaret", "york"], "warwick_lancastrian"),
    ("war_iiil", [], "henry_vi"),
    ("war_iiil", ["henry_vi"], "margaret"),
    ("war_iiil", ["henry_vi", "margaret", "somerset_1"], "somerset_1"),
])
def test_final_war_lancastrian_heirs(wid, removed, expected):
    state = final_war(wid, removed)
    assert succession._present_heirs(state, "lancastrian") == [expected]
    battle._kill_lord(state, expected)
    assert state.phase == "over" and state.victory["result"] == "yorkist"


def test_captured_heir_is_alive_not_removed():
    state = before(1099)
    state.lords["warwick_yorkist"].status = LordStatus.CAPTURED
    assert succession._automatic_victory(state) is None


# ---- G2: ready Exiles obey the current War, not inherited War-I restrictions.
def ready_second_war_exiles():
    state = GameState.model_validate_json((DATA / "war-iiy-end.json").read_text())
    # The real War ended on Turn 8; this probes the recorded future return date.
    state.phase = "levy"
    state.levy_step = "muster"
    state.turn_box = 10
    state.active_side = "lancastrian"
    state.victory = None
    state.campaign = None
    assert state.exile_alignment == {"burgundy": "yorkist", "france": "lancastrian"}
    assert state.lords["jasper_tudor_1"].calendar_exile
    assert state.lords["jasper_tudor_1"].calendar_box == 10
    return state


def test_later_war_jasper_exile_return_is_offered():
    state = ready_second_war_exiles()
    assert any(m["type"] == "muster_exiles" and "jasper_tudor_1" in m.get("lords", [])
               for m in legal_moves.legal_moves(state))


@pytest.mark.parametrize("lid", ["jasper_tudor_1", "henry_vi"])
def test_later_war_exiles_return_to_current_friendly_box(lid):
    state = ready_second_war_exiles()
    actions.apply_action(state, {"type": "muster_exiles", "side": "lancastrian", "lords": [lid]})
    assert state.lords[lid].exile_box == "france"
    assert state.lords[lid].status == LordStatus.MUSTERED


@pytest.mark.parametrize("scenario,lid,box", [
    ("henry_vi", "henry_vi", "scotland"),
    ("henry_vi", "york", "ireland"),
    ("wars_of_the_roses", "margaret", "france"),
    ("wars_of_the_roses", "warwick_yorkist", "burgundy"),
])
def test_allied_network_restrictions_still_apply_in_first_war(scenario, lid, box):
    state = scenarios.build_initial_state(scenario)
    if lid not in state.lords:  # Margaret enters War I through Succession.
        state.lords[lid] = LordState(lord_id=lid, side=static_data.load_lords()[lid]["side"],
                                    status=LordStatus.CALENDAR, calendar_box=2)
    assert actions._exile_destinations(state, lid) == [box]
    state.exile_alignment[box] = "neutral"
    assert actions._exile_destinations(state, lid) == []


@pytest.mark.parametrize("wid", ["war_iiiy", "war_iiil"])
def test_renewed_war_does_not_inherit_old_networks(wid):
    state = final_war(wid)
    assert state.grand_scenario["allied_networks"] == {}
    assert actions._allied_networks(state) == {}
    assert actions._exile_destinations(state, "jasper_tudor_2") == ["france"]


@pytest.mark.parametrize("kind", ["enemy", "unmarked", "early", "wrong_side", "duplicate"])
def test_illegal_exile_returns_reject_atomically(kind):
    state = ready_second_war_exiles()
    move = {"type": "muster_exiles", "side": "lancastrian", "lords": ["jasper_tudor_1"]}
    if kind in ("enemy", "unmarked"):
        move["exile_boxes"] = {"jasper_tudor_1": "burgundy" if kind == "enemy" else "scotland"}
    elif kind == "early":
        state.turn_box = 9
        assert not any(m["type"] == "muster_exiles" and "jasper_tudor_1" in m.get("lords", [])
                       for m in legal_moves.legal_moves(state))
    elif kind == "wrong_side":
        move["side"] = "yorkist"
    else:
        move["lords"] *= 2
    reject_unchanged(state, move)


def test_multiple_friendly_return_boxes_are_explicit_choices():
    state = ready_second_war_exiles()
    # Synthetic alignment to exercise the general multiple-destination interface.
    state.exile_alignment["scotland"] = "lancastrian"
    moves = [m for m in legal_moves.legal_moves(state)
             if m["type"] == "muster_exiles" and m["lords"] == ["jasper_tudor_1"]]
    assert {m["exile_boxes"]["jasper_tudor_1"] for m in moves} == {"france", "scotland"}
    reject_unchanged(state, {"type": "muster_exiles", "side": "lancastrian",
                             "lords": ["jasper_tudor_1"]}, "bad_exile_box")
    for move in moves:
        copy = state.model_copy(deep=True)
        actions.apply_action(copy, move)
        assert copy.lords["jasper_tudor_1"].exile_box == move["exile_boxes"]["jasper_tudor_1"]


# ---- G3: JSON and Python arrays are equivalent; malformed input is atomic.
def battle_action(json_keys=True):
    move = recorded(80)
    move.setdefault("decisions", {})["attacker_positions"] = {1: "york", 0: "salisbury"}
    move["decisions"]["defender_positions"] = {1: "somerset_1"}
    return json.loads(json.dumps(move)) if json_keys else move


def test_python_integer_key_battle_array_control():
    state = before(80)
    result = actions.apply_action(state, battle_action(False))
    assert result["approach"]["battle"]["winner_side"] == "yorkist"


def test_same_battle_array_survives_json_serialization():
    state = before(80)
    control = state.model_copy(deep=True)
    expected = actions.apply_action(control, battle_action(False))
    result = actions.apply_action(state, battle_action(True))
    assert result == expected
    assert state.model_dump(mode="json", exclude={"history"}) == control.model_dump(
        mode="json", exclude={"history"})


@pytest.mark.parametrize("positions", [
    None, [], {"left": "york"}, {"3": "york"}, {-1: "york"}, {True: "york"}, {1.0: "york"},
    {"1": "missing_lord"}, {"1": "somerset_1"}, {"1": "york", "0": "york"},
    {1: "york", "1": "salisbury"}, {"1": ["york"]},
])
def test_invalid_battle_arrays_reject_without_state_or_rng_changes(positions):
    state = before(80)
    move = battle_action()
    move["decisions"]["attacker_positions"] = positions
    reject_unchanged(state, move, "bad_battle_array")


# ---- G4: a drawn duration Event must acquire its player-chosen target.
def test_loyalty_and_trust_draw_must_request_a_target():
    state = before(43)
    result = actions.apply_action(state, recorded(43))
    assert "Y22" in result["pending"]
    assert {"card": "Y22", "side": "yorkist"} in state.pending_events
    assert not any(e["card"] == "Y22" for e in state.active_events)
    moves = legal_moves.legal_moves(state)
    assert all(m["type"] == "play_event" and m["card"] == "Y22" for m in moves)
    assert {m["decisions"]["target"] for m in moves} == set(
        events.loyalty_and_trust_targets(state, "yorkist"))
    assert not invariants.board_invariant_violations(state)
    reject_unchanged(state, {"type": "draw", "side": "lancastrian"})


def test_loyalty_and_trust_all_menu_choices_apply_bonus_and_expire():
    state = before(43)
    actions.apply_action(state, recorded(43))
    for move in legal_moves.legal_moves(state):
        copy = state.model_copy(deep=True)
        old_rng = copy.rng_state
        lid = move["decisions"]["target"]
        old = ratings.rating(copy, lid, "lordship")
        actions.apply_action(copy, move)
        assert ratings.rating(copy, lid, "lordship") == old + 3
        assert copy.rng_state == old_rng
        assert not copy.pending_events
        assert not invariants.board_invariant_violations(copy)
        events.expire_scope(copy, "this_levy")
        assert ratings.rating(copy, lid, "lordship") == old
        assert not invariants.board_invariant_violations(copy)


@pytest.mark.parametrize("target", [None, "henry_vi", "missing_lord", ["york"]])
def test_loyalty_and_trust_rejects_invalid_targets(target):
    state = before(43)
    actions.apply_action(state, recorded(43))
    reject_unchanged(state, {"type": "play_event", "side": "yorkist", "card": "Y22",
                             "decisions": {"target": target}}, "bad_event_target")


def test_loyalty_and_trust_pending_choice_survives_save_load():
    state = before(43)
    actions.apply_action(state, recorded(43))
    loaded = GameState.model_validate_json(state.model_dump_json())
    move = legal_moves.legal_moves(state)[0]
    assert actions.apply_action(state, move) == actions.apply_action(loaded, move)
    assert state.model_dump(mode="json") == loaded.model_dump(mode="json")


def test_loyalty_and_trust_no_lords_resolves_without_deadlock():
    state = before(43)
    for lord in state.lords.values():
        if lord.side == "yorkist":
            lord.status = LordStatus.REMOVED
    actions.apply_action(state, recorded(43))
    moves = legal_moves.legal_moves(state)
    assert len(moves) == 1
    result = actions.apply_action(state, moves[0])
    assert result["no_effect"]
    assert not state.pending_events


# ---- G5: all legal adjacent Levy targets appear, even when the origin is Exhausted.
def commission_moves(state):
    return [m for m in legal_moves.legal_moves(state)
            if m["type"] == "levy_troops" and m["by_lord"] == "henry_vi"]


def test_commission_of_array_remote_levy_is_in_menu():
    state = before(177)
    assert state.locales["gloucester"].depletion == "exhausted"
    assert recorded(177) in commission_moves(state)
    for move in commission_moves(state):
        actions.apply_action(state.model_copy(deep=True), move)


def test_commission_of_array_remote_executor_control():
    state = before(177)
    old = dict(state.lords["henry_vi"].forces)
    result = actions.apply_action(state, recorded(177))
    assert result["locale"] == "hereford"
    assert state.locales["hereford"].depletion == "exhausted"
    assert sum(state.lords["henry_vi"].forces.values()) == sum(old.values()) + 2


@pytest.mark.parametrize("invalid", ["exhausted", "enemy_favour", "neutral", "enemy_lord",
                                   "no_capability", "no_lordship", "not_friendly"])
def test_commission_of_array_invalid_targets_not_offered(invalid):
    state = before(177)
    lord = state.lords["henry_vi"]
    if invalid == "exhausted":
        state.locales["hereford"].depletion = "exhausted"
    elif invalid in ("enemy_favour", "neutral"):
        state.locales["hereford"].favour = "yorkist" if invalid == "enemy_favour" else "neutral"
    elif invalid == "enemy_lord":
        state.lords["york"].status = LordStatus.MUSTERED
        state.lords["york"].location = "hereford"
    elif invalid == "no_capability":
        lord.capabilities = []
    elif invalid == "no_lordship":
        lord.lordship_spent = 99
    else:
        state.locales["gloucester"].favour = "neutral"
    assert recorded(177) not in commission_moves(state)
    reject_unchanged(state, recorded(177))


def test_free_stanley_levy_can_use_commission_target():
    state = before(177)
    lord = state.lords["henry_vi"]
    # Capability interaction boundary fixture, not a historical playthrough claim.
    lord.special_vassals.append("thomas_stanley")
    lord.lordship_spent = ratings.rating(state, "henry_vi", "lordship")
    old = lord.lordship_spent
    assert recorded(177) in commission_moves(state)
    actions.apply_action(state, recorded(177))
    assert lord.lordship_spent == old and lord.free_troops_used


# ---- G6: enum representations may not make save/load change results or history.
def test_save_load_does_not_change_logged_favour_transition():
    fresh = scenarios.build_initial_state("wars_of_the_roses", 20261010)
    loaded = GameState.model_validate_json(fresh.model_dump_json())
    for step in range(18):
        assert actions.apply_action(fresh, recorded(step)) == actions.apply_action(loaded,
                                                                                recorded(step))
    assert fresh.model_dump(mode="json") == loaded.model_dump(mode="json")


def test_favour_default_is_canonical_and_manual_enum_assignment_formats_identically():
    assert type(LocaleState().favour) is str
    for fav in Favour:
        for side in Side:
            assert commands._fav_desc("london", fav, side) == commands._fav_desc(
                "london", fav.value, side.value)


def test_rising_wages_does_not_charge_its_own_lancastrian_side():
    state = before(177)
    state.active_events.append({"card": "L9", "side": "lancastrian", "scope": "this_levy"})
    state.lords["henry_vi"].assets["coin"] = 0
    assert recorded(177) in commission_moves(state)
    actions.apply_action(state, recorded(177))


def test_complete_corrected_grand_campaign_and_saved_state_replay():
    """Both transitions, all results/states, and immediate final-Heir victory.

    The 1102 original actions are unchanged. One newly required Y22 choice
    (March) is an explicit additional test input before original action 44.
    The last two old actions must be unnecessary after immediate victory.
    """
    fresh = scenarios.build_initial_state("wars_of_the_roses", 20261010)
    loaded = GameState.model_validate_json(fresh.model_dump_json())
    records = [json.loads(line)
               for line in (DATA / "campaign-actions.jsonl").read_text().splitlines()]
    moves = records[:44] + [{"type": "play_event", "side": "yorkist", "card": "Y22",
                             "decisions": {"target": "march"}}] + records[44:1100]
    assert len(records) == 1102 and len(moves) == 1101
    assert sum(m["type"] == "renew_war" for m in moves) == 2
    for index, move in enumerate(moves):
        result = actions.apply_action(fresh, deepcopy(move))
        assert actions.apply_action(loaded, deepcopy(move)) == result, index
        assert fresh.model_dump(mode="json", exclude={"history"}) == loaded.model_dump(
            mode="json", exclude={"history"}), index
        assert invariants.board_invariant_violations(fresh) == [], index
    assert fresh.grand_scenario["current_war"] == "war_iiil"
    assert fresh.lords["warwick_yorkist"].status == LordStatus.REMOVED
    assert fresh.phase == "over" and fresh.victory["result"] == "lancastrian"
    assert "Automatic War Victory" in fresh.victory["rule"]
    assert legal_moves.legal_moves(fresh) == []
    assert fresh.model_dump(mode="json") == loaded.model_dump(mode="json")
    for action in records[1100:]:
        reject_unchanged(fresh, action, "game_over")
    reject_unchanged(fresh, {"type": "concede", "side": "lancastrian"}, "game_over")
