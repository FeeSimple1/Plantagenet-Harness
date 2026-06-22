"""Pay-Troops exact-afford boundary (3.2) -- closes a mutation survivor.

Mutation testing flagged `if pool >= total_need:` in pay._pay_troops (the
"can this co-located group afford its Troop Pay" check) as a survivor: no test
pinned the boundary where coin EXACTLY meets the need. The Stronghold is set
Exhausted so the shortfall path cannot Pillage to mask the difference -- under
the boundary mutant (`>` instead of `>=`) the exactly-funded Lord would be sent
to the shortfall path and Disbanded instead of paid.
"""

from __future__ import annotations

from plantagenet import pay
from plantagenet.scenarios import build_initial_state


def _isolated_state():
    s = build_initial_state("henry_vi", seed=1)
    for lord in s.lords.values():
        lord.forces = {}                       # other groups need 0 -> trivially paid
    return s


def test_pay_troops_with_exactly_enough_coin_pays():
    s = _isolated_state()
    y = s.lords["york"]
    y.status = "mustered"
    y.location = "london"
    y.forces = {"men_at_arms": 6}              # 6 Troops -> need 1 Coin (1 per 6, round up)
    y.assets = {**y.assets, "coin": 1}         # EXACTLY enough
    s.locales["london"].depletion = "exhausted"   # no Pillage fallback available
    assert pay._troop_pay_need(y) == 1

    res = pay._pay_troops(s, "yorkist", {})
    assert "loc:london" in res["paid_groups"]
    assert "york" not in res["unpaid_disbanded"]
    assert s.lords["york"].assets.get("coin", 0) == 0     # coin drained exactly
    assert s.lords["york"].status == "mustered"           # not disbanded


def test_pay_troops_one_coin_short_cannot_pay_when_no_pillage():
    s = _isolated_state()
    y = s.lords["york"]
    y.status = "mustered"
    y.location = "london"
    y.forces = {"men_at_arms": 6}              # need 1 Coin
    y.assets = {**y.assets, "coin": 0}         # one short
    s.locales["london"].depletion = "exhausted"   # cannot Pillage to cover it
    res = pay._pay_troops(s, "yorkist", {})
    assert "loc:london" not in res["paid_groups"]
    assert "york" in res["unpaid_disbanded"]
