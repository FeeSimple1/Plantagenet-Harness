"""Regression: special Command/Event/Capability actions and the King Richard
scenario action were implemented in actions.py + commands.py but never offered
by legal_moves.py, so a menu-driven player could not discover them. Each test
asserts the move is now enumerated AND that the offered move round-trips through
apply_action (round-trip discipline)."""

from __future__ import annotations

from plantagenet import actions, legal_moves, ratings
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster
from tests.test_command_enumeration import _activate, _into_activation


def _round_trip(state, move):
    probe = state.model_copy(deep=True)
    actions.apply_action(probe, move)            # must not raise IllegalAction


# ----------------------------------------------------------- Exile Pact (Y8)
def test_exile_pact_is_offered_and_accepted():
    s = _activate(_into_activation(), _yorkist_lord())
    lid = s.campaign.active_lord
    # Force a friendly Yorkist Exile box and the EXILE PACT event.
    box = next(iter(__import__("plantagenet.static_data",
                               fromlist=["load_exile_boxes"]).load_exile_boxes()))
    s.exile_alignment[box] = "yorkist"
    s.active_events.append({"card": "Y8", "title": "EXILE PACT",
                            "side": "yorkist", "scope": "campaign"})
    moves = legal_moves.legal_moves(s)
    offered = [m for m in moves if m["type"] == "exile_pact"]
    assert offered, "Exile Pact (Y8) not offered"
    assert any(m["box"] == box and m["by_lord"] == lid for m in offered)
    _round_trip(s, next(m for m in offered if m["box"] == box))


# ------------------------------------------------------------- Agitators (Y10)
def test_agitators_is_offered_and_accepted():
    s = _activate(_into_activation(), _yorkist_lord())
    lid = s.campaign.active_lord
    here = s.lords[lid].location
    target = next(n for n, _t in actions._adjacency().get(here, []))
    s.locales[target].favour = "lancastrian"        # enemy of the Yorkist mover
    s.locales[target].depletion = None
    _give_capability(s, lid, "AGITATORS")
    moves = legal_moves.legal_moves(s)
    offered = [m for m in moves if m["type"] == "agitators" and m["target"] == target]
    assert offered, "Agitators (Y10) not offered"
    _round_trip(s, offered[0])


# ------------------------------------------------------------- Merchants (L30)
def test_merchants_is_offered_and_accepted():
    s = _activate(_into_activation(), _lancastrian_lord())
    lid = s.campaign.active_lord
    here = s.lords[lid].location
    s.locales[here].depletion = "depleted"
    _give_capability(s, lid, "MERCHANTS")
    moves = legal_moves.legal_moves(s)
    offered = [m for m in moves if m["type"] == "merchants" and here in m["targets"]]
    assert offered, "Merchants (L30) not offered"
    _round_trip(s, offered[0])


# --------------------------------------------------------------- Heralds (L4)
def test_heralds_is_offered_and_accepted():
    s = _activate(_into_activation(), _lancastrian_lord_at_port())
    lid = s.campaign.active_lord
    # Ensure a Lord sits on the Calendar to advance.
    cal = next((cid for cid, v in s.lords.items()
                if v.status == LordStatus.CALENDAR and v.calendar_box is not None), None)
    if cal is None:
        cal = next(cid for cid, v in s.lords.items()
                   if v.side == "lancastrian" and cid != lid)
        s.lords[cal].status = LordStatus.CALENDAR
        s.lords[cal].location = None
        s.lords[cal].calendar_box = s.turn_box + 2
    assert cal is not None
    _give_capability(s, lid, "HERALDS")
    moves = legal_moves.legal_moves(s)
    offered = [m for m in moves if m["type"] == "heralds" and m["target"] == cal]
    assert offered, "Heralds (L4) not offered"
    _round_trip(s, offered[0])


# ----------------------------------------------------- King Richard (My Kingdom)
def test_crown_richard_is_offered_in_muster_and_accepted():
    s = build_initial_state("my_kingdom_for_a_horse")
    to_muster(s)
    # Advance to the Yorkist Muster segment.
    while s.active_side != "yorkist":
        actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    g = "gloucester_1" if "gloucester_1" in s.lords else "gloucester_2"
    s.lords[g].status = LordStatus.MUSTERED
    s.lords[g].location = "london"
    moves = legal_moves.legal_moves(s)
    offered = [m for m in moves if m["type"] == "crown_richard"]
    assert offered, "crown_richard (King Richard) not offered in Muster"
    _round_trip(s, offered[0])


def test_crown_richard_not_offered_to_lancastrian():
    s = build_initial_state("my_kingdom_for_a_horse")
    to_muster(s)
    if s.active_side != "lancastrian":
        actions.apply_action(s, {"type": "end_muster", "side": s.active_side})
    assert s.active_side == "lancastrian"
    g = "gloucester_1" if "gloucester_1" in s.lords else "gloucester_2"
    s.lords[g].status = LordStatus.MUSTERED
    s.lords[g].location = "london"
    moves = legal_moves.legal_moves(s)
    assert not [m for m in moves if m["type"] == "crown_richard"]


# --------------------------------------------------------------- test helpers
def _give_capability(state, lord_id, title):
    # Inject the capability directly onto the Lord's ratings if needed.
    if not ratings.has_capability(state, lord_id, title):
        state.lords[lord_id].capabilities = list(
            getattr(state.lords[lord_id], "capabilities", []))
        # Map the title back to a card id present in the deck.
        from plantagenet import static_data
        cards = static_data.load_cards()
        cid = next(c for c, v in cards.items()
                   if (v.get("capability") or {}).get("title", "").upper() == title)
        state.lords[lord_id].capabilities.append(cid)
    assert ratings.has_capability(state, lord_id, title)


