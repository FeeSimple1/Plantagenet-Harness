"""Regression tests for the June 2026 rules-audit fixes.

Each test pins a specific bug found during the audit; comments cite the rule and
the audit item. These exercise behaviour the prior suite did not cover.
"""

from __future__ import annotations

from plantagenet import actions, battle, campaign, events, influence, succession
from plantagenet import pay as pay_mod
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordState, LordStatus, VassalStatus


# --------------------------------------------------------------------------- #
# CRITICAL: Succession permanent ADD cards survive later King changes (6.2/E2)  #
# --------------------------------------------------------------------------- #
def _stage_iiy():
    s = build_initial_state("wars_of_the_roses", seed=1)
    gs = s.grand_scenario
    gs["current_war"] = "war_iiy"
    gs["deck_sources"] = {}
    gs["set_aside_on_disband"] = {}
    gs["succession_fired"] = []
    gs["current_king"] = {}
    for _lid, ls in s.lords.items():
        if ls.side == "yorkist":
            ls.status = LordStatus.AVAILABLE.value
    for lid in ("york", "march", "rutland", "gloucester_1"):
        if lid not in s.lords:
            s.lords[lid] = LordState(lord_id=lid, side="yorkist",
                                     status=LordStatus.AVAILABLE.value)
        s.lords[lid].status = LordStatus.MUSTERED.value
        s.lords[lid].location = "london"
    for lid in ("edward_iv", "richard_iii", "pembroke"):
        if lid not in s.lords:
            s.lords[lid] = LordState(lord_id=lid, side="yorkist",
                                     status=LordStatus.AVAILABLE.value)
    s.decks["yorkist"] = {"draw": [], "discard": [], "held": [], "set_aside": []}
    succession.apply_setup(s)
    return s


def _ydeck(s):
    d = s.decks["yorkist"]
    return set(d["draw"]) | set(d["discard"]) | set(d["held"])


def test_edward_iv_permanent_cards_survive_repeated_recompute():
    s = _stage_iiy()
    s.lords["york"].status = LordStatus.REMOVED.value     # March -> Edward IV (King)
    succession.on_heir_removed(s, "york")
    assert {"Y23", "Y24", "Y28", "Y31"} <= _ydeck(s)
    assert s.grand_scenario["current_king"]["yorkist"] == "edward_iv"
    succession._recompute(s, "yorkist")
    succession._recompute(s, "yorkist")
    assert {"Y23", "Y24", "Y28", "Y31"} <= _ydeck(s)


def test_richard_iii_permanent_cards_survive():
    s = _stage_iiy()
    for lid in ("york", "rutland"):
        s.lords[lid].status = LordStatus.REMOVED.value
        succession.on_heir_removed(s, lid)
    s.lords["edward_iv"].status = LordStatus.REMOVED.value  # Gloucester(1) -> Richard III
    succession.on_heir_removed(s, "edward_iv")
    assert s.grand_scenario["current_king"]["yorkist"] == "richard_iii"
    assert {"Y32", "Y33", "Y34", "Y35"} <= _ydeck(s)
    succession._recompute(s, "yorkist")
    assert {"Y23", "Y24", "Y31", "Y32", "Y33", "Y34", "Y35"} <= _ydeck(s)


# --------------------------------------------------------------------------- #
# HIGH: battle Losses must not disband a victorious Retinue-only Lord (4.4.3)   #
# --------------------------------------------------------------------------- #
def test_retinue_only_winner_not_disbanded():
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1}
    f = battle._Force(s, "york")
    res: dict = {}
    battle._losses(s, f, s.dice(), res)
    assert "loss_disbands" not in res
    assert s.lords["york"].status == LordStatus.MUSTERED


def test_winner_losing_all_troops_is_disbanded():
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1, "men_at_arms": 1}
    f = battle._Force(s, "york")
    f.routed["men_at_arms"] = 1
    s.lords["york"].forces["men_at_arms"] = 0
    res: dict = {}
    battle._losses(s, f, s.dice(), res)
    assert res.get("loss_disbands") == ["york"]


