"""Seeded dice determinism and serialization (BRIEF: Determinism)."""

from __future__ import annotations

from plantagenet.rng import DiceRoller


def test_same_seed_same_sequence():
    a = DiceRoller(42)
    b = DiceRoller(42)
    assert a.roll(20) == b.roll(20)


def test_d6_in_range():
    r = DiceRoller(1)
    assert all(1 <= r.d6() <= 6 for _ in range(200))


def test_state_round_trip_reproduces_stream():
    r = DiceRoller(7)
    r.roll(5)
    saved = r.get_state()
    expected = r.roll(10)
    restored = DiceRoller(7)
    restored.set_state(saved)
    assert restored.roll(10) == expected
