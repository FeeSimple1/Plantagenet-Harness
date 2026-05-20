"""Harness exception types.

`IllegalAction` carries a machine-readable ``code`` so consumers (and the
round-trip enumerator/handler sweep) can branch on the rejection reason
rather than parsing prose.
"""

from __future__ import annotations


class HarnessError(Exception):
    """Base class for all harness-raised errors."""


class IllegalAction(HarnessError):  # noqa: N818
    """Raised when a submitted action violates the rules.

    Parameters
    ----------
    code:
        Short stable identifier for the rejection (e.g.
        ``"not_friendly_locale"``). Stable across versions so tests and
        the LLM-play retry logic can depend on it.
    message:
        Human-readable explanation, ideally citing a rule section.
    """

    def __init__(self, code: str, message: str = "") -> None:
        self.code = code
        self.message = message or code
        super().__init__(f"{code}: {self.message}")


class DataError(HarnessError):
    """Raised when static reference data is malformed or inconsistent."""