# --------------------------------------------------------------------------- #
# HIGH: Bloody Thou Art (Y33) blocks upon-Death cards; routed Yorkists Disband  #
# --------------------------------------------------------------------------- #
def test_bloody_thou_art_blocks_escape_ship_and_disbands_yorkist():
    s = build_initial_state("henry_vi")
    s.lords["henry_vi"].location = "dover"
    s.locales["dover"].favour = "lancastrian"
    s.decks.setdefault("lancastrian", {}).setdefault("held", []).append("L3")
    s.lords["richard_iii"] = LordState(lord_id="richard_iii", side="yorkist",
                                       status=LordStatus.MUSTERED, location="dover",
                                       forces={"retinue": 1}, capabilities=["Y33"])
    f_rich = battle._Force(s, "richard_iii")
    f_hen = battle._Force(s, "henry_vi")
    f_hen.lord_routed = True
    f_york = battle._Force(s, "york")
    f_york.lord_routed = True
    forces = {"richard_iii": f_rich, "york": f_york, "henry_vi": f_hen}
    battle._ending(s, "dover", forces, ["richard_iii", "york"], ["henry_vi"], [], ["henry_vi"])
    assert s.lords["henry_vi"].status == LordStatus.REMOVED      # Died, not escaped
    assert "L3" in s.decks["lancastrian"]["held"]               # card NOT consumed
    assert s.lords["york"].status == LordStatus.CALENDAR        # routed Yorkist Disbands


# --------------------------------------------------------------------------- #
# HIGH/MEDIUM: Parley Influence discounts (Y4, Y18/L18) and An Honest Tale      #
# --------------------------------------------------------------------------- #
def test_check_influence_discount_can_reach_zero():
    s = build_initial_state("henry_vi")
    before = s.influence["track"]
    chk = influence.check_influence(s, "york", "yorkist", discount=1)
    assert chk["spent"] == 0
    assert s.influence["track"] == before


def test_an_honest_tale_raises_cost():
    s = build_initial_state("henry_vi")
    chk = influence.check_influence(s, "henry_vi", "lancastrian", discount=-1)
    assert chk["spent"] == 2


# --------------------------------------------------------------------------- #
# MEDIUM: Spoils at a Neutral locale total-then-halve, not per-loser (4.4.3)    #
# --------------------------------------------------------------------------- #
def test_spoils_neutral_total_then_halve():
    s = build_initial_state("henry_vi")
    s.locales["london"].favour = "neutral"
    s.lords["york"].location = "london"
    s.lords["york"].assets = {}
    s.lords["henry_vi"].assets = {"cart": 1, "provender": 0}
    s.lords["somerset_1"] = LordState(lord_id="somerset_1", side="lancastrian",
                                      status=LordStatus.MUSTERED, location="london",
                                      assets={"cart": 1, "provender": 0})
    winner = battle._Force(s, "york")
    res: dict = {}
    battle._spoils(s, "london", [winner], ["henry_vi", "somerset_1"], res)
    assert res["spoils"]["cart"] == 1                   # ceil(2/2), not 1+1
    assert s.lords["york"].assets.get("cart", 0) == 1


# --------------------------------------------------------------------------- #
# MEDIUM: London For York (Y15) never adds a third Favour marker                #
# --------------------------------------------------------------------------- #
def test_london_for_york_caps_at_second_marker():
    s = build_initial_state("henry_vi")
    s.locales["london"].favour = "yorkist"
    s.locales["london"].favour_extra = 0
    assert events._london_for_york(s, "yorkist", {})["second_favour"] is True
    assert s.locales["london"].favour_extra == 1
    assert events._london_for_york(s, "yorkist", {})["second_favour"] is False
    assert s.locales["london"].favour_extra == 1


