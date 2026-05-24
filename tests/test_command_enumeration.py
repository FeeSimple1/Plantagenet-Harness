"""legal_moves must OFFER the legal Command actions a player needs, not just
accept them when constructed by hand (regression for under-enumeration found in
a Towton playthrough): marches into enemy contact, Group Marches, and Parley at
the Lord's own non-Friendly location."""

from __future__ import annotations

from plantagenet import actions, legal_moves
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster


def _into_activation(scenario="towton", seed=1):
    s = build_initial_state(scenario, seed=seed)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    n = s.campaign.cards_required
    for side in ("lancastrian", "yorkist"):
        lords = [lid for lid, v in s.lords.items()
                 if v.side == side and v.status == "mustered"]
        plan = [{"lord": lid} for lid in lords][:n]
        while len(plan) < n:
            plan.append({"pass": True})
        actions.apply_action(s, {"type": "build_plan", "side": side, "plan": plan})
    return s


def _activate(s, lord_id):
    for _ in range(20):
        if s.campaign.step != "activation" or s.campaign.active_lord == lord_id:
            break
        actions.apply_action(s, {"type": "end_activation", "side": s.active_side})
    assert s.campaign.active_lord == lord_id
    return s


def test_group_march_is_offered():
    # Warwick (Lieutenant) at London with March + Norfolk co-located.
    s = _activate(_into_activation(), "warwick_yorkist")
    moves = legal_moves.legal_moves(s)
    groups = [m for m in moves if m["type"] == "march" and m.get("group")]
    assert groups, "no Group March offered"
    assert any(set(m["group"]) == {"march", "norfolk"} for m in groups)


def test_march_into_enemy_contact_is_offered_and_accepted():
    s = _activate(_into_activation(), "somerset_1")
    here = s.lords["somerset_1"].location
    target = [n for n, _t in actions._adjacency().get(here, [])][0]
    s.lords["march"].location = target            # Yorkist enemy at the target
    moves = legal_moves.legal_moves(s)
    contact = [m for m in moves if m["type"] == "march" and m["to"] == target]
    assert contact, "march into enemy-held locale not offered"
    # round-trip: the handler accepts the offered move (resolves an Approach).
    probe = s.model_copy(deep=True)
    actions.apply_action(probe, contact[0])       # no IllegalAction


def test_own_location_parley_offered_on_non_friendly_stronghold():
    s = _activate(_into_activation(), "somerset_1")
    here = s.lords["somerset_1"].location
    s.locales[here].favour = "neutral"            # standing on a non-Friendly Locale
    moves = legal_moves.legal_moves(s)
    own = [m for m in moves if m["type"] == "parley" and m["target"] == here]
    assert own, "own-location Parley not offered while on a non-Friendly Stronghold"
    probe = s.model_copy(deep=True)
    actions.apply_action(probe, own[0])           # auto-success, no IllegalAction
    assert probe.locales[here].favour == "lancastrian"
