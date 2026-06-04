"""In-place Lord replacement (Scenario Ref REPLACE): a replacement swaps the
Lord card on the existing mat, keeps the cylinder position, and rewrites
Command-card references including the side's Plan stack. A replacement triggered
by a lost Battle must not seat the new Lord on the enemy-held Locale."""

from __future__ import annotations

from plantagenet import battle, invariants
from plantagenet.state import CampaignState, LordState, LordStatus
from tests.test_succession import _remove, _stage_war


def _campaign(s, plans, active):
    s.campaign = CampaignState(
        step="activation", cards_required=2, plans=plans,
        plan_built={"lancastrian": True, "yorkist": True},
        plan_index={"lancastrian": 0, "yorkist": 0}, active_lord=active)


# --------- Bug 1: battle-death replacement must not co-locate with the victor --
def test_somerset_death_in_lost_battle_goes_to_calendar_not_enemy_locale():
    s = _stage_war("war_iil", "lancastrian", ["henry_vi", "margaret", "somerset_1"])
    s.lords["somerset_1"].location = "wells"
    s.lords["somerset_1"].capabilities = ["L1", "L12"]
    s.lords["devon"] = LordState(lord_id="devon", side="yorkist",
                                 status=LordStatus.MUSTERED, location="wells")
    _campaign(s, {"lancastrian": [{"lord": "somerset_1"}, {"pass": True}],
                  "yorkist": [{"lord": "devon"}, {"pass": True}]}, "somerset_1")
    battle._kill_lord(s, "somerset_1")
    # Somerset 2 enters the Calendar -- NOT seated at Wells beside the victor.
    assert s.lords["somerset_2"].status == LordStatus.CALENDAR
    assert s.lords["somerset_2"].location is None
    assert s.lords["somerset_1"].status == LordStatus.REMOVED
    # No illegal co-location anywhere.
    assert not [v for v in invariants.board_invariant_violations(s)
                if v["kind"] == "co_location"]


# --------- Bug 2a: the Plan stack + active-Lord are rewritten on replacement ---
def test_replacement_rewrites_plan_stack_and_active_lord():
    s = _stage_war("war_iil", "lancastrian", ["henry_vi", "margaret", "somerset_1"])
    s.lords["somerset_1"].location = "wells"
    _campaign(s, {"lancastrian": [{"lord": "somerset_1"}, {"pass": True}],
                  "yorkist": [{"pass": True}, {"pass": True}]}, "somerset_1")
    battle._kill_lord(s, "somerset_1")
    assert s.campaign.plans["lancastrian"][0] == {"lord": "somerset_2"}
    assert s.campaign.active_lord == "somerset_2"


# --------- Bug 2b: a living in-place replacement keeps the mat (March->Edward) --
def test_living_replacement_preserves_mat_and_rewrites_plan():
    s = _stage_war("war_iiy", "yorkist", ["york", "march", "rutland", "gloucester_1"])
    m = s.lords["march"]
    m.location = "london"
    m.forces = {"retinue": 1, "men_at_arms": 4}
    m.assets = {"coin": 3, "cart": 2}
    m.capabilities = ["Y2"]
    _campaign(s, {"yorkist": [{"lord": "march"}, {"pass": True}],
                  "lancastrian": [{"pass": True}, {"pass": True}]}, "march")
    _remove(s, "york")                          # March becomes King -> Edward IV in place
    e = s.lords["edward_iv"]
    assert e.status == LordStatus.MUSTERED and e.location == "london"
    assert e.forces == {"retinue": 1, "men_at_arms": 4}     # mat preserved
    assert e.assets == {"coin": 3, "cart": 2}
    assert e.capabilities == ["Y2"]
    assert s.lords["march"].status == LordStatus.REMOVED
    assert s.campaign.plans["yorkist"][0] == {"lord": "edward_iv"}
    assert s.campaign.active_lord == "edward_iv"
    # No position-consistency problem from the swap (the _stage_war helper packs
    # several heirs onto london, so a blanket co_location check is not meaningful).
    assert not [v for v in invariants.lord_status_violations(s)
                if v["lord"] in ("edward_iv", "march")]


# --------- In-place seat IS used when the freed Locale has no enemy ------------
def test_replacement_seats_in_place_when_locale_is_enemy_free():
    s = _stage_war("war_iil", "lancastrian", ["henry_vi", "margaret", "somerset_1"])
    s.lords["somerset_1"].location = "wells"        # no enemy present at Wells
    _campaign(s, {"lancastrian": [{"lord": "somerset_1"}, {"pass": True}],
                  "yorkist": [{"pass": True}, {"pass": True}]}, "somerset_1")
    battle._kill_lord(s, "somerset_1")
    s2 = s.lords["somerset_2"]
    assert s2.status == LordStatus.MUSTERED and s2.location == "wells"
    assert not [v for v in invariants.board_invariant_violations(s)
                if v["kind"] == "co_location"]
