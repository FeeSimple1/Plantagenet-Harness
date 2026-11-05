"""P2-2/P2-3: all Forces count; owners can leave cargo to make a Sail."""
from __future__ import annotations

import pytest

from plantagenet import actions, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.rng import DiceRoller
from plantagenet.scenarios import build_initial_state
from plantagenet.state import CampaignState, GameState, LordStatus
from scripts import llm_action_help, llm_view


def position(lid="york"):
    state = build_initial_state("henry_vi", seed=1)
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
        deck["held"] = []
    actor = place(state, lid)
    actor.assets = {"ship": 1}
    state.active_side = actor.side
    enemy = "henry_vi" if actor.side == "yorkist" else "york"
    place(state, enemy, "london")
    state.campaign = CampaignState(
        step="activation", cards_required=1, active_lord=lid, actions_remaining=3,
        plans={actor.side: [{"lord": lid}], state.lords[enemy].side: [{"pass": True}]},
        plan_built={"yorkist": True, "lancastrian": True},
        plan_index={"yorkist": 0, "lancastrian": 0})
    return state


def place(state, lid, locale="lynn"):
    lord = state.lords[lid]
    lord.status = LordStatus.MUSTERED
    lord.calendar_box = None
    lord.location = locale
    lord.forces = {"retinue": 1}
    return lord


def sail(state, destination="north_sea", **options):
    return actions.apply_action(state, {"type": "sail", "side": state.active_side,
                                        "by_lord": state.campaign.active_lord,
                                        "to": destination, **options})


def rejected(state, *, code=None, destination="north_sea", **options):
    before = state.model_dump_json()
    with pytest.raises(IllegalAction) as error:
        sail(state, destination, **options)
    if code:
        assert error.value.code == code
    assert state.model_dump_json() == before


def sail_menu(state):
    validated = legal_moves.validated_legal_moves(state)
    assert not [r for r in validated["rejected"] if r["move"]["type"] == "sail"]
    return [m for m in validated["moves"] if m["type"] == "sail"]


@pytest.mark.parametrize("special", [[], ["hastings"]])
def test_six_units_fit_but_seventh_special_vassal_needs_another_ship(special):
    state = position()
    lord = state.lords["york"]
    lord.forces = {"retinue": 1, "men_at_arms": 5}
    lord.special_vassals = special
    if special:
        rejected(state, code="insufficient_ships")
        assert sail_menu(state) == []
    else:
        assert sail(state)["at_sea"] == "north_sea"


def test_regular_and_special_vassal_counters_both_count_as_forces():
    state = position()
    lord = state.lords["york"]
    lord.forces = {"retinue": 1, "militia": 4}
    lord.vassals = ["oxford"]
    lord.special_vassals = ["hastings"]
    rejected(state, code="insufficient_ships")
    lord.assets["ship"] = 2
    assert sail(state)["at_sea"] == "north_sea"


def test_special_vassals_also_count_on_group_sail():
    state = position()
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 4}
    ally = place(state, "salisbury")
    ally.special_vassals = ["hastings"]
    rejected(state, code="insufficient_ships", group=["salisbury"])
    ally.assets["ship"] = 1
    result = sail(state, group=["salisbury"])
    assert result["group"] == ["salisbury"]
    assert state.lords["salisbury"].at_sea == "north_sea"


@pytest.mark.parametrize("asset", ["provender", "cart"])
@pytest.mark.parametrize("destination", ["north_sea", "newcastle"])
def test_explicit_discard_makes_an_otherwise_illegal_sail(asset, destination):
    state = position()
    lord = state.lords["york"]
    lord.assets[asset] = 3
    rejected(state, code="insufficient_ships", destination=destination)
    result = sail(state, destination, discard={asset: 1})
    assert lord.assets[asset] == 2
    assert result["discarded"] == {"york": {asset: 1}}
    assert lord.moved_fought is True and state.campaign.actions_remaining == 0


def test_one_ship_carries_both_cargo_types_up_to_each_limit():
    state = position()
    state.lords["york"].assets.update(provender=5, cart=4)
    result = sail(state, discard={"provender": 3, "cart": 2})
    assert state.lords["york"].assets == {"ship": 1, "provender": 2, "cart": 2}
    assert result["discarded"] == {"york": {"provender": 3, "cart": 2}}


