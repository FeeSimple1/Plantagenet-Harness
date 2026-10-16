"""Contract tests for token-efficient navigation, not alternate game rules."""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from plantagenet import actions, legal_moves, scenarios
from plantagenet.state import GameState
from tests._helpers import to_muster
from tests.test_card_lifecycle_2026_10 import campaign_reset_state
from tests.test_reactions import _approach_setup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
nv = importlib.import_module("chatgpt_play_helper")


def quiet(fn, *args, **kwargs):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        reply = fn(*args, **kwargs)
    return reply, out.getvalue()


@pytest.fixture(autouse=True)
def reset_interface():
    nv.VALIDATE = True
    nv.SOFT_OUTPUT_CHARS = None
    yield
    nv.VALIDATE = True
    nv.SOFT_OUTPUT_CHARS = None


def attach(s, perspective="referee"):
    return quiet(nv.attach, s, perspective=perspective)


def get_id(typ, **filters):
    return next(e["id"] for e in nv.all_actions() if e["action"]["type"] == typ
                and all(e["action"].get(k) == v for k, v in filters.items()))


def plan_state():
    s = scenarios.build_initial_state("henry_vi", seed=17)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    return s


def states():
    first = scenarios.build_initial_state("wars_of_the_roses", seed=20261011)
    levy = scenarios.build_initial_state("henry_vi", seed=3)
    to_muster(levy)
    # Optional Aspielles MUST remain a separate action beside ordinary choices.
    side = levy.active_side
    cid = "Y13" if side == "yorkist" else "L13"
    for pile in levy.decks[side].values():
        if cid in pile:
            pile.remove(cid)
    for lord in levy.lords.values():
        if cid in lord.capabilities:
            lord.capabilities.remove(cid)
    levy.decks[side]["held"].append(cid)
    ps = plan_state()
    end = campaign_reset_state()
    event = deepcopy(levy)
    event.levy_step = "arts_of_war"
    event.turn_box = 2
    event.pending_events = [{"side": side, "card": "Y22" if side == "yorkist" else "L23"}]
    pending, atk, _ = _approach_setup()
    actions.apply_action(pending, {"type": "march", "side": "yorkist", "by_lord": atk,
                                   "to": "lincoln"})
    bosworth = scenarios.build_initial_state("bosworth", seed=7)
    return [first, levy, ps, end, event, pending, bosworth]


@pytest.mark.parametrize("validated", [False, True])
@pytest.mark.parametrize("which", range(7))
def test_filtered_paged_union_is_complete_raw_catalog_with_templates_and_optional_events(
        which, validated):
    s = states()[which]
    original = s.model_dump_json()
    attach(s)
    raw = legal_moves.legal_moves(s.model_copy(deep=True))
    # Raw referee view is a bijection, not merely a subset or a lossy summary.
    entries = nv.all_actions(validated=validated)
    assert [e["action"] for e in entries] == raw
    assert len({e["id"] for e in entries}) == len(raw)
    union = []
    for typ in sorted({a["type"] for a in raw}):
        page = 1
        while True:
            reply, _ = quiet(nv.menu, typ, page=page, page_size=2,
                             validated=validated, expected_version=nv.version())
            union.extend(reply["items"])
            if reply["next_page"] is None:
                break
            page = reply["next_page"]
    assert {e["id"]: e["action"] for e in union} == {e["id"]: e["action"] for e in entries}
    assert len(union) == len(entries)
    for lid in s.lords:
        expected = {e["id"] for e in entries if lid in list(nv._leaves(e["action"])) or (
            e["action"]["type"] == "build_plan" and s.lords[lid].status == "mustered"
            and e["action"].get("side") == s.lords[lid].side)}
        reply, _ = quiet(nv.menu, lord=lid, page_size=None, validated=validated)
        assert {e["id"] for e in reply["items"]} == expected
    assert s.model_dump_json() == original  # enumeration/validation never mutates RNG or state


