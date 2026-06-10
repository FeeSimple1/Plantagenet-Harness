"""Phase 5a-ii: The King's Name reaction + play_held_event windows +
Exile Pact / Be Sent For action variants + Aspielles peek."""

from __future__ import annotations

from plantagenet import actions
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def _muster(sid="warwicks_rebellion", seed=1):
    s = build_initial_state(sid, seed=seed)
    to_muster(s)
    return s


# ---------------- The King's Name (Y32) ----------------
def test_kings_name_cancels_a_lancastrian_parley():
    s = _muster()
    s.lords["gloucester_1"].status = LordStatus.MUSTERED.value
    s.lords["gloucester_1"].location = "london"
    s.active_events.append({"card": "Y32", "side": "yorkist"})
    s.active_events.append({"card": "L18", "side": "lancastrian"})  # auto-succeed the Parley
    s.locales["lincoln"].favour = "neutral"
    before = s.influence["track"].model_dump()
    r = actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                                 "by_lord": "clarence", "target": "lincoln"})
    assert r["type"] == "pending_reactions" and r["awaiting"]["card"] == "Y32"
    out = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y32"})
    assert out.get("cancelled") is True
    assert s.locales["lincoln"].favour == "neutral"          # favour reverted
    assert s.influence["track"].model_dump() != before        # Yorkist paid 1 Influence


def test_kings_name_declined_lets_parley_stand():
    s = _muster()
    s.lords["gloucester_1"].status = LordStatus.MUSTERED.value
    s.lords["gloucester_1"].location = "london"
    s.active_events.append({"card": "Y32", "side": "yorkist"})
    s.active_events.append({"card": "L18", "side": "lancastrian"})  # auto-succeed the Parley
    s.locales["lincoln"].favour = "neutral"
    actions.apply_action(s, {"type": "parley", "side": "lancastrian",
                             "by_lord": "clarence", "target": "lincoln"})
    out = actions.apply_action(s, {"type": "react", "side": "yorkist", "pass": True})
    assert out["type"] == "parley"
    assert s.locales["lincoln"].favour == "lancastrian"             # Parley stands


# ---------------- play_held_event ----------------
def _campaign(sid="henry_vi", seed=1):
    s = build_initial_state(sid, seed=seed)
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
    return s


def test_rebel_supply_depot_grants_provender_and_skips_feed():
    s = _campaign()
    lid = next(x for x, v in s.lords.items() if v.status == "mustered")
    s.lords[lid].location = "ipswich"           # a Port
    s.decks[s.lords[lid].side]["held"] = ["L28"]
    s.hold_window = {"action": "march", "side": s.lords[lid].side,
                     "lords": [lid], "dest": "ipswich"}   # just Marched to the Port
    prov = s.lords[lid].assets.get("provender", 0)
    actions.apply_action(s, {"type": "play_held_event", "card": "L28",
                                 "side": s.lords[lid].side, "decisions": {"lords": [lid]}})
    assert s.lords[lid].assets["provender"] == prov + 4
    assert s.lords[lid].ignore_next_feed is True
    assert "L28" not in s.decks[s.lords[lid].side]["held"]


def test_sun_in_splendour_musters_edward_iv():
    s = build_initial_state("warwicks_rebellion")
    s.lords["edward_iv"].status = LordStatus.CALENDAR.value
    s.lords["edward_iv"].calendar_box = 5
    s.locales["london"].favour = "yorkist"
    s.decks["yorkist"]["held"] = ["Y24"]
    actions.apply_action(s, {"type": "play_held_event", "card": "Y24",
                                 "side": "yorkist", "decisions": {"target": "london"}})
    assert s.lords["edward_iv"].status == LordStatus.MUSTERED
    assert s.lords["edward_iv"].location == "london"


def test_aspielles_peeks_enemy_held_cards():
    s = build_initial_state("henry_vi")
    s.decks["lancastrian"]["held"] = ["L1", "L19"]
    s.decks["yorkist"]["held"] = ["Y13"]
    r = actions.apply_action(s, {"type": "play_held_event", "card": "Y13", "side": "yorkist"})
    assert r["peek"]["enemy_side"] == "lancastrian"
    assert set(r["peek"]["enemy_held"]) == {"L1", "L19"}


# ---------------- action variants ----------------
def test_exile_pact_moves_lord_to_friendly_exile_box():
    s = _campaign()
    lid = next(x for x, v in s.lords.items() if v.side == "yorkist" and v.status == "mustered")
    s.active_side = "yorkist"
    s.campaign.active_lord = lid
    s.campaign.actions_remaining = 2
    box = next(iter(__import__("plantagenet.static_data", fromlist=["x"]).load_exile_boxes()))
    s.exile_alignment[box] = "yorkist"
    s.active_events.append({"card": "Y8", "side": "yorkist"})
    r = actions.apply_action(s, {"type": "exile_pact", "side": "yorkist",
                                 "by_lord": lid, "box": box})
    assert r["box"] == box
    # A Lord placed in an Exile box is Mustered there (Reference: Exile-box Lords
    # are Mustered), not a dead-end EXILE status.
    assert s.lords[lid].status == LordStatus.MUSTERED and s.lords[lid].exile_box == box
    assert s.lords[lid].location is None


def test_be_sent_for_musters_unready_lancastrian_exile():
    # L4 Be Sent For: Muster Exiles may take an Exile-marked Lancastrian from ANY
    # Calendar box, into its designated Exile box (3.3.1), not via Levy Lord.
    s = _muster("henry_vi")            # has Lancastrian Exile networks
    s.active_side = "lancastrian"
    box_of = {lid: box for box, lids in actions._allied_networks(s).items() for lid in lids}
    tgt = next(x for x, v in s.lords.items() if v.side == "lancastrian" and x in box_of)
    s.lords[tgt].status = LordStatus.CALENDAR
    s.lords[tgt].calendar_exile = True
    s.lords[tgt].calendar_box = s.turn_box + 9          # far out -> not normally Ready
    s.active_events.append({"card": "L4", "side": "lancastrian"})   # Be Sent For
    r = actions.apply_action(s, {"type": "muster_exiles", "side": "lancastrian",
                                 "lords": [tgt]})
    assert r["type"] == "muster_exiles"
    assert s.lords[tgt].status == LordStatus.MUSTERED
    assert s.lords[tgt].exile_box == box_of[tgt]
