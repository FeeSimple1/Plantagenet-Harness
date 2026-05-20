"""Static data must be internally consistent (BRIEF: Completeness).

The cross-reference checker is the Phase-0 analogue of the
enumerator/handler round-trip discipline: it catches transcription
divergence in the reference data before any logic depends on it.
"""

from __future__ import annotations

from plantagenet import data_integrity


def test_no_integrity_errors():
    report = data_integrity.check_all()
    assert report["errors"] == [], report["errors"]


def test_no_integrity_warnings():
    report = data_integrity.check_all()
    assert report["warnings"] == [], report["warnings"]


def test_expected_counts():
    counts = data_integrity.check_all()["counts"]
    # Lords and Vassals Reference: 14 Lancastrian + 14 Yorkist Lords.
    assert counts["lords"] == 28
    # 13 regular Vassals (one per Vassal Seat) + 6 Special Vassals.
    assert counts["vassals_regular"] == 13
    assert counts["vassals_special"] == 6
    # Map Reference: 54 Locales.
    assert counts["locales"] == 54
    # Six standalone scenarios + the Wars of the Roses grand scenario.
    assert counts["scenarios"] == 7
    assert counts["forces"] == 7