def test_overview_does_not_print_expanded_moves_or_duplicate_on_repr():
    _, text = attach(states()[1])
    assert '"by_lord"' not in text
    assert "play_held_event" in text and "OPTIONAL" in text
    r, output = quiet(nv.show)
    assert "menu(" in output
    assert len(repr(r)) < 120
    assert len(r["categories"]) > 1


def test_exact_and_nested_filters_and_empty_pages():
    s = states()[0]
    attach(s)
    entries = nv.all_actions()
    a = entries[0]["action"]
    cid, lid = next(iter(a["assignments"].items()))
    r, _ = quiet(nv.menu, "draw", page_size=None, **{f"assignments.{cid}": lid})
    assert all(e["action"]["assignments"].get(cid) == lid for e in r["items"])
    assert r["total"] == sum(e["action"]["assignments"].get(cid) == lid for e in entries)
    r, _ = quiet(nv.menu, "draw", page=9999)
    assert r["items"] == [] and r["total"] == len(entries)
    with pytest.raises(ValueError):
        nv.menu(page_size=0)
    r, _ = quiet(nv.menu, query=cid, page_size=None)
    assert r["items"]


def test_validation_never_renumbers_remaining_ids(monkeypatch):
    s = states()[1]
    actual = legal_moves.legal_moves
    monkeypatch.setattr(legal_moves, "legal_moves", lambda s: [
        {"type": "invalid_engine_candidate"}, *actual(s)])
    attach(s)
    raw = nv.all_actions(validated=False)
    valid = nv.all_actions(validated=True)
    assert raw[0]["status"] == "rejected"
    assert valid[0]["id"] == raw[1]["id"]
    assert valid[0]["id"].endswith("/1")
    # Filtering and toggling validation cannot change what ID /1 applies.
    chosen = valid[0]
    before = s.model_copy(deep=True)
    expected = actions.apply_action(before, nv._clean(chosen["action"]))
    quiet(nv.menu, chosen["action"]["type"], validated=False, page_size=1)
    reply, _ = quiet(nv.apply, chosen["id"])
    assert reply["result"] == expected
    assert s.model_dump(mode="json") == before.model_dump(mode="json")


def test_pagination_and_returned_mutation_do_not_change_selection():
    s = states()[1]
    attach(s)
    entry = next(e for e in nv.all_actions() if e["action"]["type"] == "levy_transport")
    original = deepcopy(entry["action"])
    entry["action"]["transport"] = "made_up"
    quiet(nv.menu, "parley", page_size=1)
    reply, _ = quiet(nv.apply, entry["id"])
    assert reply["kind"] == "result"
    assert nv._S["history"][-1]["action"] == nv._clean(original)


def test_stale_ids_raw_actions_and_page_continuations_are_rejected():
    attach(states()[1])
    old = nv.version()
    chosen = get_id("levy_transport")
    quiet(nv.apply, chosen)
    before = nv._S["state"].model_dump_json()
    with pytest.raises(nv.StaleSelectionError):
        nv.apply(chosen)
    with pytest.raises(nv.StaleSelectionError):
        nv.menu(page=2, expected_version=old)
    with pytest.raises(nv.StaleSelectionError):
        nv.apply({"type": "end_muster", "side": "yorkist"}, expected_version=old)
    with pytest.raises(nv.StaleSelectionError):
        nv.apply({"type": "end_muster", "side": "yorkist"})
    with pytest.raises(TypeError):
        nv.apply(0)
    assert nv._S["state"].model_dump_json() == before


def test_external_state_changes_invalidate_catalog_and_baseline():
    attach(states()[1])
    old = nv.version()
    chosen = get_id("levy_transport")
    nv._S["state"].lords["york"].assets["coin"] += 1
    assert nv.version() != old
    with pytest.raises(nv.StaleSelectionError):
        nv.apply(chosen)
    assert nv._S["baseline"] is None


