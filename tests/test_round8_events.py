"""Round 8 Event ownership and Tax regressions with public actions and real dice."""

import pytest

from plantagenet import actions, invariants, static_data
from plantagenet.scenarios import build_initial_state
from plantagenet.state import CampaignState, GameState
from scripts import llm_action_help, llm_view
from tests._helpers import queue_drawn_event
from tests.test_round7_events import _menu, _net_lancaster, _reject


def _apply(state, action):
    assert invariants.board_invariant_violations(state) == []
    replay = GameState.model_validate_json(state.model_dump_json())
    result = actions.apply_action(state, action)
    assert actions.apply_action(replay, action) == result
    assert state.model_dump_json() == replay.model_dump_json()
    assert invariants.board_invariant_violations(state) == []
    return result


@pytest.mark.parametrize("card", ["L23", "L24"])
def test_propaganda_waits_for_yorks_response_at_every_stronghold(card):
    state = build_initial_state("warwicks_rebellion", seed=1)
    state.locales["london"].favour_extra = 1
    queue_drawn_event(state, card)
    state.decks["lancastrian"]["draw"].remove("L30")
    state.pending_events.append({"card": "L30", "side": "lancastrian"})
    select, = _menu(state)
    targets = ["exeter", "london", "ely"]
    assert set(targets) <= set(select["event_choices"]["strongholds"]["available"])
    assert select["event_choices"]["strongholds"]["select"] == 3
    before = _net_lancaster(state)
    dice = state.rng_state
    result = _apply(state, {**select, "decisions": {"strongholds": targets}})
    assert result["awaiting_side"] == "yorkist"
    assert _net_lancaster(state) == before
    assert all(state.locales[loc].favour == "yorkist" for loc in targets)
    assert state.locales["london"].favour_extra == 1
    assert llm_view.decision_side(state) == "yorkist"
    assert state.active_side == "lancastrian"
    assert state.levy_step == "arts_of_war"
    assert [e["card"] for e in llm_view.pending_view(state, "yorkist")["events"]] == [card]
    _reject(state, {"type": "play_event", "side": "lancastrian", "card": "L30"},
            "event_order")

    for index, (loc, choice) in enumerate(zip(targets, ["pay", "remove", "remove"], strict=True)):
        remove, pay = _menu(state)
        assert all(m["side"] == "yorkist" for m in (remove, pay))
        assert [m["decisions"] for m in (remove, pay)] == [
            {"stronghold": loc, "choice": "remove"}, {"stronghold": loc, "choice": "pay"},
        ]
        detail = llm_action_help.contract(state, "play_event", pay)
        assert detail["resolver_contract"]["payload_keys_read"] == ["d.choice", "d.stronghold"]
        assert detail["event_choices"] == {"stronghold": loc}
        _reject(state, {**pay, "side": "lancastrian"}, "wrong_side")
        _reject(state, {**pay, "decisions": {"stronghold": "calais", "choice": "pay"}},
                "bad_event_target")
        _reject(state, {**pay, "decisions": {"stronghold": loc, "choice": "ignore"}},
                "bad_event_decisions")
        result = _apply(state, pay if choice == "pay" else remove)
        assert len(result["results"]) == index + 1
        assert state.rng_state == dice
        if index < 2:
            assert result["awaiting_side"] == "yorkist"
            assert card not in state.decks["lancastrian"]["draw"]
    assert _net_lancaster(state) == before + 2
    assert state.locales["exeter"].favour == state.locales["london"].favour == "yorkist"
    assert state.locales["london"].favour_extra == 0
    assert state.locales["ely"].favour == "neutral"
    assert state.decks["lancastrian"]["draw"].count(card) == 1
    assert state.pending_events == [{"card": "L30", "side": "lancastrian"}]
    assert llm_view.decision_side(state) == "lancastrian"


