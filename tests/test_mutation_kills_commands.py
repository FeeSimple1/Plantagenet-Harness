"""Mutation-kill tests for commands.py (March/Sail/Tax/Parley/Supply, 4.x).

Each test pins rules arithmetic or route/reach logic that a surviving mutant
(mutation-results/commands.py.jsonl) could otherwise change silently.
"""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
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
    for lord in s.lords.values():          # seed-dealt capabilities off; tests re-add
        lord.capabilities = []
    if prep:
        prep(s)
    n = s.campaign.cards_required
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist",
                             "plan": _pad(list(yk), n)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian",
                             "plan": _pad(list(lc), n)})
    return s


def _to_lancastrian(s):
    actions.apply_action(s, {"type": "end_activation", "side": "yorkist"})
    return s


def _net_lanc(s):
    t = s.influence["track"]
    return t.marker_at if t.marker_side == "lancastrian" else -t.marker_at


# ---------------------------------------------------------------- 4.3 March
def test_road_chain_needs_capability_or_event():
    # L172/L174: a plain lone Lord may NOT chain two Roads (no Y11/L8 event).
    s = _to_lancastrian(_campaign())
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "march", "side": "lancastrian",
                                 "by_lord": "henry_vi", "to": "hastings"})
    assert e.value.code == "no_march_route"
    # L174: Forced Marches (L8 Event) enables it for the LANCASTRIAN side.
    def prep_fm(st):
        st.active_events.append({"card": "L8", "side": "lancastrian"})
    sfm = _to_lancastrian(_campaign(prep=prep_fm))
    rfm = actions.apply_action(sfm, {"type": "march", "side": "lancastrian",
                                     "by_lord": "henry_vi", "to": "hastings"})
    assert rfm["way"] == "highway2"
    # L173: Yorkists Never Wait (Y11) DOES allow the lone Road 2-for-1 chain.
    s2 = _campaign(prep=lambda st: st.lords["york"].capabilities.append("Y11"))
    r = actions.apply_action(s2, {"type": "march", "side": "yorkist",
                                  "by_lord": "york", "to": "ipswich"})
    assert r["way"] == "highway2" and r["whole_card"] is False


def test_march_from_exile_boxes():
    # Scotland exile: only Carlisle/Bamburgh, by Path, whole card (4.3.3).
    def prep(st):
        st.lords["henry_vi"].location = None
        st.lords["henry_vi"].exile_box = "scotland"
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "march", "side": "lancastrian",
                                 "by_lord": "henry_vi", "to": "york"})
    assert e.value.code == "no_march_route"
    r = actions.apply_action(s, {"type": "march", "side": "lancastrian",
                                 "by_lord": "henry_vi", "to": "carlisle"})
    assert r["way"] == "path" and r["whole_card"] is True
    assert s.lords["henry_vi"].location == "carlisle"
    assert s.campaign.actions_remaining == 0
    # A continental Exile box has NO land exit to Carlisle.
    def prep2(st):
        st.lords["henry_vi"].location = None
        st.lords["henry_vi"].exile_box = "france"
    s2 = _to_lancastrian(_campaign(prep=prep2))
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s2, {"type": "march", "side": "lancastrian",
                                  "by_lord": "henry_vi", "to": "carlisle"})
    assert e2.value.code == "no_march_route"


def test_road_march_cost_and_haul():
    # Road March: 1 action, not the whole card; Haul trims Provender to Carts.
    def prep(st):
        st.lords["york"].assets = {"provender": 3}     # no cart key at all
    s = _campaign(prep=prep)
    before = s.campaign.actions_remaining
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": "york", "to": "bury_st_edmunds"})
    assert r["way"] == "road" and r["whole_card"] is False
    assert s.campaign.actions_remaining == before - 1
    assert s.lords["york"].assets.get("provender", 0) == 0     # 0 Carts -> all dropped
    # Hay Wains (L8): Carts count double for the Haul.
    def prep2(st):
        st.lords["henry_vi"].capabilities.append("L8")
        st.lords["henry_vi"].assets = {"provender": 5, "cart": 1}
    s2 = _to_lancastrian(_campaign(prep=prep2))
    actions.apply_action(s2, {"type": "march", "side": "lancastrian",
                              "by_lord": "henry_vi", "to": "rochester"})
    assert s2.lords["henry_vi"].assets["provender"] == 2       # 1 Cart x2 (L8)


