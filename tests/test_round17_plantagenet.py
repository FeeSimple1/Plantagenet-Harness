"""Round 17 regressions for Tax Routes and end-Campaign Disembark."""

import pytest

from plantagenet import actions, invariants, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus
from tests._helpers import queue_drawn_event, to_muster
from tests.test_llm_interface import attach, get_id, nv, quiet
from tests.test_naval_blockade_actions import _camp


def _apply(state, kind, **params):
    return actions.apply_action(state, {"type": kind, **params})


def _start_campaign(state, yorkist="york"):
    while state.levy_step == "muster":
        _apply(state, "end_muster", side=state.active_side)
    _apply(state, "begin_campaign")
    passes = [{"pass": True}] * (state.campaign.cards_required - 1)
    for side, lid in (("yorkist", yorkist), ("lancastrian", "henry_vi")):
        _apply(state, "build_plan", side=side, plan=[{"lord": lid}, *passes])


def _bristol_muster(*, capability_on, ships_on, target):
    state = to_muster(build_initial_state("henry_vi", seed=3))
    # Earlier movement and Favour. Levy the actual Ship and Capability publicly.
    for lid in ("york", "march"):
        state.lords[lid].location = "bristol"
    state.locales["bristol"].favour = state.locales[target].favour = "yorkist"
    if capability_on:
        _apply(state, "levy_capability", side="yorkist", by_lord=capability_on, card="Y6")
    if ships_on:
        _apply(state, "levy_transport", side="yorkist", by_lord=ships_on, transport="ship")
    return state


def _reject_unchanged(state, action, code):
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as exc:
        actions.apply_action(state, action)
    assert exc.value.code == code
    assert state.model_dump_json() == before


@pytest.mark.parametrize(("active", "capability_on", "ships_on", "target", "coin"), [
    ("york", "york", "york", "calais", 3),
    ("york", "york", None, "calais", 0),
    ("york", None, "york", "calais", 0),
    ("york", None, None, "harlech", 0),
    ("march", "york", "york", "calais", 3),
    ("march", "march", "york", "calais", 0),
    ("march", None, "york", "harlech", 1),
    ("york", None, "york", "harlech", 1),
])
def test_tax_menu_and_resolution_use_the_selected_ship_owners(
        active, capability_on, ships_on, target, coin):
    state = _bristol_muster(capability_on=capability_on, ships_on=ships_on, target=target)
    _start_campaign(state, yorkist=active)
    action = {"type": "tax", "side": "yorkist", "by_lord": active, "target": target}
    if ships_on and ships_on != active:
        action["share"] = [ships_on]
    before = state.model_dump_json()
    attach(state, "yorkist")
    raw = [m for m in legal_moves.legal_moves(state)
           if m["type"] == "tax" and m.get("target") == target]
    player = [e for e in nv.all_actions()
              if e["action"]["type"] == "tax" and e["action"]["target"] == target]
    if not coin:
        assert not raw and not player
        _reject_unchanged(state, action, "no_route")
        return

    move, = raw
    entry, = player
    assert all(move.get(k) == entry["action"].get(k) == v for k, v in action.items())
    initial_coin = state.lords[active].assets["coin"]
    remaining = state.campaign.actions_remaining
    result = quiet(nv.apply, entry["id"])[0]["result"]
    assert result["success"] and result["spent"] == 1 and result["coin_added"] == coin
    assert state.campaign.actions_remaining == remaining - 1
    assert state.lords[active].assets["coin"] == initial_coin + coin
    assert state.lords[ships_on].assets["ship"] == 1
    assert state.locales[target].depletion == "depleted"

    resumed = GameState.model_validate_json(before)
    attach(resumed, "yorkist")
    assert quiet(nv.apply, get_id("tax", target=target))[0]["result"] == result
    assert resumed.model_dump_json() == state.model_dump_json()
    assert not invariants.board_invariant_violations(state)


@pytest.mark.parametrize("warwick_at", ["pembroke", "dover"])
def test_tax_using_a_shared_great_ship_pauses_for_blockade(warwick_at):
    state, active, _ = _camp(seed=1, warwick_at=warwick_at)
    state.lords[active].assets.pop("ship")
    donor = state.lords["somerset_1"]
    donor.location = "bristol"
    donor.assets["ship"] = 1
    donor.capabilities = ["L6"]
    state.locales["calais"].favour = "lancastrian"
    move, = [m for m in legal_moves.legal_moves(state)
             if m["type"] == "tax" and m["target"] == "calais"]
    assert move["share"] == ["somerset_1"]
    remaining = state.campaign.actions_remaining
    before_influence = state.influence["track"].model_dump()
    before_coin = state.lords[active].assets["coin"]
    pending = actions.apply_action(state, move)
    assert pending["awaiting"]["card"] == "Y15"
    assert state.campaign.actions_remaining == remaining - 1
    resumed = GameState.model_validate_json(state.model_dump_json())
    for current in (state, resumed):
        result = _apply(current, "react", side="yorkist", play="Y15")
        assert result["cancelled"] and result["reactions"][0]["roll"] == 6
        assert current.influence["track"].model_dump() == before_influence
        assert current.lords[active].assets["coin"] == before_coin
        assert current.locales["calais"].depletion is None
    assert state.model_dump_json() == resumed.model_dump_json()