@pytest.mark.parametrize("origin", ["port", "exile", "sea"])
def test_menu_exposes_discard_sails_from_every_legal_origin(origin):
    state = position()
    lord = state.lords["york"]
    lord.assets["provender"] = 3
    if origin == "exile":
        lord.location = None
        lord.exile_box = "burgundy"
    elif origin == "sea":
        lord.location = None
        lord.at_sea = "north_sea"
    moves = sail_menu(state)
    assert moves and all(m["discard"] == {"provender": 1} for m in moves)
    assert all(m["discard_needed"] == {"provender": 1} for m in moves)
    actions.apply_action(state, moves[0])
    assert lord.assets["provender"] == 2


@pytest.mark.parametrize("drop", [
    {"york": {"provender": 2}}, {"salisbury": {"provender": 2}},
    {"york": {"provender": 1}, "salisbury": {"provender": 1}}])
def test_owner_selects_which_group_mats_discard_the_excess(drop):
    state = position()
    state.lords["york"].assets["provender"] = 2
    ally = place(state, "salisbury")
    ally.assets["provender"] = 2
    result = sail(state, group=["salisbury"], discard=drop)
    assert result["discarded"] == drop
    assert state.lords["york"].assets["provender"] == 2 - drop.get("york", {}).get("provender", 0)
    assert ally.assets["provender"] == 2 - drop.get("salisbury", {}).get("provender", 0)
    assert ally.at_sea == state.lords["york"].at_sea == "north_sea"


def test_group_menu_describes_alternate_discard_owners():
    state = position()
    state.lords["york"].assets["provender"] = 2
    ally = place(state, "salisbury")
    ally.assets["provender"] = 2
    move = next(m for m in sail_menu(state) if m.get("group") == ["salisbury"])
    assert move["discard_options"] == {"york": {"provender": 2}, "salisbury": {"provender": 2}}
    assert move["discard_needed"] == {"provender": 2}
    actions.apply_action(state, {**move, "discard": {"salisbury": {"provender": 2}}})
    assert ally.assets["provender"] == 0 and state.lords["york"].assets["provender"] == 2


@pytest.mark.parametrize("great_owner", ["york", "salisbury", None])
def test_great_ships_stays_with_the_ship_owner_when_shared(great_owner):
    state = position()
    state.lords["york"].assets = {"provender": 4}
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 5}
    state.lords["york"].special_vassals = ["hastings"]
    ally = place(state, "salisbury")
    ally.assets["ship"] = 1
    if great_owner:
        state.lords[great_owner].capabilities = ["Y6"]
    if great_owner == "salisbury":
        assert sail(state, share=["salisbury"])["at_sea"] == "north_sea"
    else:
        rejected(state, code="insufficient_ships", share=["salisbury"])


def test_shared_ships_can_avoid_a_discard_and_are_offered_in_menu():
    state = position()
    state.lords["york"].assets["provender"] = 3
    ally = place(state, "salisbury")
    ally.assets["ship"] = 1
    moves = [m for m in sail_menu(state) if m["to"] == "north_sea"]
    assert any(m.get("discard") == {"provender": 1} for m in moves)
    shared = next(m for m in moves if m.get("share") == ["salisbury"])
    assert "discard" not in shared
    assert shared["share_options"] == ["salisbury"]
    actions.apply_action(state, shared)
    assert state.lords["york"].assets["provender"] == 3
    assert ally.location == "lynn" and ally.at_sea is None


def test_partial_groups_remain_reachable_when_the_full_group_is_too_large():
    state = position()
    state.lords["york"].forces = {"retinue": 1, "men_at_arms": 6}
    state.lords["york"].assets = {}
    for lid in ("salisbury", "warwick_yorkist"):
        place(state, lid).assets["ship"] = 1
    place(state, "march").forces = {"retinue": 1, "militia": 12}
    moves = [m for m in sail_menu(state) if m["to"] == "north_sea"]
    assert not any(m.get("group") for m in moves)
    assert set(moves[0]["group_options"]) == {"salisbury", "warwick_yorkist", "march"}
    selected = {**moves[0], "group": ["salisbury", "warwick_yorkist"]}
    actions.apply_action(state, selected)
    assert state.lords["march"].location == "lynn"
    assert all(state.lords[lid].at_sea == "north_sea"
               for lid in ("york", "salisbury", "warwick_yorkist"))