def test_group_haul_math():
    # Group March Haul (4.3.2): the GROUP's excess over the GROUP's Carts drops.
    def prep(st):
        st.lords["march"].location = "ely"
        st.lords["york"].assets = {}                   # no provender/cart keys
        st.lords["march"].assets = {"provender": 5}
    s = _campaign(prep=prep)
    actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                             "to": "cambridge", "group": ["march"]})
    assert s.lords["york"].assets.get("provender", 0) == 0
    assert s.lords["march"].assets.get("provender", 0) == 0
    # Trimming continues until the excess reaches exactly 0.
    def prep2(st):
        st.lords["march"].location = "ely"
        st.lords["york"].assets = {"provender": 4}
        st.lords["march"].assets = {"provender": 1}
    s2 = _campaign(prep=prep2)
    actions.apply_action(s2, {"type": "march", "side": "yorkist", "by_lord": "york",
                              "to": "cambridge", "group": ["march"]})
    assert s2.lords["york"].assets.get("provender", 0) == 0
    assert s2.lords["march"].assets.get("provender", 0) == 0
    # No excess (Carts cover Provender): nothing is dropped.
    def prep3(st):
        st.lords["march"].location = "ely"
        st.lords["york"].assets = {"provender": 2, "cart": 3}
        st.lords["march"].assets = {}
    s3 = _campaign(prep=prep3)
    actions.apply_action(s3, {"type": "march", "side": "yorkist", "by_lord": "york",
                              "to": "cambridge", "group": ["march"]})
    assert s3.lords["york"].assets.get("provender", 0) == 2


def test_march_group_validation():
    # An Enemy Lord can never join a Group March (4.3.1).
    s = _campaign()
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge", "group": ["henry_vi"]})
    assert e.value.code == "bad_group_member"
    assert s.lords["henry_vi"].location == "london"
    # A Lieutenant may not lead a Marshal (4.3.1).
    s2 = _to_lancastrian(_campaign(lc=("somerset_1",)))
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s2, {"type": "march", "side": "lancastrian",
                                  "by_lord": "somerset_1", "to": "rochester",
                                  "group": ["henry_vi"]})
    assert e2.value.code == "lieutenant_cannot_lead_marshal"


def test_intercept_rules():
    # Intercept requires Road/Highway adjacency to the destination (4.3.4).
    s = _campaign()
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"intercept": "henry_vi"}})
    assert e.value.code == "bad_intercept"
    # Boundary: roll EQUAL to Valour succeeds; success moves + Hauls + marks.
    def prep(st):
        st.lords["somerset_1"].location = "bedford"    # Road-adjacent to Cambridge
        st.lords["somerset_1"].assets = {"provender": 3}   # no cart key
    s2 = _campaign(seed=5, prep=prep)                  # seed 5: intercept roll = 2
    r = actions.apply_action(s2, {"type": "march", "side": "yorkist", "by_lord": "york",
                                  "to": "cambridge",
                                  "decisions": {"intercept": "somerset_1",
                                                "responses": {"somerset_1": "battle"}}})
    assert r["intercept"]["roll"] == 2 == r["intercept"]["valour"]
    assert r["intercept"]["success"] is True
    assert s2.lords["somerset_1"].location == "cambridge"
    assert s2.lords["somerset_1"].moved_fought is True
    assert s2.lords["somerset_1"].assets.get("provender", 0) == 1  # Hauled to 0 Carts


# ---------------------------------------------------------------- 4.6.1 Sail
def test_sail_ship_requirement_counts_vassals():
    # 1 Ship per 6 Forces, Vassals included in the count (4.6.1).
    def prep(st):
        st.lords["york"].location = "lynn"
        st.lords["york"].forces = {"retinue": 1, "militia": 5}   # 6 units
        st.lords["york"].vassals = ["suffolk"]                   # -> 7
        st.lords["york"].assets = {"ship": 1}
    s = _campaign(prep=prep)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "yorkist",
                                 "by_lord": "york", "to": "ravenspur"})
    assert e.value.code == "insufficient_ships"
    # 1 Ship per 2 Provender and per 2 Carts (4.6.1).
    s.lords["york"].vassals = []
    s.lords["york"].forces = {"retinue": 1}
    s.lords["york"].assets = {"ship": 1, "provender": 3}
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s, {"type": "sail", "side": "yorkist",
                                 "by_lord": "york", "to": "ravenspur"})
    assert e2.value.code == "insufficient_ships"
    s.lords["york"].assets = {"ship": 1, "cart": 3}
    with pytest.raises(IllegalAction) as e3:
        actions.apply_action(s, {"type": "sail", "side": "yorkist",
                                 "by_lord": "york", "to": "ravenspur"})
    assert e3.value.code == "insufficient_ships"
    # Sharing (1.5.3): absent "ship" entries are 0 for lord and Share allies.
    from plantagenet.state import LordStatus
    s.lords["york"].assets = {}
    s.lords["salisbury"].status = LordStatus.MUSTERED
    s.lords["salisbury"].location = "lynn"
    s.lords["salisbury"].assets = {}
    with pytest.raises(IllegalAction) as e4:
        actions.apply_action(s, {"type": "sail", "side": "yorkist", "by_lord": "york",
                                 "to": "ravenspur", "share": ["salisbury"]})
    assert e4.value.code == "insufficient_ships"


