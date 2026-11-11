"""Public action regressions for Irishmen, Married to a Neville, and Piquiers."""

import pytest

from plantagenet import actions, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState


def _muster(scenario, side):
    state = build_initial_state(scenario, seed=1)
    state.levy_step = "muster"
    state.active_side = side
    return state


def _activate(state, lord_id):
    for _ in range(2):
        actions.apply_action(state, {"type": "end_muster", "side": state.active_side})
    actions.apply_action(state, {"type": "begin_campaign"})
    for side in ("yorkist", "lancastrian"):
        plan = [{"pass": True} for _ in range(state.campaign.cards_required)]
        if state.lords[lord_id].side == side:
            plan[0] = {"lord": lord_id}
        actions.apply_action(state, {"type": "build_plan", "side": side, "plan": plan})
    assert state.campaign.active_lord == lord_id


@pytest.mark.parametrize(("place", "favour", "depletion", "error"), [
    ("bristol", "yorkist", None, None),
    ("bristol", "yorkist", "depleted", None),
    ("bristol", "yorkist", "exhausted", "exhausted"),
    ("bristol", "neutral", None, "not_friendly_locale"),
    ("bristol", "lancastrian", None, "not_friendly_locale"),
    ("ireland", "yorkist", "depleted", None),
    ("ireland", "yorkist", "exhausted", "exhausted"),
])
def test_irishmen_retains_levy_troop_requirements(place, favour, depletion, error):
    state = _muster("henry_vi", "yorkist")
    york = state.lords["york"]
    # Retained from a prior Levy, even if the Port has since changed Favour.
    for pile in state.decks["yorkist"].values():
        if "Y18" in pile:
            pile.remove("Y18")
    york.capabilities = ["Y18"]
    if place == "ireland":
        york.location = None
        york.exile_box = place
        state.exile_depletion[place] = depletion
    else:
        york.location = place
        state.locales[place].favour = favour
        state.locales[place].depletion = depletion

    levy = {"type": "levy_troops", "side": "yorkist", "by_lord": "york"}
    assert (levy in legal_moves.legal_moves(state)) == (error is None)
    if error:
        before = state.model_dump_json()
        with pytest.raises(IllegalAction) as exc:
            actions.apply_action(state, levy)
        assert exc.value.code == error
        assert state.model_dump_json() == before
    else:
        assert actions.apply_action(state, levy)["added"] == {"militia": 5}
        if place == "ireland":
            assert state.exile_depletion[place] == depletion
        else:
            assert state.locales[place].depletion == depletion


def _clarence_at(start, warwick_at):
    state = _muster("warwicks_rebellion", "lancastrian")
    state.lords["clarence"].location = start
    state.lords["warwick_lancastrian"].location = warwick_at
    for locale in (start, warwick_at):
        state.locales[locale].favour = "lancastrian"
    actions.apply_action(state, {"type": "levy_capability", "side": "lancastrian",
                                 "by_lord": "clarence", "card": "L24"})
    return state


@pytest.mark.parametrize(("warwick_at", "forage_first", "remaining"), [
    ("york", False, 0),
    ("york", True, 0),
    ("scarborough", False, 1),
])
def test_clarence_command_tracks_warwick_after_march(warwick_at, forage_first, remaining):
    state = _clarence_at("york", warwick_at)
    state.locales["scarborough"].favour = "lancastrian"
    _activate(state, "clarence")
    assert state.campaign.actions_remaining == (2 if warwick_at == "york" else 1)
    forage = {"type": "forage", "side": "lancastrian", "by_lord": "clarence"}
    if forage_first:
        actions.apply_action(state, forage)
    move = {"type": "march", "side": "lancastrian", "by_lord": "clarence", "to": "scarborough"}
    restored = GameState.model_validate_json(state.model_dump_json())
    assert actions.apply_action(state, move)["to"] == "scarborough"
    actions.apply_action(restored, move)
    assert state.model_dump_json() == restored.model_dump_json()
    assert state.campaign.actions_remaining == remaining
    assert (forage in legal_moves.legal_moves(state)) == bool(remaining)
    if remaining:
        assert actions.apply_action(state, forage)["provender_added"] == 1
    else:
        with pytest.raises(IllegalAction) as exc:
            actions.apply_action(state, forage)
        assert exc.value.code == "no_actions_left"
    assert state.campaign.actions_remaining == 0


@pytest.mark.parametrize("seamanship", [False, True])
def test_clarence_sail_keeps_its_normal_card_cost(seamanship):
    state = _clarence_at("scarborough", "ravenspur")
    state.lords["clarence"].assets["ship"] = 2
    if seamanship:
        for pile in state.decks["lancastrian"].values():
            if "L6" in pile:
                pile.remove("L6")
        state.active_events.append({"card": "L6", "side": "lancastrian"})
    _activate(state, "clarence")
    sail = {"type": "sail", "side": "lancastrian", "by_lord": "clarence", "to": "ravenspur"}
    assert actions.apply_action(state, sail)["to"] == "ravenspur"
    assert state.campaign.actions_remaining == int(seamanship)


@pytest.mark.parametrize("chevaliers", [False, True])
def test_piquiers_armour_combines_with_chevaliers_missile_penalty(chevaliers):
    state = _muster("my_kingdom_for_a_horse", "lancastrian")
    oxford = state.lords["oxford"]
    oxford.location = "rochester"
    oxford.exile_box = None
    state.locales["rochester"].favour = "lancastrian"
    state.lords["norfolk"].location = "canterbury"
    for card in (["L34", "L36"] if chevaliers else ["L34"]):
        actions.apply_action(state, {"type": "levy_capability", "side": "lancastrian",
                                     "by_lord": "oxford", "card": card})
    _activate(state, "oxford")
    march = {"type": "march", "side": "lancastrian", "by_lord": "oxford", "to": "canterbury",
             "decisions": {"responses": {"norfolk": "battle"}, "valour": False,
                           "absorb_order": ["men_at_arms", "militia", "longbow", "retinue"]}}
    battle = actions.apply_action(state, march)["approach"]["battle"]
    strike = battle["rounds"][0]["engagements"][0]["strikes"][0]
    assert strike["phase"] == "missile"
    assert strike["attacker_rolls"][3] == {
        "lord": "oxford", "unit": "men_at_arms", "roll": 4, "saved": not chevaliers,
    }
