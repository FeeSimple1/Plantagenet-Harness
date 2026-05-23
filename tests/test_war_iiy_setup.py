"""War IIY succession-driven setup (Scenario Reference E4): the Yorkist roster
is placed by who survived War I, not the standalone Scenario II roster."""

from __future__ import annotations

from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import LordStatus


def _to_iiy(removed=()):
    s = build_initial_state("wars_of_the_roses")
    for lid in removed:
        if lid in s.lords:
            s.lords[lid].status = LordStatus.REMOVED
    s.victory = {"result": "yorkist"}            # Yorkists win War I -> IIY
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iiy"
    return n


def _loc(ls):
    return ls.location or (f"box{ls.calendar_box}" + ("x" if ls.calendar_exile else ""))


def test_iiy_all_heirs_survive_seats_york_with_march_and_rutland():
    n = _to_iiy()
    assert n.lords["york"].status == LordStatus.MUSTERED and n.lords["york"].location == "london"
    assert n.lords["march"].location == "ludlow"            # York is King -> March at Ludlow
    assert n.lords["rutland"].location == "canterbury"
    assert n.lords["gloucester_1"].calendar_box == 9 and n.lords["gloucester_1"].ring == "silver"
    assert n.lords["devon"].calendar_box == 1
    assert n.lords["northumberland_1"].calendar_box == 9
    assert n.locales["canterbury"].favour == "yorkist"
    # Pembroke does not join while four Heirs remain.
    assert n.lords["pembroke"].status not in (LordStatus.MUSTERED, LordStatus.CALENDAR)
    # Edward IV / Richard III are not on the board (their slots are not King).
    assert n.lords.get("edward_iv") is None or \
        n.lords["edward_iv"].status not in (LordStatus.MUSTERED, LordStatus.CALENDAR)


def test_iiy_lancastrian_lead_is_surviving_henry_vi_not_margaret():
    n = _to_iiy()
    assert n.lords["henry_vi"].calendar_box == 9 and n.lords["henry_vi"].calendar_exile
    assert n.lords["somerset_1"].calendar_box == 9 and n.lords["somerset_1"].calendar_exile
    # Margaret / Somerset (2) yield their box-9 slots to the surviving leaders.
    assert n.lords["margaret"].status not in (LordStatus.MUSTERED, LordStatus.CALENDAR)
    assert n.lords["somerset_2"].status not in (LordStatus.MUSTERED, LordStatus.CALENDAR)
    assert all(c in n.decks["lancastrian"]["draw"] for c in ("L17", "L18", "L20", "L21"))


def test_iiy_york_removed_promotes_edward_iv_to_king():
    n = _to_iiy(removed=["york"])
    assert n.lords["edward_iv"].status == LordStatus.MUSTERED
    assert n.lords["edward_iv"].location == "london"            # March -> Edward IV in place
    assert "march" not in n.lords or n.lords["march"].status not in (
        LordStatus.MUSTERED, LordStatus.CALENDAR)
    assert n.lords["rutland"].location == "canterbury"
    assert all(c in n.decks["yorkist"]["draw"] for c in ("Y23", "Y24", "Y28", "Y31"))


def test_iiy_only_gloucester_left_gives_richard_iii_king_and_pembroke():
    n = _to_iiy(removed=["york", "march", "rutland"])
    assert n.lords["richard_iii"].status == LordStatus.MUSTERED
    assert n.lords["richard_iii"].location == "london"
    assert n.lords["pembroke"].location == "pembroke"          # two or fewer Heirs -> Pembroke
    assert all(c in n.decks["yorkist"]["draw"] for c in ("Y32", "Y33", "Y34", "Y35"))


def test_iiy_dead_henry_vi_leaves_margaret_in_the_lead():
    n = _to_iiy(removed=["henry_vi"])
    # A Henry VI who died in War I is not on the IIY board; Margaret keeps the
    # box-9 (Exile) lead she holds in the base Scenario II setup.
    assert "henry_vi" not in n.lords or n.lords["henry_vi"].status not in (
        LordStatus.MUSTERED, LordStatus.CALENDAR)
    assert n.lords["margaret"].calendar_box == 9 and n.lords["margaret"].calendar_exile
