"""Mutation-kill tests for campaign.py (Plan/Forage/Feed/Pillage/Tides/End, 4.x).

Each test pins rules arithmetic that a surviving mutant
(mutation-results/campaign.py.jsonl) could otherwise change silently.
"""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def _pad(lords, n):
    e = [{"lord": x} for x in lords][:n]
    while len(e) < n:
        e.append({"pass": True})
    return e


def _campaign(yk=("york",), lc=("henry_vi",), seed=1, prep=None):
    """Levy done, campaign begun, capabilities cleared, custom plans built."""
    s = build_initial_state("henry_vi", seed=seed)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    for lord in s.lords.values():
        lord.capabilities = []
    if prep:
        prep(s)
    n = s.campaign.cards_required
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist",
                             "plan": _pad(list(yk), n)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian",
                             "plan": _pad(list(lc), n)})
    return s


def _net_lanc(s):
    t = s.influence["track"]
    return t.marker_at if t.marker_side == "lancastrian" else -t.marker_at


# ------------------------------------------------------------------ 4.1 Plan
def test_season_grow_waste_boxes():
    # Grow on boxes 4, 9, 14; Waste on 5 and 10 (4.8.4 / 4.8.5).
    assert campaign.season_info(9)["grow"] is True
    assert campaign.season_info(14)["grow"] is True
    assert campaign.season_info(10)["waste"] is True


def test_plan_validation():
    # A Plan may not use Enemy Lords; a Lord has exactly three Command cards.
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "build_plan", "side": "yorkist",
                                 "plan": _pad(["henry_vi"], 4)})
    assert e.value.code == "bad_plan_lord"
    r = actions.apply_action(s, {"type": "build_plan", "side": "yorkist",
                                 "plan": _pad(["york", "york", "york"], 4)})
    assert r["built"]["yorkist"] is True       # 3 activations are legal (4.1.1)


def test_reveal_advances_one_card_and_skips_offmap_lord():
    s = _campaign(yk=("york", "march"))
    assert s.campaign.plan_index["yorkist"] == 0
    actions.apply_action(s, {"type": "end_activation", "side": "yorkist"})
    assert s.campaign.plan_index["yorkist"] == 1        # exactly one card flipped
    # march Disbands before its card comes up: reveal must be a no-op (4.2.3).
    s.lords["march"].status = LordStatus.CALENDAR
    s.lords["march"].location = None
    actions.apply_action(s, {"type": "end_activation", "side": "lancastrian"})
    assert s.active_side == "yorkist"
    assert s.campaign.active_lord is None
    assert s.campaign.actions_remaining == 0


# --------------------------------------------------------------- 4.6.2 Forage
def test_forage_thresholds():
    # Neutral Locale: roll <= 4 Forages; costs one action (4.6.2).
    def prep(st):
        st.lords["york"].location = "cambridge"
    s = _campaign(seed=6, prep=prep)                    # seed 6: first roll = 4
    before = s.campaign.actions_remaining
    r = actions.apply_action(s, {"type": "forage", "side": "yorkist", "by_lord": "york"})
    assert r["roll"] == 4 and r["success"] is True
    assert s.campaign.actions_remaining == before - 1
    s2 = _campaign(seed=2, prep=prep)                   # seed 2: first roll = 5
    r2 = actions.apply_action(s2, {"type": "forage", "side": "yorkist", "by_lord": "york"})
    assert r2["roll"] == 5 and r2["success"] is False
    # Enemy-Favour Locale: threshold is 3, so a 4 fails (4.6.2).
    def prep3(st):
        st.lords["york"].location = "cambridge"
        st.locales["cambridge"].favour = "lancastrian"
    s3 = _campaign(seed=6, prep=prep3)
    r3 = actions.apply_action(s3, {"type": "forage", "side": "yorkist", "by_lord": "york"})
    assert r3["roll"] == 4 and r3["success"] is False