def test_sail_great_ships_capacity():
    # Great Ships (Y6): each Ship carries 12 Forces / 4 Provender / 4 Carts.
    def prep(st):
        st.lords["york"].location = "lynn"
        st.lords["york"].capabilities.append("Y6")
        st.lords["york"].forces = {"retinue": 1, "militia": 12}  # 13 > 12
        st.lords["york"].assets = {"ship": 1}
    s = _campaign(prep=prep)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "yorkist",
                                 "by_lord": "york", "to": "ravenspur"})
    assert e.value.code == "insufficient_ships"
    s.lords["york"].forces = {"retinue": 1}
    s.lords["york"].assets = {"ship": 1, "provender": 4, "cart": 4}
    r = actions.apply_action(s, {"type": "sail", "side": "yorkist",
                                 "by_lord": "york", "to": "ravenspur"})
    assert r["to"] == "ravenspur" and s.lords["york"].location == "ravenspur"


def test_sail_group_rules():
    # A groupmate must share the leader's origin (4.6.1).
    def prep(st):
        st.lords["york"].location = "lynn"
        st.lords["york"].forces = {"retinue": 1}
        st.lords["york"].assets = {"ship": 1}
        st.lords["march"].forces = {"retinue": 1}
    s = _campaign(prep=prep)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "yorkist", "by_lord": "york",
                                 "to": "ravenspur", "group": ["march"]})
    assert e.value.code == "bad_group_member"
    assert s.lords["march"].location == "ludlow"
    # Group Sail pools the WHOLE group's Forces against pooled Ships.
    def prep2(st):
        st.lords["york"].location = "lynn"
        st.lords["york"].forces = {"retinue": 1}
        st.lords["york"].assets = {"ship": 1}
        st.lords["march"].location = "lynn"
        st.lords["march"].forces = {"retinue": 1, "militia": 11}   # group = 13
        st.lords["march"].assets = {}
    s2 = _campaign(prep=prep2)
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s2, {"type": "sail", "side": "yorkist", "by_lord": "york",
                                  "to": "ravenspur", "group": ["march"]})
    assert e2.value.code == "insufficient_ships"
    # Absent Asset entries count as 0 across the whole group.
    from plantagenet.state import LordStatus
    def prep3(st):
        for lid in ("york", "march", "salisbury"):
            st.lords[lid].status = LordStatus.MUSTERED
            st.lords[lid].location = "lynn"
            st.lords[lid].forces = {"retinue": 1}
            st.lords[lid].assets = {}
    s3 = _campaign(prep=prep3)
    with pytest.raises(IllegalAction) as e3:
        actions.apply_action(s3, {"type": "sail", "side": "yorkist", "by_lord": "york",
                                  "to": "ravenspur",
                                  "group": ["march", "salisbury"]})
    assert e3.value.code == "insufficient_ships"
    s3.lords["york"].assets = {"ship": 1}
    r = actions.apply_action(s3, {"type": "sail", "side": "yorkist", "by_lord": "york",
                                  "to": "ravenspur", "group": ["march", "salisbury"]})
    assert s3.lords["salisbury"].location == "ravenspur" and r["to"] == "ravenspur"


def test_sail_at_sea_to_adjacent_sea_port():
    # A Lord at Sea may land at a Port on an ADJACENT Sea (4.6.1).
    def prep(st):
        st.lords["york"].location = None
        st.lords["york"].at_sea = "north_sea"
        st.lords["york"].forces = {"retinue": 1}
        st.lords["york"].assets = {"ship": 1}
        # an unrelated active Event must not leak into other Event checks
        st.active_events.append({"card": "Y8", "side": "yorkist"})
    s = _campaign(prep=prep)
    r = actions.apply_action(s, {"type": "sail", "side": "yorkist",
                                 "by_lord": "york", "to": "dover"})
    assert s.lords["york"].location == "dover" and s.lords["york"].at_sea is None
    assert r["from_sea"] == "north_sea" and r["to_sea"] == "english_channel"


# ---------------------------------------------------------------- 4.6.3 Tax
def test_tax_remote_target_needs_route():
    # A remote Tax target needs a Friendly Route free of Enemy Lords (4.6.3).
    s = _campaign()
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "tax", "side": "yorkist",
                                 "by_lord": "york", "target": "harlech"})
    assert e.value.code == "no_route"


def test_tax_route_by_ship_needs_a_ship():
    # Calais from Dover is Sea-only: no Ship -> no Route; 1 Ship -> Route.
    def prep(st):
        st.lords["henry_vi"].location = "dover"
        st.locales["dover"].favour = "lancastrian"
        st.lords["henry_vi"].assets = {}
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "calais"})
    assert e.value.code == "no_route"
    s.lords["henry_vi"].assets = {"ship": 1}
    r = actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "calais"})
    assert r["type"] == "tax" and r["target"] == "calais"


