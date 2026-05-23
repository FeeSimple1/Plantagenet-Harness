"""For Trust Not Him (L7): in-Battle Levy of a regular Enemy Vassal (4.4.1)."""

from __future__ import annotations

import pytest

from plantagenet import battle
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus, VassalState, VassalStatus


def _battle_with_vassal(seed=1, owner="york", vid="beaumont", give_alice=False):
    """Lancastrian Henry VI vs a Yorkist Lord that holds a regular Vassal on
    its mat; Lancastrians hold L7. Both Lords at cambridge."""
    s = build_initial_state("henry_vi", seed=seed)
    for lid in ("henry_vi", owner):
        s.lords[lid].location = "cambridge"
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].capabilities = []
    if give_alice:
        s.lords[owner].capabilities = ["Y17"]            # Alice Montagu
    s.lords[owner].vassals = [vid]
    s.vassals[vid] = VassalState(vassal_id=vid, status=VassalStatus.MUSTERED,
                                 on_lord=owner, service_box=2)
    s.decks["lancastrian"]["held"] = ["L7"]
    return s


def _resolve(s):
    """Resolve L7 at the Event step (before Rounds) and return the outcome."""
    forces = {lid: battle._Force(s, lid) for lid in ("henry_vi", "york")}
    out = battle._resolve_for_trust(
        s, ["henry_vi"], ["york"], forces,
        {"for_trust_not_him": {"by": "henry_vi", "target": "beaumont"}})
    return out, forces


def test_for_trust_captures_enemy_vassal_on_success():
    won = False
    for seed in range(1, 20):
        s = _battle_with_vassal(seed=seed)
        out, _ = _resolve(s)
        assert out["by"] == "henry_vi" and out["from_lord"] == "york"
        assert "L7" not in s.decks["lancastrian"]["held"]    # Hold Event used either way
        if out["success"]:
            won = True
            v = s.vassals["beaumont"]
            assert v.on_lord == "henry_vi"                   # marker moved to the Lanc mat
            assert "beaumont" in s.lords["henry_vi"].vassals
            assert "beaumont" not in s.lords["york"].vassals
            assert v.service_box == s.turn_box + 1           # shifted as if newly Levied
            break
    assert won


def test_for_trust_keeps_vassal_on_failure_but_consumes_card():
    failed = False
    for seed in range(1, 60):
        s = _battle_with_vassal(seed=seed)
        out, _ = _resolve(s)
        if not out["success"]:
            failed = True
            assert s.vassals["beaumont"].on_lord == "york"   # unchanged
            assert "beaumont" in s.lords["york"].vassals
            assert "beaumont" not in s.lords["henry_vi"].vassals
            assert "L7" not in s.decks["lancastrian"]["held"]   # card still spent
            break
    assert failed


def test_for_trust_swings_the_current_battle_force():
    """On success the captured Vassal counter fights this Battle for its new
    Lord: +1 vassal unit to the Levying side, -1 from the former owner."""
    for seed in range(1, 20):
        s = _battle_with_vassal(seed=seed)
        forces = {lid: battle._Force(s, lid) for lid in ("henry_vi", "york")}
        before_by = forces["henry_vi"].count.get("vassal", 0)
        before_old = forces["york"].count.get("vassal", 0)
        out = battle._resolve_for_trust(
            s, ["henry_vi"], ["york"], forces,
            {"for_trust_not_him": {"by": "henry_vi", "target": "beaumont"}})
        if out["success"]:
            assert forces["henry_vi"].count["vassal"] == before_by + 1
            assert forces["york"].count["vassal"] == before_old - 1
            return
    pytest.fail("no successful seed found")


def test_for_trust_alice_montagu_vassal_immune():
    s = _battle_with_vassal(owner="salisbury", give_alice=True)
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "henry_vi", "salisbury",
                              {"for_trust_not_him": {"by": "henry_vi", "target": "beaumont"}})
    assert e.value.code == "for_trust_immune"


def test_for_trust_rejects_own_and_off_battle_vassals():
    # Targeting a Friendly (Lancastrian) Vassal is illegal.
    s = _battle_with_vassal()
    s.lords["york"].vassals = []
    s.lords["henry_vi"].vassals = ["beaumont"]
    s.vassals["beaumont"] = VassalState(vassal_id="beaumont", status=VassalStatus.MUSTERED,
                                        on_lord="henry_vi", service_box=2)
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "henry_vi", "york",
                              {"for_trust_not_him": {"by": "henry_vi", "target": "beaumont"}})
    assert e.value.code == "for_trust_own_vassal"

    # A Vassal not on a participating Lord's mat cannot be taken.
    s2 = _battle_with_vassal()
    s2.lords["york"].vassals = []
    s2.vassals["beaumont"] = VassalState(vassal_id="beaumont", status=VassalStatus.AT_SEAT,
                                         location="lincoln")
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s2, "cambridge", "henry_vi", "york",
                              {"for_trust_not_him": {"by": "henry_vi", "target": "beaumont"}})
    assert e.value.code == "for_trust_not_in_battle"


def test_for_trust_requires_held_event():
    s = _battle_with_vassal()
    s.decks["lancastrian"]["held"] = []                  # no L7 to play
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "henry_vi", "york",
                              {"for_trust_not_him": {"by": "henry_vi", "target": "beaumont"}})
    assert e.value.code == "no_for_trust"
