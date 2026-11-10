"""Round 7 Event regressions through the public dispatcher and move catalog."""

from __future__ import annotations

import pytest

from plantagenet import actions, invariants, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus, VassalState, VassalStatus
from scripts import llm_action_help, llm_view
from tests._helpers import queue_drawn_event
from tests.test_cross_game_battle_pools_and_death import position


def _menu(state):
    report = legal_moves.validated_legal_moves(state)
    assert report["rejected"] == []
    return report["moves"]


def _reject(state, move, code):
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, move)
    assert error.value.code == code
    assert state.model_dump_json() == before


def _net_lancaster(state):
    track = state.influence["track"]
    return track.marker_at if track.marker_side == "lancastrian" else -track.marker_at


@pytest.mark.parametrize("extra_spend", [None, 0, 1, 3])
def test_dubious_clarence_offers_decline_and_all_bids(extra_spend):
    state = build_initial_state("warwicks_rebellion", seed=1)
    queue_drawn_event(state, "Y26")
    moves = _menu(state)
    assert [move["decisions"] for move in moves] == [
        {}, {"extra_spend": 0}, {"extra_spend": 1}, {"extra_spend": 3},
    ]
    move = next(move for move in moves if move["decisions"].get("extra_spend") == extra_spend)
    before_dice = state.rng_state
    before_influence = _net_lancaster(state)
    result = actions.apply_action(state, move)
    if extra_spend is None:
        assert "declined" in result["no_effect"]
        assert state.rng_state == before_dice
        assert _net_lancaster(state) == before_influence
        assert state.lords["clarence"].status == LordStatus.MUSTERED
    else:
        assert result["disbanded"] and result["spent"] == 1 + extra_spend
        assert _net_lancaster(state) == before_influence + result["spent"]
        assert state.lords["clarence"].status == LordStatus.CALENDAR
    assert not state.pending_events
    assert invariants.board_invariant_violations(state) == []


def test_dubious_clarence_can_disband_from_an_exile_box():
    state = build_initial_state("warwicks_rebellion", seed=1)
    clarence = state.lords["clarence"]
    clarence.location = None
    clarence.exile_box = next(box for box, side in state.exile_alignment.items()
                             if side == clarence.side)
    queue_drawn_event(state, "Y26")
    check = next(move for move in _menu(state) if move["decisions"] == {"extra_spend": 0})
    assert actions.apply_action(state, check)["disbanded"]
    assert clarence.status == LordStatus.CALENDAR
    assert clarence.calendar_exile and clarence.exile_box is None


def _aragne():
    state = position("warwicks_rebellion", "pembroke", "ludlow", seed=7)
    lord = state.lords["pembroke"]
    lord.vassals = ["dudley", "suffolk"]
    for vid in lord.vassals:
        state.vassals[vid] = VassalState(vassal_id=vid, status=VassalStatus.MUSTERED,
                                         on_lord="pembroke", service_box=4)
    state.campaign = None
    queue_drawn_event(state, "L27")
    return state


def test_aragne_rejects_duplicate_targets_and_spending_by_the_wrong_side():
    state = _aragne()
    select, = _menu(state)
    _reject(state, {**select, "decisions": {"vassals": ["dudley", "dudley"]}}, "bad_targets")
    _reject(state, {**select, "decisions": {"vassals": ["dudley", "hastings"]}}, "bad_vassal")
    _reject(state, {**select, "side": "yorkist", "decisions": {"extra_spend": 0}}, "wrong_side")
    targets = {"vassals": ["dudley", "suffolk"]}
    _reject(state, {**select, "decisions": {**targets, "extra_spend": 1}}, "bad_event_decisions")
    actions.apply_action(state, {**select, "decisions": targets})
    check, *_ = _menu(state)
    _reject(state, {**check, "side": "lancastrian"}, "wrong_side")
    for extra in (None, 2, True):
        _reject(state, {**check, "decisions": {"vassal": "dudley", "extra_spend": extra}},
                "bad_extra_spend")


