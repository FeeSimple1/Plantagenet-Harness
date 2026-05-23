"""Phase 5a: the reaction protocol (Q-004), proven on Naval Blockade gating a
Lancastrian Sail -- pause/resolve loop, decline, cancel, and serializability."""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState, LordStatus
from tests._helpers import to_muster


def _setup(seed=1):
    """A campaign with a Lancastrian Lord ready to Sail Irish-Sea ports, and a
    Yorkist Warwick holding Naval Blockade (Y15) at a Port on that Sea."""
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
    lord.location = "bristol"           # Irish Sea Port
    s.locales["bristol"].favour = "lancastrian"
    lord.assets["ship"] = 5
    lord.forces = {"retinue": 1}
    # Yorkist Warwick with Naval Blockade at Harlech (Irish Sea).
    wk = yk[0]
    s.lords[wk].location = "harlech"
    s.locales["harlech"].favour = "yorkist"
    s.lords[wk].capabilities = ["Y15"]
    return s, lanc, wk


def test_sail_pauses_for_naval_blockade():
    s, lanc, _wk = _setup()
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lanc, "to": "pembroke"})
    assert r["type"] == "pending_reactions"
    assert r["awaiting"]["card"] == "Y15" and r["awaiting"]["side"] == "yorkist"
    assert s.pending                                  # interaction recorded on state
    # While pending, ordinary actions are refused.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "pass", "side": "lancastrian"})
    assert e.value.code == "reaction_pending"


def test_command_cost_is_spent_before_the_blockade_roll():
    s, lanc, _wk = _setup()
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lanc, "to": "pembroke"})
    assert s.campaign.actions_remaining == 0          # whole Command card spent regardless


def test_blockade_roll_decides_cancel_or_proceed():
    # Sweep seeds to observe both a blocking (3-6) and a non-blocking (1-2) roll.
    saw_block = saw_pass = False
    for seed in range(1, 40):
        s, lanc, _wk = _setup(seed=seed)
        actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lanc, "to": "pembroke"})
        r = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y15"})
        roll = r["reactions"][0]["roll"]
        if roll > 2:
            assert r.get("cancelled") is True         # blockaded -> Sail cancelled
            assert s.lords[lanc].location == "bristol"
            saw_block = True
        else:
            assert r["to"] == "pembroke"              # 1-2 -> Sail proceeds
            assert s.lords[lanc].location == "pembroke"
            saw_pass = True
        assert not s.pending                          # interaction cleared
    assert saw_block and saw_pass


def test_decline_lets_the_action_proceed():
    s, lanc, _wk = _setup()
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lanc, "to": "pembroke"})
    r = actions.apply_action(s, {"type": "react", "side": "yorkist", "pass": True})
    assert r["to"] == "pembroke"
    assert s.lords[lanc].location == "pembroke"


def test_paused_state_round_trips_through_serialization():
    s, lanc, _wk = _setup()
    actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                             "by_lord": lanc, "to": "pembroke"})
    blob = s.model_dump_json()
    s2 = GameState.model_validate_json(blob)          # save + reload mid-reaction
    assert s2.pending and s2.pending[0]["resume_key"] == "commands:sail_finish"
    r = actions.apply_action(s2, {"type": "react", "side": "yorkist", "pass": True})
    assert r["to"] == "pembroke"
    assert s2.lords[lanc].location == "pembroke"
    assert not s2.pending


def test_no_blockade_when_warwick_off_the_sea():
    s, lanc, wk = _setup()
    s.lords[wk].location = "ipswich"                  # North Sea, not Irish Sea
    s.locales["ipswich"].favour = "yorkist"
    r = actions.apply_action(s, {"type": "sail", "side": "lancastrian",
                                 "by_lord": lanc, "to": "pembroke"})
    assert r["type"] == "sail" and r["to"] == "pembroke"   # no reaction window


def _approach_setup(seed=1, henry_holds_kings_parley=True):
    """Yorkist 'march' (York) into Lincoln where Henry VI defends; Henry VI may
    hold King's Parley. Returns (state, attacker_id, defender_id)."""
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

    atk, dfn = "york", "henry_vi"
    s.active_side = "yorkist"
    s.campaign.active_lord = atk
    s.campaign.actions_remaining = 2
    s.lords[atk].location = "york"            # York locale, Highway to Lincoln
    s.lords[atk].forces = {"retinue": 1, "men_at_arms": 2}
    s.lords[dfn].status = LordStatus.MUSTERED.value
    s.lords[dfn].location = "lincoln"
    s.lords[dfn].forces = {"retinue": 1, "militia": 2}
    s.lords[dfn].capabilities = ["L15"] if henry_holds_kings_parley else []
    return s, atk, dfn


