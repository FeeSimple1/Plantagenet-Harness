"""Levy/economy card effects: Beloved Warwick, Alice Montagu, Great Ships."""

from __future__ import annotations

from plantagenet import actions
from plantagenet.scenarios import build_initial_state
from plantagenet.state import VassalStatus
from tests._helpers import to_muster


def _muster(sid="henry_vi", seed=1):
    s = build_initial_state(sid, seed=seed)
    to_muster(s)
    return s


def test_beloved_warwick_levies_five_militia():
    s = _muster()
    york = s.lords["york"]                 # at Ely (Friendly City), Yorkist active
    york.capabilities = ["Y16"]            # Beloved Warwick
    mil = york.forces.get("militia", 0)
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert r["added"] == {"militia": 5}    # 5 Militia instead of City's 1 Longbow + 1 Militia
    assert york.forces["militia"] == mil + 5


def test_alice_montagu_adds_one_service():
    s = _muster(seed=2)
    york = s.lords["york"]
    york.capabilities = ["Y17"]            # Alice Montagu
    s.locales["ipswich"].favour = "yorkist"   # Suffolk's Seat Friendly
    for _ in range(20):
        if s.vassals["suffolk"].status == VassalStatus.MUSTERED:
            break
        york.lordship_spent = 0
        actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                 "by_lord": "york", "target": "suffolk"})
    # Suffolk Service 3 -> normally Turn 1 + 3 = box 4; Alice Montagu -> box 5.
    assert s.vassals["suffolk"].service_box == 5


def test_great_ships_connects_all_ports_for_route():
    s = build_initial_state("henry_vi")
    # Calais (English Channel) to Harlech (Irish Sea): only linked with Great Ships.
    base = actions._parley_route_cost(s, ("stronghold", "calais"), "harlech",
                                      "yorkist", has_ship=True, all_seas=False)
    gs = actions._parley_route_cost(s, ("stronghold", "calais"), "harlech",
                                    "yorkist", has_ship=True, all_seas=True)
    assert base is None              # different Seas, no normal Ship route
    assert gs == 1                   # Great Ships: all Ports 1 Way apart


def _campaign(sid="henry_vi", seed=1):
    s = build_initial_state(sid, seed=seed)
    to_muster(s)
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


def test_great_ships_supply_two_provender_per_ship():
    s = _campaign()
    lid = s.campaign.active_lord
    lord = s.lords[lid]
    lord.location = "ipswich"              # a Friendly Port
    s.locales["ipswich"].favour = lord.side
    lord.assets["ship"] = 2
    lord.capabilities = ["Y6"]             # Great Ships
    prov = lord.assets.get("provender", 0)
    r = actions.apply_action(s, {"type": "supply", "side": lord.side,
                                 "by_lord": lid, "source": "ipswich", "use_ships": True})
    assert r["provender_added"] == 4       # 2 Ships x 2 Provender (Great Ships)
    assert lord.assets["provender"] == prov + 4