@pytest.mark.parametrize("side", ["lancastrian", "yorkist"])
def test_custom_plans_are_free_constructions_not_defaults(side):
    s = plan_state()
    attach(s, side)
    raw = nv.all_actions()
    template = next(e for e in raw if e["action"]["type"] == "build_plan")
    assert "plan" not in template["action"]
    assert template["status"] == "template"
    info, _ = quiet(nv.describe, template["id"])
    assert "at most 3" in info["constraints"] and "No default" in info["example_policy"]
    n = s.campaign.cards_required
    ids = [lid for lid, lord in s.lords.items() if lord.side == side and lord.status == "mustered"]
    # Nondefault order, repeated activations, and mixed Pass positions.
    choices = [[{"lord": ids[0]}] * 3 + [{"pass": True}],
               [{"pass": True}, {"lord": ids[-1]}, {"pass": True}, {"lord": ids[0]}]]
    for plan in choices:
        base = plan_state()
        attach(base, side)
        reply, _ = quiet(nv.apply, get_id("build_plan"), parameters={"plan": plan[:n]})
        assert reply["kind"] == "result"
        assert base.campaign.plans[side] == plan[:n]
        assert not any(f["kind"] == "under_enum_accepted" for f in nv._S["findings"])


def test_invalid_plan_is_atomic_and_does_not_print_a_menu():
    s = plan_state()
    attach(s)
    chosen = get_id("build_plan", side="yorkist")
    original = s.model_dump_json()
    stamp = nv.version()
    reply, text = quiet(nv.apply, chosen, parameters={"plan": [{"lord": "york"}] * 4})
    assert reply["kind"] == "error"
    assert s.model_dump_json() == original and nv.version() == stamp
    assert len(text) < 600 and "Actions " not in text


def test_auto_does_not_execute_templates_or_optional_parameter_defaults():
    attach(plan_state(), "yorkist")
    before = nv._S["state"].model_dump_json()
    reply, _ = quiet(nv.auto)
    assert reply["steps"] == 0 and nv._S["state"].model_dump_json() == before
    attach(campaign_reset_state())
    reply, _ = quiet(nv.auto)
    assert reply["steps"] == 0


def test_pending_reactor_not_active_mover_and_both_responses_reachable(tmp_path):
    s, atk, _ = _approach_setup()
    attach(s, "active")
    r, text = quiet(nv.apply, {"type": "march", "side": "yorkist", "by_lord": atk,
                              "to": "lincoln"}, expected_version=nv.version())
    assert r["overview"]["acting_side"] == "lancastrian" and s.active_side == "yorkist"
    assert "PENDING" in text and "FRESH BASELINE" in text
    responses = nv.all_actions()
    assert len(responses) == 2 and {e["action"]["type"] for e in responses} == {"react"}
    assert any(e["action"].get("pass") for e in responses)
    assert any(e["action"].get("play") for e in responses)
    path = tmp_path / "pending.json"
    quiet(nv.save, path)
    old_id = responses[0]["id"]
    quiet(nv.load, path)
    with pytest.raises(nv.StaleSelectionError):
        nv.apply(old_id)
    reply, _ = quiet(nv.apply, get_id("react", play="L15"))
    assert reply["kind"] == "result" and not nv._S["state"].pending
    assert nv._S["state"].lords[atk].location == "york"


def test_save_resume_preserves_future_rng_and_forces_fresh_namespace(tmp_path):
    attach(states()[1])
    chosen = get_id("levy_transport")
    action = nv._clean(nv._resolve_id(chosen)["action"])
    path = tmp_path / "game.json"
    quiet(nv.save, path)
    reference = nv._S["state"].model_copy(deep=True)
    expected = actions.apply_action(reference, action)
    quiet(nv.apply, chosen)
    _, text = quiet(nv.load, path)
    assert "Influence " in text and "Cards " in text
    with pytest.raises(nv.StaleSelectionError):
        nv.apply(chosen)
    reply, _ = quiet(nv.apply, action, expected_version=nv.version())
    assert reply["result"] == expected
    assert nv._S["state"].model_dump_json() == reference.model_dump_json()