def test_aragne_york_chooses_before_each_roll_and_replays_after_loading():
    state = _aragne()
    state.decks["lancastrian"]["draw"].remove("L30")
    state.pending_events.append({"card": "L30", "side": "lancastrian"})
    select, = _menu(state)
    assert select["event_choices"]["vassals"] == {
        "available": {"dudley": "pembroke", "suffolk": "pembroke"}, "select": 2,
    }
    before_dice, before_influence = state.rng_state, _net_lancaster(state)
    selected = {**select, "decisions": {"vassals": ["dudley", "suffolk"]}}
    started = actions.apply_action(state, selected)
    assert started["awaiting_side"] == "yorkist"
    assert state.rng_state == before_dice and _net_lancaster(state) == before_influence
    assert state.active_side == "lancastrian" and state.levy_step == "arts_of_war"
    assert llm_view.decision_side(state) == "yorkist"
    assert [e["card"] for e in llm_view.pending_view(state, "yorkist")["events"]] == ["L27"]
    _reject(state, {"type": "play_event", "card": "L30", "side": "lancastrian"}, "event_order")
    zero, one, three = _menu(state)
    assert all(move["side"] == "yorkist" for move in (zero, one, three))
    assert [move["decisions"]["extra_spend"] for move in (zero, one, three)] == [0, 1, 3]
    contract = llm_action_help.contract(state, "play_event", one)
    assert contract["event_choices"] == {"vassal": "dudley", "lord": "pembroke"}
    assert contract["resolver_contract"]["payload_keys_read"] == ["d.extra_spend", "d.vassal"]

    control = GameState.model_validate_json(state.model_dump_json())
    lost, = actions.apply_action(control, zero)["checks"]
    assert (lost["roll"], lost["rating"], lost["disbanded"]) == (3, 2, True)
    assert control.vassals["dudley"].status == VassalStatus.DISBANDED
    result = actions.apply_action(state, one)
    saved, = result["checks"]
    assert (saved["roll"], saved["rating"], saved["disbanded"], saved["spent"]) == (3, 3, False, 2)
    assert result["awaiting_side"] == "yorkist"
    assert "L27" not in state.decks["lancastrian"]["draw"]
    _reject(state, one, "bad_event_target")

    restored = GameState.model_validate_json(state.model_dump_json())
    last = _menu(restored)[2]
    assert last["event_choices"]["vassal"] == "suffolk"
    result = actions.apply_action(state, last)
    assert actions.apply_action(restored, last) == result
    assert restored.model_dump_json() == state.model_dump_json()
    assert result["checks"][1]["rating"] == 5  # Pembroke 2, Suffolk Loyalty 1, spend bonus 2.
    assert result["checks"][1]["spent"] == 4
    assert _net_lancaster(state) == before_influence + 6
    assert state.pending_events == [{"card": "L30", "side": "lancastrian"}]
    assert state.decks["lancastrian"]["draw"].count("L27") == 1
    assert llm_view.decision_side(state) == "lancastrian"
    assert invariants.board_invariant_violations(state) == []


def _rebellion(*targets):
    state = position("warwicks_rebellion", "clarence", "london")
    state.campaign = None
    for loc in ("guildford", "london", "oxford", "rochester", "st_albans"):
        state.locales[loc].favour = "yorkist" if loc in targets else "neutral"
    queue_drawn_event(state, "L29")
    return state


def test_wilful_disobedience_requires_a_distinct_full_selection():
    state = _rebellion("london", "guildford", "rochester")
    state.locales["london"].favour_extra = 1
    move, = _menu(state)
    assert move["event_choices"]["strongholds"] == {
        "available": ["guildford", "london", "rochester"], "remove": 2,
    }
    _reject(state, move, "bad_count")
    for targets in ([], ["guildford"], ["guildford", "guildford"]):
        _reject(state, {**move, "decisions": {"strongholds": targets}}, "bad_count")
    _reject(state, {**move, "decisions": {"strongholds": ["london", "york"]}}, "bad_target")

    targets = ["london", "rochester"]
    result = actions.apply_action(state, {**move, "decisions": {"strongholds": targets}})
    assert result["removed"] == targets
    assert all(state.locales[loc].favour == "neutral" for loc in targets)
    assert state.locales["london"].favour_extra == 0
    assert state.locales["guildford"].favour == "yorkist"
    cities = [state.locales[loc].favour for loc, data in static_data.load_locales().items()
              if data.get("type") == "city"]
    margin = cities.count("yorkist") - cities.count("lancastrian")
    marker = state.influence["track"].stronghold_markers["city"]
    assert marker.at == abs(margin)
    assert marker.side == ("yorkist" if margin >= 0 else "lancastrian")


@pytest.mark.parametrize("targets", [[], ["guildford"], ["guildford", "rochester"]])
def test_wilful_disobedience_menu_resolves_forced_removals(targets):
    state = _rebellion(*targets)
    move, = _menu(state)
    if targets:
        _reject(state, {**move, "decisions": {"strongholds": []}}, "bad_count")
    assert actions.apply_action(state, move)["removed"] == targets
    assert all(state.locales[loc].favour == "neutral" for loc in targets)
