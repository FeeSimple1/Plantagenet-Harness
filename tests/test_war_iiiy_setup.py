"""War IIIY succession-driven setup (Scenario Reference E6): the entire roster
is placed from Succession (the base Scenario III lords/seats/favour suppressed),
keyed on who survived earlier Wars and the Y28 set-aside."""

from __future__ import annotations

from plantagenet import invariants
from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import LordState, LordStatus

_IN_PLAY = (LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE)


def _to_iiiy(removed=(), gloucester_as_heir=False):
    s = build_initial_state("wars_of_the_roses")
    s.grand_scenario["current_war"] = "war_iiy"          # transition the 2nd War -> IIIY
    if gloucester_as_heir:
        s.grand_scenario["gloucester_as_heir_played"] = True
    for lid in removed:
        if lid not in s.lords:
            side = "lancastrian" if lid in ("margaret", "henry_tudor") else "yorkist"
            s.lords[lid] = LordState(lord_id=lid, side=side, status=LordStatus.MUSTERED)
        s.lords[lid].status = LordStatus.REMOVED
    s.turn_box = 3                                        # avoid Natural-Causes auto-removals
    s.victory = {"result": "yorkist"}
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iiiy"
    return n


def _inplay(n, lid):
    ls = n.lords.get(lid)
    return ls is not None and ls.status in _IN_PLAY


def _at(n, lid):
    ls = n.lords[lid]
    return ls.location or ls.exile_box or f"box{ls.calendar_box}"


def test_iiiy_all_survive_seats_york_keeps_march_removes_rest():
    n = _to_iiiy()
    assert _at(n, "york") == "london" and {"Y14", "Y21"} <= set(n.decks["yorkist"]["draw"])
    assert _at(n, "march") == "ludlow" and "Y20" in n.decks["yorkist"]["draw"]
    # Only King + next Heir survive; Rutland and Gloucester are removed.
    assert not _inplay(n, "rutland") and not _inplay(n, "gloucester_1")
    assert _at(n, "norfolk") == "arundel"               # Norfolk always
    assert not _inplay(n, "northumberland_2")           # three seniors remain
    assert invariants.co_location_violations(n) == []


def test_iiiy_lancastrian_lead_is_margaret_with_l26():
    n = _to_iiiy()
    assert _at(n, "margaret") == "france"
    assert {"L27", "L31"} <= set(n.decks["lancastrian"]["draw"])
    assert "L26" in n.lords["margaret"].capabilities
    assert _at(n, "oxford") == "france" and _at(n, "jasper_tudor_2") == "france"


def test_iiiy_york_and_march_gone_make_rutland_king_gloucester2_gold():
    n = _to_iiiy(removed=["york", "march"])
    assert _at(n, "rutland") == "london" and {"Y20", "Y21"} <= set(n.decks["yorkist"]["draw"])
    assert _at(n, "gloucester_2") == "london" and n.lords["gloucester_2"].ring == "gold"
    assert _at(n, "northumberland_2") == "carlisle"     # exactly one senior (Gloucester) remains
    assert "Y37" in n.decks["yorkist"]["draw"]


def test_iiiy_only_gloucester_gives_richard_iii_king():
    n = _to_iiiy(removed=["york", "march", "rutland"])
    assert _at(n, "richard_iii") == "london" and n.lords["richard_iii"].ring == "gold"
    assert {"Y32", "Y33"} <= set(n.decks["yorkist"]["draw"])


def test_iiiy_sole_rutland_promotes_yorkist_warwick_to_king():
    n = _to_iiiy(removed=["york", "march", "gloucester_1", "gloucester_2", "richard_iii"])
    assert _at(n, "warwick_yorkist") == "london"
    assert _at(n, "salisbury") == "york"
    assert {"Y16", "Y17", "Y22"} <= set(n.decks["yorkist"]["draw"])
    assert not _inplay(n, "rutland")                    # the sole Heir is removed


def test_iiiy_y28_set_aside_displaces_rutland_with_gloucester():
    # York is King; March gone. Without Y28 the next Heir is Rutland (Canterbury);
    # with Y28 set aside, Rutland is displaced so Gloucester (1) is the Heir.
    n = _to_iiiy(removed=["march"], gloucester_as_heir=True)
    assert _at(n, "york") == "london"
    assert not _inplay(n, "rutland")
    assert _at(n, "gloucester_1") == "gloucester" and n.lords["gloucester_1"].ring == "silver"


def test_iiiy_henry_tudor_leads_when_margaret_gone_and_king_not_edward():
    n = _to_iiiy(removed=["margaret"])                   # York is King (not Edward IV)
    assert _at(n, "henry_tudor") == "france"
    assert {"L32", "L35"} <= set(n.decks["lancastrian"]["draw"])


def test_iiiy_warwick_leads_at_calais_when_edward_iv_is_king():
    n = _to_iiiy(removed=["margaret", "york"])           # York gone -> Edward IV King
    assert _at(n, "edward_iv") == "london"
    assert _at(n, "warwick_lancastrian") == "calais"     # Henry Tudor barred (Edward IV King)
    assert _at(n, "oxford") == "calais" and _at(n, "jasper_tudor_2") == "calais"
    assert {"L23", "L30"} <= set(n.decks["lancastrian"]["draw"])


def test_iiiy_favour_is_london_yorkist_plus_marked_seats():
    n = _to_iiiy()
    assert n.locales["london"].favour == "yorkist"
    assert n.locales["arundel"].favour == "yorkist"      # Norfolk's Seat
    assert n.locales["ludlow"].favour == "yorkist"       # March's Seat


def test_iiiy_recomputes_stronghold_markers_from_favour():
    n = _to_iiiy()
    locs_static = __import__("plantagenet.static_data", fromlist=["x"]).load_locales()
    track = n.influence["track"]
    for typ in ("city", "town", "fortress"):
        counts = {s: sum(1 for lid, lc in locs_static.items()
                         if lc.get("type") == typ and n.locales[lid].favour == s)
                  for s in ("yorkist", "lancastrian")}
        m = track.stronghold_markers[typ]
        assert m.at == abs(counts["yorkist"] - counts["lancastrian"])
        if counts["yorkist"] != counts["lancastrian"]:
            assert m.side == ("yorkist" if counts["yorkist"] > counts["lancastrian"]
                              else "lancastrian")