def test_forage_friendly_with_enemy_adjacent_rolls():
    # Friendly Locale is automatic ONLY without an adjacent Enemy Lord (4.6.2).
    def prep(st):
        st.lords["henry_vi"].location = "cambridge"     # adjacent to Ely
    s = _campaign(seed=2, prep=prep)                    # seed 2: first roll = 5
    r = actions.apply_action(s, {"type": "forage", "side": "yorkist", "by_lord": "york"})
    assert r["enemy_adjacent"] is True
    assert r["roll"] == 5 and r["success"] is False     # threshold 3


def test_forage_exile_box():
    # Exile box Forage: automatic, +1 Provender, Deplete then Exhaust (4.6.2).
    def prep(st):
        st.lords["york"].location = None
        st.lords["york"].exile_box = "scotland"
        st.lords["york"].assets = {}
    s = _campaign(seed=1, prep=prep)
    r = actions.apply_action(s, {"type": "forage", "side": "yorkist", "by_lord": "york"})
    assert r["roll"] is None and r["success"] is True
    assert s.lords["york"].assets["provender"] == 1
    assert s.exile_depletion["scotland"] == "depleted"
    r2 = actions.apply_action(s, {"type": "forage", "side": "yorkist", "by_lord": "york"})
    assert r2["success"] is True
    assert s.lords["york"].assets["provender"] == 2
    assert s.exile_depletion["scotland"] == "exhausted"


# --------------------------------------------------------------- 3.2.1 Pillage
def test_pillage_yields_influence_and_favour():
    s = build_initial_state("henry_vi", seed=1)
    s.locales["bedford"].favour = "yorkist"
    york = s.lords["york"]
    york.assets = {}
    r = campaign._pillage(s, york, "cambridge")         # Town: 1 Coin + 1 Provender
    assert york.assets["coin"] == 1 and york.assets["provender"] == 1
    assert r["assets_gained"] == 2 and r["influence_lost"] == 4
    assert _net_lanc(s) == 4                            # Yorkists lose 2x toward the foe
    assert s.locales["cambridge"].depletion == "exhausted"
    assert str(s.locales["cambridge"].favour) == "lancastrian"
    assert str(s.locales["bedford"].favour) == "neutral"       # friendly nbr -> neutral
    assert str(s.locales["ely"].favour) == "neutral"           # friendly nbr -> neutral
    assert str(s.locales["bury_st_edmunds"].favour) == "lancastrian"   # neutral -> foe
    assert str(s.locales["st_albans"].favour) == "lancastrian"


# --------------------------------------------------------------- 3.2.4 Disband
def test_disband_lord_vassal_and_captive():
    s = build_initial_state("henry_vi", seed=1)
    york = s.lords["york"]
    york.vassals = ["suffolk"]                          # Service 3
    s.vassals["suffolk"].on_lord = "york"
    s.lords["henry_vi"].status = LordStatus.CAPTURED    # Capture of the King
    s.lords["henry_vi"].captured_by = "york"
    s.lords["henry_vi"].location = None
    campaign._disband_lord(s, york)
    assert york.status == LordStatus.CALENDAR
    assert york.calendar_box == s.turn_box + 1          # 6 - Influence 5 (3.2.4)
    assert york.calendar_exile is False
    vs = s.vassals["suffolk"]
    assert vs.service_box == s.turn_box + 3             # 6 - Service 3 (3.2.4)
    assert campaign.ready_vassals(s) == []              # not due until that box
    hv = s.lords["henry_vi"]                            # freed "as if just Disbanded"
    assert hv.status == LordStatus.CALENDAR and hv.captured_by is None
    assert hv.calendar_box == s.turn_box + 1 and hv.calendar_exile is False
    assert _net_lanc(s) == 10                           # Lancastrians +10 (3.2.4)


# ------------------------------------------------------------------- 4.7 Feed
def test_feed_needs_and_sharing():
    # 1 Provender per 6 Troops rounded up, drawn own-mat-first then allies'.
    s = build_initial_state("henry_vi", seed=1)
    york = s.lords["york"]
    york.forces = {"retinue": 1, "militia": 7}          # 7 Troops -> need 2
    york.assets = {}
    york.moved_fought = True
    sal = s.lords["salisbury"]
    sal.status = LordStatus.MUSTERED
    sal.location = "ely"
    sal.assets = {"provender": 3}
    r = campaign._feed(s, "yorkist")
    assert r["fed"] == [{"lord": "york", "fed": 2, "needed": 2}]
    assert york.assets.get("provender", 0) == 0
    assert sal.assets["provender"] == 1                 # ally's mat drained second


