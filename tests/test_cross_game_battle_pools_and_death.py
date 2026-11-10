"""Fourth-audit public regressions for Battle troop pools and Death Events."""
from __future__ import annotations

from copy import deepcopy

import pytest

from plantagenet import actions, invariants, legal_moves, static_data
from plantagenet.errors import IllegalAction
from plantagenet.rng import DiceRoller
from plantagenet.scenarios import build_initial_state
from plantagenet.state import CampaignState, GameState, LordStatus, VassalState, VassalStatus
from scripts import llm_action_help, llm_view
from tests.test_cross_game_escape_transport import hold
from tests.test_cross_game_sail import place


def position(scenario, leader, origin, *, seed=1):
    state = build_initial_state(scenario, seed=seed)
    for lord in state.lords.values():
        lord.status = LordStatus.CALENDAR
        lord.calendar_box = 9
        lord.location = lord.exile_box = lord.at_sea = None
        lord.assets = {}
        lord.forces = {}
        lord.capabilities = []
        lord.vassals = []
        lord.special_vassals = []
        lord.moved_fought = False
    state.pending = []
    state.pending_events = []
    state.active_events = []
    state.phase = "campaign"
    state.levy_step = "done"
    for deck in state.decks.values():
        deck["draw"].extend(deck["held"])
        deck["held"] = []
    state.active_side = place(state, leader, origin).side
    state.lords[leader].forces["militia"] = 1
    state.campaign = CampaignState(
        step="activation", cards_required=1, active_lord=leader, actions_remaining=3,
        plans={state.active_side: [{"lord": leader}]},
        plan_built={"yorkist": True, "lancastrian": True},
    )
    state.store_dice(DiceRoller(seed))
    return state


def capability(state, lid, card):
    hold(state, state.lords[lid].side, card)
    state.decks[state.lords[lid].side]["held"].remove(card)
    state.lords[lid].capabilities.append(card)


def march(state, dest, **decisions):
    return {"type": "march", "side": state.active_side, "to": dest,
            "by_lord": state.campaign.active_lord, "decisions": decisions}


def fight(state, action):
    result = actions.apply_action(state, action)["approach"]["battle"]
    assert invariants.board_invariant_violations(state) == []
    return result


@pytest.mark.parametrize(("maa", "longbow", "missile", "melee"), [
    (0, 0, 1, 3), (1, 1, 3, 5), (2, 1, 3, 6),
])
def test_battle_troop_capability_uses_only_available_pieces(maa, longbow, missile, melee):
    state = position("henry_vi", "york", "ely")
    place(state, "henry_vi", "cambridge").forces["militia"] = 1
    pools = static_data.load_forces()
    remote = place(state, "salisbury", "london")
    remote.forces.update(men_at_arms=pools["men_at_arms"]["pool"] - maa,
                         longbow=pools["longbow"]["pool"] - longbow)
    state.locales["cambridge"].favour = "yorkist"
    capability(state, "york", "Y3")
    result = fight(state, march(state, "cambridge", valour=False))
    strikes = result["rounds"][0]["engagements"][0]["strikes"]
    assert [row["attacker_hits"] for row in strikes] == [missile, melee]
    assert not state.lords["york"].forces.get("longbow")
    assert not state.lords["york"].forces.get("men_at_arms")


def test_defender_and_attacker_share_the_last_longbow_piece():
    state = position("warwicks_rebellion", "pembroke", "gloucester")
    place(state, "jasper_tudor_1", "cardiff").forces["militia"] = 1
    remote = place(state, "edward_iv", "london")
    remote.forces["longbow"] = static_data.load_forces()["longbow"]["pool"] - 1
    capability(state, "pembroke", "Y25")
    capability(state, "jasper_tudor_1", "L25")
    result = fight(state, march(state, "cardiff", valour=False))
    missile = result["rounds"][0]["engagements"][0]["strikes"][0]
    assert (missile["attacker_hits"], missile["defender_hits"]) == (1, 3)


