"""Always-on board invariants beyond co-location (cross-harness advisory §3)."""

from __future__ import annotations

import json
import os

import pytest

from plantagenet import invariants
from plantagenet.influence import INFLUENCE_CAP
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _scenario_ids():
    out = []
    for f in sorted(os.listdir("src/plantagenet/data/scenarios")):
        if f.endswith(".json"):
            d = json.load(open(os.path.join("src/plantagenet/data/scenarios", f)))
            if d.get("id"):
                out.append(d["id"])
    return out


@pytest.mark.parametrize("sid", _scenario_ids())
def test_every_scenario_setup_satisfies_all_invariants(sid):
    assert invariants.board_invariant_violations(build_initial_state(sid)) == []


def test_influence_marker_out_of_bounds_is_flagged():
    s = build_initial_state("henry_vi")
    s.influence["track"].marker_at = INFLUENCE_CAP + 5
    assert any(v["kind"] == "influence_marker_oob"
               for v in invariants.influence_violations(s))


def test_mustered_lord_with_no_position_is_flagged():
    s = build_initial_state("henry_vi")
    lid = next(k for k, v in s.lords.items() if v.status == LordStatus.MUSTERED)
    s.lords[lid].location = None
    s.lords[lid].exile_box = None
    s.lords[lid].at_sea = None
    assert any(v["kind"] == "mustered_nowhere" and v["lord"] == lid
               for v in invariants.lord_status_violations(s))


def test_battle_only_mustered_lords_are_not_flagged():
    s = build_initial_state("bosworth")              # battle-only: Lords have no Locale
    assert invariants.lord_status_violations(s) == []


def test_card_in_two_zones_is_flagged():
    s = build_initial_state("henry_vi")
    side = "yorkist"
    c = s.decks[side]["draw"][0]
    s.decks[side]["discard"].append(c)               # same card now in two piles
    kinds = {v["kind"] for v in invariants.card_zone_violations(s)}
    assert "card_in_two_piles" in kinds
    # And a card both in a deck pile and on a mat.
    s2 = build_initial_state("henry_vi")
    c2 = s2.decks[side]["draw"][0]
    lord = next(k for k, v in s2.lords.items() if v.side == side)
    s2.lords[lord].capabilities.append(c2)
    assert any(v["kind"] == "card_in_deck_and_on_mat"
               for v in invariants.card_zone_violations(s2))