@pytest.mark.parametrize("targets,code", [
    ([], "bad_count"), (["ely"], "bad_count"), (["ely", "ely", "london"], "bad_count"),
    (["ely", "london", "unknown"], "not_yorkist"),
    ({"ely": "remove", "london": "pay", "exeter": "remove"}, "bad_count"),
])
def test_propaganda_rejects_invalid_selections_and_lancastrian_payment_choices(targets, code):
    state = build_initial_state("warwicks_rebellion", seed=1)
    queue_drawn_event(state, "L23")
    select, = _menu(state)
    _reject(state, {**select, "decisions": {"strongholds": targets}}, code)


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_propaganda_menu_supplies_a_forced_selection_without_choosing_yorks_response(count):
    state = build_initial_state("warwicks_rebellion", seed=1)
    targets = ["ely", "london", "exeter"][:count]
    for loc, locale in state.locales.items():
        locale.favour = "yorkist" if loc in targets else "neutral"
        locale.favour_extra = 0
    queue_drawn_event(state, "L24")
    move, = _menu(state)
    assert move["decisions"] == {"strongholds": sorted(targets)}
    result = _apply(state, move)
    if count:
        assert result["awaiting_side"] == "yorkist"
        assert len(_menu(state)) == 2
        assert all(state.locales[loc].favour == "yorkist" for loc in targets)
    else:
        assert "no_effect" in result and not state.pending_events


def _campaign(scenario, lid, locale, seed):
    state = build_initial_state(scenario, seed=seed)
    state.phase, state.levy_step = "campaign", "done"
    state.active_side = state.lords[lid].side
    state.lords[lid].location = locale
    state.campaign = CampaignState(
        step="activation", active_lord=lid, actions_remaining=3, cards_required=3,
        plans={state.active_side: [{"lord": lid}] * 3},
        plan_built={"yorkist": True, "lancastrian": True},
    )
    state.locales[locale].depletion = None
    return state


@pytest.mark.parametrize("extra,success", [(0, False), (1, True), (3, True)])
def test_tax_collectors_offers_each_influence_bid_and_uses_the_normal_check(extra, success):
    state = _campaign("warwicks_rebellion", "pembroke", "london", seed=7)
    ordinary = state.model_copy(deep=True)
    control = _apply(ordinary, {"type": "tax", "side": "yorkist", "by_lord": "pembroke",
                                "target": "london", "extra_spend": extra})
    state.campaign = None
    queue_drawn_event(state, "Y10")
    move, = _menu(state)
    assert "london" in move["event_choices"]["tax_targets"]["pembroke"]
    assert move["event_choices"]["extra_spend"] == [0, 1, 3]
    detail = llm_action_help.contract(state, "play_event", move)
    assert detail["resolver_contract"]["payload_keys_read"] == [
        "d.extra_spend", "d.lords", "d.tax_targets",
    ]
    before = _net_lancaster(state)
    result = _apply(state, {**move, "decisions": {
        "lords": ["pembroke"], "tax_targets": {"pembroke": "london"},
        "extra_spend": {"pembroke": extra},
    }})["taxes"]["pembroke"]
    assert result["roll"] == control["roll"] == 3
    assert result["success"] == control["success"] == success
    assert result["rating"] == control["rating"]
    assert result["spent"] == control["spent"] == 1 + extra
    assert _net_lancaster(state) == before + 1 + extra
    assert result["coin"] == control["coin_added"] * 2
    assert state.locales["london"].depletion == ordinary.locales["london"].depletion


@pytest.mark.parametrize("extra", [None, -1, 2, True, "1"])
def test_tax_collectors_rejects_invalid_spending_without_mutation(extra):
    state = _campaign("warwicks_rebellion", "pembroke", "london", seed=7)
    state.campaign = None
    queue_drawn_event(state, "Y10")
    move, = _menu(state)
    _reject(state, {**move, "decisions": {
        "lords": ["pembroke"], "tax_targets": {"pembroke": "london"},
        "extra_spend": {"pembroke": extra},
    }}, "bad_extra_spend")