def test_tax_own_seat_yield_exact():
    # Auto Tax of the own Seat adds EXACTLY the table yield (4.6.3).
    from plantagenet.state import LordStatus
    def prep(st):
        st.lords["exeter_1"].status = LordStatus.MUSTERED
        st.lords["exeter_1"].location = "exeter"
        st.lords["exeter_1"].assets = {}
        st.locales["exeter"].favour = "lancastrian"
    s = _to_lancastrian(_campaign(lc=("exeter_1",), prep=prep))
    r = actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                                 "by_lord": "exeter_1", "target": "exeter"})
    assert r["auto"] is True and r["coin_added"] == 2          # City: 2 Coin
    assert s.lords["exeter_1"].assets["coin"] == 2             # +1 nowhere
    assert s.locales["exeter"].depletion == "depleted"


def test_tax_costs_and_extra_spend():
    # extra_spend 1 and 3 are legal (1.4.2); each Tax costs ONE action.
    s = _to_lancastrian(_campaign())
    before = s.campaign.actions_remaining
    actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                             "by_lord": "henry_vi", "target": "london",
                             "extra_spend": 1})
    assert s.campaign.actions_remaining == before - 1
    actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                             "by_lord": "henry_vi", "target": "london",
                             "extra_spend": 3})
    assert s.campaign.actions_remaining == before - 2
    # Non-auto Tax with no extra_spend spends exactly 1 Influence.
    def prep(st):
        st.lords["henry_vi"].location = "st_albans"
        st.locales["st_albans"].favour = "lancastrian"
        st.lords["henry_vi"].vassals = ["essex"]       # Vassal Seat: st_albans
    s2 = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s2, {"type": "tax", "side": "lancastrian",
                                  "by_lord": "henry_vi", "target": "st_albans"})
    assert r["spent"] == 1


# --------------------------------------------------------------- 4.6.4 Parley
def test_parley_own_location_auto():
    # Own-location Parley: auto, free, 1 action; Enemy Favour -> Neutral.
    def prep(st):
        st.lords["henry_vi"].location = "rochester"
        st.locales["rochester"].favour = "yorkist"
    s = _to_lancastrian(_campaign(prep=prep))
    net0 = _net_lanc(s)
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi"})
    assert r["auto"] is True and r["honest_tale_cost"] == 0
    assert str(s.locales["rochester"].favour) == "neutral"
    assert s.campaign.actions_remaining == 1                   # command 2 - 1
    assert _net_lanc(s) == net0                                # free (no Y34)


def test_parley_remote_spend_math():
    # Campaign Parley one Way out: spends 1 + extra + 1 Way (1.4.2 / 4.6.4).
    s = _to_lancastrian(_campaign())
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "rochester"})
    assert r["spent"] == 2
    r2 = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                  "by_lord": "henry_vi", "target": "guildford",
                                  "extra_spend": 1})
    assert r2["spent"] == 3
    s2 = _to_lancastrian(_campaign())
    r3 = actions.apply_action(s2, {"type": "parley", "side": "lancastrian",
                                   "by_lord": "henry_vi", "target": "oxford",
                                   "extra_spend": 3})
    assert r3["spent"] == 5
    # Standing at Exeter grants NO Dorset (Y29) free ride without Devon+Event.
    def prep_ex(st):
        st.lords["henry_vi"].location = "exeter"
        st.locales["exeter"].favour = "lancastrian"
    s3 = _to_lancastrian(_campaign(prep=prep_ex))
    r4 = actions.apply_action(s3, {"type": "parley", "side": "lancastrian",
                                   "by_lord": "henry_vi", "target": "dorchester"})
    assert r4["spent"] == 2


def test_parley_sea_reach_needs_ship_and_same_sea_port():
    # Same-Sea Port reach requires a Ship; a Ship reaches ONLY same-Sea Ports.
    def prep(st):
        st.lords["henry_vi"].location = "dover"
        st.locales["dover"].favour = "lancastrian"
        st.lords["henry_vi"].assets = {}
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "plymouth"})
    assert e.value.code == "out_of_reach"
    s.lords["henry_vi"].assets = {"ship": 1}
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "oxford"})
    assert e2.value.code == "out_of_reach"


