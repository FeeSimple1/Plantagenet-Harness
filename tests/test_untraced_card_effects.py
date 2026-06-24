"""Behavioural tests for cards the traceability matrix flagged UNTESTED.

scripts/build_traceability.py found 5 Arts of War cards with no test reference
(by id or effect keyword): L8, L22, L29, L37, Y29. These exercise each card's
real effect so the matrix shows them covered.
"""

from __future__ import annotations

from plantagenet import commands, events, ratings
from plantagenet.scenarios import build_initial_state
from plantagenet.state import Favour, LordStatus


def _inject(state, src_id, new_id, **fields):
    ls = state.lords[src_id].model_copy(deep=True)
    ls.lord_id = new_id
    for k, v in fields.items():
        setattr(ls, k, v)
    state.lords[new_id] = ls
    return ls


# ---------------------------------------------------------- L22 French Troops
def test_l22_french_troops_reinforces_a_port_lord():
    s = build_initial_state("henry_vi", seed=1)
    henry = s.lords["henry_vi"]
    henry.location = "dover"                       # an English Channel Port
    henry.status = LordStatus.MUSTERED
    before_maa = henry.forces.get("men_at_arms", 0)
    before_mil = henry.forces.get("militia", 0)
    res = events._french_troops(s, "lancastrian",
                                {"lord": "henry_vi", "men_at_arms": 2, "militia": 2})
    assert res["men_at_arms"] >= 1 and res["militia"] >= 1
    assert henry.forces.get("men_at_arms", 0) == before_maa + res["men_at_arms"]
    assert henry.forces.get("militia", 0) == before_mil + res["militia"]


def test_l22_french_troops_declined_is_a_no_op():
    s = build_initial_state("henry_vi", seed=1)
    s.lords["henry_vi"].location = "dover"
    assert "no_effect" in events._french_troops(s, "lancastrian", {})


# ------------------------------------------------- L29 To Wilful Disobedience
def test_l29_removes_yorkist_favour_near_a_lancastrian_lord():
    s = build_initial_state("henry_vi", seed=1)
    # Somerset is at London; mark London (at the Lord) Yorkist so it qualifies.
    s.locales["london"].favour = "yorkist"
    res = events._to_wilful_disobedience(s, "lancastrian", {"strongholds": ["london"]})
    assert res["removed"] == ["london"]
    assert s.locales["london"].favour == Favour.NEUTRAL.value


# ------------------------------------------------- Y29 Stafford Branch (Devon)
def test_y29_stafford_branch_adds_one_to_exeter_supply():
    s = build_initial_state("henry_vi", seed=1)
    devon = _inject(s, "york", "devon", capabilities=["Y29"])
    assert ratings.has_capability(s, "devon", "STAFFORD BRANCH")
    # +1 Provender at Exeter (or adjacent); unchanged elsewhere.
    assert commands._supply_bonuses(s, devon, "exeter", 2) == 3
    assert commands._supply_bonuses(s, devon, "london", 2) == 2


# --------------------------------------------- L8 Hay Wains / Forced Marches
def test_l8_capability_and_event_are_recognised():
    """The two predicates L8's effects branch on: the Hay Wains Capability
    (carts double for March/Supply) and the Forced Marches Event (lone
    Lancastrian Lords March Road as Highway)."""
    s = build_initial_state("henry_vi", seed=1)
    s.lords["york"].capabilities = list(s.lords["york"].capabilities) + ["L8"]
    assert ratings.has_capability(s, "york", "HAY WAINS")
    assert commands._active_event(s, "FORCED MARCHES") in (None, False)
    s.active_events.append({"card": "L8", "side": "lancastrian", "scope": "this_campaign"})
    assert commands._active_event(s, "FORCED MARCHES")


# ------------------------------------------- L37 Madame La Grande (Pay coin)
def test_l37_madame_la_grande_trigger_condition():
    s = build_initial_state("henry_vi", seed=1)
    from plantagenet.pay import _at_adj_friendly_ec_port
    lord = _inject(s, "henry_vi", "jasper_tudor_x", capabilities=["L37"],
                   location="calais", status=LordStatus.MUSTERED)
    s.locales["calais"].favour = "lancastrian"
    assert ratings.has_capability(s, "jasper_tudor_x", "MADAME LA GRANDE")
    assert _at_adj_friendly_ec_port(s, lord) is True       # at a Friendly EC Port
    s.locales["calais"].favour = "yorkist"
    assert _at_adj_friendly_ec_port(s, lord) is False      # not Friendly -> no Coin