def test_show_never_renews_war_and_transition_forces_baseline(tmp_path):
    fixture = ROOT / "tests/fixtures/grand_campaign_2026_10/war-iiy-end.json"
    s = GameState.model_validate_json(fixture.read_text())
    attach(s)
    before = s.model_dump_json()
    old_war = s.grand_scenario["current_war"]
    quiet(nv.show)
    assert s.model_dump_json() == before
    entry = get_id("renew_war")
    path = tmp_path / "war_end.json"
    quiet(nv.save, path)
    quiet(nv.load, path)
    assert nv._S["state"].grand_scenario["current_war"] == old_war
    with pytest.raises(nv.StaleSelectionError):
        nv.apply(entry)
    r, text = quiet(nv.apply, get_id("renew_war"))
    assert r["kind"] == "result"
    assert "FRESH BASELINE" in text and "Influence " in text and "Cards " in text
    assert nv._S["state"].grand_scenario["current_war"] != old_war
    assert nv._S["transitions"] == 1


def test_fixed_perspective_hides_enemy_held_future_plans_and_raw_state():
    s = plan_state()
    s.decks["lancastrian"]["held"] = ["L13", "L11"]
    s.campaign.plans["lancastrian"] = [{"lord": "somerset_1"}, {"lord": "henry_vi"},
                                         {"pass": True}, {"pass": True}]
    s.campaign.plan_built["lancastrian"] = True
    attach(s, "yorkist")
    view, text = quiet(nv.inspect, "state")
    assert "L13" not in text and "L11" not in text
    assert view["data"]["campaign"]["plans"]["lancastrian"] == {
        "revealed": [], "unrevealed_count": 4}
    assert "rng_state" not in view["data"] and "seed" not in view["data"]
    assert "draw" not in view["data"]["decks"]["yorkist"]
    with pytest.raises(PermissionError):
        nv.inspect("raw")
    with pytest.raises(PermissionError):
        nv.inspect("engine_history")
    assert all(e["action"].get("side") in (None, "yorkist") for e in nv.all_actions())


def test_safe_battle_metadata_does_not_reveal_enemy_held_event():
    s, _, dfn = _approach_setup()
    s.lords[dfn].capabilities = []
    s.decks["lancastrian"]["held"] = ["L12"]  # Ravine is unplayed/private
    attach(s, "yorkist")
    r, text = quiet(nv.menu, "march", to="lincoln", page_size=None)
    assert r["items"] and "L12" not in text
    assert "L12" not in json.dumps(nv.all_actions())


def test_bosworth_opponent_selection_is_hidden_after_perspective_change():
    s = scenarios.build_initial_state("bosworth", seed=8)
    attach(s, "active")
    owner = nv._viewer()
    chosen = next(e for e in nv.all_actions() if e["action"]["type"] == "choose_battle_capability")
    cid = chosen["action"]["card"]
    quiet(nv.apply, chosen["id"])
    other = next(side for side in nv._view.SIDES if side != owner)
    stamp = nv.version()
    _, text = quiet(nv.set_perspective, other)
    assert nv.version() != stamp
    assert cid not in text
    r, text = quiet(nv.inspect, "history")
    assert cid not in text
    assert r["data"][0]["result"]["private_result"] == "withheld"


def test_aspielles_information_gain_is_visible_only_to_its_owner():
    s = states()[1]
    s.decks["lancastrian"]["held"] = ["L11", "L12"]
    attach(s, "yorkist")
    r, text = quiet(nv.apply, get_id("play_held_event", card="Y13"))
    assert "L11" in text and "L12" in text
    assert r["result"]["peek"]["enemy_held"] == ["L11", "L12"]
    # The card reveals a snapshot, not perpetual live access to the enemy hand.
    s.decks["lancastrian"]["held"].append("L6")
    _, text = quiet(nv.inspect, "result")
    assert "L6" not in text
    quiet(nv.set_perspective, "lancastrian")
    _, text = quiet(nv.inspect, "result")
    assert '"enemy_held"' not in text


