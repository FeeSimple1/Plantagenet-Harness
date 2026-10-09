"""Rules regressions from the Plantagenet command/levy audit."""

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import CampaignState


def _campaign(actor="york", scenario="henry_vi"):
    state = build_initial_state(scenario, seed=1)
    state.phase = "campaign"
    state.levy_step = "done"
    state.active_side = state.lords[actor].side
    state.campaign = CampaignState(step="activation", active_lord=actor, actions_remaining=2)
    state.rng_state = None
    return state


def _do(state, action_type, **kwargs):
    return actions.apply_action(state, {
        "type": action_type, "side": state.active_side,
        "by_lord": state.campaign.active_lord, **kwargs,
    })


def test_exiled_lord_cannot_levy_to_seat():
    """Errata FAQ #3: Exiled Lords must Muster in their Exile box (3.3.1)."""
    state = build_initial_state("henry_vi", seed=1)
    state.levy_step = "muster"
    state.active_side = "yorkist"
    state.lords["salisbury"].calendar_box = state.turn_box
    state.lords["salisbury"].calendar_exile = True
    with pytest.raises(IllegalAction, match="target_in_exile"):
        actions.apply_action(state, {"type": "levy_lord", "side": "yorkist",
                                     "by_lord": "york", "target": "salisbury"})
    assert state.lords["salisbury"].calendar_exile
    assert state.lords["salisbury"].location is None


def test_intercept_reinforces_an_existing_defender():
    """4.3.4: Intercept may reinforce a Stronghold that is already an Approach."""
    state = _campaign()
    state.lords["henry_vi"].location = "cambridge"
    state.lords["somerset_1"].location = "bedford"
    result = _do(state, "march", to="cambridge", decisions={
        "intercept": "somerset_1",
        "responses": {"henry_vi": "exile", "somerset_1": "exile"},
    })
    assert result["intercept"]["success"]
    assert result["intercept"]["roll"] == 2
    assert set(result["approach"]["exiles"]) == {"henry_vi", "somerset_1"}


def test_uncontested_port_march_adds_burgundians_immediately():
    """Y14 Burgundians: first arrival at any Port immediately adds 2 Handgunners."""
    state = _campaign()
    state.lords["york"].capabilities = ["Y14"]
    _do(state, "march", to="lynn")
    assert state.lords["york"].forces["handgunners"] == 2
    _do(state, "march", to="ely")
    assert state.lords["york"].forces["handgunners"] == 2


def test_uncontested_port_march_opens_rebel_supply_depot_window():
    """L28: Rebel Supply Depot may be played immediately after March to a Port."""
    state = _campaign("henry_tudor", "my_kingdom_for_a_horse")
    lord = state.lords["henry_tudor"]
    lord.location = "ely"
    lord.exile_box = None
    state.decks["lancastrian"]["held"] = ["L28"]
    _do(state, "march", to="lynn")
    before = lord.assets["provender"]
    actions.apply_action(state, {"type": "play_held_event", "side": "lancastrian",
                                 "card": "L28", "decisions": {"lords": ["henry_tudor"]}})
    assert lord.assets["provender"] == before + 4
    assert lord.ignore_next_feed


@pytest.mark.parametrize("owner, expected", [("york", 1), ("march", 2)])
def test_supply_shared_great_ships_belong_to_owner(owner, expected):
    """Y6/L6: only the owner's Ships count double, including when Shared out."""
    state = _campaign()
    state.lords["york"].location = state.lords["march"].location = "lynn"
    state.locales["lynn"].favour = "yorkist"
    state.lords["york"].assets = {"ship": 0}
    state.lords["march"].assets = {"ship": 1}
    state.lords[owner].capabilities = ["Y6"]
    result = _do(state, "supply", source="lynn", use_ships=True, share=["march"])
    assert result["provender_added"] == expected
    assert state.lords["march"].assets["ship"] == 1


