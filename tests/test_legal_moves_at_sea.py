"""Command enumeration for a Lord at Sea (4.6.1) -- closes a coverage gap.

Coverage-guided gap hunting found legal_moves._command_moves' "Lord at Sea"
branch (loc is None and lord.at_sea set) was never exercised by any test. A Lord
in transit at Sea may only Sail or Pass (4.6.1); this pins that restriction.
"""

from __future__ import annotations

from plantagenet import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _put_at_sea(state, lid, zone="irish_sea"):
    lord = state.lords[lid]
    lord.status = LordStatus.MUSTERED
    lord.location = None
    lord.exile_box = None
    lord.at_sea = zone
    lord.assets = {**lord.assets, "ship": 1}


def test_lord_at_sea_palette_is_only_sail_or_pass():
    s = build_initial_state("wars_of_the_roses", seed=1)
    lid = next(i for i, v in s.lords.items() if v.side == "yorkist")
    _put_at_sea(s, lid)

    moves = legal_moves._command_moves(s, "yorkist", lid)
    types = {m["type"] for m in moves}
    assert "pass" in types                       # a Lord at Sea may always Pass
    assert types <= {"pass", "sail"}             # and otherwise only Sail (4.6.1)
    assert all(m["by_lord"] == lid for m in moves)
