"""Phase 5a: the reaction protocol (Q-004), proven on Naval Blockade gating a
Lancastrian Sail -- pause/resolve loop, decline, cancel, and serializability."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState
from tests._helpers import to_muster


def _setup(seed=1):
    """A campaign with a Lancastrian Lord ready to Sail Irish-Sea ports, and a
    Yorkist Warwick holding Naval Blockade (Y15) at a Port on that Sea."""
    s = build_initial_state("henry_vi", seed=seed)
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

    lanc = lc[0]
    s.active_side = "lancastrian"
    s.campaign.active_lord = lanc
    s.campaign.actions_remaining = 2
    lord = s.lords[lanc]
    lord.location = "bristol"           # Irish Sea Port
    s.locales["bristol"].favour = "lancastrian"
    lord.assets["ship"] = 5
    lord.forces = {"retinue": 1}
    # Yorkist Warwick with Naval Blockade at Harlech (Irish Sea).
    wk = yk[0]
    s.lords[wk].location = "harlech"
    s.locales["harlech"].favour = "yorkist"
    s.lords[wk].capabilities = ["Y15"]
    return s, lanc, wk


def test_sail_pauses_for_naval_blockade():
    s, lanc, _wk = _setup()
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lanc, "to": "pembroke"})
    assert r["type"] == "pending_reactions"
    assert r["awaiting"]["card"] == "Y15" and r["awaiting"]["side"] == "yorkist"
    assert s.pending                                  # interaction recorded on state
    # While pending, ordinary actions are refused.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "pass", "side": "lancastrian"})
    assert e.value.code == "reaction_pending"


def test_command_cost_is_spent_before_the_blockade_roll():
    s, lanc, _wk = _setup()
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lanc, "to": "pembroke"})
    assert s.campaign.actions_remaining == 0          # whole Command card spent regardless


def test_blockade_roll_decides_cancel_or_proceed():
    # Sweep seeds to observe both a blocking (3-6) and a non-blocking (1-2) roll.
    saw_block = saw_pass = False
    for seed in range(1, 40):
        s, lanc, _wk = _setup(seed=seed)
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lanc, "to": "pembroke"})
        r = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y15"})
        roll = r["reactions"][0]["roll"]
        if roll > 2:
            assert r.get("cancelled") is True         # blockaded -> Sail cancelled
            assert s.lords[lanc].location == "bristol"
            saw_block = True
        else:
            assert r["to"] == "pembroke"              # 1-2 -> Sail proceeds
            assert s.lords[lanc].location == "pembroke"
            saw_pass = True
        assert not s.pending                          # interaction cleared
    assert saw_block and saw_pass


def test_decline_lets_the_action_proceed():
    s, lanc, _wk = _setup()
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lanc, "to": "pembroke"})
    r = actions.apply_action(s, {"type": "react", "side": "yorkist", "pass": True})
    assert r["to"] == "pembroke"
    assert s.lords[lanc].location == "pembroke"


def test_paused_state_round_trips_through_serialization():
    s, lanc, _wk = _setup()
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lanc, "to": "pembroke"})
    blob = s.model_dump_json()
    s2 = GameState.model_validate_json(blob)          # save + reload mid-reaction
    assert s2.pending and s2.pending[0]["resume_key"] == "commands:sail_finish"
    r = actions.apply_action(s2, {"type": "react", "side": "yorkist", "pass": True})
    assert r["to"] == "pembroke"
    assert s2.lords[lanc].location == "pembroke"
    assert not s2.pending


def test_no_blockade_when_warwick_off_the_sea():
    s, lanc, wk = _setup()
    s.lords[wk].location = "ipswich"                  # North Sea, not Irish Sea
    s.locales["ipswich"].favour = "yorkist"
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lanc, "to": "pembroke"})
    assert r["type"] == "sail" and r["to"] == "pembroke"   # no reaction window
