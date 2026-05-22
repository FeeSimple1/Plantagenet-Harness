"""Wave B: Capability effects at Tides of War (4.8.1 / 1.9.1)."""

from __future__ import annotations

from plantagenet import campaign, static_data
from plantagenet.scenarios import build_initial_state
from plantagenet.state import Favour, LordStatus


def _muster(state, lord_id, location):
    ls = state.lords[lord_id]
    ls.status = LordStatus.MUSTERED.value
    ls.location = location


def _clear_region(state, area):
    loc = static_data.load_locales()
    for k, v in loc.items():
        if isinstance(v, dict) and v.get("region") == area:
            state.locales[k].favour = Favour.NEUTRAL.value


def test_welshmen_dominates_wales_without_all_favour():
    s = build_initial_state("henry_vi")
    _clear_region(s, "wales")
    _muster(s, "warwick_yorkist", "pembroke")
    for loc in ("pembroke", "cardiff", "harlech"):      # 3 of 7 (not all)
        s.locales[loc].favour = "yorkist"
    base = campaign.tides_of_war(s)["points"]["yorkist"]
    s.lords["warwick_yorkist"].capabilities = ["Y19"]   # WELSHMEN
    assert campaign.tides_of_war(s)["points"]["yorkist"] == base + 2


def test_welshmen_needs_three_friendly_strongholds():
    s = build_initial_state("henry_vi")
    _clear_region(s, "wales")
    _muster(s, "warwick_yorkist", "pembroke")
    s.lords["warwick_yorkist"].capabilities = ["Y19"]
    for loc in ("pembroke", "cardiff"):                 # only 2 Friendly
        s.locales[loc].favour = "yorkist"
    tow = campaign.tides_of_war(s)
    assert not any("Dominates wales" in d for d in tow["detail"])


def test_northmen_dominates_north():
    s = build_initial_state("henry_vi")
    _clear_region(s, "north")
    _muster(s, "somerset_1", "carlisle")
    for loc in ("carlisle", "newcastle", "hexham"):     # 3 Friendly (of 6)
        s.locales[loc].favour = "lancastrian"
    base = campaign.tides_of_war(s)["points"]["lancastrian"]
    s.lords["somerset_1"].capabilities = ["L16"]        # NORTHMEN
    assert campaign.tides_of_war(s)["points"]["lancastrian"] == base + 2


def test_first_son_adds_one_yorkist_influence():
    s = build_initial_state("henry_vi")
    _muster(s, "salisbury", "york")
    base = campaign.tides_of_war(s)["points"]["yorkist"]
    s.lords["salisbury"].capabilities = ["Y28"]         # FIRST SON
    assert campaign.tides_of_war(s)["points"]["yorkist"] == base + 1


def test_council_member_adds_one_lancastrian_influence():
    s = build_initial_state("henry_vi")
    _muster(s, "somerset_1", "york")
    base = campaign.tides_of_war(s)["points"]["lancastrian"]
    s.lords["somerset_1"].capabilities = ["L18"]        # COUNCIL MEMBER
    assert campaign.tides_of_war(s)["points"]["lancastrian"] == base + 1


def test_margaret_takes_the_reins_only_outside_london():
    s = build_initial_state("henry_vi")
    _muster(s, "henry_vi", "york")
    base = campaign.tides_of_war(s)["points"]["lancastrian"]
    s.lords["henry_vi"].capabilities = ["L17"]          # MARGARET TAKES THE REINS
    assert campaign.tides_of_war(s)["points"]["lancastrian"] == base + 2   # outside London
    _muster(s, "henry_vi", "london")
    assert campaign.tides_of_war(s)["points"]["lancastrian"] == base       # at London: none


def test_deeds_of_charity_pays_provender_for_influence():
    s = build_initial_state("henry_vi")
    _muster(s, "salisbury", "york")
    s.lords["salisbury"].capabilities = ["Y4"]          # WE DONE DEEDS OF CHARITY
    s.lords["salisbury"].assets["provender"] = 2
    base = campaign.tides_of_war(s)["points"]["yorkist"]
    tow = campaign.tides_of_war(s, {"charity": {"salisbury": 2}})
    assert tow["points"]["yorkist"] == base + 2
    assert s.lords["salisbury"].assets["provender"] == 0
