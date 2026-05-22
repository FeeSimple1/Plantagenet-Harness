"""Special Vassal effects (1.5.4; Capabilities Y24/L19/L21/L23/L26/L35)."""

from __future__ import annotations

from plantagenet import actions, battle, campaign, ratings
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def test_effective_rating_adds_special_vassal_modifiers():
    s = build_initial_state("henry_vi")
    base_v = ratings.rating(s, "henry_vi", "valour")
    s.lords["henry_vi"].special_vassals = ["clifford"]      # Valour +1
    assert ratings.rating(s, "henry_vi", "valour") == base_v + 1
    s2 = build_initial_state("warwicks_rebellion")          # has Edward IV
    base_c = ratings.rating(s2, "edward_iv", "command")
    s2.lords["edward_iv"].special_vassals = ["hastings"]    # Command +1
    assert ratings.rating(s2, "edward_iv", "command") == base_c + 1


def test_levy_capability_musters_hastings_and_adds_men_at_arms():
    s = build_initial_state("warwicks_rebellion")           # Edward IV (Yorkist King) at London
    to_muster(s)
    # Yorkist is King here -> Lancastrian Rebel acts first; pass to Yorkist Muster.
    while s.active_side != "yorkist":
        actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    ed = s.lords["edward_iv"]
    ed.capabilities = []
    maa = ed.forces.get("men_at_arms", 0)
    r = actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                                 "by_lord": "edward_iv", "card": "Y24"})
    assert r["special_vassal"] == "hastings"
    assert "hastings" in ed.special_vassals
    assert ed.forces["men_at_arms"] == maa + 2              # Hastings adds 2 Men-at-Arms
    assert ratings.rating(s, "edward_iv", "command") == \
        2 + 1                                              # Edward IV Command 2, +1 Hastings


def test_montagu_gives_retinue_armour_one_to_five_in_battle():
    s = build_initial_state("henry_vi")
    s.lords["warwick_yorkist"].location = "cambridge"
    s.lords["henry_vi"].location = "cambridge"
    s.lords["warwick_yorkist"].special_vassals = ["montagu"]
    forces = {lid: battle._Force(s, lid) for lid in ("warwick_yorkist", "henry_vi")}
    battle._apply_special_vassal_armour(s, forces)
    assert forces["warwick_yorkist"].prof["retinue"]["prot"] == [1, 5]
    assert forces["henry_vi"].prof["retinue"]["prot"] == [1, 4]   # unaffected


def test_thomas_stanley_free_levy_troops_once_when_lordship_spent():
    s = build_initial_state("my_kingdom_for_a_horse")      # Lancastrian Rebel; Jasper in France
    to_muster(s)
    jt = s.lords["jasper_tudor_2"]
    jt.special_vassals = ["thomas_stanley"]
    jt.location = "pembroke"                                # a Friendly Stronghold to Levy Troops
    s.locales["pembroke"].favour = "lancastrian"
    jt.lordship_spent = actions._lordship("jasper_tudor_2")  # Lordship exhausted
    r = actions.apply_action(s, {"type": "levy_troops", "side": "lancastrian",
                                 "by_lord": "jasper_tudor_2"})
    assert r["stanley_free"] is True                        # free Levy despite no Lordship
    assert jt.free_troops_used is True


def test_disband_discards_capabilities_and_special_vassals():
    s = build_initial_state("henry_vi")
    lord = s.lords["york"]
    lord.capabilities = ["Y1"]
    lord.special_vassals = ["clifford"]
    campaign._disband_lord(s, lord)
    assert lord.capabilities == [] and lord.special_vassals == []
    assert "Y1" in s.decks["yorkist"]["discard"]
    assert lord.status == LordStatus.CALENDAR
