"""Deterministic, seedable dice.

Every die the harness rolls comes from here. The RNG state is stored in
the game-state file so that a saved game replays bit-for-bit. The harness
rolls all dice; the consumer never does (per BRIEF: "Dice and Mechanical
Resolution").

Plantagenet uses ordinary six-sided dice. Implemented on Python's
``random.Random`` (Mersenne Twister), whose stream is stable across
CPython versions for a given seed.
"""

from __future__ import annotations

import random


class DiceRoller:
    """A seeded source of d6 rolls with serializable state."""

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._rng = random.Random(seed)

    @property
    def seed(self) -> int:
        return self._seed

    def d6(self) -> int:
        """Roll a single six-sided die (1-6)."""
        return self._rng.randint(1, 6)

    def roll(self, n: int) -> list[int]:
        """Roll ``n`` six-sided dice, returning each result in order."""
        if n < 0:
            raise ValueError("cannot roll a negative number of dice")
        return [self.d6() for _ in range(n)]

    # -- serialization: getstate/setstate round-trips the full MT state --
    def get_state(self) -> list:
        # Fully list-ify (the MT internal is a tuple) so a JSON round-trip
        # is an identity: json load yields lists, and so do we.
        version, internal, gauss = self._rng.getstate()
        return [version, list(internal), gauss]

    def set_state(self, state: list) -> None:
        # random.setstate expects a tuple whose middle element is a tuple.
        version, internal, gauss = state
        self._rng.setstate((version, tuple(internal), gauss))