def test_feed_shortfall_pillages_then_disbands():
    s = build_initial_state("henry_vi", seed=1)
    york = s.lords["york"]
    york.forces = {"retinue": 1, "militia": 6}
    york.assets = {}
    york.vassals = ["suffolk"]
    s.vassals["suffolk"].on_lord = "york"
    york.moved_fought = True
    s.locales["ely"].depletion = "exhausted"            # nothing left to Pillage
    r = campaign._feed(s, "yorkist")
    assert r["disbanded"] == ["york"]
    assert york.status == LordStatus.CALENDAR
    assert york.calendar_exile is False                 # Disbanded from a Stronghold
    assert _net_lanc(s) == 6                            # Influence 5 + 1 Vassal (3.2.1)
    # Pillage helps but absent ally Provender entries still count as 0.
    s3 = build_initial_state("henry_vi", seed=1)
    y3 = s3.lords["york"]
    y3.forces = {"retinue": 1, "militia": 13}           # need 3 > Pillage yield 2
    y3.assets = {}
    y3.moved_fought = True
    s3.lords["salisbury"].status = LordStatus.MUSTERED
    s3.lords["salisbury"].location = "ely"
    s3.lords["salisbury"].assets = {}
    r3 = campaign._feed(s3, "yorkist")
    assert r3["disbanded"] == ["york"]
    # Rebel Supply Depot (L28) skips exactly ONE Feed.
    s2 = build_initial_state("henry_vi", seed=1)
    y2 = s2.lords["york"]
    y2.forces = {"retinue": 1, "militia": 6}
    y2.assets = {}
    y2.ignore_next_feed = True
    y2.moved_fought = True
    s2.locales["ely"].depletion = "exhausted"
    r1 = campaign._feed(s2, "yorkist")
    assert r1["fed"] == [{"lord": "york", "skipped": "rebel_supply_depot"}]
    assert y2.status == "mustered"
    y2.moved_fought = True
    campaign._feed(s2, "yorkist")
    assert y2.status == LordStatus.CALENDAR             # second Feed is for real


# ----------------------------------------------------------------- 4.8.1 Tides
def test_tides_of_war_exact_points():
    s = build_initial_state("henry_vi", seed=1)         # turn 1: Lords' Influence gained
    for ls in s.locales.values():
        ls.favour = "neutral"
    for lid in ("london", "calais", "rochester", "bedford"):
        s.locales[lid].favour = "lancastrian"
    for lid in ("ely", "york", "ludlow", "harlech"):
        s.locales[lid].favour = "yorkist"
    s.lords["henry_vi"].location = "rochester"          # south area presence
    s.lords["northumberland_lancastrian"].status = LordStatus.MUSTERED
    s.lords["northumberland_lancastrian"].location = "scarborough"   # north presence
    s.lords["march"].location = "harlech"               # wales; friendly at Harlech
    s.lords["warwick_yorkist"].status = LordStatus.MUSTERED
    s.lords["warwick_yorkist"].location = "calais"      # Enemy occupies Calais
    r = campaign.tides_of_war(s, None)
    # lanc: +1 south, +1 north, +2 London, +1 most towns,
    #       +14 Lords' Influence (5+5+4)
    # york: +1 wales, +1 Harlech (friendly Lord there does not withhold),
    #       +2 most cities, +1 most fortresses, +12 Lords' Influence (5+5+2);
    #       Calais withheld (Enemy Lord there)
    assert r["points"] == {"lancastrian": 19, "yorkist": 17}


