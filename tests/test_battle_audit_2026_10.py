"""Regressions for Battle fidelity: 1.5.4, 4.4.2–.3, L12, and Y36."""

from __future__ import annotations

import pytest

from plantagenet import battle
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus, VassalState, VassalStatus


class FixedDice:
    def __init__(self, value):
        self.value = value

    def d6(self):
        return self.value


def _colocate(state, ids):
    for lid in ids:
        state.lords[lid].location = "cambridge"
        state.lords[lid].status = LordStatus.MUSTERED


def _fixed_dice(monkeypatch, value):
    monkeypatch.setattr(GameState, "dice", lambda self: FixedDice(value))
    monkeypatch.setattr(GameState, "store_dice", lambda self, dice: None)


def test_partial_flee_stays_routed_until_battle_ending():
    """4.4.2 Flee/Reposition: a fleeing Lord never returns to Unrouted status."""
    s = build_initial_state("henry_vi", seed=1)
    _colocate(s, ["york", "salisbury", "somerset_1"])
    result = battle.resolve_battle(
        s, "cambridge", ["york", "salisbury"], ["somerset_1"],
        {"flee": ["york"], "valour": False},
    )
    assert result["rounds"][0]["fled"] == ["york"]
    assert result["winner_side"] == "lancastrian"
    assert len(result["rounds"]) < 60
    assert "york" in result["deaths"] + result["disbands"]
    assert s.lords["york"].status != LordStatus.MUSTERED


def test_special_vassal_contributes_battle_forces_and_defeat_influence():
    """1.5.4/Forces table/4.4.3: Montagu fights and counts for defeat Influence."""
    s = build_initial_state("somersets_return", seed=1)
    lord = s.lords["warwick_yorkist"]
    assert lord.special_vassals == ["montagu"] and not lord.vassals
    force = battle._Force(s, "warwick_yorkist")
    assert force.count["vassal"] == 1
    assert force.raw_hits("melee") == 8
    _colocate(s, ["warwick_yorkist", "somerset_1"])
    result = battle.resolve_battle(
        s, "cambridge", ["warwick_yorkist"], ["somerset_1"],
        {"flee": ["warwick_yorkist"]},
    )
    assert result["influence_award"]["lancastrian"] == 6


@pytest.mark.parametrize("target", ["devon", "montagu"])
def test_owner_selects_regular_or_special_vassal_to_absorb_hit(monkeypatch, target):
    """4.4.2–.3/1.5.4/L23: only the chosen Vassal Disbands; its card follows."""
    s = build_initial_state("somersets_return", seed=1)
    _colocate(s, ["warwick_yorkist", "somerset_1"])
    lord = s.lords["warwick_yorkist"]
    lord.vassals = ["devon"]
    s.vassals["devon"] = VassalState(
        vassal_id="devon", status=VassalStatus.MUSTERED,
        on_lord="warwick_yorkist", service_box=5,
    )
    forces = {lid: battle._Force(s, lid) for lid in ["warwick_yorkist", "somerset_1"]}
    battle._apply_special_vassal_armour(s, forces)
    force = forces["warwick_yorkist"]
    log = []
    battle._absorb_side(
        [force], 1, FixedDice(6), battle._ABSORB_DEFAULT, False, log,
        plan=[{"lord": "warwick_yorkist", "unit": "vassal", "vassal": target}],
    )
    assert log[0]["vassal"] == target
    assert force.routed_vassal_ids == [target]
    assert force.avail("vassal") == 1
    assert force.raw_hits("melee") == 8
    assert force.prot_range("retinue", "melee") == [1, 5]  # L23 lasts through Battle
    assert "L23" in lord.capabilities
    forces["somerset_1"].lord_routed = True
    _fixed_dice(monkeypatch, 1)
    result = battle._ending(
        s, "cambridge", forces, ["warwick_yorkist"], ["somerset_1"], [], [],
    )
    assert result["vassal_disbands"] == [target]
    assert ("montagu" in lord.special_vassals) == (target != "montagu")
    assert ("L23" in lord.capabilities) == (target != "montagu")
    assert ("devon" in lord.vassals) == (target != "devon")
    if target == "montagu":
        assert s.decks["yorkist"]["discard"].count("L23") == 1


def test_ravine_recomputes_flanking_against_the_empty_position(monkeypatch):
    """L12 Tips/4.4.2 Engage: the ignored position is empty for Flanking."""
    s = build_initial_state("henry_vi", seed=1)
    _colocate(s, ["york", "salisbury", "henry_vi", "somerset_1"])
    s.decks["lancastrian"]["held"] = ["L12"]
    _fixed_dice(monkeypatch, 1)
    result = battle.resolve_battle(
        s, "cambridge", ["york", "salisbury"], ["henry_vi", "somerset_1"],
        {"ravine": "york", "flee_rounds": {"henry_vi": 3, "somerset_1": 3}},
    )
    first = result["rounds"][0]["engagements"]
    assert len(first) == 1
    assert first[0]["attacker"] == ["salisbury"]
    assert set(first[0]["defender"]) == {"henry_vi", "somerset_1"}
    assert any("york" in e["attacker"] for e in result["rounds"][1]["engagements"])


@pytest.mark.parametrize("phase", ["missile", "melee"])
@pytest.mark.parametrize("end_round", [True, False])
def test_swift_maneuver_interrupts_immediately_if_selected(monkeypatch, phase, end_round):
    """Y36 Tips: skip remaining Hits immediately on Retinue Rout, if desired."""
    s = build_initial_state("henry_vi", seed=1)
    _colocate(s, ["york", "somerset_1"])
    unit = "longbow" if phase == "missile" else "men_at_arms"
    s.lords["york"].forces = {"retinue": 1, unit: 2}
    s.lords["somerset_1"].forces = {"retinue": 1, "men_at_arms": 3}
    s.decks["yorkist"]["held"] = ["Y36"]
    _fixed_dice(monkeypatch, 6)
    result = battle.resolve_battle(
        s, "cambridge", ["york"], ["somerset_1"],
        {"swift_maneuver": "yorkist", "swift_maneuver_end": end_round,
         "valour": False, "absorb_order": ["retinue", "longbow", "men_at_arms"]},
    )
    strikes = result["rounds"][0]["engagements"][0]["strikes"]
    hit_step = next(step for step in strikes if step["phase"] == phase)
    assert hit_step["defender_rolls"][0]["unit"] == "retinue"
    assert hit_step["defender_rolls"][0]["saved"] is False
    if end_round:
        assert len(hit_step["defender_rolls"]) == 1
        assert hit_step["attacker_rolls"] == []
        assert strikes[-1]["phase"] == phase
    else:
        assert len(hit_step["defender_rolls"]) > 1
        assert strikes[-1]["phase"] == "melee"
