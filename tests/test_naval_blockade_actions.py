"""Naval Blockade (Y15) gates Lancastrian Tax / Parley / Supply that use a Port
on the blockaded Sea -- not just Sail (D-006 residue (b))."""

from __future__ import annotations

from plantagenet import actions
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster


def _camp(seed=1, warwick_at="harlech"):
    """Campaign with a Lancastrian Lord at bristol (Irish Sea Port, Friendly,
    with Ships) and a Yorkist Warwick holding Naval Blockade (Y15) at an Irish
    Sea Port."""
    s = build_initial_state("henry_vi", seed=seed)
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

    lanc = lc[0]
    s.active_side = "lancastrian"
    s.campaign.active_lord = lanc
    s.campaign.actions_remaining = 2
    lord = s.lords[lanc]
    lord.location = "bristol"
    s.locales["bristol"].favour = "lancastrian"
    lord.assets["ship"] = 5
    lord.assets["cart"] = 5
    lord.forces = {"retinue": 1}
    wk = yk[0]
    s.lords[wk].location = warwick_at
    s.locales[warwick_at].favour = "yorkist"
    s.lords[wk].capabilities = ["Y15"]
    return s, lanc, wk


# ---------------------------------------------------------------- Parley
def test_parley_over_sea_pauses_for_blockade():
    s, lanc, _ = _camp()
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": lanc, "target": "pembroke"})
    assert r["type"] == "pending_reactions"
    assert r["awaiting"]["card"] == "Y15" and r["awaiting"]["side"] == "yorkist"
    assert s.pending[0]["resume_key"] == "commands:parley_finish"


def test_parley_adjacent_overland_does_not_pause():
    # gloucester is adjacent to bristol by land -> no Port/Sea used -> no Blockade.
    s, lanc, _ = _camp()
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": lanc, "target": "gloucester"})
    assert r["type"] == "parley"            # resolved synchronously, no reaction window


def test_parley_blockade_roll_cancels_or_proceeds():
    saw_cancel = saw_proceed = False
    for seed in range(1, 25):
        s, lanc, _ = _camp(seed=seed)
        before = s.campaign.actions_remaining
        actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": lanc, "target": "pembroke"})
        assert s.campaign.actions_remaining == before - 1   # Command cost spent regardless
        r = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y15"})
        roll = r["reactions"][0]["roll"]
        if roll > 2:
            saw_cancel = True
            assert r.get("cancelled") is True
            assert s.locales["pembroke"].favour == "neutral"   # no Favour shift
        else:
            saw_proceed = True
            assert "cancelled" not in r
        if saw_cancel and saw_proceed:
            break
    assert saw_cancel and saw_proceed


# ---------------------------------------------------------------- Supply
def test_ship_supply_over_sea_pauses_and_cancel_gives_no_provender():
    for seed in range(1, 25):
        s, lanc, _ = _camp(seed=seed)
        prov0 = s.lords[lanc].assets.get("provender", 0)
        r = actions.apply_action(s, {"type": "supply", "side": "lancastrian",
                                     "by_lord": lanc, "source": "pembroke",
                                     "use_ships": True})
        assert r["type"] == "pending_reactions"
        r2 = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y15"})
        if r2["reactions"][0]["roll"] > 2:
            assert r2.get("cancelled") is True
            assert s.lords[lanc].assets.get("provender", 0) == prov0   # no Provender
            return
    raise AssertionError("no blockading seed found")


# ---------------------------------------------------------------- Tax
def test_tax_route_over_sea_pauses_for_blockade():
    # Warwick at pembroke blockades the Irish Sea; Tax of harlech (special) must
    # sea-hop bristol->harlech, so it uses a Port on the blockaded Sea.
    s, lanc, _ = _camp(warwick_at="pembroke")
    r = actions.apply_action(s, {"type": "tax", "side": "lancastrian",
                                 "by_lord": lanc, "target": "harlech"})
    assert r["type"] == "pending_reactions"
    assert s.pending[0]["resume_key"] == "commands:tax_finish"


def test_no_blockade_when_warwick_off_the_sea():
    # Warwick on the English Channel (dover) does not gate an Irish Sea Parley.
    s, lanc, _ = _camp(warwick_at="dover")
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": lanc, "target": "pembroke"})
    assert r["type"] == "parley"
