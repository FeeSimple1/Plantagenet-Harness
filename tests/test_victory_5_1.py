"""Campaign Victory 5.1: the side with no Lords on the map (incl. Exile boxes)
and no next-Turn Exile arrives loses; the OTHER side wins. (Regression: the
winner was previously reported reversed -- found in a Towton playthrough.)"""

from __future__ import annotations

from plantagenet import campaign
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _wipe_to_calendar(state, side):
    """Send every Lord of `side` to a non-Exile Calendar box that never arrives
    (Towton is box 1 only), removing all presence for 5.1."""
    for v in state.lords.values():
        if v.side == side:
            v.status = LordStatus.CALENDAR.value
            v.calendar_box = 2
            v.calendar_exile = False
            v.location = None


def test_5_1_awards_the_side_that_retains_lords():
    s = build_initial_state("towton", seed=1)
    _wipe_to_calendar(s, "yorkist")
    res = campaign._victory_check(s)
    assert res == {"result": "lancastrian", "rule": "5.1"}, res

    s2 = build_initial_state("towton", seed=1)
    _wipe_to_calendar(s2, "lancastrian")
    assert campaign._victory_check(s2) == {"result": "yorkist", "rule": "5.1"}


def test_5_1_draw_when_neither_side_has_presence():
    s = build_initial_state("towton", seed=1)
    _wipe_to_calendar(s, "yorkist")
    _wipe_to_calendar(s, "lancastrian")
    assert campaign._victory_check(s) == {"result": "draw", "rule": "5.1"}


def test_5_1_counts_an_exile_box_lord_as_presence():
    # A Lord sitting in an Exile box keeps a side present (5.1 "including none in
    # Exile boxes"), so 5.1 must NOT fire for that side.
    s = build_initial_state("towton", seed=1)
    _wipe_to_calendar(s, "yorkist")
    survivor = next(v for v in s.lords.values() if v.side == "yorkist")
    survivor.status = LordStatus.EXILE.value
    survivor.exile_box = "calais"
    survivor.calendar_box = None
    res = campaign._victory_check(s)
    # Yorkist still present via the Exile box -> no 5.1 elimination of Yorkist.
    assert res is None or res.get("result") != "lancastrian" or res.get("rule") != "5.1"
