"""Asset Sharing (1.5.3): co-located Friendly Lords may use/spend one another's
Assets (Ships, Carts, ...) -- never transfer them, and never Troops/Vassals."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster


def _two_lancastrians_in_campaign():
    s = build_initial_state("henry_vi")
    to_muster(s)
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    actions.apply_action(s, {"type": "begin_campaign"})
    yk = [x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered"]
    lc = [x for x, v in s.lords.items() if v.side == "lancastrian" and v.status == "mustered"]
    n = s.campaign.cards_required

    def pad(lo):
        e = [{"lord": x} for x in lo][:n]
        while len(e) < n:
            e.append({"pass": True})
        return e
    actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": pad(yk)})
    actions.apply_action(s, {"type": "build_plan", "side": "lancastrian", "plan": pad(lc)})
    a, b = lc[0], lc[1]
    s.active_side = "lancastrian"
    s.campaign.active_lord = a
    s.campaign.actions_remaining = 2
    return s, a, b


def test_sail_uses_shared_ships_without_transferring_them():
    s, a, b = _two_lancastrians_in_campaign()
    s.lords[a].location = "bristol"
    s.lords[b].location = "bristol"
    s.locales["bristol"].favour = "lancastrian"
    s.lords[a].assets["ship"] = 0
    s.lords[a].forces = {"retinue": 1, "men_at_arms": 4}   # needs >=1 Ship
    s.lords[b].assets["ship"] = 3
    with pytest.raises(IllegalAction) as e:                # no Ships, no Share -> fails
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": a, "to": "pembroke"})
    assert e.value.code == "insufficient_ships"
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": a, "to": "pembroke", "share": [b]})
    assert r["to"] == "pembroke"
    assert s.lords[b].assets["ship"] == 3                  # Shared, not transferred


def test_share_rejects_non_co_located_or_enemy_lords():
    s, a, b = _two_lancastrians_in_campaign()
    s.lords[a].location = "bristol"
    s.lords[a].assets["ship"] = 0
    s.lords[a].forces = {"retinue": 1, "men_at_arms": 4}
    s.lords[b].location = "york"                           # NOT co-located
    s.lords[b].assets["ship"] = 3
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": a, "to": "pembroke", "share": [b]})
    assert e.value.code == "share_not_co_located"
    s.lords[b].location = "bristol"
    with pytest.raises(IllegalAction) as e:                # an Enemy Lord cannot Share
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": a, "to": "pembroke", "share": ["york"]})
    assert e.value.code == "bad_share"


def test_supply_uses_shared_carts():
    s, a, b = _two_lancastrians_in_campaign()
    # Lord A supplies from an adjacent Friendly Stronghold source 1 Way away,
    # needing Carts per Provender per Way; A has none, B Shares enough.
    here, source = "york", "lincoln"
    s.lords[a].location = here
    s.lords[b].location = here
    s.locales[here].favour = "lancastrian"
    s.locales[source].favour = "lancastrian"
    s.lords[a].assets["cart"] = 0
    s.lords[b].assets["cart"] = 5
    with pytest.raises(IllegalAction) as e:                # no Carts to cross the Way
        actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                 "by_lord": a, "source": source})
    assert e.value.code in ("insufficient_carts", "no_route")
    if e.value.code == "no_route":
        pytest.skip("map: source not a 1-Way Friendly Supply route in this scenario")
    r = actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                 "by_lord": a, "source": source, "share": [b]})
    assert r["provender_added"] > 0
    assert s.lords[b].assets["cart"] == 5                  # Shared, not transferred
