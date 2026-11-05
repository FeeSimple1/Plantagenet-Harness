"""P3-03: the Warden owner selects any subset and any Friendly North refuge."""
from __future__ import annotations

from copy import deepcopy
from itertools import product

import pytest

from plantagenet import actions, battle, reactions, static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordState, LordStatus
from scripts import llm_action_help
from tests.test_cross_game_escape_transport import hold
from tests.test_cross_game_sail import place, position


def warden_position(attacker="york", defenders=("somerset_1", "buckingham")):
    state = position()
    if attacker != "york":
        state.lords[attacker] = LordState(lord_id=attacker, side="yorkist",
                                         status=LordStatus.MUSTERED, forces={"retinue": 1})
        state.campaign.active_lord = attacker
    state.lords[attacker].location = "hexham"
    state.lords[attacker].assets = {}
    state.lords["henry_vi"].location = "london"
    for lid in defenders:
        lord = place(state, lid, "newcastle")
        lord.forces = {"retinue": 1, "men_at_arms": 2}
        lord.assets = {"coin": 2, "cart": 1, "provender": 2}
    for loc, meta in static_data.load_locales().items():
        if meta.get("region") == "north":
            state.locales[loc].favour = "neutral"
    for loc in ("newcastle", "carlisle", "appleby"):
        state.locales[loc].favour = "lancastrian"
    hold(state, "lancastrian", "L16")
    action = {"type": "march", "side": "yorkist", "by_lord": attacker,
              "to": "newcastle", "decisions": {"flee": list(defenders), "warden": True}}
    return state, action


@pytest.mark.parametrize("destinations", list(product([None, "carlisle", "appleby"], repeat=2)))
def test_warden_allows_every_subset_and_independent_destinations(destinations):
    state, action = warden_position()
    chosen = {lid: dest for lid, dest in zip(("somerset_1", "buckingham"), destinations,
                                           strict=True) if dest is not None}
    action["decisions"]["warden_to"] = chosen
    saved = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, action)
    outcome = result["approach"]["battle"]
    assert set(outcome.get("warden_moved", [])) == set(chosen)
    assert outcome.get("warden_to", {}) == chosen
    for lid in ("somerset_1", "buckingham"):
        lord = state.lords[lid]
        if lid in chosen:
            assert lord.status == LordStatus.MUSTERED and lord.location == chosen[lid]
            assert lord.forces == {"retinue": 1, "men_at_arms": 2}
            assert lord.assets == {"coin": 2, "cart": 1, "provender": 2}
        else:
            assert lid in outcome["deaths"] + outcome["disbands"]
    assert state.decks["lancastrian"]["held"] == ([] if chosen else ["L16"])
    assert state.decks["lancastrian"]["discard"] == (["L16"] if chosen else [])
    assert actions.apply_action(saved, action) == result
    assert saved.model_dump_json() == state.model_dump_json()


def test_destination_map_can_request_warden_without_a_redundant_flag():
    state, action = warden_position()
    del action["decisions"]["warden"]
    action["decisions"]["warden_to"] = {"somerset_1": "appleby"}
    result = actions.apply_action(state, action)["approach"]["battle"]
    assert result["warden_moved"] == ["somerset_1"]
    assert state.lords["somerset_1"].location == "appleby"
    assert state.decks["lancastrian"]["discard"] == ["L16"]


def test_legacy_boolean_keeps_its_default_for_all_eligible_lords():
    state, action = warden_position()
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert outcome["warden_moved"] == ["somerset_1", "buckingham"]
    assert {state.lords[lid].location for lid in outcome["warden_moved"]} == {"appleby"}
    assert state.decks["lancastrian"]["discard"] == ["L16"]


@pytest.mark.parametrize("selection", [
    None, ["somerset_1"], {"somerset_1": ["appleby"]}, {"somerset_1": 4},
    {"not_a_lord": "appleby"}, {"york": "carlisle"}, {"exeter_1": "appleby"},
    {"somerset_1": "not_a_locale"}, {"somerset_1": "london"},
    {"somerset_1": "newcastle"}, {"somerset_1": "scarborough"},
])
def test_invalid_warden_choices_reject_atomically_and_allow_valid_retry(selection):
    state, action = warden_position()
    state.locales["london"].favour = "lancastrian"  # Friendly but outside North.
    action["decisions"]["warden_to"] = selection
    before = state.model_dump_json()
    submitted = deepcopy(action)
    lord, assets, history = state.lords["york"], state.lords["york"].assets, state.history
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, action)
    assert error.value.code == "bad_warden_choice"
    assert state.model_dump_json() == before
    assert state.lords["york"] is lord and lord.assets is assets and state.history is history
    assert action == submitted
    control = GameState.model_validate_json(before)
    action["decisions"]["warden_to"] = {"somerset_1": "appleby"}
    assert actions.apply_action(state, action) == actions.apply_action(control, action)
    assert state.model_dump_json() == control.model_dump_json()


