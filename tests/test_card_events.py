"""Wave E1: immediate Arts of War Event effects via the play_event action."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus, VassalStatus


def _muster_all(state, side):
    for ls in state.lords.values():
        if ls.side == side and ls.status != LordStatus.MUSTERED:
            ls.status = LordStatus.MUSTERED.value
            if ls.location is None:
                ls.location = "york"


def test_charles_the_bold_grants_coin_and_provender():
    s = build_initial_state("warwicks_rebellion")
    _muster_all(s, "yorkist")
    ylords = [lid for lid, v in s.lords.items()
              if v.side == "yorkist" and v.status == LordStatus.MUSTERED]
    before = {lid: s.lords[lid].assets.get("coin", 0) for lid in ylords}
    actions.apply_action(s, {"type": "play_event", "card": "Y23", "side": "yorkist"})
    for lid in ylords:
        assert s.lords[lid].assets["coin"] == before[lid] + 1
        assert s.lords[lid].assets.get("provender", 0) >= 1


def test_yorkist_north_influence_gain():
    s = build_initial_state("warwicks_rebellion")
    lid = next(lo for lo, v in s.lords.items() if v.side == "yorkist")
    s.lords[lid].status = LordStatus.MUSTERED.value
    s.lords[lid].location = "carlisle"          # a North Stronghold
    s.locales["carlisle"].favour = "yorkist"
    r = actions.apply_action(s, {"type": "play_event", "card": "Y27", "side": "yorkist"})
    assert r["influence"] >= 2                   # >=1 Lord + >=1 Stronghold in the North


def test_london_for_york_adds_second_favour_only_if_yorkist():
    s = build_initial_state("warwicks_rebellion")
    s.locales["london"].favour = "yorkist"
    actions.apply_action(s, {"type": "play_event", "card": "Y15", "side": "yorkist"})
    assert s.locales["london"].favour_extra == 1
    s.locales["london"].favour = "neutral"
    r = actions.apply_action(s, {"type": "play_event", "card": "Y15", "side": "yorkist"})
    assert r["second_favour"] is False


def test_sir_richard_leigh_clears_lancastrian_london():
    s = build_initial_state("warwicks_rebellion")
    s.locales["london"].favour = "lancastrian"
    actions.apply_action(s, {"type": "play_event", "card": "Y21", "side": "yorkist"})
    assert s.locales["london"].favour == "neutral"


def test_henry_released_five_influence_if_london_lancastrian():
    s = build_initial_state("warwicks_rebellion")
    s.locales["london"].favour = "lancastrian"
    r = actions.apply_action(s, {"type": "play_event", "card": "L26", "side": "lancastrian"})
    assert r["lancastrian_influence"] == 5


def test_she_wolf_shifts_yorkist_vassals_right():
    s = build_initial_state("warwicks_rebellion")
    # Muster a Vassal onto a Yorkist Lord.
    lid = next(lo for lo, v in s.lords.items() if v.side == "yorkist")
    s.lords[lid].status = LordStatus.MUSTERED.value
    vid = next(iter(s.vassals))
    s.vassals[vid].status = VassalStatus.MUSTERED.value
    s.vassals[vid].on_lord = lid
    s.vassals[vid].service_box = 3
    s.lords[lid].vassals = [vid]
    actions.apply_action(s, {"type": "play_event", "card": "Y17", "side": "yorkist"})
    assert s.vassals[vid].service_box == 4


def test_warwicks_propaganda_removes_favour():
    s = build_initial_state("warwicks_rebellion")
    locs = ["york", "coventry", "nottingham"]
    for loc in locs:
        s.locales[loc].favour = "yorkist"
    actions.apply_action(s, {"type": "play_event", "card": "L23", "side": "lancastrian",
                             "decisions": {"strongholds": {loc: "remove" for loc in locs}}})
    assert all(s.locales[loc].favour == "neutral" for loc in locs)


def test_dubious_clarence_influence_check_disband():
    s = build_initial_state("warwicks_rebellion")
    for lid in ("edward_iv", "clarence"):
        s.lords[lid].status = LordStatus.MUSTERED.value
        s.lords[lid].location = "london"
    r = actions.apply_action(s, {"type": "play_event", "card": "Y26", "side": "yorkist",
                                 "decisions": {"extra_spend": 3}})
    if r["success"]:
        assert s.lords["clarence"].status == LordStatus.CALENDAR


def test_play_event_rejects_wrong_side():
    s = build_initial_state("warwicks_rebellion")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_event", "card": "Y23", "side": "lancastrian"})
    assert e.value.code == "wrong_side"


def test_play_event_rejects_non_immediate():
    s = build_initial_state("warwicks_rebellion")
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_event", "card": "Y1", "side": "yorkist"})
    assert e.value.code == "not_immediate_event"
