"""Regressions from the bug-finding gauntlet (2026-06, decision-payload fuzz +
mass grand-scenario sweeps).

1. Malformed battle ``regroup`` decision must be rejected gracefully. The
   handler expects ``{"regroup": {"lord": <id>, "round": <n>}}`` (4.4.2); a
   wrong-shaped value (e.g. a bare Lord-id string, or a dict missing "lord")
   used to crash with a raw ``TypeError``/``KeyError`` instead of an
   ``IllegalAction``. An agent-facing harness must never crash on a bad payload.

2. Succession deck ADDs must honour the one-zone invariant. A while_king /
   count-threshold Succession trigger re-registers cards into the deck via
   ``_add_to_deck``; its ``_deck_has`` guard checked only deck piles, not Lords'
   mats, so a card currently deployed as a Capability on a mat (e.g. Y20 Yorkist
   Parade) was cloned into the draw pile -> card_in_deck_and_on_mat. Surfaced by
   a battle that changed the Yorkist Heir while Y20 sat on rutland's mat.
"""

from __future__ import annotations

import pytest

from plantagenet import battle, invariants, succession
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state


def _duel(seed=5):
    s = build_initial_state("henry_vi", seed=seed)
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "cambridge"
        s.lords[lid].capabilities = []
    return s


# -------------------------------------------------- 1. malformed regroup payload
@pytest.mark.parametrize("bad", [
    "york",            # bare Lord-id string (the natural "name the lord" mistake)
    {"round": 2},      # non-empty dict missing the required "lord" key
    {"lord": ""},      # empty lord id
])
def test_malformed_regroup_is_rejected_not_crash(bad):
    s = _duel()
    s.decks["yorkist"]["held"] = ["Y30"]                  # Regroup held (so we reach the parse)
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"regroup": bad})
    assert e.value.code == "bad_regroup"


def test_wellformed_regroup_still_works():
    s = _duel()
    s.decks["yorkist"]["held"] = ["Y30"]
    battle.resolve_battle(s, "cambridge", "york", "henry_vi",
                          {"regroup": {"lord": "york", "round": 2}})
    assert "Y30" not in s.decks["yorkist"]["held"]        # consumed -> not regressed


# -------------------------------------- 2. succession deck-add honours the mat
def test_deck_has_sees_mat_capabilities():
    """A card deployed on a Friendly Lord's mat counts as in play."""
    s = build_initial_state("wars_of_the_roses", seed=1)
    lid = next(i for i, v in s.lords.items() if v.side == "yorkist")
    for pile in ("draw", "discard", "held", "set_aside"):
        if "Y20" in s.decks["yorkist"].get(pile, []):
            s.decks["yorkist"][pile].remove("Y20")
    s.lords[lid].capabilities.append("Y20")
    assert succession._deck_has(s, "yorkist", "Y20") is True


def test_register_source_does_not_clone_a_mat_capability_into_the_deck():
    s = build_initial_state("wars_of_the_roses", seed=1)
    # Put Y20 solely on a Yorkist Lord's mat (strip every deck pile first).
    lid = next(i for i, v in s.lords.items() if v.side == "yorkist")
    for pile in ("draw", "discard", "held", "set_aside"):
        if "Y20" in s.decks["yorkist"].get(pile, []):
            s.decks["yorkist"][pile].remove("Y20")
    s.lords[lid].capabilities.append("Y20")
    assert invariants.card_zone_violations(s) == []

    # A Succession re-registering Y20 (while_king/count ADD) must NOT duplicate it.
    succession._register_source(s, "yorkist", "Y20", lid)
    assert "Y20" not in s.decks["yorkist"].get("draw", [])
    assert invariants.card_zone_violations(s) == []
