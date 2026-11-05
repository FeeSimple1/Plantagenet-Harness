"""P3-01/P3-02: one Escape Ship covers a selection; transport is physical."""
from __future__ import annotations

from copy import deepcopy

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState, LordStatus
from tests.test_cross_game_sail import place, position


def hold(state, side, card):
    for deck in state.decks.values():
        for pile in deck.values():
            while card in pile:
                pile.remove(card)
    state.decks[side]["held"].append(card)


def escape_position(side="yorkist", cards=("Y3",)):
    leader, ally, enemy = (("york", "salisbury", "henry_vi") if side == "yorkist"
                           else ("henry_vi", "somerset_1", "york"))
    state = position(leader)
    state.lords[leader].location = "ely"
    place(state, ally, "ely")
    state.lords[enemy].location = "lynn"
    state.locales["lynn"].favour = side
    for card in cards:
        hold(state, side, card)
    action = {"type": "march", "side": side, "by_lord": leader, "to": "lynn",
              "group": [ally], "decisions": {"flee": [leader, ally],
                                            "escape_ship": [leader, ally]}}
    return state, action, leader, ally


@pytest.mark.parametrize("side,cards", [
    ("yorkist", ("Y3",)), ("yorkist", ("Y9",)),
    ("yorkist", ("Y3", "Y9")), ("lancastrian", ("L3",)),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_one_escape_ship_rescues_every_selected_lord(side, cards, reverse):
    state, action, leader, ally = escape_position(side, cards)
    if reverse:
        action["decisions"]["escape_ship"].reverse()
    restored = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, action)
    battle = result["approach"]["battle"]
    assert set(battle["exiles"]) == {leader, ally}
    assert battle["deaths"] == battle["disbands"] == []
    for lid in (leader, ally):
        lord = state.lords[lid]
        assert lord.status == LordStatus.CALENDAR and lord.calendar_exile
        assert lord.location is None
    assert state.decks[side]["discard"] == [cards[0]]
    assert state.decks[side]["held"] == list(cards[1:])
    assert actions.apply_action(restored, action) == result
    assert restored.model_dump_json() == state.model_dump_json()


def test_escape_ship_respects_subset_and_duplicate_selection():
    state, action, leader, ally = escape_position()
    action["decisions"]["escape_ship"] = [ally, ally]
    battle = actions.apply_action(state, action)["approach"]["battle"]
    assert battle["exiles"] == [ally]
    assert leader in battle["deaths"] + battle["disbands"]
    assert state.decks["yorkist"]["discard"] == ["Y3"]


def test_escape_ship_cannot_be_spent_without_a_friendly_port_route():
    state, action, _, _ = escape_position()
    for locale in state.locales.values():
        locale.favour = "lancastrian"
    battle = actions.apply_action(state, action)["approach"]["battle"]
    assert battle["exiles"] == []
    assert state.decks["yorkist"]["held"] == ["Y3"]
    assert state.decks["yorkist"]["discard"] == []


def test_one_escape_ship_also_covers_england_is_my_home_and_another_lord():
    state, action, leader, ally = escape_position()
    hold(state, "yorkist", "Y8")
    state.decks["yorkist"]["held"].remove("Y8")
    state.lords[leader].capabilities = ["Y8"]
    battle = actions.apply_action(state, action)["approach"]["battle"]
    assert battle["exiles"] == [ally]
    assert battle["disbands"] == [leader] and battle["deaths"] == []
    assert not state.lords[leader].calendar_exile
    assert state.lords[ally].calendar_exile
    assert state.decks["yorkist"]["discard"] == ["Y3", "Y8"]


def transport_position(kind):
    state = position()
    state.lords["york"].assets = {}
    ally = place(state, "salisbury")
    if kind == "ship_supply":
        ally.assets = {"ship": 1}
        state.locales["lynn"].favour = "yorkist"
        action = {"type": "supply", "side": "yorkist", "by_lord": "york",
                  "source": "lynn", "use_ships": True, "share": ["salisbury"]}
    elif kind in ("cart_supply", "march"):
        state.lords["york"].location = ally.location = "ely"
        ally.assets = {"cart": 1}
        state.locales["ely"].favour = state.locales["cambridge"].favour = "yorkist"
        if kind == "cart_supply":
            action = {"type": "supply", "side": "yorkist", "by_lord": "york",
                      "source": "cambridge", "share": ["salisbury"]}
        else:
            state.lords["york"].assets = {"provender": 2}
            action = {"type": "march", "side": "yorkist", "by_lord": "york",
                      "to": "cambridge", "group": ["salisbury"]}
    else:
        state.lords["york"].location = "ely"
        state.lords["york"].assets = {"provender": 2}
        state.lords["henry_vi"].location = "bedford"
        state.lords["henry_vi"].assets = {"provender": 2}
        place(state, "somerset_1", "bedford").assets = {"cart": 1}
        hold(state, "lancastrian", "L2")
        action = {"type": "march", "side": "yorkist", "by_lord": "york",
                  "to": "cambridge", "decisions": {"intercept": "henry_vi",
                    "intercept_group": ["somerset_1"], "flank_attack": True, "flee": ["york"]}}
    return state, action


@pytest.mark.parametrize("kind", ["ship_supply", "cart_supply", "march", "intercept"])
def test_unique_transport_owners_keep_their_real_capacity(kind):
    state, action = transport_position(kind)
    result = actions.apply_action(state, action)
    if kind.endswith("supply"):
        assert result["provender_added"] == 1
        assert state.lords["york"].assets["provender"] == 1
        asset = "ship" if kind == "ship_supply" else "cart"
        assert state.lords["salisbury"].assets == {asset: 1}
    elif kind == "march":
        assert state.lords["york"].assets["provender"] == 1
        assert state.lords["salisbury"].assets == {"cart": 1}
    else:
        assert result["intercept"]["success"]
        assert state.lords["henry_vi"].assets["provender"] == 1
        assert state.lords["somerset_1"].assets == {"cart": 1}


@pytest.mark.parametrize("kind", ["ship_supply", "cart_supply", "march", "intercept"])
@pytest.mark.parametrize("bad", ["duplicate", "self", "non_string", "nested", "string", "dict"])
def test_malformed_transport_lists_reject_atomically_and_allow_valid_retry(kind, bad):
    state, action = transport_position(kind)
    original = deepcopy(action)
    if kind == "intercept":
        parent, key = action["decisions"], "intercept_group"
        leader, donor = "henry_vi", "somerset_1"
    else:
        parent, key = action, "share" if kind.endswith("supply") else "group"
        leader, donor = "york", "salisbury"
    parent[key] = {"duplicate": [donor, donor], "self": [leader],
                   "non_string": [donor, 3], "nested": [[donor]],
                   "string": donor, "dict": {donor: 1}}[bad]
    submitted = deepcopy(action)
    before = state.model_dump_json()
    lord, assets, campaign, history = (state.lords["york"], state.lords["york"].assets,
                                      state.campaign, state.history)
    with pytest.raises(IllegalAction) as error:
        actions.apply_action(state, action)
    assert error.value.code == ("bad_share" if kind.endswith("supply") else "bad_group")
    assert state.model_dump_json() == before
    assert state.lords["york"] is lord and lord.assets is assets
    assert state.campaign is campaign and state.history is history
    assert action == submitted
    control = GameState.model_validate_json(before)
    assert actions.apply_action(state, original) == actions.apply_action(control, original)
    assert state.model_dump_json() == control.model_dump_json()
