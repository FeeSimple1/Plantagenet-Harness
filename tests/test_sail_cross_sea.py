"""Sail across Seas (4.6.1 / FAQ #1): no direct Port-to-Port hop across Seas --
cross-Sea movement transits at Sea (into an adjacent Sea, then to a Port)."""

from __future__ import annotations

import pytest

from plantagenet import actions, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster


def _sailor_at(locale, sea_favour="lancastrian"):
    s = build_initial_state("henry_vi")
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian" and v.status == "mustered"]
    n = s.campaign.cards_required

    def pad(lo):
        e = [{"lord": x} for x in lo][:n]
        while len(e) < n:
            e.append({"pass": True})
        return e
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": pad(yk)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": pad(lc)})
    lid = lc[0]
    s.active_side = "lancastrian"
    s.campaign.active_lord = lid
    s.campaign.actions_remaining = 2
    s.lords[lid].location = locale
    s.locales[locale].favour = sea_favour
    s.lords[lid].assets["ship"] = 5
    s.lords[lid].forces = {"retinue": 1}
    return s, lid


def test_direct_port_to_port_across_seas_is_rejected():
    # bristol (Irish Sea) -> southampton (English Channel): no direct cross-Sea hop.
    s, lid = _sailor_at("bristol")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "southampton"})
    assert e.value.code == "cross_sea_port_to_port"


def test_same_sea_port_to_port_still_allowed():
    s, lid = _sailor_at("bristol")
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "pembroke"})   # both Irish Sea
    assert r["to"] == "pembroke"


def test_cross_sea_travel_via_at_sea_transit():
    s, lid = _sailor_at("bristol")
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lid, "to": "english_channel"})   # into adjacent Sea
    assert s.lords[lid].at_sea == "english_channel"
    s.campaign.actions_remaining = 2                       # next Command card
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lid, "to": "southampton"})   # at Sea -> Port
    assert r["to"] == "southampton" and s.lords[lid].location == "southampton"


def test_enumerator_offers_no_cross_sea_port_to_port():
    s, lid = _sailor_at("bristol")
    moves = legal_moves.legal_moves(s)
    sail_ports = {m["to"] for m in moves if m["type"] == "sail" and m["to"] in s.locales}
    # Reachable Sail Ports must all be on the Irish Sea (same Sea as bristol).
    assert "pembroke" in sail_ports and "harlech" in sail_ports
    assert "southampton" not in sail_ports and "dover" not in sail_ports
    # The cross-Sea path is offered as a "sail into a Sea" move instead.
    assert {"type": "sail", "side": "lancastrian", "by_lord": lid,
            "to": "english_channel"} in moves