@pytest.mark.parametrize("drop,code", [
    ({"provender": 2}, "unnecessary_discard"),
    ({"coin": 1}, "bad_discard"), ({"ship": 1}, "bad_discard"),
    ({"loot": 1}, "bad_discard"), ({"provender": -1}, "bad_discard"),
    ({"provender": True}, "bad_discard"), ({"provender": 1.5}, "bad_discard"),
    ({"provender": "1"}, "bad_discard"), ({"provender": 4}, "bad_discard"),
    ({"henry_vi": {"provender": 1}}, "bad_discard"),
    ({"york": []}, "bad_discard"), (None, "bad_discard"),
])
def test_invalid_or_unnecessary_discards_reject_atomically(drop, code):
    state = position()
    state.lords["york"].assets.update(provender=3, coin=1, loot=1)
    rejected(state, code=code, discard=drop)


def test_a_stationary_ship_donor_cannot_have_his_cargo_discarded():
    state = position()
    state.lords["york"].assets = {"provender": 3}
    ally = place(state, "salisbury")
    ally.assets = {"ship": 1, "provender": 3}
    rejected(state, code="bad_discard", share=["salisbury"],
             discard={"salisbury": {"provender": 1}})


@pytest.mark.parametrize("options", [
    {"group": ["york"]}, {"group": ["salisbury", "salisbury"]},
    {"share": ["salisbury", "salisbury"]}, {"group": "salisbury"},
    {"share": "salisbury"},
])
def test_duplicate_or_malformed_groups_and_ship_donors_cannot_inflate_capacity(options):
    state = position()
    place(state, "salisbury").assets["ship"] = 1
    rejected(state, **options)


def test_invalid_destination_does_not_discard_cargo_or_spend_actions():
    state = position()
    state.lords["york"].assets["provender"] = 3
    rejected(state, code="cross_sea_port_to_port", destination="bristol", discard={"provender": 1})


def blockade_position():
    state = position("henry_vi")
    state.lords["henry_vi"].location = "bristol"
    state.lords["henry_vi"].assets.update(provender=3, cart=3)
    place(state, "warwick_yorkist", "harlech").capabilities = ["Y15"]
    return state


@pytest.mark.parametrize("roll,cancelled", [(1, False), (6, True)])
def test_blockade_waits_to_discard_until_a_sail_actually_occurs(monkeypatch, roll, cancelled):
    state = blockade_position()
    monkeypatch.setattr(DiceRoller, "d6", lambda _: roll)
    original = dict(state.lords["henry_vi"].assets)
    result = sail(state, "pembroke", discard={"provender": 1, "cart": 1})
    assert result["type"] == "pending_reactions"
    assert state.lords["henry_vi"].assets == original and state.campaign.actions_remaining == 0
    state = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, {"type": "react", "side": "yorkist", "play": "Y15"})
    lord = state.lords["henry_vi"]
    assert (lord.location == "bristol") == cancelled
    assert result["discarded"] == ({} if cancelled else {"henry_vi": {"provender": 1, "cart": 1}})
    assert lord.assets == (original if cancelled else {"ship": 1, "provender": 2, "cart": 2})


def test_declined_blockade_resumes_saved_discard_once():
    state = blockade_position()
    sail(state, "pembroke", discard={"provender": 1, "cart": 1})
    state = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, {"type": "react", "side": "yorkist", "pass": True})
    assert result["discarded"] == {"henry_vi": {"provender": 1, "cart": 1}}
    assert state.lords["henry_vi"].assets == {"ship": 1, "provender": 2, "cart": 2}
    before = state.model_dump_json()
    with pytest.raises(IllegalAction):
        actions.apply_action(state, {"type": "react", "side": "yorkist", "pass": True})
    assert state.model_dump_json() == before