def test_tides_deeds_of_charity():
    s = build_initial_state("henry_vi", seed=1)
    york = s.lords["york"]
    york.capabilities.append("Y4")                      # WE DONE DEEDS OF CHARITY
    york.assets = {}
    with pytest.raises(IllegalAction) as e:
        campaign.tides_of_war(s, {"charity": {"york": 1}})
    assert e.value.code == "no_provender"
    york.assets = {"provender": 2}
    r_with = campaign.tides_of_war(s, {"charity": {"york": 1}})
    assert york.assets["provender"] == 1
    r_without = campaign.tides_of_war(s, None)
    assert r_with["points"]["yorkist"] == r_without["points"]["yorkist"] + 1


# --------------------------------------------------------------- 4.8.3 Victory
def test_victory_51_presence_via_next_turn_exile():
    s = build_initial_state("henry_vi", seed=1)
    for ls in s.lords.values():
        if ls.side == "lancastrian":
            ls.status = LordStatus.CALENDAR
            ls.location = None
            ls.exile_box = None
            ls.calendar_exile = False
    bk = s.lords["buckingham"]
    bk.calendar_exile = True
    bk.calendar_box = s.turn_box + 1                    # arrives next Turn: presence
    assert campaign._victory_check(s) is None
    bk.calendar_box = s.turn_box + 2                    # too late: 5.1 loss
    r = campaign._victory_check(s)
    assert r == {"result": "yorkist", "rule": "5.1"}


def test_victory_threshold_boundary():
    s = build_initial_state("henry_vi", seed=1)
    assert campaign._current_threshold(s) == 40         # turns "1-5" includes 1
    t = s.influence["track"]
    t.marker_side = "yorkist"
    t.marker_at = 40                                    # exactly the threshold
    r = campaign._victory_check(s)
    assert r == {"result": "yorkist", "rule": "5.2", "threshold": 40}


def test_test_of_arms_only_at_campaign_end():
    s = build_initial_state("towton", seed=1)
    s.calendar.last_box = 3                             # mid-scenario: no check yet
    s.locales["york"].favour = "lancastrian"
    assert campaign._victory_check(s) is None
    s.calendar.last_box = 1                             # final Turn: Favour at York wins
    r = campaign._victory_check(s)
    assert r == {"result": "lancastrian", "rule": "Test of Arms"}


# ------------------------------------------------------------- 4.8.2 Disembark
def test_disembark_shipwreck_and_landing():
    # Shipwreck on 1-4 with the Unpaid penalty (Influence + 1 per Vassal).
    s = build_initial_state("henry_vi", seed=6)         # first roll = 4
    sm = s.lords["somerset_1"]
    sm.location = None
    sm.at_sea = "north_sea"
    sm.vassals = ["beaumont"]
    s.vassals["beaumont"].on_lord = "somerset_1"
    r = campaign._disembark(s, None)
    assert r["rolls"][0]["roll"] == 4 and r["rolls"][0]["shipwreck"] is True
    assert _net_lanc(s) == -6                           # Influence 5 + 1 Vassal
    # Land on 5-6: default Port is the Sea's first free Port; then Feed (4.7).
    s2 = build_initial_state("henry_vi", seed=2)        # first roll = 5
    sm2 = s2.lords["somerset_1"]
    sm2.location = None
    sm2.at_sea = "north_sea"
    sm2.forces = {"retinue": 1, "militia": 6}           # 6 Troops -> Feed needs 1
    sm2.assets = {"provender": 2}
    r2 = campaign._disembark(s2, None)
    assert r2["rolls"][0]["landed"] == "ipswich"
    assert sm2.location == "ipswich" and sm2.at_sea is None
    assert sm2.assets["provender"] == 1                 # fed immediately
    assert sm2.moved_fought is False


# ----------------------------------------------------------- 4.8.6 End / reset
def test_end_campaign_guard_and_reset():
    s = _campaign()
    with pytest.raises(IllegalAction) as e:             # only after both stacks end
        actions.apply_action(s, {"type": "end_campaign"})
    assert e.value.code == "wrong_step"
    s2 = _campaign(yk=(), lc=())                        # all-Pass plans
    for _ in range(8):
        actions.apply_action(s2, {"type": "end_activation", "side": s2.active_side})
    assert s2.campaign.step == "end"
    s2.lords["york"].lordship_spent = 3
    s2.lords["york"].free_troops_used = True
    r = actions.apply_action(s2, {"type": "end_campaign"})
    assert r["victory"] is None and s2.phase == "levy" and s2.turn_box == 2
    assert s2.lords["york"].lordship_spent == 0
    assert all(not v.moved_fought for v in s2.lords.values())
    assert s2.lords["york"].free_troops_used is False


