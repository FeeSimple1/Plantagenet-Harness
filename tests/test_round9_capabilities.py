"""Round9 public-action witnesses. Run at Plantagenet root with PYTHONPATH=src:."""

from __future__ import annotations

import hashlib

import pytest

from plantagenet import actions, invariants, legal_moves, ratings, static_data
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus


def digest(state):
    return hashlib.sha256(state.model_dump_json().encode()).hexdigest()


def net_influence(state):
    track = state.influence["track"]
    return track.marker_at if track.marker_side == "lancastrian" else -track.marker_at


def apply(state, action, receipt):
    assert invariants.board_invariant_violations(state) == []
    restored = GameState.model_validate_json(state.model_dump_json())
    before = state.model_dump_json()
    influence_before = net_influence(state)
    try:
        result = actions.apply_action(state, action)
    except IllegalAction as exc:
        assert state.model_dump_json() == before
        try:
            actions.apply_action(restored, action)
        except IllegalAction as again:
            assert again.code == exc.code
        else:
            raise AssertionError("restored state accepted rejected action")
        receipt.append({"action": action, "rejected": exc.code, "unchanged": True})
        return {"rejected": exc.code}
    assert actions.apply_action(restored, action) == result
    assert state.model_dump_json() == restored.model_dump_json()
    assert invariants.board_invariant_violations(state) == []
    entry = {"action": action, "result": result, "state_sha256": digest(state)}
    if action["type"] == "pay":
        entry["influence_before"] = influence_before
        entry["influence_after"] = net_influence(state)
    receipt.append(entry)
    return result


def muster_position(seed, turn):
    """Legal constructed later-Levy tactical position, printed Salisbury mat."""
    state = build_initial_state("henry_vi", seed=seed)
    state.phase = "levy"
    state.levy_step = "muster"
    state.active_side = "yorkist"
    state.turn_box = turn
    salisbury = state.lords["salisbury"]
    salisbury.status = LordStatus.MUSTERED
    salisbury.calendar_box = None
    salisbury.location = "york"
    salisbury.forces = dict(static_data.load_lords()["salisbury"]["forces"])
    salisbury.assets = dict(static_data.load_lords()["salisbury"]["assets"])
    for locale in ("york", "leicester", "appleby"):
        state.locales[locale].favour = "yorkist"
    return state


def next_muster(state, receipt):
    """Advance actual seeded draws and Pay; no phase/position edits."""
    for _ in range(30):
        if state.phase == "levy" and state.levy_step == "muster" and state.active_side == "yorkist":
            return
        if state.phase == "over":
            raise AssertionError("unexpected victory")
        move = legal_moves.legal_moves(state)[0]
        apply(state, move, receipt)
    raise AssertionError("did not reach next Muster")


def campaign(state, receipt, exile=False):
    for _ in range(2):
        apply(state, {"type": "end_muster", "side": state.active_side}, receipt)
    apply(state, {"type": "begin_campaign"}, receipt)
    n = state.campaign.cards_required
    for side in ("yorkist", "lancastrian"):
        # Real decks: three cards per Lord; avoid relying on unlimited Pass cards.
        ids = (
            (["march"] * 3 + ["york"] * 2 + ["salisbury"])
            if side == "yorkist"
            else (["henry_vi"] * 3 + ["somerset_1"] * 3)
        )
        assert n == 6
        plan = [{"lord": lid} for lid in ids]
        apply(state, {"type": "build_plan", "side": side, "plan": plan}, receipt)
    while state.campaign.step == "activation":
        if exile and state.campaign.active_lord == "salisbury":
            apply(
                state,
                {"type": "exile_pact", "side": "yorkist", "by_lord": "salisbury", "box": "ireland"},
                receipt,
            )
        apply(state, {"type": "end_activation", "side": state.active_side}, receipt)
    apply(state, {"type": "end_campaign"}, receipt)
    next_muster(state, receipt)


