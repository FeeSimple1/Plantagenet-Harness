"""Regression: Exile Pact (Y8) left a Lord at Sea AND in an Exile box at once,
the invariant checker missed the dual location, and the menu re-offered the
identical no-op once the Lord was already in the box."""

from __future__ import annotations

import pytest

from plantagenet import actions, invariants, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.state import LordStatus
from tests.test_command_enumeration import _activate, _into_activation


def _yorkist_at_sea_with_pact():
    """An active Yorkist Lord at Sea, with EXILE PACT in effect and a Friendly
    (Yorkist) Exile box available."""
    s = _into_activation()
    lid = next(cid for cid, v in s.lords.items()
               if v.side == "yorkist" and v.status == "mustered" and v.location)
    _activate(s, lid)
    lord = s.lords[lid]
    lord.location = None
    lord.at_sea = "english_channel"        # Sailing "into a Sea"
    s.exile_alignment["scotland"] = "yorkist"
    s.active_events.append({"card": "Y8", "side": "yorkist"})   # EXILE PACT
    return s, lid


# ---------------- Bug 1: at_sea cleared on Exile Pact ----------------
def test_exile_pact_from_sea_clears_at_sea():
    s, lid = _yorkist_at_sea_with_pact()
    actions.apply_action(s, {"type": "exile_pact", "side": "yorkist",
                             "by_lord": lid, "box": "scotland"})
    lord = s.lords[lid]
    assert lord.status == LordStatus.EXILE
    assert lord.exile_box == "scotland"
    assert lord.at_sea is None            # no longer "in the English Channel"
    assert lord.location is None
    assert lord.calendar_box is None and lord.captured_by is None
    # The board is now in a legal configuration.
    assert invariants.board_invariant_violations(s) == []


# ---------------- Bug 2: invariant detects an impossible dual location -------
def test_invariant_flags_incompatible_position():
    s, lid = _yorkist_at_sea_with_pact()
    lord = s.lords[lid]
    # Hand-build the impossible state the old handler produced.
    lord.status = LordStatus.EXILE
    lord.exile_box = "scotland"
    lord.at_sea = "english_channel"       # still recorded at Sea -> impossible
    viol = [v for v in invariants.lord_status_violations(s)
            if v["kind"] == "incompatible_position" and v["lord"] == lid]
    assert viol, "the invariant checker should flag the dual location"
    assert set(viol[0]["fields"]) >= {"exile_box", "at_sea"}


def test_invariant_accepts_lord_mustered_in_exile_box():
    # A Lord legitimately Mustered in an Exile box (3.3.1) uses exile_box alone.
    s, lid = _yorkist_at_sea_with_pact()
    lord = s.lords[lid]
    lord.status = LordStatus.MUSTERED
    lord.at_sea = None
    lord.location = None
    lord.exile_box = "scotland"
    assert not [v for v in invariants.lord_status_violations(s)
                if v["lord"] == lid]


# ---------------- Bug 3: no redundant re-offer / no-op rejected -------------
def test_exile_pact_not_reoffered_for_current_box_and_rejected_as_noop():
    s, lid = _yorkist_at_sea_with_pact()
    actions.apply_action(s, {"type": "exile_pact", "side": "yorkist",
                             "by_lord": lid, "box": "scotland"})
    # The Lord is now Exiled in scotland; the menu must not re-offer that box.
    again = [m for m in legal_moves.legal_moves(s)
             if m["type"] == "exile_pact" and m["box"] == "scotland"]
    assert not again, "Exile Pact re-offered for the box the Lord already occupies"
    # And the raw no-op action is rejected.
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "exile_pact", "side": "yorkist",
                                 "by_lord": lid, "box": "scotland"})
    assert e.value.code == "already_in_box"


# ---------- Related dual-location bug found via the new invariant ----------
def test_disband_clears_at_sea_position():
    """A Lord Disbanded while at Sea must not keep its at_sea field -- a
    Disbanded Lord goes to the Calendar (the invariant caught this in
    self-play: at_sea + calendar_box at once)."""
    from plantagenet import campaign
    s, lid = _yorkist_at_sea_with_pact()
    lord = s.lords[lid]
    assert lord.at_sea == "english_channel"
    campaign._disband_lord(s, lord)
    assert lord.status == LordStatus.CALENDAR
    assert lord.calendar_box is not None
    assert lord.at_sea is None and lord.location is None and lord.captured_by is None
    assert invariants.board_invariant_violations(s) == []