@pytest.mark.parametrize("has_ship", [False, True])
def test_tax_collectors_routes_can_use_a_shared_ship(has_ship):
    state = _bristol_muster(capability_on="york", ships_on="york" if has_ship else None,
                            target="calais")
    queue_drawn_event(state, "Y10")
    move, = legal_moves.legal_moves(state)
    for lid in ("york", "march"):
        targets = move["event_choices"]["tax_targets"].get(lid, [])
        assert ("calais" in targets) == has_ship
    result = _apply(state, "play_event", side="yorkist", card="Y10", decisions={
        "lords": ["march"], "tax_targets": {"march": "calais"},
    })
    if has_ship:
        assert result["taxes"]["march"]["coin"] == 6
        assert state.locales["calais"].depletion == "depleted"
    else:
        assert not result["taxes"]
        assert state.locales["calais"].depletion is None


def test_great_ships_without_a_ship_adds_no_parley_or_supply_route():
    state = _bristol_muster(capability_on="york", ships_on=None, target="calais")
    state.locales["calais"].favour = "neutral"
    parley = {"type": "parley", "side": "yorkist", "by_lord": "york", "target": "calais"}
    assert parley not in legal_moves.legal_moves(state)
    _reject_unchanged(state, parley, "no_route")
    state.locales["calais"].favour = "yorkist"
    _start_campaign(state)
    supply = {"type": "supply", "side": "yorkist", "by_lord": "york", "source": "calais"}
    assert supply not in legal_moves.legal_moves(state)
    _reject_unchanged(state, supply, "no_route")


def _sailors(york_food):
    state = to_muster(build_initial_state("henry_vi", seed=2))
    # Earlier travel, depletion, and expenditure of food before the Sails.
    state.lords["york"].location = "bristol"
    state.lords["henry_vi"].location = "pembroke"
    state.locales["bristol"].favour = "yorkist"
    state.locales["pembroke"].favour = "lancastrian"
    state.locales["pembroke"].depletion = state.locales["harlech"].depletion = "exhausted"
    state.lords["york"].assets["provender"] = york_food
    for side, lid in (("yorkist", "york"), ("lancastrian", "henry_vi")):
        for _ in range(2):
            _apply(state, "levy_transport", side=side, by_lord=lid, transport="ship")
        if side == "yorkist":
            _apply(state, "end_muster", side=side)
    _start_campaign(state)
    for side, lid in (("yorkist", "york"), ("lancastrian", "henry_vi")):
        _apply(state, "sail", side=side, by_lord=lid, to="irish_sea")
        _apply(state, "end_activation", side=side)
    while state.campaign.step == "activation":
        _apply(state, "end_activation", side=state.active_side)
    assert state.lords["york"].assets["provender"] == york_food - 1
    assert state.lords["henry_vi"].assets["provender"] == 0
    return state


def _end_with_landings(state, rebel_port):
    attach(state, "yorkist")
    quiet(nv.stage_reset, {"disembark_land": {"york": rebel_port}},
          expected_version=nv.version())
    quiet(nv.set_perspective, "lancastrian")
    quiet(nv.stage_reset, {"disembark_land": {"henry_vi": "pembroke"}},
          expected_version=nv.version())
    return quiet(nv.apply, get_id("end_campaign"))[0]["result"]["disembark"]


@pytest.mark.parametrize(("york_food", "rebel_port", "king_port"), [
    (1, "pembroke", "pembroke"),
    (2, "pembroke", "bristol"),
    (1, "harlech", "pembroke"),
])
def test_rebel_disembark_feeds_before_the_kings_port_is_checked(york_food, rebel_port, king_port):
    state = _sailors(york_food)
    resumed = GameState.model_validate_json(state.model_dump_json())
    result = _end_with_landings(state, rebel_port)
    assert result["rolls"] == [
        {"lord": "york", "roll": 5, "landed": rebel_port},
        {"lord": "henry_vi", "roll": 5, "landed": king_port},
    ]
    assert result["feed"]["yorkist"]["disbanded"] == (["york"] if york_food == 1 else [])
    assert result["feed"]["lancastrian"]["disbanded"] == (
        ["henry_vi"] if king_port == "pembroke" else [])
    henry = state.lords["henry_vi"]
    assert (henry.status, henry.location) == (
        (LordStatus.CALENDAR, None) if king_port == "pembroke"
        else (LordStatus.MUSTERED, "bristol"))
    assert not invariants.board_invariant_violations(state)
    assert _end_with_landings(resumed, rebel_port) == result
    assert resumed.model_dump_json() == state.model_dump_json()
