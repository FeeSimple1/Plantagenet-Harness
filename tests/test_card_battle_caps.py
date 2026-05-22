"""Wave C1: battle troop-add and uniform-armour Capabilities (1.9.1)."""

from __future__ import annotations

from plantagenet import battle
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _force(state, lord_id, location, favour=None, caps=None):
    ls = state.lords[lord_id]
    ls.status = LordStatus.MUSTERED.value
    ls.location = location
    ls.capabilities = list(caps or [])
    if favour is not None:
        state.locales[location].favour = favour
    return battle._Force(state, lord_id)


def test_musterd_my_soldiers_at_friendly_stronghold():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "cambridge", favour="yorkist", caps=["Y3"])
    base_maa = f.count.get("men_at_arms", 0)
    base_lb = f.count.get("longbow", 0)
    forces = {"york": f}
    battle._apply_battle_troop_caps(s, forces, "cambridge")
    assert f.count["men_at_arms"] == base_maa + 2
    assert f.count["longbow"] == base_lb + 1


def test_musterd_my_soldiers_not_at_friendly_stronghold():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "cambridge", favour="lancastrian", caps=["Y3"])
    base = f.count.get("men_at_arms", 0)
    battle._apply_battle_troop_caps(s, {"york": f}, "cambridge")
    assert f.count.get("men_at_arms", 0) == base


def test_pembroke_adds_longbow_in_wales():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "pembroke", caps=["Y25"])     # pembroke is in Wales
    base = f.count.get("longbow", 0)
    battle._apply_battle_troop_caps(s, {"york": f}, "pembroke")
    assert f.count["longbow"] == base + 2


def test_percys_north_y27_militia_in_north_only():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "newcastle", caps=["Y27"])    # newcastle is North
    base = f.count.get("militia", 0)
    battle._apply_battle_troop_caps(s, {"york": f}, "newcastle")
    assert f.count["militia"] == base + 4
    # not in the North -> nothing added
    f2 = _force(s, "york", "cambridge", caps=["Y27"])
    base2 = f2.count.get("militia", 0)
    battle._apply_battle_troop_caps(s, {"york": f2}, "cambridge")
    assert f2.count.get("militia", 0) == base2


def test_percys_north_y37_route_to_carlisle():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "carlisle", caps=["Y37"])     # at Carlisle: Route trivially exists
    base = f.count.get("men_at_arms", 0)
    battle._apply_battle_troop_caps(s, {"york": f}, "carlisle")
    assert f.count["men_at_arms"] == base + 2


def test_philibert_at_friendly_english_channel_port():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "dover", favour="yorkist", caps=["L33"])   # dover is an EC Port
    base = f.count.get("men_at_arms", 0)
    battle._apply_battle_troop_caps(s, {"york": f}, "dover")
    assert f.count["men_at_arms"] == base + 2


def test_church_blessing_men_at_arms_armour_one_to_four():
    s = build_initial_state("henry_vi")
    f = _force(s, "york", "cambridge", caps=["L5"])
    battle._apply_armour_caps(s, {"york": f})
    assert f.prof["men_at_arms"]["prot"] == [1, 4]