# --------------------------------------------------------------------------- #
# HIGH: Special Vassal Hastings counted (L15) and targetable (L27)              #
# --------------------------------------------------------------------------- #
def test_l15_counts_special_vassal_hastings():
    s = build_initial_state("wars_of_the_roses")
    ed = s.lords.setdefault("edward_iv", LordState(lord_id="edward_iv", side="yorkist",
                                                   status=LordStatus.MUSTERED))
    ed.side = "yorkist"
    ed.status = LordStatus.MUSTERED
    ed.special_vassals = ["hastings"]
    t = s.influence["track"]
    before = (t.marker_side, t.marker_at)
    out = events._henry_pressures_parliament(s, "lancastrian", {})
    assert out["yorkist_influence_lost"] >= 1
    assert (t.marker_side, t.marker_at) != before        # Yorkist Influence moved


def test_l27_targets_special_vassal_hastings():
    s = build_initial_state("wars_of_the_roses")
    ed = s.lords.setdefault("edward_iv", LordState(lord_id="edward_iv", side="yorkist",
                                                   status=LordStatus.MUSTERED))
    ed.side = "yorkist"
    ed.status = LordStatus.MUSTERED
    ed.special_vassals = ["hastings"]
    ed.capabilities = ["Y24"]
    # Hastings is a legal target (no bad_vassal); a check is performed for it.
    out = events._luniverselle_aragne(s, "lancastrian", {"vassals": ["hastings"]})
    assert out["checks"][0]["vassal"] == "hastings"


def test_disband_special_vassal_discards_capability():
    s = build_initial_state("wars_of_the_roses")
    ed = s.lords.setdefault("edward_iv", LordState(lord_id="edward_iv", side="yorkist",
                                                   status=LordStatus.MUSTERED))
    ed.side = "yorkist"
    ed.status = LordStatus.MUSTERED
    ed.special_vassals = ["hastings"]
    ed.capabilities = ["Y24"]
    campaign._disband_special_vassal(s, ed, "hastings")   # 3.2.4 / 1.5.4
    assert "hastings" not in ed.special_vassals
    assert "Y24" not in ed.capabilities
    assert "Y24" in s.decks["yorkist"]["discard"]


# --------------------------------------------------------------------------- #
# MEDIUM: Forage from an Exile box Depletes/Exhausts and Grows back (4.6.2)     #
# --------------------------------------------------------------------------- #
def test_exile_box_depletion_grows_back():
    s = build_initial_state("wars_of_the_roses")
    box = "france"
    assert s.exile_depletion.get(box) is None
    s.exile_depletion[box] = "exhausted"
    campaign._grow(s)
    assert s.exile_depletion[box] == "depleted"
    campaign._grow(s)
    assert box not in s.exile_depletion


# --------------------------------------------------------------------------- #
# MEDIUM: Tides "Gain Lords Influence" includes Lords in Exile boxes (4.8.1)    #
# --------------------------------------------------------------------------- #
def test_tides_counts_exile_status_lords():
    s = build_initial_state("wars_of_the_roses")
    s.turn_box = 1
    lanc = [lid for lid, ld in s.lords.items()
            if ld.side == "lancastrian" and ld.status == LordStatus.MUSTERED][0]
    mustered = campaign.tides_of_war(s.model_copy(deep=True))
    s.lords[lanc].status = LordStatus.EXILE
    s.lords[lanc].exile_box = "france"
    exiled = campaign.tides_of_war(s.model_copy(deep=True))
    assert mustered["points"] == exiled["points"]       # Exile Lord still counts


# --------------------------------------------------------------------------- #
# MEDIUM: She-Wolf (Y17) may shift a service marker off-calendar (2.2.3)        #
# --------------------------------------------------------------------------- #
def test_she_wolf_shifts_off_calendar():
    s = build_initial_state("wars_of_the_roses")
    vid = next(iter(s.vassals))
    s.vassals[vid].status = VassalStatus.MUSTERED
    s.vassals[vid].service_box = 15
    s.vassals[vid].on_lord = [lid for lid, ld in s.lords.items() if ld.side == "yorkist"][0]
    events._she_wolf(s, "yorkist", {})
    assert s.vassals[vid].service_box == 16             # not clamped to 15