@pytest.mark.parametrize("flee", [False, True])
def test_warden_keeps_only_unrouted_vassals(flee):
    state = position("henry_vi", "york", "hexham", seed=3)
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 2, "longbow": 2}
    lord = place(state, "somerset_1", "newcastle")
    lord.forces = {"retinue": 1, "men_at_arms": 5, "longbow": 3, "militia": 3}
    lord.assets = {"coin": 2, "cart": 1, "provender": 2}
    lord.vassals = ["oxford"]
    vassal = VassalState(vassal_id="oxford", status=VassalStatus.MUSTERED,
                         on_lord="somerset_1", service_box=6)
    state.vassals["oxford"] = vassal
    state.locales["newcastle"].favour = state.locales["appleby"].favour = "lancastrian"
    hold(state, "lancastrian", "L16")
    action = march(state, "newcastle", warden_to={"somerset_1": "appleby"}, valour=False)
    if flee:
        action["decisions"]["flee"] = ["somerset_1"]
    else:
        action["decisions"]["absorb_plan"] = {
            "defender": [{"unit": "vassal"}, {"unit": "retinue"}] * 3,
        }
    result = fight(state, action)
    assert result["warden_to"] == {"somerset_1": "appleby"}
    assert lord.status == LordStatus.MUSTERED and lord.location == "appleby"
    if flee:
        assert lord.vassals == ["oxford"] and vassal.status == VassalStatus.MUSTERED
        assert vassal.on_lord == "somerset_1" and vassal.service_box == 6
        assert not result.get("vassal_disbands")
    else:
        rolls = [roll for row in result["rounds"] for e in row["engagements"]
                 for strike in e["strikes"] for roll in strike["defender_rolls"]]
        assert any(roll.get("vassal") == "oxford" and not roll["saved"] for roll in rolls)
        assert result["vassal_disbands"] == ["oxford"]
        assert lord.vassals == [] and vassal.status == VassalStatus.DISBANDED
        assert vassal.on_lord is None
        assert vassal.service_box == state.turn_box + 6 - static_data.load_vassals()[
            "regular"]["oxford"]["service"]


def talbot_position(*, card=True):
    state = position("my_kingdom_for_a_horse", "richard_iii", "ely", seed=5)
    for lid in ("henry_tudor", "oxford"):
        place(state, lid, "cambridge").forces["militia"] = 1
    if card:
        hold(state, "lancastrian", "L36")
    action = march(state, "cambridge", flee=["henry_tudor", "oxford"])
    return state, action


@pytest.mark.parametrize(("selection", "deaths", "saved"), [
    (False, ["henry_tudor"], []),
    ([], ["henry_tudor"], []),
    (["henry_tudor"], ["oxford"], ["henry_tudor"]),
    (["oxford"], ["henry_tudor"], ["oxford"]),
    (["oxford", "henry_tudor"], [], ["henry_tudor", "oxford"]),
    (True, [], ["henry_tudor", "oxford"]),
])
def test_talbot_saves_only_the_elected_lords_and_replays(selection, deaths, saved):
    state, action = talbot_position()
    action["decisions"]["talbot"] = selection
    restored = GameState.model_validate_json(state.model_dump_json())
    result = fight(state, action)
    assert result["deaths"] == deaths
    assert result.get("talbot_disbands", []) == saved
    assert set(result["disbands"]) == {"henry_tudor", "oxford"} - set(deaths)
    assert state.decks["lancastrian"]["held"] == ([] if saved else ["L36"])
    assert state.decks["lancastrian"]["discard"].count("L36") == int(bool(saved))
    assert fight(restored, action) == result
    assert restored.model_dump_json() == state.model_dump_json()


@pytest.mark.parametrize("selection", [
    ["henry_tudor", "henry_tudor"], ["richard_iii"], ["jasper_tudor_2"],
    [["oxford"]], {"oxford": True}, "oxford", 1,
])
def test_talbot_rejects_invalid_selections_atomically(selection):
    state, action = talbot_position()
    action["decisions"]["talbot"] = selection
    before, submitted = state.model_dump_json(), deepcopy(action)
    with pytest.raises(IllegalAction, match="bad_talbot_choice"):
        fight(state, action)
    assert state.model_dump_json() == before
    assert action == submitted


def test_talbot_keeps_the_card_when_only_an_unselected_lord_faces_death():
    state, action = talbot_position()
    action["decisions"] = {"flee": ["richard_iii", "oxford"], "talbot": ["henry_tudor"]}
    result = fight(state, action)
    assert result["winner_side"] == "lancastrian" and "oxford" in result["deaths"]
    assert state.decks["lancastrian"]["held"] == ["L36"]
    assert not result.get("talbot_disbands")


def test_nonempty_talbot_selection_requires_the_held_event():
    state, action = talbot_position(card=False)
    action["decisions"]["talbot"] = ["henry_tudor"]
    before = state.model_dump_json()
    with pytest.raises(IllegalAction, match="no_talbot"):
        fight(state, action)
    assert state.model_dump_json() == before
    action["decisions"]["talbot"] = []
    assert fight(state, action)["deaths"] == ["henry_tudor"]


