"""Battle engine and Approach/Exile (4.3.5, 4.4)."""

from __future__ import annotations

from plantagenet import battle
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _two_lords_at(loc, seed=1):
    s = build_initial_state("henry_vi", seed=seed)
    s.lords["york"].location = loc
    s.lords["henry_vi"].location = loc
    return s


def test_strike_hit_totals_match_forces_table():
    # Background Book example: 5 Longbow + 4 Militia -> 12 Missile Hits.
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1, "longbow": 5, "militia": 4}
    f = battle._Force(s, "york")
    assert f.hits("missile") == 12
    assert f.hits("melee") == 5            # Retinue 3 + 4 Militia x 0.5 = 5


def test_lord_routs_when_retinue_routs():
    s = build_initial_state("henry_vi")
    f = battle._Force(s, "york")
    f.routed["retinue"] = 1                # Retinue Routed
    assert f.is_lord_routed() is True


def test_lord_routs_when_all_troops_rout():
    s = build_initial_state("henry_vi")
    f = battle._Force(s, "york")
    for t in ("men_at_arms", "longbow", "militia"):
        f.routed[t] = f.count.get(t, 0)    # all Troops Routed (Retinue intact)
    assert f.is_lord_routed() is True


def test_flee_routs_immediately_and_other_side_wins():
    s = _two_lords_at("cambridge", seed=2)
    # Attacker (York) Flees -> immediately Routs; Defender (Henry VI) wins.
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"flee": ["york"]})
    assert r["winner"] == "henry_vi"
    # Winner gains the loser's printed Influence + 1 per Vassal.
    assert r["influence_award"]["lancastrian"] == 5   # York's Influence rating


def test_battle_winner_gains_influence_and_loser_removed_or_disbanded():
    s = _two_lords_at("cambridge", seed=7)
    r = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {})
    assert r["rounds"]
    # Whichever Lords Routed are Dead (REMOVED) or Disbanded (CALENDAR).
    for lid in r["deaths"]:
        assert s.lords[lid].status == LordStatus.REMOVED
    for lid in r["disbands"]:
        assert s.lords[lid].status == LordStatus.CALENDAR


def test_spoils_all_when_stronghold_favours_winner():
    s = _two_lords_at("cambridge", seed=2)
    s.locales["cambridge"].favour = "lancastrian"   # favours Henry VI (the winner here)
    s.lords["york"].assets["cart"] = 2
    s.lords["york"].assets["provender"] = 2
    hv_cart = s.lords["henry_vi"].assets.get("cart", 0)
    battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"flee": ["york"]})
    # York Routed (Fled); Henry VI takes all of York's Carts (favours winner).
    assert s.lords["henry_vi"].assets["cart"] == hv_cart + 2


def test_approach_exile_disbands_to_calendar_with_exile_marker():
    s = _two_lords_at("cambridge", seed=1)
    s.locales["cambridge"].favour = "yorkist"
    york_cart = s.lords["york"].assets.get("cart", 0)
    hv_cart = s.lords["henry_vi"].assets.get("cart", 0)
    r = battle.approach(s, "cambridge", ["york"], {"responses": {"henry_vi": "exile"}})
    assert r["exiles"] == ["henry_vi"] and r["battle"] is None
    assert s.lords["henry_vi"].status == LordStatus.CALENDAR
    assert s.lords["henry_vi"].calendar_exile is True
    # Stronghold Favours York -> York takes all of Henry's Carts as Spoils.
    assert s.lords["york"].assets["cart"] == york_cart + hv_cart


def test_approach_battle_resolves_when_defender_defends():
    s = _two_lords_at("cambridge", seed=5)
    r = battle.approach(s, "cambridge", ["york"], {"responses": {"henry_vi": "battle"}})
    assert r["battle"] is not None
    assert r["battle"]["attacker"] == "york" and r["battle"]["defender"] == "henry_vi"


def test_multi_lord_battle_deferred_to_3b_ii():
    import pytest

    from plantagenet.errors import IllegalAction
    s = _two_lords_at("cambridge")
    s.lords["somerset_1"].location = "cambridge"   # a second Lancastrian Defender
    with pytest.raises(IllegalAction) as e:
        battle.approach(s, "cambridge", ["york"], {})
    assert e.value.code == "multi_lord_battle_phase_3b_ii"