def test_kings_parley_cancels_approach_and_rewinds():
    s, atk, dfn = _approach_setup()
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": atk, "to": "lincoln"})
    assert r["type"] == "pending_reactions"
    assert r["awaiting"]["card"] == "L15" and r["awaiting"]["side"] == "lancastrian"
    out = actions.apply_action(s, {"type": "react", "side": "lancastrian", "play": "L15"})
    assert out["approach"] is None and out["approach_cancelled"] == "kings_parley"
    assert s.lords[atk].location == "york"          # rewound to origin
    assert s.lords[atk].moved_fought is False
    assert "L15" not in s.lords[dfn].capabilities    # King's Parley discarded
    assert s.campaign.actions_remaining == 0         # Command card ended


def test_kings_parley_forecloses_blocked_ford():
    s, atk, dfn = _approach_setup()
    s.decks["yorkist"]["held"] = ["Y11"]             # Yorkist holds Blocked Ford
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": atk, "to": "lincoln"})
    # King's Parley is offered first (priority 10).
    assert r["awaiting"]["card"] == "L15"
    out = actions.apply_action(s, {"type": "react", "side": "lancastrian", "play": "L15"})
    # Cancel forecloses the downstream Blocked Ford offer entirely.
    assert out["approach"] is None
    assert "Y11" in s.decks["yorkist"]["held"]       # never consumed
    assert len(out["reactions"]) == 1


def test_blocked_ford_forces_battle_when_kings_parley_declined():
    s, atk, dfn = _approach_setup()
    s.decks["yorkist"]["held"] = ["Y11"]
    actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": atk, "to": "lincoln"})
    actions.apply_action(s, {"type": "react", "side": "lancastrian", "pass": True})  # decline L15
    out = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y11"})
    assert out["approach"] is not None               # Battle resolved (no Exile)
    assert "Y11" not in s.decks["yorkist"]["held"]   # Blocked Ford consumed


def test_no_approach_window_without_reactors():
    s, atk, dfn = _approach_setup(henry_holds_kings_parley=False)
    r = actions.apply_action(s, {"type": "march", "side": "yorkist",
                                 "by_lord": atk, "to": "lincoln"})
    assert r["type"] == "march" and r["approach"] is not None   # resolves immediately


def test_battle_reaction_catalog_lists_live_windows():
    from plantagenet import reactions
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s.lords[lid].status = LordStatus.MUSTERED.value
        s.lords[lid].location = "cambridge"
    s.lords["york"].capabilities = ["Y1"]                 # Culverins (capability)
    s.decks["lancastrian"]["held"] = ["L1", "L19"]        # Leeward + a non-battle Event
    s.decks["yorkist"]["held"] = ["Y19"]                  # Caltrops
    av = reactions.available_battle_reactions(s, ["york"], ["henry_vi"])
    effects = {(o["side"], o["effect"]) for o in av}
    assert ("lancastrian", "leeward") in effects
    assert ("yorkist", "culverins") in effects
    assert ("yorkist", "caltrops") in effects
    assert all(o["effect"] != "henrys_proclamation" for o in av)   # non-battle excluded
    # ordered by window then priority
    assert av == sorted(av, key=lambda o: (o["window"], o["priority"]))


def test_battle_catalog_covers_implemented_battle_cards():
    """The registry catalog is the single source of truth: every battle-card
    effect resolve_battle knows about is declared in BATTLE_REACTIONS / caps."""
    from plantagenet import battle, reactions
    declared = {m["effect"] for m in reactions.BATTLE_REACTIONS.values()}
    declared |= {m["effect"] for m in reactions._BATTLE_CAPS.values()}
    implemented = {
        battle.LEEWARD: "leeward", battle.CALTROPS: "caltrops", battle.RAVINE: "ravine",
        battle.SUSPICION: "suspicion", battle.REGROUP: "regroup",
        battle.ESCAPE_SHIP: "escape_ship", battle.FLANK_ATTACK: "flank_attack",
        battle.WARDEN: "warden", battle.TALBOT: "talbot", battle.PATRICK: "patrick",
        battle.SWIFT_MANEUVER: "swift_maneuver", battle.CULVERINS: "culverins",
    }
    missing = set(implemented.values()) - declared
    assert not missing, f"battle effects missing from the reaction catalog: {missing}"