@pytest.mark.parametrize("owner, expected", [("henry_vi", 1), ("somerset_1", 2)])
def test_supply_shared_hay_wains_belong_to_owner(owner, expected):
    """L8 Hay Wains: only the owner's Carts count double, including when Shared."""
    state = _campaign("henry_vi")
    state.lords["henry_vi"].location = state.lords["somerset_1"].location = "york"
    state.locales["york"].favour = state.locales["lincoln"].favour = "lancastrian"
    state.lords["henry_vi"].assets = {"cart": 0}
    state.lords["somerset_1"].assets = {"cart": 1}
    state.lords[owner].capabilities = ["L8"]
    result = _do(state, "supply", source="lincoln", share=["somerset_1"])
    assert result["provender_added"] == expected


@pytest.mark.parametrize("owner, allowed", [("york", False), ("march", True)])
@pytest.mark.parametrize("group", [False, True])
def test_sail_shared_great_ships_belong_to_owner(owner, allowed, group):
    """4.6.1/Y6: borrowed or Group Ships retain only their owner's capacity bonus."""
    state = _campaign()
    state.lords["york"].location = state.lords["march"].location = "lynn"
    state.lords["york"].assets = {"ship": 0}
    state.lords["march"].assets = {"ship": 1}
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 6}
    state.lords["march"].forces = {"retinue": 1, "men_at_arms": 1}
    state.lords[owner].capabilities = ["Y6"]
    passengers = {"group" if group else "share": ["march"]}
    if allowed:
        _do(state, "sail", to="ipswich", **passengers)
        assert state.lords["york"].location == "ipswich"
        assert state.lords["march"].location == ("ipswich" if group else "lynn")
    else:
        with pytest.raises(IllegalAction, match="insufficient_ships"):
            _do(state, "sail", to="ipswich", **passengers)


def test_intercept_group_haul_shares_hay_wains_carts():
    """4.3.2/.4 and L8: Intercept uses Group Sharing and Hay Wains for Haul."""
    state = _campaign()
    state.lords["henry_vi"].location = state.lords["somerset_1"].location = "bedford"
    state.lords["henry_vi"].assets = {"cart": 0, "provender": 2}
    state.lords["somerset_1"].assets = {"cart": 1, "provender": 0}
    state.lords["somerset_1"].capabilities = ["L8"]
    state.lords["york"].assets = {"cart": 0, "provender": 0}
    state.decks["lancastrian"]["held"] = ["L2"]
    _do(state, "march", to="cambridge", decisions={
        "intercept": "henry_vi", "intercept_group": ["somerset_1"],
        "flank_attack": True, "responses": {"york": "exile"},
    })
    assert state.lords["henry_vi"].assets["provender"] == 2
    assert state.lords["henry_vi"].location == "cambridge"
    assert state.lords["somerset_1"].location == "cambridge"


@pytest.mark.parametrize("favour, occupied", [
    ("neutral", False), ("lancastrian", False), ("yorkist", True),
])
def test_sea_supply_requires_friendly_enemy_free_source(favour, occupied):
    """4.5/.1: a Port Supply Source is Friendly and Enemy-free even when used by Sea."""
    state = _campaign()
    state.lords["york"].location = "ipswich"
    state.locales["ipswich"].favour = "yorkist"
    state.lords["york"].assets["ship"] = 1
    state.locales["lynn"].favour = favour
    if occupied:
        state.lords["henry_vi"].location = "lynn"
    with pytest.raises(IllegalAction, match="no_route"):
        _do(state, "supply", source="lynn", use_ships=True)


def test_cancelled_approach_keeps_earlier_moved_marker():
    """L15 King's Parley: movement before the canceled Approach still requires Feed."""
    state = _campaign()
    state.lords["henry_vi"].location = "st_albans"
    state.lords["henry_vi"].capabilities = ["L15"]
    _do(state, "march", to="cambridge")
    _do(state, "march", to="st_albans")
    # The pre-Approach marker survives a saved and resumed reaction, too.
    state = type(state).model_validate_json(state.to_json())
    actions.apply_action(state, {"type": "react", "side": "lancastrian", "play": "L15"})
    assert state.lords["york"].location == "cambridge"
    assert state.lords["york"].moved_fought
    assert state.campaign.actions_remaining == 0
