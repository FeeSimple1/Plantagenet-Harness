"""Battle-card reaction timing (4.4.1/4.4.3): Death-check cards must be advertised
and consumed only inside their real window. Regressions for:
  1. WARDEN OF THE MARCHES (L16) offered/consumed outside the North.
  2. BLOODY THOU ART (Y33) blocking L16/L36 but still discarding them.
  3. PATRICK DE LA MOTE (Y37) offered/accepted without CULVERINS in the Battle.
  4. TALBOT TO THE RESCUE (L36) consumed before any Lancastrian routs."""

from __future__ import annotations

import pytest

from plantagenet import battle, reactions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _muster(s, lid, loc, caps=None):
    s.lords[lid].status = LordStatus.MUSTERED.value
    s.lords[lid].location = loc
    s.lords[lid].capabilities = list(caps or [])


def _held(av, effect):
    return any(o["effect"] == effect for o in av)


# ---------------- Bug 1: Warden only in the North ----------------
def test_warden_not_advertised_or_accepted_outside_the_north():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "london")
    _muster(s, "henry_vi", "london")
    s.decks["lancastrian"]["held"] = ["L16"]
    # Not advertised at a non-North Battle...
    av = reactions.available_battle_reactions(s, ["york"], ["henry_vi"], locale="london")
    assert not _held(av, "warden")
    # ...and the handler rejects it without discarding the card.
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "london", "york", "henry_vi", {"warden": True})
    assert e.value.code == "warden_not_north"
    assert "L16" in s.decks["lancastrian"]["held"]


def test_warden_is_advertised_in_the_north():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "newcastle")          # newcastle is in the North
    _muster(s, "henry_vi", "newcastle")
    s.decks["lancastrian"]["held"] = ["L16"]
    av = reactions.available_battle_reactions(s, ["york"], ["henry_vi"], locale="newcastle")
    assert _held(av, "warden")


# ---------------- Bug 2: Bloody Thou Art blocks without consuming ----------------
def test_bloody_thou_art_blocks_l16_l36_without_discarding_them():
    s = build_initial_state("my_kingdom_for_a_horse")
    rid = "richard_iii"
    foe = next(lo for lo, v in s.lords.items() if v.side == "lancastrian")
    _muster(s, rid, "newcastle", caps=["Y33"])     # Bloody Thou Art, in the North
    _muster(s, foe, "newcastle")
    s.decks["lancastrian"]["held"] = ["L16", "L36"]
    forces = {rid: battle._Force(s, rid), foe: battle._Force(s, foe)}
    forces[foe].lord_routed = True                 # Richard wins; Lancastrian routed
    res = battle._ending(s, "newcastle", forces, [rid], [foe], [], [],
                         warden=True, talbot=True, warden_cid="L16", talbot_cid="L36")
    # Death checks skipped -> the routed Lancastrian Dies, and neither card is spent.
    assert foe in res.get("deaths", [])
    assert "L16" in s.decks["lancastrian"]["held"]
    assert "L36" in s.decks["lancastrian"]["held"]


# ---------------- Bug 3: Patrick needs Culverins in the Battle ----------------
def test_patrick_not_advertised_or_accepted_without_culverins():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "cambridge")          # no Culverins capability
    _muster(s, "henry_vi", "cambridge")
    s.decks["yorkist"]["held"] = ["Y37"]
    av = reactions.available_battle_reactions(s, ["york"], ["henry_vi"], locale="cambridge")
    assert not _held(av, "patrick")
    with pytest.raises(IllegalAction) as e:
        battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"patrick": True})
    assert e.value.code == "no_culverins_for_patrick"
    assert "Y37" in s.decks["yorkist"]["held"]


def test_patrick_is_advertised_with_culverins_present():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "cambridge", caps=["Y1"])     # Y1 = Culverins and Falconets
    _muster(s, "henry_vi", "cambridge")
    s.decks["yorkist"]["held"] = ["Y37"]
    av = reactions.available_battle_reactions(s, ["york"], ["henry_vi"], locale="cambridge")
    assert _held(av, "patrick")