def test_private_reset_contributions_preserve_both_players_choices(tmp_path):
    s = campaign_reset_state()
    attach(s, "yorkist")
    _, text = quiet(nv.menu, "end_campaign")
    assert "L13" not in text and "Y13" in text
    with pytest.raises(ValueError, match="Private Reset"):
        nv.apply(get_id("end_campaign"))
    quiet(nv.stage_reset, {"discard_held": ["Y13"]}, expected_version=nv.version())
    quiet(nv.set_perspective, "lancastrian")
    quiet(nv.stage_reset, {"discard_held": ["L11"]}, expected_version=nv.version())
    path = tmp_path / "reset.json"
    quiet(nv.save, path)
    quiet(nv.load, path)
    r, text = quiet(nv.apply, get_id("end_campaign"))
    assert r["kind"] == "result"
    assert "Y13" not in text  # opposing sealed contribution never printed
    assert "L11" not in nv._S["state"].decks["lancastrian"]["held"]
    assert "Y13" not in nv._S["state"].decks["yorkist"]["held"]
    assert "L13" in nv._S["state"].decks["lancastrian"]["held"]


def test_results_include_influence_supply_forces_cards_and_effect_changes():
    s = states()[1]
    attach(s, "yorkist")
    chosen = get_id("levy_troops", by_lord="york")
    r, text = quiet(nv.apply, chosen)
    assert r["kind"] == "result"
    assert any("forces" in key for key in r["changes"])
    assert "Changes " in text
    for topic in ("influence", "cards", "effects", "victory", "lords", "calendar"):
        detail, _ = quiet(nv.inspect, topic)
        assert "data" in detail


def test_soft_budget_never_changes_menu_membership_or_truncates():
    attach(states()[1])
    all_before = nv.all_actions()
    nv.SOFT_OUTPUT_CHARS = 1
    r, text = quiet(nv.menu, page_size=None)
    assert r["items"] == all_before
    assert "nothing truncated" in text
    assert all(e["id"] in text for e in all_before)


def test_no_rule_modules_changed():
    """An explicit engineering boundary: interface imports, but never patches rules."""
    assert nv.apply_action_local.__module__ == "chatgpt_play_helper"
    assert actions.apply_action.__module__ == "plantagenet.actions"


@pytest.mark.parametrize("fixture", ["llm_interface/war-i-end.json",
                                     "grand_campaign_2026_10/war-iiy-end.json"])
def test_both_renewed_war_boundaries_match_direct_engine(fixture):
    s = GameState.model_validate_json((ROOT / "tests/fixtures" / fixture).read_text())
    shadow = s.model_copy(deep=True)
    attach(s, "active")
    expected = actions.apply_action(shadow, {"type": "renew_war"})
    result, text = quiet(nv.apply, get_id("renew_war"))
    assert result["result"] == expected
    assert s.model_dump_json() == shadow.model_dump_json()
    assert "FRESH BASELINE" in text and result["baseline_required"]
    assert nv._S["transitions"] == 1


def test_custom_partial_group_is_reachable_and_not_reported_under_enumeration():
    from tests.test_command_enumeration import _activate, _into_activation
    s = _activate(_into_activation(), "warwick_yorkist")
    attach(s, "yorkist")
    full = next(e for e in nv.all_actions() if e["action"]["type"] == "march"
                and set(e["action"].get("group", [])) == {"march", "norfolk"})
    shadow = s.model_copy(deep=True)
    custom = {**nv._clean(full["action"]), "group": ["march"]}
    expected = actions.apply_action(shadow, custom)
    r, _ = quiet(nv.apply, full["id"], parameters={"group": ["march"]})
    assert r["kind"] == "result"
    assert r["result"] == nv._view.result_view(expected, "yorkist", "yorkist", s)
    assert s.model_dump_json() == shadow.model_dump_json()
    assert not any(f["kind"] == "under_enum_accepted" for f in nv._S["findings"])


def test_custom_influence_bid_preserved():
    s = states()[1]
    attach(s, "yorkist")
    entry = next(e for e in nv.all_actions() if e["action"]["type"] == "parley")
    shadow = s.model_copy(deep=True)
    custom = {**nv._clean(entry["action"]), "extra_spend": 3}
    expected = actions.apply_action(shadow, custom)
    r, _ = quiet(nv.apply, custom, expected_version=nv.version())
    assert r["kind"] == "result" and r["result"] == expected
    assert s.model_dump_json() == shadow.model_dump_json()