def test_talbot_choices_are_discoverable_without_revealing_the_enemy_hold():
    state, _ = talbot_position()
    move = next(move for move in legal_moves.legal_moves(state)
                if move["type"] == "march" and move["to"] == "cambridge")
    assert not llm_view.action_view(move, "yorkist", state)["battle_reactions"]
    options = llm_view.action_view(move, "lancastrian", state)["battle_reactions"]
    assert options[0]["talbot_options"] == {"lords": ["henry_tudor", "oxford"]}
    assert "list" in llm_action_help.COMBAT["talbot"]


def death_order_position():
    state = position("henry_vi", "york", "ely", seed=5)
    place(state, "salisbury", "ely").forces["militia"] = 1
    for lid in ("somerset_1", "northumberland_lancastrian"):
        place(state, lid, "cambridge").forces["militia"] = 1
    move = next(m for m in legal_moves.legal_moves(state)
                if m["type"] == "march" and m["to"] == "cambridge"
                and m.get("group") == ["salisbury"])
    return state, move


@pytest.mark.parametrize("choose_priorities", [False, True])
def test_death_order_prioritizes_each_faction_with_defenders_first(choose_priorities):
    state, move = death_order_position()
    defenders = ["somerset_1", "northumberland_lancastrian"]
    attackers = ["york", "salisbury"]
    options = {"lancastrian": defenders, "yorkist": attackers}
    assert move["death_order_options"] == options
    help_info = llm_action_help.contract(state, "march", move)
    assert help_info["death_order_options"] == options
    assert "Defenders roll before Attackers" in help_info["combat"]["death_order"]
    choices = {"flee": defenders + attackers, "valour": False}
    if choose_priorities:
        # Put the attacker's key first and leave both lists partial.
        choices["death_order"] = {"yorkist": ["salisbury"],
                                  "lancastrian": ["northumberland_lancastrian"]}
        defenders.reverse()
        attackers.reverse()
    action = {**move, "decisions": choices}
    restored = GameState.model_validate_json(state.model_dump_json())
    result = fight(state, action)
    assert result["death_order"] == defenders + attackers
    assert result["deaths"] == [defenders[0], attackers[0]]
    assert result["disbands"] == [defenders[1], attackers[1]]
    assert fight(restored, action) == result
    assert restored.model_dump_json() == state.model_dump_json()


@pytest.mark.parametrize("selection", [
    None, ["somerset_1"], {"defender": ["somerset_1"]}, {"lancastrian": "somerset_1"},
    {"lancastrian": ["somerset_1", "somerset_1"]}, {"yorkist": ["somerset_1"]},
    {"lancastrian": ["somerset_1", "henry_vi"]}, {"lancastrian": [["somerset_1"]]},
])
def test_death_order_rejects_invalid_priorities_atomically(selection):
    state, move = death_order_position()
    action = {**move, "decisions": {"death_order": selection}}
    before, submitted = state.model_dump_json(), deepcopy(action)
    with pytest.raises(IllegalAction, match="bad_death_order"):
        actions.apply_action(state, action)
    assert state.model_dump_json() == before and action == submitted


def test_death_order_omits_talbot_disbands_and_unrouted_lords():
    state, action = talbot_position()
    action["decisions"].update(talbot=["henry_tudor"], death_order={
        "lancastrian": ["henry_tudor", "oxford"], "yorkist": ["richard_iii"],
    })
    result = fight(state, action)
    assert result["death_order"] == result["deaths"] == ["oxford"]
    assert result["talbot_disbands"] == ["henry_tudor"]


def test_bosworth_death_order_uses_committed_participants():
    from tests.test_bosworth_setup import complete_setup

    state = build_initial_state("bosworth", seed=5)
    complete_setup(state)
    move, = legal_moves.legal_moves(state)
    options = llm_action_help.contract(state, "resolve_battle", move)["death_order_options"]
    assert options == state.battle_setup.arrays
    priorities = {side: list(reversed(front)) for side, front in options.items()}
    result = actions.apply_action(state, {**move, "decisions": {
        "death_order": priorities, "flee": options["yorkist"] + options["lancastrian"],
    }})
    assert result["death_order"] == priorities["yorkist"] + priorities["lancastrian"]
    assert not invariants.board_invariant_violations(state)