def test_sailing_from_a_port_out_to_sea_checks_that_ports_blockade():
    state = blockade_position()
    result = sail(state, "irish_sea", discard={"provender": 1, "cart": 1})
    assert result["type"] == "pending_reactions"
    assert result["awaiting"]["card"] == "Y15"
    assert state.lords["henry_vi"].location == "bristol"
    assert state.lords["henry_vi"].assets["provender"] == 3


def test_proposed_discards_and_menu_hints_stay_private_until_the_sail_occurs():
    state = blockade_position()
    action = {"type": "sail", "side": "lancastrian", "by_lord": "henry_vi",
              "to": "pembroke", "discard": {"provender": 1, "cart": 1},
              "discard_options": {"henry_vi": {"provender": 1, "cart": 1}},
              "discard_needed": {"provender": 1, "cart": 1},
              "group_options": ["buckingham"], "share_options": ["buckingham"]}
    actions.apply_action(state, action)
    public = llm_view.private_action(action, "lancastrian", "yorkist", state)
    for key in ("discard", "discard_options", "discard_needed", "group_options", "share_options"):
        assert key not in public
    assert llm_view.private_action(action, "lancastrian", "lancastrian", state) == action
    assert "discards" not in str(llm_view.pending_view(state, "yorkist"))
    result = actions.apply_action(state, {"type": "react", "side": "yorkist", "pass": True})
    assert llm_view.result_view(result, "lancastrian", "yorkist", state)["discarded"] == {
        "henry_vi": {"provender": 1, "cart": 1}}


@pytest.mark.parametrize("origin", ["sea", "exile"])
def test_sailing_from_a_sea_or_exile_box_to_sea_uses_no_port_for_blockade(origin):
    state = blockade_position()
    actor = state.lords["henry_vi"]
    actor.location = None
    actor.at_sea = "irish_sea" if origin == "sea" else None
    actor.exile_box = "france" if origin == "exile" else None
    sea = "irish_sea" if origin == "sea" else "english_channel"
    if origin == "exile":
        state.lords["warwick_yorkist"].location = "plymouth"
    result = sail(state, sea, discard={"provender": 1, "cart": 1})
    assert result["type"] == "sail" and state.pending == []
    assert actor.at_sea == sea and actor.assets["provender"] == 2


def test_sailing_to_a_port_checks_only_the_sea_of_the_used_port():
    state = blockade_position()  # Blockader at Harlech on the Irish Sea.
    actor = state.lords["henry_vi"]
    actor.location = None
    actor.at_sea = "irish_sea"
    result = sail(state, "southampton", discard={"provender": 1, "cart": 1})
    assert result["type"] == "sail" and state.pending == []
    assert actor.location == "southampton"


def test_sailing_into_adjacent_sea_does_not_use_a_port_on_that_sea():
    state = blockade_position()
    state.lords["warwick_yorkist"].location = "plymouth"
    result = sail(state, "english_channel", discard={"provender": 1, "cart": 1})
    assert result["type"] == "sail" and state.pending == []
    assert state.lords["henry_vi"].at_sea == "english_channel"


def test_seamanship_still_spends_only_one_action_with_a_discard():
    state = position()
    state.active_events = [{"card": "Y6", "side": "yorkist", "scope": "this_campaign"}]
    state.lords["york"].assets["provender"] = 3
    sail(state, discard={"provender": 1})
    assert state.campaign.actions_remaining == 2


def test_high_admiral_enemy_ports_are_discoverable_and_truce_still_blocks_them():
    state = position("exeter_1")
    state.lords["exeter_1"].capabilities = ["L29"]
    state.lords["york"].location = "newcastle"
    assert any(m["type"] == "sail" and m["to"] == "newcastle"
               for m in legal_moves.legal_moves(state))
    state.active_events = [{"card": "L20", "side": "lancastrian", "scope": "this_campaign"}]
    assert not any(m["type"] == "sail" and m["to"] == "newcastle"
                   for m in legal_moves.legal_moves(state))


def test_chat_parameter_reference_explains_discard_and_partial_groups():
    contract = llm_action_help.CONTRACTS["sail"]
    assert "discard" in contract["parameters"]
    assert "partial groups" in contract["constraints"]
