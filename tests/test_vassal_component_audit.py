"""Independent component checks from Plantagenet_1.0.vmod and printed rules.

See VASSAL_AUDIT.md for exact source members and source-priority decisions.
"""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign, legal_moves, ratings
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import CampaignState, LordStatus


@pytest.mark.parametrize("grand", [False, True])
def test_clarence_sets_up_with_printed_assets(grand):
    """1.5.3 / Scenario II (and IIY): Clarence's card lists 2 Prov, 2 Coin, 1 Cart."""
    if grand:
        state = build_initial_state("wars_of_the_roses")
        state.phase = "over"
        state.victory = {"result": "yorkist"}
        state = renew_war(state)
        assert state.grand_scenario["current_war"] == "war_iiy"
    else:
        state = build_initial_state("warwicks_rebellion")
    assert state.lords["clarence"].assets == {"provender": 2, "coin": 2, "cart": 1}


def test_clarence_remusters_with_printed_assets():
    """1.5.3 / 3.4.2: a later Muster also restores Clarence's printed Assets."""
    state = build_initial_state("warwicks_rebellion", seed=1)
    state.levy_step = "muster"
    state.active_side = "lancastrian"
    lord = state.lords["clarence"]
    lord.status = LordStatus.CALENDAR
    lord.calendar_box = state.turn_box
    lord.location = None
    lord.forces = {}
    lord.assets = {}
    state.rng_state = None
    result = actions.apply_action(state, {
        "type": "levy_lord", "side": "lancastrian",
        "by_lord": "warwick_lancastrian", "target": "clarence",
    })
    assert result["success"]
    assert state.lords["clarence"].assets == {"provender": 2, "coin": 2, "cart": 1}


@pytest.mark.parametrize("scenario", ["towton", "my_kingdom_for_a_horse", "bosworth"])
def test_norfolk_printed_command_is_two(scenario):
    """1.5.2 / rulebook p.22: Norfolk has Influence 3, Lordship 3, Command 2, Valour 2."""
    state = build_initial_state(scenario)
    assert ratings.rating(state, "norfolk", "command") == 2


def test_norfolk_activation_cannot_take_a_third_unmodified_command():
    """4.2.2 / p.22: two Command actions exhaust Norfolk's unmodified card."""
    state = build_initial_state("towton")
    # Isolate the printed Command allowance from random first-Levy Capabilities.
    state.levy_step = "done"
    actions.apply_action(state, {"type": "begin_campaign"})
    actions.apply_action(state, {
        "type": "build_plan", "side": "yorkist",
        "plan": [{"lord": "norfolk"}] + [{"pass": True}] * 3,
    })
    actions.apply_action(state, {
        "type": "build_plan", "side": "lancastrian", "plan": [{"pass": True}] * 4,
    })
    assert state.campaign.active_lord == "norfolk"
    assert state.campaign.actions_remaining == 2
    for _ in range(2):
        actions.apply_action(state, {"type": "pass", "side": "yorkist"})
    before = state.model_dump(mode="json")
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(state, {"type": "pass", "side": "yorkist"})
    assert exc.value.code == "no_actions_left"
    assert state.model_dump(mode="json") == before


def test_clarence_waste_restores_two_coin():
    """4.8.5: Waste restores printed Coin, not the former erroneous zero."""
    state = build_initial_state("warwicks_rebellion")
    state.lords["clarence"].assets["coin"] = 7
    campaign._waste(state)
    assert state.lords["clarence"].assets["coin"] == 2


def _march_in_burgundy():
    state = build_initial_state("henry_vi", seed=1)
    lord = state.lords["march"]
    lord.location = None
    lord.exile_box = "burgundy"
    lord.assets = {"ship": 2}
    lord.forces = {"retinue": 1}
    state.phase = "campaign"
    state.active_side = "yorkist"
    state.campaign = CampaignState(step="activation", active_lord="march", actions_remaining=2)
    return state


def test_burgundy_sail_menu_offers_north_sea_ports_only():
    """1.3.1 / 4.6.1 / FAQ 1: Burgundy's arrow points to the North Sea."""
    state = _march_in_burgundy()
    destinations = {m["to"] for m in legal_moves.legal_moves(state)
                    if m["type"] == "sail" and m["to"] in state.locales}
    assert destinations == {"ipswich", "lynn", "ravenspur", "scarborough", "newcastle"}


def test_burgundy_sails_directly_to_ipswich():
    """4.6.1 / D-008: Burgundy and Ipswich share a Sea."""
    state = _march_in_burgundy()
    actions.apply_action(state, {"type": "sail", "side": "yorkist", "to": "ipswich"})
    assert state.lords["march"].location == "ipswich"
    assert state.lords["march"].exile_box is None


def test_burgundy_cannot_sail_directly_to_channel_port():
    """4.6.1 / FAQ 1: Burgundy to Dover must transit at Sea; reject atomically."""
    state = _march_in_burgundy()
    before = state.model_dump(mode="json")
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(state, {"type": "sail", "side": "yorkist", "to": "dover"})
    assert exc.value.code == "cross_sea_port_to_port"
    assert state.model_dump(mode="json") == before


def test_burgundy_supply_uses_north_sea_port():
    """4.5.1: an Exile box uses Ships and a Source Port on the same Sea."""
    state = _march_in_burgundy()
    state.locales["ipswich"].favour = "yorkist"
    actions.apply_action(state, {
        "type": "supply", "side": "yorkist", "source": "ipswich", "use_ships": True,
    })
    assert state.lords["march"].assets["provender"] == 2


def test_burgundy_levy_parley_has_one_way_route_to_ipswich():
    """1.3.1 / 3.4.1: a Ship connects Burgundy to North Sea Ports for Parley."""
    state = _march_in_burgundy()
    state.phase = "levy"
    state.levy_step = "muster"
    result = actions.apply_action(state, {
        "type": "parley", "side": "yorkist", "by_lord": "march", "target": "ipswich",
    })
    assert result["way_cost"] == 1


def test_burgundy_levy_parley_cannot_use_channel_without_great_ships():
    """3.4.1: no direct route from Burgundy to Dover without Great Ships."""
    state = _march_in_burgundy()
    state.phase = "levy"
    state.levy_step = "muster"
    before = state.model_dump(mode="json")
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(state, {
            "type": "parley", "side": "yorkist", "by_lord": "march", "target": "dover",
        })
    assert exc.value.code == "no_route"
    assert state.model_dump(mode="json") == before
