"""Wave D: command/economy Capabilities and the new Capability Command actions."""

from __future__ import annotations

from plantagenet import actions, battle
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def _muster(sid="henry_vi", seed=1):
    s = build_initial_state(sid, seed=seed)
    to_muster(s)
    return s


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


# ---------------- Levy Troops modifiers ----------------
def test_woodvilles_no_depletion():
    s = _muster()
    york = s.lords["york"]
    york.capabilities = ["Y31"]            # Woodvilles
    here = york.location
    actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert s.locales[here].depletion is None      # not Depleted


def test_soldiers_of_fortune_adds_mercenaries_for_coin():
    s = _muster()
    york = s.lords["york"]
    york.capabilities = ["Y12"]            # Soldiers of Fortune
    york.assets["coin"] = 1
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                 "by_lord": "york", "soldiers_of_fortune": True})
    assert r["added"].get("mercenaries") == 2
    assert york.assets["coin"] == 0


def test_the_commons_event_adds_militia():
    s = _muster()
    york = s.lords["york"]
    s.active_events.append({"card": "Y16", "side": "yorkist"})   # THE COMMONS (Event)
    mil = york.forces.get("militia", 0)
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                 "by_lord": "york", "commons_extra": 2})
    assert york.forces["militia"] == mil + r["added"]["militia"]
    assert r["added"]["militia"] >= 2


# ---------------- Supply / Forage / Tax modifiers ----------------
def test_harbingers_doubles_supply_provender():
    s = _campaign()
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    lord.location = "ipswich"
    s.locales["ipswich"].favour = lord.side
    lord.assets["ship"] = 1
    lord.capabilities = ["Y7"]             # Harbingers
    r = actions.apply_action(s, {"type": "supply", "side": lord.side,
                                 "by_lord": lid, "source": "ipswich", "use_ships": True})
    assert r["provender_added"] == 2       # 1 Ship x1, doubled by Harbingers


def test_scourers_forage_plus_one():
    s = _campaign()
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    s.locales[lord.location].favour = lord.side       # Friendly -> auto success
    s.locales[lord.location].depletion = None
    lord.capabilities = ["Y13"]            # Scourers
    prov = lord.assets.get("provender", 0)
    r = actions.apply_action(s, {"type": "forage", "side": lord.side, "by_lord": lid})
    assert r["provender_added"] == 2 and lord.assets["provender"] == prov + 2


def test_so_wise_so_young_tax_plus_one_coin():
    s = _campaign()
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    lord.capabilities = ["Y34"]            # So Wise, So Young
    seat = __import__("plantagenet.static_data", fromlist=["x"]).load_lords()[lid]["seat"]
    lord.location = seat
    s.locales[seat].favour = lord.side
    s.locales[seat].depletion = None
    base = __import__("plantagenet.static_data", fromlist=["x"]).stronghold_yields(
        seat)["tax"]["coin"]
    r = actions.apply_action(s, {"type": "tax", "side": lord.side,
                                 "by_lord": lid, "target": seat})
    assert r["coin_added"] == base + 1


# ---------------- New Command actions ----------------
def test_agitators_depletes_adjacent_enemy():
    s = _campaign()
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    nbr = next(n for n, _t in
               __import__("plantagenet.commands", fromlist=["_adjacency"])._adjacency()
               .get(lord.location, []))
    lord.capabilities = ["Y10"]            # Agitators
    s.locales[nbr].favour = "neutral"
    s.locales[nbr].depletion = None
    r = actions.apply_action(s, {"type": "agitators", "side": lord.side,
                                 "by_lord": lid, "target": nbr})
    assert r["depletion"] == "depleted"


def test_merchants_removes_depletion_on_success():
    s = _campaign(seed=3)
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    lord.capabilities = ["L30"]            # Merchants
    s.locales[lord.location].depletion = "exhausted"
    r = actions.apply_action(s, {"type": "merchants", "side": lord.side,
                                 "by_lord": lid, "targets": [lord.location],
                                 "extra_spend": 3})
    if r["success"]:
        # Removing an Exhausted marker clears the Stronghold entirely (L30):
        # "neither Exhausted nor Depleted".
        assert s.locales[lord.location].depletion is None


def test_heralds_shifts_calendar_lord_on_success():
    s = _campaign(seed=4)
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    # Put the Lord at a Port.
    port = next(k for k, v in
                __import__("plantagenet.static_data", fromlist=["x"]).load_locales().items()
                if isinstance(v, dict) and v.get("port"))
    lord.location = port
    s.locales[port].favour = lord.side
    lord.capabilities = ["L4"]             # Heralds
    target = next(lo for lo, v in s.lords.items()
                  if v.side == lord.side and v.status == LordStatus.CALENDAR
                  and v.calendar_box is not None)
    r = actions.apply_action(s, {"type": "heralds", "side": lord.side,
                                 "by_lord": lid, "target": target, "extra_spend": 3})
    if r["success"]:
        assert s.lords[target].calendar_box == s.turn_box + 1


# ---------------- Pay-timing and Exile ----------------
def test_england_is_my_home_disbands_instead_of_exile():
    s = build_initial_state("warwicks_rebellion")
    foe = "clarence"                       # any Lord at a Locale
    s.lords[foe].status = LordStatus.MUSTERED.value
    s.lords[foe].location = "york"
    s.lords[foe].capabilities = ["Y8"]     # England Is My Home
    s.locales["york"].favour = "yorkist"
    atk = next(lo for lo, v in s.lords.items()
               if v.side != s.lords[foe].side and v.status == LordStatus.MUSTERED)
    s.lords[atk].location = "york"
    battle._exile(s, "york", foe, atk)
    assert s.lords[foe].status == LordStatus.CALENDAR
    assert s.lords[foe].calendar_box == s.turn_box + 1
    assert s.lords[foe].calendar_exile is False
