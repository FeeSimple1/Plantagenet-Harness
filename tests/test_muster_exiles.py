"""Muster Exiles (3.3.1): the active side may Muster Exile-marked Lords from the
Calendar into their designated Exile box for free during the Muster window."""

from __future__ import annotations

import pytest

from plantagenet import actions, legal_moves
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import LordStatus
from tests._helpers import to_muster


def _iiy_at_muster():
    s = build_initial_state("wars_of_the_roses")
    s.victory = {"result": "yorkist"}
    n = renew_war(s)                                     # IIY: Henry VI/Somerset(1) box9 Exile
    n.lords["henry_vi"].calendar_box = 1                 # bring into the current box
    n.lords["somerset_1"].calendar_box = 1
    to_muster(n)                                         # -> Muster step, Lancastrian (Rebel) first
    assert n.levy_step == "muster" and n.active_side == "lancastrian"
    return n


def test_muster_exiles_places_lord_in_designated_box_for_free():
    n = _iiy_at_muster()
    r = actions.apply_action(n, {"type": "muster_exiles", "side": "lancastrian",
                                 "lords": ["henry_vi"]})
    assert r["mustered"] == [{"lord": "henry_vi", "box": "scotland"}]
    hv = n.lords["henry_vi"]
    assert hv.status == LordStatus.MUSTERED and hv.exile_box == "scotland"
    assert not hv.calendar_exile and hv.calendar_box is None
    assert hv.forces                                     # mat set up (Forces from the card)
    # Free: no Lordship/Influence machinery -- a brought-in Exile may still act (3.3.1).
    assert not hv.mustered_this_segment


def test_muster_exiles_rejects_non_exile_or_future_box_lords():
    n = _iiy_at_muster()
    with pytest.raises(IllegalAction) as e:              # Mustered, not Calendar-Exile
        actions.apply_action(n, {"type": "muster_exiles", "side": "lancastrian",
                                 "lords": ["warwick_lancastrian"]})
    assert e.value.code == "not_exile_musterable"
    n.lords["somerset_1"].calendar_box = 9               # future box -> not yet ready
    n.turn_box = 1
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(n, {"type": "muster_exiles", "side": "lancastrian",
                                 "lords": ["somerset_1"]})
    assert e.value.code == "not_exile_musterable"


def test_muster_exiles_only_on_active_side_and_muster_step():
    n = _iiy_at_muster()
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(n, {"type": "muster_exiles", "side": "yorkist",
                                 "lords": ["henry_vi"]})
    assert e.value.code == "not_active_side"


def test_muster_exiles_is_enumerated_in_legal_moves():
    n = _iiy_at_muster()
    moves = legal_moves.legal_moves(n)
    assert {"type": "muster_exiles", "side": "lancastrian", "lords": ["henry_vi"]} in moves
    # And the enumerated move is accepted by apply_action (round-trip discipline).
    actions.apply_action(n, {"type": "muster_exiles", "side": "lancastrian",
                             "lords": ["henry_vi"]})
