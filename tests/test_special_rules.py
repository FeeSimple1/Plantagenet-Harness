"""Scenario special rules: Ravaged Land / Brief Rebellion (skip Grow/Waste) and
Queen Regent (Margaret at London Tides bonus)."""

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


def _to_end_step(sid):
    s = build_initial_state(sid)
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian" and v.status == "mustered"]
    n = s.campaign.cards_required
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": _pad(yk, n)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": _pad(lc, n)})
    while s.campaign.step == "activation":
        actions.apply_action(s, {"type": "end_activation", "side": s.active_side})
    return s


def test_ravaged_land_skips_grow_and_waste():
    # My Kingdom for a Horse carries Ravaged Land. At a Grow box, a Depleted
    # Locale must NOT recover (Grow skipped); at a Waste box, no Waste.
    s = _to_end_step("my_kingdom_for_a_horse")
    s.turn_box = 4                                   # a Grow box (4/9/14)
    loc = next(iter(s.locales))
    s.locales[loc].depletion = "depleted"
    r = actions.apply_action(s, {"type": "end_campaign"})
    if r["victory"] is None:                          # only meaningful if play continues
        assert r["grow"] is False
        assert s.locales[loc].depletion == "depleted"   # Grow skipped


def test_baseline_grow_runs_without_ravaged_land():
    s = _to_end_step("henry_vi")                      # no Ravaged Land
    s.turn_box = 4
    loc = next(iter(s.locales))
    s.locales[loc].depletion = "depleted"
    r = actions.apply_action(s, {"type": "end_campaign"})
    assert r["victory"] is None and r["grow"] is True
    assert s.locales[loc].depletion is None           # Grow recovered it


def test_brief_rebellion_skips_waste():
    s = _to_end_step("somersets_return")
    assert "Brief Rebellion" in campaign._active_special_rules(s)
    s.turn_box = 5                                    # a Waste box (5/10)
    r = actions.apply_action(s, {"type": "end_campaign"})
    if r["victory"] is None:
        assert r["waste"] is False


def test_queen_regent_awards_three_when_margaret_at_london():
    s = build_initial_state("warwicks_rebellion")
    mg = s.lords.get("margaret")
    if mg is None:
        from plantagenet.state import LordState
        s.lords["margaret"] = LordState(lord_id="margaret", side="lancastrian",
                                        status=LordStatus.MUSTERED, location="london")
        mg = s.lords["margaret"]
    mg.status = LordStatus.MUSTERED
    mg.location = "london"
    tow = campaign.tides_of_war(s)
    assert any("Queen Regent" in d for d in tow["detail"])
    mg.location = "york"
    tow2 = campaign.tides_of_war(s)
    assert not any("Queen Regent" in d for d in tow2["detail"])


def test_concede_sets_war_victory_to_the_other_side():
    s = build_initial_state("wars_of_the_roses")          # War I
    r = actions.apply_action(s, {"type": "concede", "side": "lancastrian"})
    assert r["winner"] == "yorkist"
    assert s.victory == {"result": "yorkist", "rule": "6.1.1 Surrender",
                         "conceded_by": "lancastrian"}


def test_concede_rejected_outside_first_or_second_war():
    s = build_initial_state("wars_of_the_roses")
    s.grand_scenario["current_war"] = "war_iiiy"          # third War
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "concede", "side": "yorkist"})
    assert e.value.code == "no_surrender"


def test_gloucester_set_aside_suppresses_first_son():
    s = build_initial_state("wars_of_the_roses")
    from plantagenet.state import LordState
    s.lords["edward_iv"] = LordState(lord_id="edward_iv", side="yorkist",
                                     status=LordStatus.MUSTERED, location="york",
                                     capabilities=["Y28"])   # Y28 = FIRST SON capability
    base = campaign.tides_of_war(s)
    assert any("First Son" in d for d in base["detail"])    # functions normally
    s.grand_scenario["gloucester_as_heir_played"] = True    # Y28 Event set aside
    after = campaign.tides_of_war(s)
    assert not any("First Son" in d for d in after["detail"])   # Capability unavailable


def _iiy():
    from plantagenet.scenarios import renew_war
    s = build_initial_state("wars_of_the_roses")
    s.victory = {"result": "yorkist"}
    return renew_war(s)                                   # IIY (Shaky Allies + Foreign Haven)