def fair_arbiter(exile):
    state = muster_position(2, 2)
    receipt = []
    # Legal possession of a drawn This-Campaign Event. All later transitions are public.
    for pile in state.decks["yorkist"].values():
        while "Y8" in pile:
            pile.remove("Y8")
    state.active_events.append({"card": "Y8", "side": "yorkist", "scope": "this_campaign"})
    apply(
        state,
        {"type": "levy_capability", "side": "yorkist", "by_lord": "salisbury", "card": "Y22"},
        receipt,
    )
    campaign(state, receipt, exile=exile)
    lord = state.lords["salisbury"]
    assert lord.status == LordStatus.MUSTERED and lord.capabilities == ["Y22"]
    assert (
        (lord.exile_box == "ireland" and lord.location is None)
        if exile
        else lord.location == "york"
    )
    effective = {
        name: ratings.rating(state, "salisbury", name) for name in ("influence", "lordship")
    }
    levy = apply(
        state,
        {"type": "levy_vassal", "side": "yorkist", "by_lord": "salisbury", "target": "dudley"},
        receipt,
    )
    assert levy["roll"] == levy["rating"] == 4
    assert levy["success"]
    transport = {
        "type": "levy_transport",
        "side": "yorkist",
        "by_lord": "salisbury",
        "transport": "cart",
    }
    for _ in range(2):
        apply(state, transport, receipt)
    offered = transport in legal_moves.legal_moves(state)
    fourth = apply(state, transport, receipt)
    assert offered
    assert fourth["added"] == "2 cart"
    return {
        "id": "P9-01",
        "branch": "ireland" if exile else "friendly_york",
        "seed": 2,
        "effective": effective,
        "vassal_check": levy,
        "fourth_levy_offered": offered,
        "fourth_levy": fourth,
        "receipt": receipt,
    }


def alice_montagu(card, turn=14):
    state = muster_position(3, turn)
    receipt = []
    if card:
        apply(
            state,
            {"type": "levy_capability", "side": "yorkist", "by_lord": "salisbury", "card": "Y17"},
            receipt,
        )
    levy = apply(
        state,
        {"type": "levy_vassal", "side": "yorkist", "by_lord": "salisbury", "target": "westmorland"},
        receipt,
    )
    assert levy["success"] and levy["roll"] == 2
    service = state.vassals["westmorland"].service_box
    assert service == turn + 3
    campaign(state, receipt)
    vs = state.vassals["westmorland"]
    pay_entry = next(r for r in receipt if r["action"] == {"type": "pay", "side": "yorkist"})
    pay = pay_entry["result"]
    assert pay["vassals"]["paid"] == []
    influence_paid = pay_entry["influence_after"] - pay_entry["influence_before"]
    assert influence_paid == pay["lords"]["influence_paid"]
    return {
        "id": "P9-02",
        "branch": "alice" if card else "no_card",
        "seed": 3,
        "muster_turn": turn,
        "service_after_muster": service,
        "levy": levy,
        "next_turn": state.turn_box,
        "next_pay": pay,
        "total_influence_paid": influence_paid,
        "vassal_after_pay": vs.model_dump(mode="json"),
        "receipt": receipt,
    }


@pytest.mark.parametrize("exile", [False, True])
def test_fair_arbiter_keeps_both_bonuses_through_exile_and_next_levy(exile):
    result = fair_arbiter(exile)
    assert result["effective"] == {"influence": 4, "lordship": 4}


@pytest.mark.parametrize("card", [False, True])
def test_alice_montagu_does_not_create_a_final_turn_pay_obligation(card):
    alice_montagu(card)


@pytest.mark.parametrize("turn,service", [(10, 14), (11, 15), (12, 16), (13, 16), (14, 17)])
def test_alice_montagu_moves_service_right_once_and_leaves_off_calendar_alone(turn, service):
    state = muster_position(3, turn)
    receipt = []
    apply(
        state,
        {"type": "levy_capability", "side": "yorkist", "by_lord": "salisbury", "card": "Y17"},
        receipt,
    )
    result = apply(
        state,
        {"type": "levy_vassal", "side": "yorkist", "by_lord": "salisbury", "target": "westmorland"},
        receipt,
    )
    assert result["success"]
    assert state.vassals["westmorland"].service_box == service


@pytest.mark.parametrize("status", ["calendar", "removed"])
def test_fair_arbiter_does_not_grant_bonuses_to_an_unmustered_lord(status):
    state = muster_position(3, 2)
    lord = state.lords["salisbury"]
    lord.status, lord.location, lord.exile_box = status, None, "ireland"
    lord.capabilities = ["Y22"]
    assert ratings.rating(state, "salisbury", "influence") == 3
    assert ratings.rating(state, "salisbury", "lordship") == 3