def test_enemy_refuge_rejected_even_when_it_is_in_the_north():
    state, action = warden_position()
    state.locales["appleby"].favour = "yorkist"
    action["decisions"]["warden_to"] = {"somerset_1": "appleby"}
    before = state.model_dump_json()
    with pytest.raises(IllegalAction, match="bad_warden_choice"):
        actions.apply_action(state, action)
    assert state.model_dump_json() == before


def test_explicit_choice_still_requires_a_held_warden():
    state, action = warden_position()
    state.decks["lancastrian"]["held"] = []
    del action["decisions"]["warden"]
    action["decisions"]["warden_to"] = {"somerset_1": "appleby"}
    before = state.model_dump_json()
    with pytest.raises(IllegalAction, match="no_warden"):
        actions.apply_action(state, action)
    assert state.model_dump_json() == before


def test_selected_unrouted_lord_does_not_spend_warden():
    state, action = warden_position()
    action["decisions"].update(flee=["york"], warden_to={"somerset_1": "appleby"})
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert not outcome.get("warden_moved")
    assert state.decks["lancastrian"]["held"] == ["L16"]


def test_escape_ship_precedes_warden_and_unselected_lords_do_not_spend_it():
    state, action = warden_position()
    hold(state, "lancastrian", "L3")
    action["decisions"].update(escape_ship=["somerset_1"],
                                warden_to={"somerset_1": "appleby"})
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert outcome["exiles"] == ["somerset_1"] and not outcome.get("warden_moved")
    assert "buckingham" in outcome["deaths"] + outcome["disbands"]
    assert state.decks["lancastrian"]["held"] == ["L16"]


def test_capture_of_the_king_does_not_spend_warden_for_an_unselected_other_lord():
    state, action = warden_position(defenders=("henry_vi", "buckingham"))
    action["decisions"]["warden_to"] = {"henry_vi": "appleby"}
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert outcome["captured"] == [{"lord": "henry_vi", "by": "york"}]
    assert not outcome.get("warden_moved")
    assert "buckingham" in outcome["deaths"] + outcome["disbands"]
    assert state.decks["lancastrian"]["held"] == ["L16"]


def test_bloody_thou_art_blocks_explicit_warden_selection():
    state, action = warden_position(attacker="richard_iii")
    state.lords["richard_iii"].capabilities = ["Y33"]
    action["decisions"]["warden_to"] = {"somerset_1": "appleby"}
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert set(outcome["deaths"]) == {"somerset_1", "buckingham"}
    assert not outcome.get("warden_moved")
    assert state.decks["lancastrian"]["held"] == ["L16"]


def test_empty_troop_mat_still_disbands_after_selected_escape():
    state, action = warden_position(defenders=("somerset_1",))
    state.lords["somerset_1"].forces = {"retinue": 1}
    action["decisions"]["warden_to"] = {"somerset_1": "appleby"}
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert outcome["warden_to"] == {"somerset_1": "appleby"}
    assert outcome["disbands"] == ["somerset_1"]
    assert state.lords["somerset_1"].status == LordStatus.CALENDAR


def test_real_routed_troops_are_removed_from_the_chosen_refuge():
    state, action = warden_position(defenders=("somerset_1",))
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 3, "longbow": 3}
    state.lords["somerset_1"].forces = {
        "retinue": 1, "men_at_arms": 3, "longbow": 3, "militia": 3}
    action["decisions"] = {"warden_to": {"somerset_1": "appleby"}, "valour": False,
                            "absorb_plan": {"defender": [{"unit": "retinue"}] * 6}}
    outcome = actions.apply_action(state, action)["approach"]["battle"]
    assert outcome["warden_moved"] == ["somerset_1"]
    assert state.lords["somerset_1"].location == "appleby"
    assert state.lords["somerset_1"].forces == {"retinue": 1, "men_at_arms": 1}


def test_warden_choices_are_discoverable_in_reactions_and_combat_help():
    state, _ = warden_position()
    choices = next(row for row in reactions.available_battle_reactions(
        state, ["york"], ["somerset_1", "buckingham"], locale="newcastle")
        if row["effect"] == "warden")
    assert choices["warden_options"] == {
        "lords": ["somerset_1", "buckingham"], "destinations": ["appleby", "carlisle"]}
    assert "warden_to" in llm_action_help.COMBAT["parameters"]
    assert battle.WARDEN == "WARDEN OF THE MARCHES"
