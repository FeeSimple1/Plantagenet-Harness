"""Regression tests for the second audit batch (Fauconberg, L31, grand-scenario
capability membership, event-card discard, Bosworth, Exile Pact status, Feed
sharing, L25 disband, build_plan in-play)."""

from __future__ import annotations

import pytest

from plantagenet import actions, campaign, events, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


# 1. Fauconberg is on March's vassal list at Towton.
def test_fauconberg_on_march_mat():
    s = build_initial_state("towton", seed=1)
    assert s.vassals["fauconberg"].on_lord == "march"
    assert "fauconberg" in s.lords["march"].vassals


# 2. Robin's Rebellion (L31) favour validation.
def test_l31_rejects_placing_enemy_favour():
    s = build_initial_state("henry_vi", seed=1)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "play_event", "side": "lancastrian", "card": "L31",
                                 "decisions": {"favour": [{"locale": "scarborough",
                                                           "side": "yorkist"}]}})
    assert e.value.code == "bad_favour_side"
    assert s.locales["scarborough"].favour.value == "neutral"


def test_l31_allows_remove_enemy_and_place_own():
    s = build_initial_state("henry_vi", seed=1)
    from plantagenet.state import Favour
    s.locales["scarborough"].favour = Favour("yorkist")
    s.locales["carlisle"].favour = Favour.NEUTRAL
    actions.apply_action(s, {"type": "play_event", "side": "lancastrian", "card": "L31",
                             "decisions": {"favour": [
                                 {"locale": "scarborough", "side": "neutral"},
                                 {"locale": "carlisle", "side": "lancastrian"}]}})
    assert s.locales["scarborough"].favour.value == "neutral"   # Yorkist removed
    assert s.locales["carlisle"].favour.value == "lancastrian"    # own Favour placed


# 3. Grand scenario: a Lord cannot levy a Capability that isn't in this War's deck.
def test_grand_scenario_rejects_offdeck_capability():
    s = build_initial_state("wars_of_the_roses", seed=1)
    live = {c for pile in ("draw", "discard", "held", "set_aside")
            for c in s.decks.get("lancastrian", {}).get(pile, [])}
    ghost = next(c for c in ("L27", "L28", "L30") if c not in live)
    lid = next(cid for cid, v in s.lords.items()
               if v.side == "lancastrian" and v.status == "mustered")
    # offered set excludes the ghost...
    offered = {m["card"] for m in legal_moves.legal_moves(s)
               if m["type"] == "levy_capability"}
    assert ghost not in offered
    # ...and the handler rejects a raw attempt.
    s.campaign = None
    with pytest.raises(IllegalAction):
        actions.apply_action(s, {"type": "levy_capability", "side": "lancastrian",
                                 "by_lord": lid, "card": ghost})


# 4. A drawn This-Levy Event card is discarded (not lost) when the scope ends.
def test_this_levy_event_card_is_discarded_at_scope_end():
    s = build_initial_state("henry_vi", seed=1)
    # A card that lives only in active_events (drawn this-levy), in no pile.
    for pile in ("draw", "discard", "held", "set_aside"):
        if "L9" in s.decks["lancastrian"].get(pile, []):
            s.decks["lancastrian"][pile].remove("L9")
    s.active_events.append({"card": "L9", "side": "lancastrian", "scope": "this_levy"})
    events.expire_scope(s, "this_levy")
    assert "L9" in s.decks["lancastrian"]["discard"]
    assert not any(e.get("card") == "L9" for e in s.active_events)


# 5. Bosworth (battle-only) plays to completion through the action API.
def test_bosworth_resolves_through_api():
    s = build_initial_state("bosworth", seed=3)
    assert legal_moves.legal_moves(s) == [{"type": "resolve_battle"}]
    actions.apply_action(s, {"type": "resolve_battle"})
    assert s.phase == "over"
    assert (s.victory or {}).get("result") in ("yorkist", "lancastrian", None)
    assert legal_moves.legal_moves(s) == []


# 6. Exile Pact leaves the Lord Mustered in the box (actable), not stranded.
def test_exile_pact_lord_is_mustered_in_box():
    from tests.test_exile_pact_position import _yorkist_at_sea_with_pact
    s, lid = _yorkist_at_sea_with_pact()
    actions.apply_action(s, {"type": "exile_pact", "side": "yorkist",
                             "by_lord": lid, "box": "scotland"})
    lord = s.lords[lid]
    assert lord.status == LordStatus.MUSTERED and lord.exile_box == "scotland"
    assert actions.lord_location(lord) == ("exile", "scotland")    # a real, actable position


# 7. A Capability can't be Levied while that card's This-Levy Event is active.
def test_capability_blocked_while_its_event_active():
    s = build_initial_state("henry_vi", seed=1)
    # L9 has both an Event (Rising Wages) and a Capability (Quartermasters).
    s.active_events.append({"card": "L9", "side": "lancastrian", "scope": "this_levy"})
    assert "L9" in actions._capabilities_in_play(s, "lancastrian")


# 8. Feed pools co-located Provender (Sharing 1.5.3).
def test_feed_shares_co_located_provender():
    s = build_initial_state("henry_vi", seed=1)
    loc = s.lords["york"].location
    s.lords["march"].location = loc
    s.lords["march"].status = LordStatus.MUSTERED
    s.lords["york"].moved_fought = True
    s.lords["york"].forces = {"retinue": 1, "men_at_arms": 6}   # needs ~2 provender
    s.lords["york"].assets = {"provender": 0}
    s.lords["march"].assets = {"provender": 5}
    s.locales[loc].depletion = "exhausted"                       # no pillage fallback
    r = campaign._feed(s, "yorkist")
    assert "york" not in r["disbanded"]                          # fed from March's pool
    assert s.lords["march"].assets["provender"] < 5             # ally's Provender drawn down


# 9. Welsh Rebellion (L25): a Yorkist Lord stripped of all Troops Disbands.
def test_l25_disbands_zero_troop_lord():
    s = build_initial_state("henry_vi", seed=1)
    wales_lord = "york"
    import plantagenet.events as ev
    wales = ev._region_locales("wales")
    s.lords[wales_lord].location = wales[0]
    s.lords[wales_lord].status = LordStatus.MUSTERED
    s.lords[wales_lord].forces = {"men_at_arms": 2}             # only wooden troops
    res = actions.apply_action(s, {"type": "play_event", "side": "lancastrian", "card": "L25",
                                   "decisions": {}})
    assert wales_lord in res.get("disbanded", [])
    assert s.lords[wales_lord].status == LordStatus.CALENDAR


# 10. build_plan rejects a non-Mustered Lord.
def test_build_plan_rejects_non_mustered_lord():
    from tests.test_command_enumeration import _into_activation
    s = _into_activation()
    # _into_activation already built plans; rebuild a fresh plan step to test.
    s.campaign.step = "plan"
    s.campaign.plan_built = {"lancastrian": False, "yorkist": False}
    # Force a Yorkist Lord to a non-in-play status, then try to Plan it.
    off = next(cid for cid, v in s.lords.items() if v.side == "yorkist")
    s.lords[off].status = LordStatus.CALENDAR
    n = s.campaign.cards_required
    plan = [{"lord": off}] + [{"pass": True}] * (n - 1)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "build_plan", "side": "yorkist", "plan": plan})
    assert e.value.code == "plan_lord_not_in_play"