# ----------------------------------------------------------------- 4.5 Supply
def test_supply_route_rules():
    # (a) the Source itself must be Friendly (4.5.1).
    s = _campaign()
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "supply", "side": "yorkist",
                                 "by_lord": "york", "source": "cambridge"})
    assert e.value.code == "no_route"
    # (b) a Friendly Source without a Friendly chain is unreachable.
    def prep2(st):
        st.locales["york"].favour = "yorkist"
    s2 = _campaign(prep=prep2)
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s2, {"type": "supply", "side": "yorkist",
                                  "by_lord": "york", "source": "york"})
    assert e2.value.code == "no_route"
    # (c) a two-Way Route costs one Cart per Provender per Way (4.5.1).
    def prep3(st):
        st.locales["cambridge"].favour = "yorkist"
        st.locales["st_albans"].favour = "yorkist"
        st.lords["york"].assets = {"cart": 2}
    s3 = _campaign(prep=prep3)
    r = actions.apply_action(s3, {"type": "supply", "side": "yorkist",
                                  "by_lord": "york", "source": "st_albans"})
    assert r["provender_added"] == 1 and r["ways"] == 2
    assert s3.lords["york"].assets.get("provender", 0) == 1
    # (d) Hay Wains (L8) doubles Carts for Supply: 1 Cart -> 2 Provender cap.
    def prep_hw(st):
        st.lords["henry_vi"].capabilities.append("L8")
        st.lords["henry_vi"].location = "rochester"
        st.locales["rochester"].favour = "lancastrian"
        st.lords["henry_vi"].assets = {"cart": 1}
    shw = _to_lancastrian(_campaign(prep=prep_hw))
    rhw = actions.apply_action(shw, {"type": "supply", "side": "lancastrian",
                                     "by_lord": "henry_vi", "source": "london"})
    assert rhw["provender_added"] == 2                 # min(3 London, 1 Cart x2)
    # (e) a Stronghold Source is Depleted by the Supply (4.5.2).
    def prep4(st):
        st.locales["st_albans"].favour = "lancastrian"
        st.lords["henry_vi"].vassals = ["essex"]
        st.lords["henry_vi"].assets = {"cart": 2}
    s4 = _to_lancastrian(_campaign(prep=prep4))
    actions.apply_action(s4, {"type": "supply", "side": "lancastrian",
                              "by_lord": "henry_vi", "source": "st_albans"})
    assert s4.locales["st_albans"].depletion == "depleted"


def test_supply_by_ship():
    # Ship Supply needs a Ship; same-Sea Port: 1 Provender per Ship, Source
    # NOT Depleted, one action (4.5.1-.2).
    def prep(st):
        st.lords["york"].location = "lynn"
        st.locales["lynn"].favour = "yorkist"
        st.lords["york"].assets = {}
    s = _campaign(prep=prep)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "supply", "side": "yorkist", "by_lord": "york",
                                 "source": "ravenspur", "use_ships": True})
    assert e.value.code == "no_ships"
    s.lords["york"].assets = {"ship": 1}
    before = s.campaign.actions_remaining
    r = actions.apply_action(s, {"type": "supply", "side": "yorkist", "by_lord": "york",
                                 "source": "ravenspur", "use_ships": True})
    assert r["provender_added"] == 1
    assert s.lords["york"].assets.get("provender", 0) == 1
    assert s.locales["ravenspur"].depletion is None
    assert s.campaign.actions_remaining == before - 1
    # Cross-Sea Ship Supply is never direct: it needs the land Route (4.5.1).
    def prep2(st):
        st.lords["york"].location = "ipswich"
        st.locales["ipswich"].favour = "yorkist"
        st.locales["dover"].favour = "yorkist"
        st.lords["york"].assets = {"ship": 1}
    s2 = _campaign(prep=prep2)
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s2, {"type": "supply", "side": "yorkist", "by_lord": "york",
                                  "source": "dover", "use_ships": True})
    assert e2.value.code == "no_route"


# --------------------------------------------------- 1.9.1 Capability commands
def test_merchants_targets_and_cost():
    # Merchants (L30): up to 2 targets, at or adjacent only; 1 action.
    def prep(st):
        st.lords["henry_vi"].capabilities.append("L30")
        st.locales["rochester"].depletion = "depleted"
        st.locales["oxford"].depletion = "exhausted"
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "merchants", "side": "lancastrian",
                                 "by_lord": "henry_vi", "targets": ["york"]})
    assert e.value.code == "bad_targets"
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s, {"type": "merchants", "side": "lancastrian",
                                 "by_lord": "henry_vi",
                                 "targets": ["rochester", "oxford", "st_albans"]})
    assert e2.value.code == "bad_targets"
    before = s.campaign.actions_remaining
    r = actions.apply_action(s, {"type": "merchants", "side": "lancastrian",
                                 "by_lord": "henry_vi",
                                 "targets": ["rochester", "oxford"]})
    assert s.campaign.actions_remaining == before - 1
    assert r["spent"] == 1                             # no extra spend requested


# ============================================================================
# Engineered kills for classified surviving mutants (commands.py, 2026-07).
# Not pinned here (see mutation notes): line 246 flank-attack card cost is
# masked by a later fall-through decrement (clean code ends at -1), and the
# line 805 Gt->GtE / default-ship mutants are behaviourally equivalent.
# ============================================================================


# ------------------------------------------ Capability commands (1.9.1)
def test_agitators_consumes_exactly_one_action():
    # Agitators (Y10) is ONE Command action, not two.
    s = _campaign()
    s.lords["york"].capabilities.append("Y10")
    before = s.campaign.actions_remaining
    r = actions.apply_action(s, {"type": "agitators", "side": "yorkist",
                                 "by_lord": "york", "target": "cambridge"})
    assert r["depletion"] == "depleted"
    assert s.campaign.actions_remaining == before - 1