@pytest.mark.parametrize("favour", ["neutral", "lancastrian", "yorkist"])
@pytest.mark.parametrize("origin", ["ely", "cambridge"])
def test_tax_collectors_requires_a_friendly_source_even_at_the_lords_own_seat(favour, origin):
    state = _campaign("henry_vi", "york", origin, seed=1)
    state.locales[origin].favour = "yorkist"
    state.locales["ely"].favour = favour
    state.locales["ely"].depletion = None
    ordinary = state.model_copy(deep=True)
    action = {"type": "tax", "side": "yorkist", "by_lord": "york", "target": "ely"}
    if favour == "yorkist":
        assert _apply(ordinary, action)["coin_added"] == 2
    else:
        _reject(ordinary, action, "not_friendly_locale" if origin == "ely" else "no_route")
    state.campaign = None
    queue_drawn_event(state, "Y10")
    move, = _menu(state)
    offered = move["event_choices"]["tax_targets"].get("york", [])
    assert ("ely" in offered) == (favour == "yorkist")
    dice, influence = state.rng_state, _net_lancaster(state)
    result = _apply(state, {**move, "decisions": {
        "lords": ["york", "york"], "tax_targets": {"york": "ely"},
        "extra_spend": {"york": 3},
    }})["taxes"]
    assert state.rng_state == dice and _net_lancaster(state) == influence
    if favour == "yorkist":
        assert result["york"]["coin"] == 4 and result["york"]["spent"] == 0
        assert state.locales["ely"].depletion == "depleted"
    else:
        assert result == {} and state.locales["ely"].depletion is None


def test_tax_collectors_cannot_reuse_a_source_exhausted_by_an_earlier_lord():
    state = _campaign("warwicks_rebellion", "pembroke", "london", seed=7)
    state.lords["edward_iv"].location = "london"
    state.locales["london"].depletion = "depleted"
    state.campaign = None
    queue_drawn_event(state, "Y10")
    move, = _menu(state)
    assert all("london" in move["event_choices"]["tax_targets"][lid]
               for lid in ("pembroke", "edward_iv"))
    before = _net_lancaster(state)
    result = _apply(state, {**move, "decisions": {
        "lords": ["pembroke", "edward_iv"],
        "tax_targets": {"pembroke": "london", "edward_iv": "london"},
        "extra_spend": {"pembroke": 3, "edward_iv": 3},
    }})["taxes"]
    assert list(result) == ["pembroke"]
    assert result["pembroke"]["roll"] == 3 and result["pembroke"]["coin"] == 6
    assert _net_lancaster(state) == before + 4
    assert state.locales["london"].depletion == "exhausted"


@pytest.mark.parametrize("seed", [1, 4])
@pytest.mark.parametrize("have_card", [False, True])
@pytest.mark.parametrize("event", [False, True])
def test_so_wise_so_young_adds_coin_on_both_successful_and_failed_tax(seed, have_card, event):
    state = _campaign("my_kingdom_for_a_horse", "gloucester_2", "calais", seed=seed)
    lord = state.lords["gloucester_2"]
    if have_card:
        state.decks["yorkist"]["draw"].remove("Y34")
        lord.capabilities.append("Y34")
    before_coin = lord.assets.get("coin", 0)
    if event:
        state.campaign = None
        queue_drawn_event(state, "Y10")
        move, = _menu(state)
        result = _apply(state, {**move, "decisions": {
            "lords": ["gloucester_2"], "tax_targets": {"gloucester_2": "calais"},
        }})["taxes"]["gloucester_2"]
        added = result["coin"]
    else:
        result = _apply(state, {"type": "tax", "side": "yorkist", "by_lord": "gloucester_2",
                                "target": "calais"})
        added = result["coin_added"]
    success = seed == 1
    assert result["roll"] == (4 if success else 6)
    assert result["success"] == success
    base = static_data.stronghold_yields("calais")["tax"]["coin"] if success else 0
    assert added == (base + int(have_card)) * (2 if event else 1)
    assert state.lords["gloucester_2"].assets.get("coin", 0) == before_coin + added
    assert state.locales["calais"].depletion == ("depleted" if success else None)