# --------------------------------------------------------------------------- #
# LOW: Pay-Troops honours the player's choice of which Lords go unpaid (3.2.1)   #
# --------------------------------------------------------------------------- #
def test_pay_troops_respects_unpay_lords_choice():
    s = build_initial_state("henry_vi")
    yk = [lid for lid, ld in s.lords.items()
          if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED][:2]
    a, b = yk
    for lid in (a, b):
        s.lords[lid].location = "london"
        s.lords[lid].forces = {"retinue": 1, "men_at_arms": 6}
        s.lords[lid].assets = {"coin": 0}
        s.lords[lid].vassals = []
    s.lords[a].assets["coin"] = 1
    s.locales["london"].depletion = "exhausted"
    res = pay_mod._pay_troops(s, "yorkist", {"unpay_lords": [b]})
    assert b in res["unpaid_disbanded"]
    assert s.lords[b].status == LordStatus.CALENDAR
    assert s.lords[a].status == LordStatus.MUSTERED


# --------------------------------------------------------------------------- #
# LOW: Captured King released onto the Calendar "as if Disbanded" (6 - Inf)     #
# --------------------------------------------------------------------------- #
def test_release_captive_uses_six_minus_influence():
    s = build_initial_state("wars_of_the_roses")
    holder = [lid for lid, ld in s.lords.items() if ld.side == "yorkist"][0]
    s.lords["henry_vi"].status = LordStatus.CAPTURED
    s.lords["henry_vi"].captured_by = holder
    s.turn_box = 3
    campaign._release_captive(s, holder)
    inf = influence.lord_influence_rating("henry_vi")
    assert s.lords["henry_vi"].calendar_box == 3 + (6 - inf)


# --------------------------------------------------------------------------- #
# LOW: Parley-mod peek (commit=False) must not consume a use (enumeration)      #
# --------------------------------------------------------------------------- #
def test_parley_event_mods_peek_does_not_consume():
    s = build_initial_state("wars_of_the_roses")
    m1 = actions._parley_event_mods(s, "york", "yorkist", commit=False)
    m2 = actions._parley_event_mods(s, "york", "yorkist", commit=False)
    assert m2["used"] == m1["used"]


# --------------------------------------------------------------------------- #
# Battle: Flee may be declared in any Round, not only Round 1 (4.4.2)           #
# --------------------------------------------------------------------------- #
def _two_armies(seed):
    s = build_initial_state("henry_vi", seed=seed)
    s.lords["york"].location = "london"
    s.lords["york"].forces = {"retinue": 1, "men_at_arms": 8}
    s.lords["henry_vi"].location = "london"
    s.lords["henry_vi"].forces = {"retinue": 1, "men_at_arms": 8}
    return s


def test_flee_in_a_later_round():
    # seed 1 yields a >=2-round Battle with no early Rout.
    s = _two_armies(1)
    r = battle.resolve_battle(s, "london", "york", "henry_vi",
                              {"flee_rounds": {"york": 2}})
    assert len(r["rounds"]) >= 2
    assert "fled" not in r["rounds"][0]                 # fought Round 1
    assert r["rounds"][1].get("fled") == ["york"]       # fled at the start of Round 2


def test_flee_list_still_means_round_one():
    s = _two_armies(1)
    r = battle.resolve_battle(s, "london", "york", "henry_vi", {"flee": ["york"]})
    assert r["rounds"][0].get("fled") == ["york"]       # backward compatible


def test_flee_rounds_validates_participant_and_round():
    import pytest

    from plantagenet.errors import IllegalAction
    s = _two_armies(1)
    with pytest.raises(IllegalAction) as e1:
        battle.resolve_battle(s, "london", "york", "henry_vi",
                              {"flee_rounds": {"salisbury": 2}})
    assert e1.value.code == "bad_flee"
    s = _two_armies(1)
    with pytest.raises(IllegalAction) as e2:
        battle.resolve_battle(s, "london", "york", "henry_vi",
                              {"flee_rounds": {"york": 0}})
    assert e2.value.code == "bad_flee_round"