def _yorkist_lord():
    s = _into_activation()
    return next(lid for lid, v in s.lords.items()
                if v.side == "yorkist" and v.status == "mustered" and v.location)


def _lancastrian_lord():
    s = _into_activation()
    return next(lid for lid, v in s.lords.items()
                if v.side == "lancastrian" and v.status == "mustered" and v.location)


def _lancastrian_lord_at_port():
    from plantagenet import static_data
    locales = static_data.load_locales()
    s = _into_activation()
    return next(lid for lid, v in s.lords.items()
                if v.side == "lancastrian" and v.status == "mustered"
                and v.location and locales.get(v.location, {}).get("port"))


# ------------------------------------ concede is a manual-adjudication action
def test_concede_is_not_enumerated_but_still_accepted():
    """6.1.1 Surrender has no modeled timing window, so legal_moves must NOT
    offer it (avoids misrepresenting its legal moment); the raw action is still
    accepted by apply_action when its conditions hold."""
    s = build_initial_state("wars_of_the_roses")
    # Drive the enumerator through a Levy Muster and assert concede never shows.
    to_muster(s)
    assert not [m for m in legal_moves.legal_moves(s) if m["type"] == "concede"]
    # The handler still accepts it (first War, Heir present).
    r = actions.apply_action(s, {"type": "concede", "side": "lancastrian"})
    assert r["winner"] == "yorkist"


# ------------------------ crown_richard clears the replaced Lord's mat (6.2)
def test_crown_richard_clears_gloucester_mat_no_invariant_break():
    from plantagenet import invariants, static_data
    s = build_initial_state("my_kingdom_for_a_horse")
    g = "gloucester_1" if "gloucester_1" in s.lords else "gloucester_2"
    s.lords[g].status = LordStatus.MUSTERED
    s.lords[g].location = "london"
    # Levy a Yorkist Capability onto Gloucester (removed from the draw deck).
    cards = static_data.load_cards()
    cid = next(c for c, v in cards.items()
               if v.get("side") == "yorkist" and v.get("capability"))
    for pile in ("draw", "discard", "held", "set_aside"):
        if cid in s.decks["yorkist"].get(pile, []):
            s.decks["yorkist"][pile].remove(cid)
    s.lords[g].capabilities = [cid]
    assert invariants.board_invariant_violations(s) == []
    actions.apply_action(s, {"type": "crown_richard", "side": "yorkist"})
    # Card transferred to Richard, none left on the REMOVED Gloucester mat.
    assert s.lords[g].capabilities == []
    assert cid in s.lords["richard_iii"].capabilities
    assert invariants.board_invariant_violations(s) == []


# ------------------- Merchants clears an Exhausted marker outright (L30) ------
def test_merchants_clears_exhausted_marker_outright():
    """L30: 'Removal of Exhausted leaves the Stronghold neither Exhausted nor
    Depleted' -- one removal fully clears the Stronghold (not Exhausted->Depleted)."""
    s = _activate(_into_activation(), _lancastrian_lord())
    lid = s.campaign.active_lord
    here = s.lords[lid].location
    s.locales[here].depletion = "exhausted"
    _give_capability(s, lid, "MERCHANTS")
    # Spend enough to make the Influence check certain, then apply.
    r = actions.apply_action(s, {"type": "merchants", "side": "lancastrian",
                                 "by_lord": lid, "targets": [here], "extra_spend": 3})
    if r["success"]:
        assert s.locales[here].depletion is None


# ------------------- Heralds offers only own-side Calendar Lords (L4) ---------
def test_heralds_does_not_offer_enemy_calendar_lord():
    s = _activate(_into_activation(), _lancastrian_lord_at_port())
    lid = s.campaign.active_lord
    _give_capability(s, lid, "HERALDS")
    # Force a Yorkist (enemy) Lord onto the Calendar.
    enemy = next(cid for cid, v in s.lords.items() if v.side == "yorkist")
    s.lords[enemy].status = LordStatus.CALENDAR
    s.lords[enemy].location = None
    s.lords[enemy].calendar_box = s.turn_box + 2
    moves = legal_moves.legal_moves(s)
    assert not [m for m in moves if m["type"] == "heralds" and m["target"] == enemy]


# ----------- Succession replace-in-place also clears the replaced mat (6.2) ---
def test_succession_replace_in_place_clears_old_mat():
    """The shared _apply_replace_in_place (used by becomes_highest_heir, e.g.
    March -> Edward IV in the grand scenario) must clear the replaced Lord's
    mat, not just crown_richard's path."""
    from plantagenet import invariants, static_data, succession
    s = build_initial_state("wars_of_the_roses")
    old, new = "march", "edward_iv"
    s.lords[old].status = LordStatus.MUSTERED
    s.lords[old].location = "york"
    cards = static_data.load_cards()
    cid = next(c for c, v in cards.items()
               if v.get("side") == "yorkist" and v.get("capability"))
    for pile in ("draw", "discard", "held", "set_aside"):
        if cid in s.decks["yorkist"].get(pile, []):
            s.decks["yorkist"][pile].remove(cid)
    s.lords[old].capabilities = [cid]
    assert invariants.board_invariant_violations(s) == []
    succession._apply_replace_in_place(s, "yorkist", old, new)
    assert s.lords[old].capabilities == []
    assert s.lords[old].status == LordStatus.REMOVED
    assert cid in s.lords[new].capabilities
    assert invariants.board_invariant_violations(s) == []
