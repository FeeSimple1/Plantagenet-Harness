"""War IIIL succession-driven setup (Scenario Reference E7): Lancastrians King,
Yorkist Rebels placed by Succession in Burgundy (or Calais if Warwick is Heir)."""

from __future__ import annotations

from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import LordState, LordStatus

_IN_PLAY = (LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE)


def _to_iiil(removed=(), gloucester_as_heir=False):
    s = build_initial_state("wars_of_the_roses")
    s.grand_scenario["current_war"] = "war_iil"
    if gloucester_as_heir:
        s.grand_scenario["gloucester_as_heir_played"] = True
    for lid in removed:
        if lid not in s.lords:
            lanc = lid in ("henry_vi", "margaret", "somerset_1", "somerset_2")
            s.lords[lid] = LordState(lord_id=lid, side="lancastrian" if lanc else "yorkist",
                                     status=LordStatus.MUSTERED)
        s.lords[lid].status = LordStatus.REMOVED
    s.turn_box = 3
    s.victory = {"result": "lancastrian"}
    n = renew_war(s)
    assert n.grand_scenario["current_war"] == "war_iiil"
    return n


def _at(n, lid):
    ls = n.lords[lid]
    return ls.location or ls.exile_box or f"box{ls.calendar_box}"


def _inplay(n, lid):
    ls = n.lords.get(lid)
    return ls is not None and ls.status in _IN_PLAY


def test_iiil_lancastrian_king_and_supporting_lords():
    n = _to_iiil()
    assert _at(n, "henry_vi") == "london"                # highest L Heir is King
    assert {"L15", "L17"} <= set(n.decks["lancastrian"]["draw"])
    assert _at(n, "oxford") == "oxford" and _at(n, "jasper_tudor_2") == "pembroke"
    assert n.locales["london"].favour == "lancastrian"


def test_iiil_somerset2_yields_to_somerset1_as_king():
    n = _to_iiil(removed=["henry_vi", "margaret", "somerset_1"])
    assert _at(n, "somerset_1") == "london"              # Somerset (2) yields to (1)
    assert not _inplay(n, "somerset_2")
    assert {"L18", "L20", "L27"} <= set(n.decks["lancastrian"]["draw"])


def test_iiil_margaret_king_gets_l26():
    n = _to_iiil(removed=["henry_vi"])
    assert _at(n, "margaret") == "london"
    assert "L26" in n.lords["margaret"].capabilities
    assert {"L27", "L31"} <= set(n.decks["lancastrian"]["draw"])


def test_iiil_yorkist_heirs_go_to_burgundy_with_norfolk():
    n = _to_iiil()
    assert _at(n, "york") == "burgundy" and {"Y14", "Y18"} <= set(n.decks["yorkist"]["draw"])
    assert _at(n, "march") == "burgundy" and "Y20" in n.decks["yorkist"]["draw"]
    assert _at(n, "norfolk") == "burgundy"               # Norfolk always
    assert not _inplay(n, "rutland") and not _inplay(n, "gloucester_1")   # only York + next


def test_iiil_sole_gloucester_heir_gets_gloucester2_and_salisbury():
    n = _to_iiil(removed=["york", "march", "rutland"])
    assert _at(n, "gloucester_2") == "burgundy" and "Y35" in n.decks["yorkist"]["draw"]
    assert _at(n, "salisbury") == "burgundy"             # exactly one Heir -> Salisbury
    assert {"Y17", "Y22"} <= set(n.decks["yorkist"]["draw"])


def test_iiil_warwick_heir_lands_at_calais():
    n = _to_iiil(removed=["york", "gloucester_1", "gloucester_2", "richard_iii"])
    assert _at(n, "warwick_yorkist") == "calais" and "Y16" in n.decks["yorkist"]["draw"]
    assert _at(n, "salisbury") == "calais" and _at(n, "norfolk") == "calais"