def test_heralds_full_card_and_no_default_extra_spend():
    # Heralds (L4): the whole Command card is spent and the default added
    # Influence spend is 0 -> exactly 1 point paid (1.4.2).
    def prep(st):
        st.lords["henry_vi"].location = "dover"            # a Port (L4)
        st.lords["henry_vi"].capabilities.append("L4")
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "heralds", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "buckingham"})
    assert r["spent"] == 1
    assert s.campaign.actions_remaining == 0


def test_heralds_rejects_a_mustered_target():
    # Heralds shifts CALENDAR cylinders only; a Mustered Lord is no target
    # (L4) -- even one carrying a stale calendar_box value.
    def prep(st):
        st.lords["henry_vi"].location = "dover"
        st.lords["henry_vi"].capabilities.append("L4")
        st.lords["somerset_1"].calendar_box = 4            # stale; still MUSTERED
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "heralds", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "somerset_1"})
    assert e.value.code == "bad_target"


def test_exile_pact_needs_the_event_even_for_a_yorkist():
    # Exile Pact is an Event (Y8): a Yorkist Lord alone does not qualify.
    s = _campaign()
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "exile_pact", "side": "yorkist",
                                 "by_lord": "york", "box": "burgundy"})
    assert e.value.code == "no_exile_pact"
    assert s.lords["york"].exile_box is None


# --------------------------------------------- Y14/Y23 Burgundians
def test_burgundians_respects_the_handgunner_pool_floor():
    # Pool is 2; with both already in play the grant is 0 -- never forced up.
    def prep(st):
        st.lords["york"].location = "lynn"
        st.lords["york"].capabilities.append("Y14")
        st.lords["york"].forces = {"retinue": 1}
        st.lords["york"].assets = {"ship": 1}
        st.lords["henry_vi"].forces["handgunners"] = 2
    s = _campaign(prep=prep)
    actions.apply_action(s, {"type": "sail", "side": "yorkist", "by_lord": "york",
                             "to": "ravenspur"})
    assert s.lords["york"].forces.get("handgunners", 0) == 0
    assert not s.flags.get("burgundians_york")


def test_burgundians_grant_is_pool_minus_in_play():
    # Pool 2 with 1 in play elsewhere -> exactly 1 Handgunner arrives.
    def prep(st):
        st.lords["york"].location = "lynn"
        st.lords["york"].capabilities.append("Y14")
        st.lords["york"].forces = {"retinue": 1}
        st.lords["york"].assets = {"ship": 1}
        st.lords["henry_vi"].forces["handgunners"] = 1
    s = _campaign(prep=prep)
    actions.apply_action(s, {"type": "sail", "side": "yorkist", "by_lord": "york",
                             "to": "ravenspur"})
    assert s.lords["york"].forces.get("handgunners", 0) == 1


def test_burgundians_fires_only_the_first_time():
    # "The first time this Lord is at any Port" -- once granted (and later
    # lost in Battle), a later Port visit adds nothing (Y14/Y23).
    from plantagenet import commands
    s = _campaign()
    york = s.lords["york"]
    york.capabilities.append("Y14")
    york.location = "lynn"
    assert commands._apply_burgundians(s, york) == 2
    york.forces["handgunners"] = 0                         # Battle losses
    assert commands._apply_burgundians(s, york) == 0
    assert york.forces.get("handgunners", 0) == 0


# --------------------------------------------------- 4.6.4 Parley extras
def test_dorset_devon_at_exeter_parley_auto_and_free_way():
    # DORSET (Y29): only DEVON and only AT EXETER; "cost 0 Influence and
    # auto-succeed" -- no check, no roll, no spend (fixed 2026-07-02c).
    from plantagenet.state import LordState, LordStatus
    def prep(st):
        st.lords["devon"] = LordState(lord_id="devon", side="yorkist",
                                      status=LordStatus.MUSTERED, location="exeter")
        st.locales["exeter"].favour = "yorkist"
        st.active_events.append({"card": "Y29", "side": "yorkist"})
    s = _campaign(yk=("devon",), prep=prep)
    r = actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "devon", "target": "dorchester"})
    assert r["success"] is True
    assert r["spent"] == 0 and r["roll"] is None    # Y29: cost 0, no roll


def test_new_act_of_parliament_takes_the_entire_card():
    # NEW ACT OF PARLIAMENT (L10): a Yorkist Campaign Parley uses ALL of the
    # Command card's actions.
    s = _campaign()
    s.active_events.append({"card": "L10", "side": "lancastrian"})
    r = actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "cambridge"})
    assert r["type"] == "parley"
    assert s.campaign.actions_remaining == 0