# ---------------- Bug 4: Talbot not spent if no Lancastrian routs ----------------
def test_talbot_not_consumed_when_no_lancastrian_routs():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "cambridge")
    foe = "henry_vi"
    _muster(s, foe, "cambridge")
    s.decks["lancastrian"]["held"] = ["L36"]
    forces = {"york": battle._Force(s, "york"), foe: battle._Force(s, foe)}
    forces["york"].lord_routed = True              # the Yorkist routs; no Lancastrian does
    res = battle._ending(s, "cambridge", forces, ["york"], [foe], [], [],
                         talbot=True, talbot_cid="L36")
    # Talbot's window (routed Lancastrian) never opens -> the card is not spent.
    assert "L36" in s.decks["lancastrian"]["held"]
    assert foe not in res.get("disbands", [])


# ---------------- Positive paths: consumed when the window opens ----------------
def test_warden_consumed_and_applied_when_window_opens():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "newcastle")          # North, no Bloody Thou Art
    foe = next(lo for lo, v in s.lords.items()
               if v.side == "lancastrian" and lo != "henry_vi")
    _muster(s, foe, "newcastle")
    s.decks["lancastrian"]["held"] = ["L16"]
    forces = {"york": battle._Force(s, "york"), foe: battle._Force(s, foe)}
    forces[foe].lord_routed = True
    battle._ending(s, "newcastle", forces, ["york"], [foe], [], [],
                   warden=True, warden_cid="L16")
    assert "L16" not in s.decks["lancastrian"]["held"]   # spent now that it applied
    assert "L16" in s.decks["lancastrian"]["discard"]


def test_talbot_consumed_and_applied_when_lancastrian_routs():
    s = build_initial_state("henry_vi")
    _muster(s, "york", "cambridge")
    foe = next(lo for lo, v in s.lords.items()
               if v.side == "lancastrian" and lo != "henry_vi")
    _muster(s, foe, "cambridge")
    s.decks["lancastrian"]["held"] = ["L36"]
    forces = {"york": battle._Force(s, "york"), foe: battle._Force(s, foe)}
    forces[foe].lord_routed = True
    res = battle._ending(s, "cambridge", forces, ["york"], [foe], [], [],
                         talbot=True, talbot_cid="L36")
    assert foe in res.get("disbands", [])
    assert "L36" not in s.decks["lancastrian"]["held"]   # spent


def test_talbot_not_consumed_when_only_routed_lancastrian_is_captured():
    """Capture of the King (Scenario Ia): Henry VI is captured rather than
    death-rolled, so Talbot's Death-check window never opens for him and the
    card is not spent."""
    s = build_initial_state("henry_vi")
    _muster(s, "york", "cambridge")
    _muster(s, "henry_vi", "cambridge")
    s.decks["lancastrian"]["held"] = ["L36"]
    forces = {"york": battle._Force(s, "york"), "henry_vi": battle._Force(s, "henry_vi")}
    forces["henry_vi"].lord_routed = True
    res = battle._ending(s, "cambridge", forces, ["york"], ["henry_vi"], [], [],
                         talbot=True, talbot_cid="L36")
    assert "henry_vi" in [c["lord"] for c in res.get("captured", [])]
    assert "L36" in s.decks["lancastrian"]["held"]          # window never opened


# ---------------- Wiring: legal_moves annotates contact marches ----------------
def test_legal_moves_annotates_contact_march_with_gated_reactions():
    """A March that would resolve a Battle carries the playable in-Battle
    reaction windows, gated by location/capability (Warden only in the North)."""
    from plantagenet import legal_moves as lm
    s = build_initial_state("henry_vi")
    _muster(s, "henry_vi", "newcastle")              # Lancastrian defender, North
    s.decks["lancastrian"]["held"] = ["L16"]
    north_move = [{"type": "march", "side": "yorkist", "by_lord": "york", "to": "newcastle"}]
    lm._attach_battle_reactions(s, "yorkist", north_move)
    assert "warden" in {o["effect"] for o in north_move[0].get("battle_reactions", [])}
    # The same card is NOT advertised for a Battle outside the North.
    _muster(s, "henry_vi", "london")
    south_move = [{"type": "march", "side": "yorkist", "by_lord": "york", "to": "london"}]
    lm._attach_battle_reactions(s, "yorkist", south_move)
    assert "warden" not in {o["effect"] for o in south_move[0].get("battle_reactions", [])}
    # A move not resolving a Battle (no enemy at the destination) is untouched.
    quiet = [{"type": "march", "side": "yorkist", "by_lord": "york", "to": "york"}]
    lm._attach_battle_reactions(s, "yorkist", quiet)
    assert "battle_reactions" not in quiet[0]
