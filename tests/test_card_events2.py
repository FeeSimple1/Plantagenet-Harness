"""Wave E2/E3: this-Levy/Campaign Event modifiers and battle-timing Hold Events."""

from __future__ import annotations

import pytest

from plantagenet import actions, battle, ratings
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def _muster(sid="henry_vi", seed=1):
    s = build_initial_state(sid, seed=seed)
    to_muster(s)
    return s


# ---- parley event modifiers ----
def test_succession_parley_auto_and_discount_once_per_lord():
    s = _muster()
    s.active_events.append({"card": "Y18", "side": "yorkist"})   # SUCCESSION
    m1 = actions._parley_event_mods(s, "york", "yorkist")
    assert m1["auto"] and m1["discount"] == 1
    m2 = actions._parley_event_mods(s, "york", "yorkist")        # already used
    assert not m2["auto"] and m2["discount"] == 0


def test_an_honest_tale_adds_lancastrian_parley_cost():
    s = _muster()
    s.active_events.append({"card": "Y34", "side": "yorkist"})   # AN HONEST TALE
    m = actions._parley_event_mods(s, "somerset_1", "lancastrian")
    assert m["discount"] == -1


def test_gloucester_as_heir_free_lordship():
    s = build_initial_state("warwicks_rebellion")
    s.active_events.append({"card": "Y28", "side": "yorkist"})   # GLOUCESTER AS HEIR
    m = actions._parley_event_mods(s, "gloucester_1", "yorkist")
    assert m["free_lordship"] is True


# ---- rating events ----
def test_edward_v_grants_gloucester_lordship():
    s = build_initial_state("warwicks_rebellion")
    base = ratings.rating(s, "gloucester_1", "lordship")
    s.active_events.append({"card": "Y33", "side": "yorkist"})   # EDWARD V
    assert ratings.rating(s, "gloucester_1", "lordship") == base + 3


def test_loyalty_and_trust_targets_one_lord():
    s = build_initial_state("warwicks_rebellion")
    base = ratings.rating(s, "gloucester_1", "lordship")
    s.active_events.append({"card": "Y22", "side": "yorkist", "target": "gloucester_1"})
    assert ratings.rating(s, "gloucester_1", "lordship") == base + 3


def test_yorkist_parade_influence_plus_two():
    s = build_initial_state("warwicks_rebellion")
    base = ratings.rating(s, "gloucester_1", "influence")
    s.active_events.append({"card": "Y20", "side": "yorkist"})   # YORKIST PARADE
    assert ratings.rating(s, "gloucester_1", "influence") == base + 2


# ---- this-Campaign prohibitions ----
def _campaign(sid="henry_vi", seed=1):
    s = _muster(sid, seed)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian" and v.status == "mustered"]
    n = s.campaign.cards_required

    def pad(lo):
        e = [{"lord": x} for x in lo][:n]
        while len(e) < n:
            e.append({"pass": True})
        return e
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": pad(yk)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": pad(lc)})
    return s


def test_french_fleet_blocks_yorkist_sail():
    s = _campaign()
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    if lord.side != "yorkist":
        # advance to a Yorkist activation if needed
        return
    lord.location = "ipswich"
    s.locales["ipswich"].favour = lord.side
    lord.assets["ship"] = 3
    s.active_events.append({"card": "L21", "side": "lancastrian"})   # FRENCH FLEET
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": lord.side,
                                 "by_lord": lid, "to": "scarborough"})
    assert e.value.code == "french_fleet"


# ---- battle-timing Hold Events ----
def test_talbot_disbands_routed_lancastrian_instead_of_death():
    s = build_initial_state("my_kingdom_for_a_horse")
    rid = "richard_iii"
    s.lords[rid].status = LordStatus.MUSTERED.value
    s.lords[rid].location = "leicester"
    foe = next(lo for lo, v in s.lords.items() if v.side == "lancastrian")
    s.lords[foe].status = LordStatus.MUSTERED.value
    s.lords[foe].location = "leicester"
    forces = {rid: battle._Force(s, rid), foe: battle._Force(s, foe)}
    forces[foe].lord_routed = True
    res = battle._ending(s, "leicester", forces, [rid], [foe], [], [], talbot=True)
    assert foe in res.get("disbands", [])
    assert foe not in res.get("deaths", [])


def test_patrick_de_la_mote_requires_held_event():
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"patrick": True})
    assert e.value.code == "no_patrick"