def test_begin_campaign_grants_nothing_without_stafford_estates():
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    coin = {lid: v.assets.get("coin", 0) for lid, v in s.lords.items()}
    prov = {lid: v.assets.get("provender", 0) for lid, v in s.lords.items()}
    actions.apply_action(s, {"type": "begin_campaign"})
    assert {lid: v.assets.get("coin", 0) for lid, v in s.lords.items()} == coin
    assert {lid: v.assets.get("provender", 0) for lid, v in s.lords.items()} == prov


def test_foreign_haven_shift_boundaries():
    s = build_initial_state("henry_vi", seed=1)
    cur = s.turn_box
    hv = s.lords["henry_vi"]
    hv.status = LordStatus.CALENDAR
    hv.location = None
    hv.calendar_box = cur + 3
    wk = s.lords["warwick_yorkist"]
    wk.status = LordStatus.CALENDAR
    wk.calendar_box = cur                               # already due: must NOT move
    sal = s.lords["salisbury"]
    sal.status = LordStatus.CALENDAR
    sal.calendar_box = cur + 2                          # late Yorkist -> next box
    campaign._foreign_haven_shift(s)
    assert hv.calendar_box == cur                       # Lancastrians to current box
    assert wk.calendar_box == cur
    assert sal.calendar_box == cur + 1


def test_waste_resets_coin_to_setup():
    s = build_initial_state("warwicks_rebellion", seed=1)
    cl = s.lords["clarence"]                            # setup Assets have no Coin
    assert cl.status == "mustered"
    cl.assets = {"coin": 5, "provender": 4, "cart": 3, "ship": 2}
    campaign._waste(s)
    assert cl.assets["coin"] == 0                       # reset to setup (4.8.5)
    assert cl.assets["provender"] == 2 and cl.assets["cart"] == 2
    assert cl.assets["ship"] == 1                       # halve, round up


def test_begin_campaign_stafford_estates_goes_to_mustered_holder_only():
    # L84 cmp Eq->NotEq (site 2287): the L22 STAFFORD ESTATES grant at Campaign
    # start goes to a MUSTERED holder, never to one still on the Calendar.
    s = build_initial_state("henry_vi", seed=1)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    bk = s.lords["buckingham"]
    bk.status = LordStatus.MUSTERED
    bk.location = "coventry"                            # his Seat
    bk.calendar_box = None
    bk.capabilities = ["L22"]
    ex = s.lords["exeter_1"]
    assert ex.status == LordStatus.CALENDAR             # still waiting to Muster
    ex.capabilities = ["L22"]
    bk_before = dict(bk.assets)
    ex_before = dict(ex.assets)
    actions.apply_action(s, {"type": "begin_campaign"})
    assert bk.assets.get("coin", 0) == bk_before.get("coin", 0) + 1
    assert bk.assets.get("provender", 0) == bk_before.get("provender", 0) + 1
    assert dict(ex.assets) == ex_before                 # Calendar holder gains nothing


def test_queen_regent_tides_bonus_is_exactly_three():
    # L559 int 3->4 (site 3132): Queen Regent (Warwick's Rebellion special rule)
    # awards exactly +3 for Margaret Mustered at London.
    def lanc_tides(location):
        s = build_initial_state("warwicks_rebellion", seed=1)
        mg = s.lords["margaret"]
        mg.status = LordStatus.MUSTERED
        mg.location = location
        mg.calendar_box = None
        return campaign.tides_of_war(s, None)["points"]["lancastrian"]

    # Calais as the control seat: like London its region is None (no Area-presence
    # delta), and its Favour is Lancastrian, so a friendly occupant never withholds
    # the special-Stronghold award. Only Queen Regent separates the two runs.
    assert lanc_tides("london") - lanc_tides("calais") == 3     # 19 vs 16
