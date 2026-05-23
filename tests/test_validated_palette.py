"""Validated agent-facing action palette (cross-harness advisory §2): probe each
enumerated move and drop/log any the handler rejects, without corrupting the RNG."""

from __future__ import annotations

from plantagenet import legal_moves
from plantagenet.scenarios import build_initial_state
from tests._helpers import to_muster


def test_palette_matches_enumerator_when_clean():
    s = build_initial_state("henry_vi")
    to_muster(s)
    v = legal_moves.validated_legal_moves(s)
    assert v["rejected"] == []
    assert v["moves"] == legal_moves.legal_moves(s)        # nothing dropped


def test_probing_does_not_corrupt_the_real_rng():
    s = build_initial_state("henry_vi")
    to_muster(s)
    before = s.rng_state
    legal_moves.validated_legal_moves(s)                   # probes deep copies
    assert s.rng_state == before                           # real dice untouched


def test_palette_drops_and_logs_an_over_enumerated_move(monkeypatch):
    s = build_initial_state("henry_vi")
    to_muster(s)
    real = legal_moves.legal_moves(s)
    # An end_muster for the NON-active side is rejected by the handler.
    bogus = {"type": "end_muster", "side": "lancastrian" if s.active_side == "yorkist"
             else "yorkist"}
    monkeypatch.setattr(legal_moves, "legal_moves", lambda _st: real + [bogus])
    v = legal_moves.validated_legal_moves(s)
    assert bogus not in v["moves"]                         # filtered out
    assert any(r["move"] == bogus and r["code"] == "not_active_side"
               for r in v["rejected"])                     # logged as a diagnostic
