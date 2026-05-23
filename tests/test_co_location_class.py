"""Advisory #2: the illegal co-location bug class. Audit the placement door
(Door C) and assert no setup/transition leaves opposing Lords sharing a Locale.
(Doors A/B -- Retreat and Siege/Bypass markers -- do not exist in Plantagenet.)"""

from __future__ import annotations

import json
import os

import pytest

from plantagenet import events, invariants
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import LordState, LordStatus

_SCN_DIR = "src/plantagenet/data/scenarios"


def _scenario_ids():
    out = []
    for f in sorted(os.listdir(_SCN_DIR)):
        if f.endswith(".json"):
            d = json.load(open(os.path.join(_SCN_DIR, f)))
            if d.get("id"):
                out.append(d["id"])
    return out


# ---- Door C: Sun in Splendour (Y24) must not Muster onto an enemy Locale ----
def _edward_ready():
    s = build_initial_state("henry_vi")
    s.lords["edward_iv"] = LordState(lord_id="edward_iv", side="yorkist",
                                     status=LordStatus.CALENDAR, calendar_box=1)
    return s


def test_y24_rejects_friendly_locale_occupied_by_enemy_lord():
    s = _edward_ready()
    s.locales["leicester"].favour = "yorkist"            # Friendly by Favour ...
    s.lords["henry_vi"].location = "leicester"           # ... but an Enemy Lord is here
    s.lords["henry_vi"].status = LordStatus.MUSTERED
    with pytest.raises(IllegalAction) as e:
        events._hp_sun_in_splendour(s, "yorkist", {"target": "leicester"})
    assert e.value.code == "bad_target"
    assert s.lords["edward_iv"].status == LordStatus.CALENDAR   # not mutated on rejection
    assert invariants.co_location_violations(s) == []


def test_y24_places_at_enemy_free_friendly_locale_or_yorkist_exile_box():
    s = _edward_ready()
    s.locales["york"].favour = "yorkist"
    events._hp_sun_in_splendour(s, "yorkist", {"target": "york"})
    assert s.lords["edward_iv"].location == "york"
    assert invariants.co_location_violations(s) == []
    s2 = _edward_ready()
    box = next(b for b, sd in s2.exile_alignment.items() if sd == "yorkist")
    events._hp_sun_in_splendour(s2, "yorkist", {"target": box})
    assert s2.lords["edward_iv"].exile_box == box
    assert s2.lords["edward_iv"].location is None


# ---- The illegal state never appears at setup or across War transitions ----
@pytest.mark.parametrize("sid", _scenario_ids())
def test_every_scenario_setup_is_co_location_clean(sid):
    assert invariants.co_location_violations(build_initial_state(sid)) == []


@pytest.mark.parametrize("winner", ["yorkist", "lancastrian"])
def test_first_war_transition_is_co_location_clean(winner):
    for seed in range(1, 5):
        s = build_initial_state("wars_of_the_roses", seed=seed)
        s.victory = {"result": winner}
        n = renew_war(s)                                  # War I -> IIY / IIL
        assert invariants.co_location_violations(n) == []


def test_iiy_to_iiiy_transition_is_co_location_clean():
    for seed in range(1, 5):
        s = build_initial_state("wars_of_the_roses", seed=seed)
        s.grand_scenario["current_war"] = "war_iiy"
        s.turn_box = 3
        s.victory = {"result": "yorkist"}
        n = renew_war(s)                                  # IIY -> IIIY
        assert n.grand_scenario["current_war"] == "war_iiiy"
        assert invariants.co_location_violations(n) == []


@pytest.mark.xfail(strict=True, reason="KNOWN GAP: War IIIL setup is unimplemented "
                   "(E7) -- its JSON has prose Favour and a 'yorkist_lords_per_succession' "
                   "placeholder, so renew_war crashes building it. Surfaced (not swallowed) "
                   "per Advisory #2. Flip when IIIL gets a succession-driven setup like IIIY.")
def test_iil_to_iiil_transition_builds():
    s = build_initial_state("wars_of_the_roses")
    s.grand_scenario["current_war"] = "war_iil"
    s.turn_box = 3
    s.victory = {"result": "lancastrian"}
    renew_war(s)                                          # IIL -> IIIL (currently DataError)