def test_selection_event_template_retained_and_parameters_resolve_pending():
    s = scenarios.build_initial_state("wars_of_the_roses", seed=4)
    s.turn_box = 2
    s.active_side = "lancastrian"
    s.phase = "levy"
    s.levy_step = "arts_of_war"
    for pile in s.decks["lancastrian"].values():
        if "L23" in pile:
            pile.remove("L23")
    s.pending_events = [{"side": "lancastrian", "card": "L23"}]
    attach(s, "lancastrian")
    e = nv.all_actions()[0]
    assert e["status"] == "template" and "decisions" not in e["action"]
    detail, _ = quiet(nv.describe, e["id"])
    assert "d.strongholds" in detail["resolver_contract"]["payload_keys_read"]
    targets = [lid for lid, locale in s.locales.items() if locale.favour == "yorkist"][:3]
    r, _ = quiet(nv.apply, e["id"], parameters={"decisions": {
        "strongholds": {lid: "remove" for lid in targets}}})
    assert r["kind"] == "result" and not s.pending_events
    assert not any(f["kind"] == "over_enum_filtered" for f in nv._S["findings"])


def test_legal_optional_events_survive_normal_category_browsing():
    s = states()[1]
    attach(s, "yorkist")
    optional = get_id("play_held_event", card="Y13")
    quiet(nv.menu, "parley", page_size=1)
    quiet(nv.menu, "levy_troops", page_size=1)
    assert nv._resolve_id(optional)["action"]["card"] == "Y13"
    result, _ = quiet(nv.apply, optional)
    assert result["kind"] == "result"


def test_benchmark_measures_additional_requests_and_full_state_parity(tmp_path):
    # Use the pre-change helper supplied by the benchmark runner, not a second
    # executable interface shipped as part of the game. Normal CI invokes the
    # benchmark separately from its pinned git revision.
    import os

    from benchmark_llm_interface import compare, load_baseline, trajectories
    path = os.environ.get("PLANTAGENET_BASELINE_HELPER")
    if path is None:
        # Traffic accounting is still tested without the optional old helper.
        from benchmark_llm_interface import Traffic
        traffic = Traffic()
        traffic.request("yorkist", "show()", print, "abc")
        traffic.request("yorkist", "menu(page=2)", print, "def")
        stats = traffic.stats()
        assert stats["requests"] == 2
        assert stats["output_chars"] == 8
        assert stats["request_chars"] == len("show()\nmenu(page=2)")
        return
    old = load_baseline(Path(path))
    for case in trajectories():
        row = compare(*case, old, tmp_path, None)
        assert row["state_history_rng_identical"]
        assert row["new"]["requests"] >= row["baseline"]["requests"]


def test_pending_context_exposes_declared_movement_not_private_tactics():
    s, atk, dfn = _approach_setup(seed=4)
    attach(s, "yorkist")
    quiet(nv.apply, {"type": "march", "side": "yorkist", "by_lord": atk,
                     "to": "lincoln"}, expected_version=nv.version())
    assert s.pending
    s.pending[0]["finish_data"]["decisions"] = {"flee_rounds": {"york": [3]}}
    s.pending[0]["offers"].append({"side": "yorkist", "card": "Y11", "kind": "held"})
    r, _ = quiet(nv.inspect, "result")
    assert "remaining" not in r["data"]
    quiet(nv.set_perspective, "lancastrian")
    r, text = quiet(nv.inspect, "pending")
    assert r["data"]["context"]["dest"] == "lincoln"
    assert dfn in r["data"]["context"]["target_lords"]
    assert atk in r["data"]["declared_operation"]["movers"]
    assert "flee_rounds" not in text and "Y11" not in text
    assert "finish_data" not in text and "resume_key" not in text


def test_fresh_baseline_identifies_heirs_and_captured_lords():
    s = scenarios.build_initial_state("wars_of_the_roses", seed=1)
    s.lords["henry_vi"].status = "captured"
    s.lords["henry_vi"].captured_by = "york"
    s.lords["henry_vi"].location = None
    _, text = quiet(nv.attach, s)
    assert "ring=" in text and "captured-by=york" in text