def test_honest_tale_own_location_parley_costs_exactly_one():
    # AN HONEST TALE (Y34): the otherwise-free own-location Lancastrian
    # Parley costs exactly 1 Influence.
    def prep(st):
        st.lords["henry_vi"].location = "rochester"
        st.locales["rochester"].favour = "yorkist"
        st.active_events.append({"card": "Y34", "side": "yorkist"})
    s = _to_lancastrian(_campaign(prep=prep))
    net0 = _net_lanc(s)
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi"})
    assert r["honest_tale_cost"] == 1
    assert net0 - _net_lanc(s) == 1


def test_honest_tale_remote_parley_surcharge_is_one():
    # Y34 adds exactly +1: 1 base + 1 Way + 1 surcharge = 3.
    def prep(st):
        st.active_events.append({"card": "Y34", "side": "yorkist"})
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "rochester"})
    assert r["spent"] == 3


# ---------------------------------------------------- 4.5 Supply extras
def test_chamberlains_supply_does_not_deplete_a_vassal_seat():
    # Chamberlains (L10 Capability): Supply from the Lord's own Vassal's
    # Seat adds no Depletion marker.
    def prep(st):
        st.lords["henry_vi"].capabilities.append("L10")
        st.lords["henry_vi"].vassals = ["essex"]           # Seat: st_albans
        st.lords["henry_vi"].assets = {"cart": 2}
        st.locales["st_albans"].favour = "lancastrian"
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                 "by_lord": "henry_vi", "source": "st_albans"})
    assert r["provender_added"] >= 1
    assert s.locales["st_albans"].depletion is None


def test_great_ships_supply_hops_start_only_at_ports():
    # Great Ships (Y6/L6) makes all PORTS 1 Way apart; an inland Lord gains
    # no all-port hop from a non-port node.
    def prep(st):
        st.lords["york"].capabilities.append("Y6")
        st.lords["york"].assets = {"cart": 2}
        st.locales["truro"].favour = "yorkist"
    s = _campaign(prep=prep)                               # york at ely (inland)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "supply", "side": "yorkist",
                                 "by_lord": "york", "source": "truro"})
    assert e.value.code == "no_route"


def test_great_ships_supply_port_to_port_is_one_way():
    # Great Ships: a Port Lord reaches any Port Source in exactly 1 Way.
    def prep(st):
        st.lords["york"].capabilities.append("Y6")
        st.lords["york"].location = "lynn"
        st.locales["lynn"].favour = "yorkist"
        st.locales["dover"].favour = "yorkist"
        st.lords["york"].assets = {"cart": 2}
    s = _campaign(prep=prep)
    r = actions.apply_action(s, {"type": "supply", "side": "yorkist",
                                 "by_lord": "york", "source": "dover"})
    assert r["ways"] == 1 and r["provender_added"] == 1


def test_continental_exile_supply_requires_ship_and_port():
    # Only the SCOTLAND box is exempt (Path); a continental Exile box must
    # Supply via Ship from a same-Sea Port (4.5.1).
    def prep(st):
        st.lords["henry_vi"].location = None
        st.lords["henry_vi"].exile_box = "france"
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                 "by_lord": "henry_vi", "source": "dover"})
    assert e.value.code == "exile_needs_ship_port"


# ------------------------------------------------ Y15 Naval Blockade
def test_blockade_skips_a_sea_routed_around_by_land():
    # Y15 fires only when blocking the Sea RAISES the Route cost; here an
    # equally short land Way to Exeter means no Blockade window opens.
    def prep(st):
        st.lords["henry_vi"].location = "dorchester"
        st.locales["dorchester"].favour = "lancastrian"
        st.lords["henry_vi"].assets = {"ship": 1}
        st.lords["henry_vi"].vassals = ["devon"]           # Vassal Seat: exeter
        st.lords["york"].location = "plymouth"             # Blockade the Channel
        st.lords["york"].capabilities.append("Y15")
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "exeter"})
    assert r["type"] == "tax"


def test_blockade_recompute_keeps_other_sea_hops():
    # Blocking the NORTH SEA must not strip the Channel hop of a one-Ship
    # Lord from the recompute: the Calais Route is unaffected, so no Y15
    # reaction window opens.
    def prep(st):
        st.lords["henry_vi"].location = "hastings"
        st.locales["hastings"].favour = "lancastrian"
        st.lords["henry_vi"].assets = {"ship": 1}          # exactly one Ship
        st.lords["york"].location = "scarborough"          # Blockade the North Sea
        st.lords["york"].capabilities.append("Y15")
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "calais"})
    assert r["type"] == "tax"


# --------------------------------------------- 4.3.4 Intercept groups
def test_intercepting_lieutenant_cannot_bring_a_marshal():
    def prep(st):
        st.lords["somerset_1"].location = "bedford"        # Lieutenant
        st.lords["henry_vi"].location = "bedford"          # Marshal
    s = _campaign(prep=prep)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"intercept": "somerset_1",
                                               "intercept_group": ["henry_vi"]}})
    assert e.value.code == "lieutenant_cannot_lead_marshal"


