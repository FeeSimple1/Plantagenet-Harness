"""Scenario loader fidelity (Scenario Reference)."""

from __future__ import annotations

import pytest

from plantagenet import static_data
from plantagenet.scenarios import build_initial_state
from plantagenet.state import Favour, LordStatus, VassalStatus

ALL = ["henry_vi", "towton", "somersets_return", "warwicks_rebellion",
       "my_kingdom_for_a_horse", "bosworth", "wars_of_the_roses"]


@pytest.mark.parametrize("sid", ALL)
def test_all_scenarios_build(sid):
    state = build_initial_state(sid, seed=1)
    assert state.scenario == sid
    assert state.lords  # at least some lords


def test_ia_placements():
    s = build_initial_state("henry_vi")
    mustered = {k for k, v in s.lords.items() if v.status == LordStatus.MUSTERED}
    calendar = {k for k, v in s.lords.items() if v.status == LordStatus.CALENDAR}
    assert mustered == {"henry_vi", "somerset_1", "york", "march"}
    assert calendar == {"northumberland_lancastrian", "salisbury",
                        "exeter_1", "warwick_yorkist", "buckingham", "rutland"}
    # Mustered Lords carry their static starting Forces/Assets.
    assert s.lords["henry_vi"].forces == static_data.load_lords()["henry_vi"]["forces"]
    # Silver-ring Somerset.
    assert s.lords["somerset_1"].ring == "silver"
    # Calendar boxes per the reference.
    assert s.lords["northumberland_lancastrian"].calendar_box == 2
    assert s.lords["buckingham"].calendar_box == 5


def test_ia_favour_and_influence():
    s = build_initial_state("henry_vi")
    assert s.locales["london"].favour == Favour.LANCASTRIAN
    assert s.locales["ely"].favour == Favour.YORKIST
    inf = s.influence["track"]
    assert inf.marker_at == 0 and inf.marker_side == "lancastrian"
    assert inf.victory_check == 40
    assert inf.stronghold_markers["fortress"].side == "yorkist"


def test_iii_exile_lords_and_available_richard():
    s = build_initial_state("my_kingdom_for_a_horse")
    exile = {k for k, v in s.lords.items() if v.status == LordStatus.EXILE}
    assert exile == {"henry_tudor", "jasper_tudor_2", "oxford"}
    assert all(s.lords[x].exile_box == "france" for x in exile)
    # Richard III is a Lord card but starts neither mustered nor placed.
    assert s.lords["richard_iii"].status == LordStatus.AVAILABLE


def test_towton_fauconberg_mustered_on_march():
    s = build_initial_state("towton")
    f = s.vassals["fauconberg"]
    assert f.status == VassalStatus.MUSTERED
    assert f.on_lord == "march"
    assert f.service_box == 4
    # Norfolk is excepted from the on-map Vassals (it is a Lord here).
    assert s.vassals["norfolk"].status == VassalStatus.OFF_MAP


def test_bosworth_is_battle_only_no_influence():
    s = build_initial_state("bosworth")
    assert s.phase == "battle"
    assert s.influence == {}
    assert all(v.status == LordStatus.MUSTERED for v in s.lords.values())


def test_grand_scenario_initializes_war_one():
    s = build_initial_state("wars_of_the_roses")
    assert s.grand_scenario["current_war"] == "war_i"
    assert s.grand_scenario["base_scenario"] == "henry_vi"
    # Setup matches the Ia base.
    assert s.lords["henry_vi"].status == LordStatus.MUSTERED


def test_exile_alignment_recorded():
    s = build_initial_state("henry_vi")
    assert s.exile_alignment["scotland"] == "lancastrian"
    assert s.exile_alignment["ireland"] == "yorkist"