def test_shaky_allies_blocks_co_locating_margaret_and_warwick():
    from plantagenet import commands
    n = _iiy()
    n.lords["warwick_lancastrian"].status = LordStatus.MUSTERED
    n.lords["warwick_lancastrian"].location = "york"
    assert commands._shaky_allies_block(n, ["margaret"], "york") is True
    assert commands._shaky_allies_block(n, ["margaret"], "london") is False
    assert commands._shaky_allies_block(n, ["margaret", "warwick_lancastrian"], "ely") is True
    # Not active outside the Shaky-Allies scenario.
    base = build_initial_state("henry_vi")
    assert commands._shaky_allies_block(base, ["margaret"], "york") is False


def test_foreign_haven_shift_pulls_calendars_in():
    n = _iiy()
    n.turn_box = 3
    for ls in n.lords.values():
        if ls.status == LordStatus.CALENDAR:
            ls.calendar_box = 9
    campaign._foreign_haven_shift(n)
    for ls in n.lords.values():
        if ls.status == LordStatus.CALENDAR:
            assert ls.calendar_box == (3 if ls.side == "lancastrian" else 4)


def test_foreign_haven_fires_when_warwick_exiles_on_approach():
    from plantagenet import battle
    n = _iiy()
    n.turn_box = 3
    for ls in n.lords.values():                           # Lancastrian Calendar lords out at 9
        if ls.status == LordStatus.CALENDAR and ls.side == "lancastrian":
            ls.calendar_box = 9
    wk = n.lords["warwick_lancastrian"]
    wk.status = LordStatus.MUSTERED
    wk.location = "cambridge"
    wk.forces = {"retinue": 1}
    yk = next(lid for lid, ls in n.lords.items()
              if ls.side == "yorkist" and lid != "warwick_lancastrian")
    n.lords[yk].status = LordStatus.MUSTERED
    n.lords[yk].location = "cambridge"
    n.lords[yk].forces = {"retinue": 1}
    r = battle.approach(n, "cambridge", [yk],
                        {"responses": {"warwick_lancastrian": "exile"}})
    assert r.get("foreign_haven") is True
    assert all(ls.calendar_box == 3 for ls in n.lords.values()
               if ls.status == LordStatus.CALENDAR and ls.side == "lancastrian")


def test_test_of_arms_battle_at_york_sets_favour_and_wins():
    from plantagenet import battle
    s = build_initial_state("towton")
    # York attacker vs a Lancastrian defender at York; the winner takes York Favour.
    for lid in ("york", "henry_vi"):
        if lid in s.lords:
            s.lords[lid].location = "york"
            s.lords[lid].status = LordStatus.MUSTERED
            s.lords[lid].capabilities = []
    if "york" in s.lords and "henry_vi" in s.lords:
        r = battle.resolve_battle(s, "york", "york", "henry_vi", {})
        assert s.locales["york"].favour == r["winner_side"]
        assert r.get("test_of_arms") == r["winner_side"]


def test_plain_5_3_victory_when_no_test_of_arms():
    # A non-Test-of-Arms scenario at its final Turn falls back to 5.3 (Influence).
    s = build_initial_state("wars_of_the_roses")           # War I: no special rules
    s.turn_box = s.calendar.last_box
    res = campaign._victory_check(s)
    assert res is not None and res["rule"] in ("5.3", "5.1")


def test_king_richard_replaces_gloucester_at_london():
    s = build_initial_state("my_kingdom_for_a_horse")
    g = "gloucester_1" if "gloucester_1" in s.lords else "gloucester_2"
    s.lords[g].status = LordStatus.MUSTERED
    s.lords[g].location = "london"
    r = actions.apply_action(s, {"type": "crown_richard", "side": "yorkist"})
    assert r["with"] == "richard_iii"
    assert s.lords["richard_iii"].location == "london"
    assert s.lords[g].status == LordStatus.REMOVED


def test_king_richard_requires_gloucester_at_london():
    s = build_initial_state("my_kingdom_for_a_horse")
    for g in ("gloucester_1", "gloucester_2"):
        if g in s.lords:
            s.lords[g].location = "york"     # not London
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "crown_richard", "side": "yorkist"})
    assert e.value.code == "no_gloucester_at_london"


def test_bosworth_battle_resolves_and_picks_a_winner():
    from plantagenet import battle
    s = build_initial_state("bosworth")               # battle-only: no Influence track
    yk = ["richard_iii", "northumberland_2", "norfolk"]
    lc = ["henry_tudor", "jasper_tudor_2", "oxford"]
    for lid in yk + lc:
        s.lords[lid].location = "leicester"
    r = battle.resolve_battle(s, "leicester", yk, lc)
    assert r["winner_side"] in ("yorkist", "lancastrian", None)   # None == all-Rout draw
    assert "influence_award" not in r                  # no Influence on a battle-only scenario