def test_intercept_group_member_must_be_co_located():
    from plantagenet.state import LordStatus
    def prep(st):
        st.lords["somerset_1"].location = "bedford"
        st.lords["exeter_1"].status = LordStatus.MUSTERED  # same side, elsewhere
        st.lords["exeter_1"].location = "london"
        st.lords["exeter_1"].calendar_box = None
    s = _campaign(prep=prep)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"intercept": "somerset_1",
                                               "intercept_group": ["exeter_1"]}})
    assert e.value.code == "bad_group_member"


# ------------------------------------------------- 4.6.1 Sail extras
def test_group_sail_lieutenant_cannot_lead_a_marshal():
    def prep(st):
        st.lords["somerset_1"].location = "dover"          # Lieutenant
        st.lords["henry_vi"].location = "dover"            # Marshal
    s = _to_lancastrian(_campaign(lc=("somerset_1",), prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": "somerset_1", "to": "hastings",
                                 "group": ["henry_vi"]})
    assert e.value.code == "lieutenant_cannot_lead_marshal"


def test_owain_glyndwr_bars_lancastrian_sail_into_wales():
    # Y25 bars the LANCASTRIAN side (not the Yorkist) from Sailing to Wales.
    def prep(st):
        st.lords["henry_vi"].location = "bristol"
        st.lords["henry_vi"].forces = {"retinue": 1}
        st.lords["henry_vi"].assets = {"ship": 1}
        st.active_events.append({"card": "Y25", "side": "yorkist"})
    s = _to_lancastrian(_campaign(prep=prep))
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": "henry_vi", "to": "harlech"})
    assert e.value.code == "owain_glyndwr"
    assert s.lords["henry_vi"].location == "bristol"


def test_sharing_works_within_the_same_exile_box():
    # Sharing (1.5.3) reaches an ally in the SAME Exile box; a lone exiled
    # Lord Sails on a groupmate's Ship.
    def prep(st):
        st.lords["henry_vi"].location = None
        st.lords["henry_vi"].exile_box = "france"
        st.lords["henry_vi"].forces = {"retinue": 1}
        st.lords["henry_vi"].assets = {}
        st.lords["somerset_1"].location = None
        st.lords["somerset_1"].exile_box = "france"
        st.lords["somerset_1"].assets = {"ship": 1}
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": "henry_vi", "to": "dover",
                                 "share": ["somerset_1"]})
    assert r["type"] == "sail"
    assert s.lords["henry_vi"].location == "dover"


def test_sharing_works_on_the_same_sea():
    # Sharing (1.5.3) reaches an ally at the SAME Sea.
    def prep(st):
        st.lords["henry_vi"].location = None
        st.lords["henry_vi"].at_sea = "english_channel"
        st.lords["henry_vi"].forces = {"retinue": 1}
        st.lords["henry_vi"].assets = {}
        st.lords["somerset_1"].location = None
        st.lords["somerset_1"].at_sea = "english_channel"
        st.lords["somerset_1"].assets = {"ship": 1}
    s = _to_lancastrian(_campaign(prep=prep))
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": "henry_vi", "to": "dover",
                                 "share": ["somerset_1"]})
    assert r["type"] == "sail"
    assert s.lords["henry_vi"].location == "dover"


# ----------------------------------------------- 4.3.5 Approach window
def test_approach_ctx_lists_only_lords_at_the_destination():
    # King's Parley (L15) is offered only when Henry VI is a TARGET of the
    # Approach -- not merely Mustered somewhere else on the map.
    def prep(st):
        st.lords["somerset_1"].location = "cambridge"
        st.lords["henry_vi"].capabilities.append("L15")    # KING'S PARLEY
    s = _campaign(prep=prep)
    r = actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"responses": {"somerset_1": "battle"}}})
    assert r["type"] == "march"



# ------------------------------------------ 4.3.4 Flank Attack card economy
def test_flank_attack_march_ends_the_card_at_zero_not_minus_one():
    # Y2/L2 Flank Attack: the Intercept Battle consumes the Marching side's
    # command card. The march tail used to fall through to the normal
    # decrement, ending at actions_remaining == -1 (masked: every consumer
    # gates on > 0). Fixed 2026-07-02c.
    def prep(st):
        st.lords["somerset_1"].location = "bedford"
        st.decks["lancastrian"]["held"] = ["L2"]           # FLANK ATTACK held
    s = _campaign(prep=prep)
    r = actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": "york",
                                 "to": "cambridge",
                                 "decisions": {"intercept": "somerset_1",
                                               "flank_attack": True}})
    assert r["intercept"]["success"] and r["intercept"]["flank_attack"]
    assert r["approach"] is not None                       # the flank Battle happened
    assert s.campaign.actions_remaining == 0
