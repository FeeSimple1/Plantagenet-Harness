"""Runtime board invariant: no two opposing Mustered Lords share a Locale
(Plantagenet has no Siege/Retreat -- co-location resolves via Approach, 4.3.5)."""

from __future__ import annotations

import json
import os

import pytest

from plantagenet import battle, invariants
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus

_SCN_DIR = "src/plantagenet/data/scenarios"


def _scenario_ids():
    out = []
    for f in sorted(os.listdir(_SCN_DIR)):
        if f.endswith(".json"):
            d = json.load(open(os.path.join(_SCN_DIR, f)))
            if d.get("id"):
                out.append(d["id"])
    return out


@pytest.mark.parametrize("sid", _scenario_ids())
def test_every_scenario_setup_is_co_location_clean(sid):
    s = build_initial_state(sid)
    assert invariants.co_location_violations(s) == []
    invariants.assert_board_invariants(s)               # does not raise


def test_battle_loser_leaves_the_locale():
    # York (Yorkist) vs Henry VI (Lancastrian) at cambridge; the Routed loser
    # Dies or Disbands -- either way it must leave, so no co-location remains.
    for seed in range(1, 8):
        s = build_initial_state("henry_vi", seed=seed)
        for lid in ("york", "henry_vi"):
            s.lords[lid].location = "cambridge"
            s.lords[lid].status = LordStatus.MUSTERED
            s.lords[lid].capabilities = []
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {})
        assert invariants.co_location_violations(s) == []


def test_deliberate_co_location_is_detected_and_raises():
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):                    # opposing, both Mustered
        s.lords[lid].location = "leicester"
        s.lords[lid].status = LordStatus.MUSTERED
    bad = invariants.co_location_violations(s)
    assert len(bad) == 1 and bad[0]["locale"] == "leicester"
    assert set(bad[0]["lords"]) == {"york", "henry_vi"}
    with pytest.raises(IllegalAction) as e:
        invariants.assert_board_invariants(s)
    assert e.value.code == "co_located_enemies"


def test_pending_approach_co_location_is_exempt():
    # While an Approach reaction is open, the Marching Lord is legally at the
    # dest alongside the defender (4.3.5 / Q-004) -- not a violation.
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "leicester"
        s.lords[lid].status = LordStatus.MUSTERED
    s.pending = [{"trigger": "on_approach", "ctx": {"dest": "leicester"}}]
    assert invariants.co_location_violations(s) == []
    invariants.assert_board_invariants(s)               # does not raise
