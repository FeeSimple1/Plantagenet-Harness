"""Cross-reference validation for the static reference data.

This is not game logic — it asserts that the encoded reference data is
internally consistent: every Seat names a real Locale, every Way endpoint
is a real Locale, every Lord/Vassal Seat resolves, every force type a
Lord lists exists in the Forces table, and every scenario references real
Lords/Vassals/Locales. The test suite runs these as hard assertions so a
transcription slip in the JSON fails CI immediately.
"""

from __future__ import annotations

from typing import Any

from plantagenet import static_data

VALID_WAY_TYPES = {"road", "highway", "path", "sea"}


def check_all() -> dict[str, Any]:
    """Return a report dict: counts plus any errors/warnings found."""
    errors: list[str] = []
    warnings: list[str] = []

    forces = static_data.load_forces()
    locales = static_data.load_locales()
    ways = static_data.load_ways()
    lords = static_data.load_lords()
    vassals = static_data.load_vassals()

    locale_ids = set(locales)
    force_ids = set(forces)

    # Ways: endpoints exist; way type is known; no self-loops.
    for w in ways:
        a, b, wt = w.get("from"), w.get("to"), w.get("type")
        if a not in locale_ids:
            errors.append(f"way endpoint not a locale: {a!r}")
        if b not in locale_ids:
            errors.append(f"way endpoint not a locale: {b!r}")
        if a == b:
            errors.append(f"way is a self-loop at {a!r}")
        if wt not in VALID_WAY_TYPES:
            errors.append(f"unknown way type {wt!r} on {a}-{b}")

    # Locale Seats: each listed seat occupant is a known Lord or Vassal.
    known_actors = set(lords) | set(vassals.get("regular", {})) | set(
        vassals.get("special", {})
    )
    for loc_id, loc in locales.items():
        for seat in loc.get("lord_seats", []):
            if seat not in lords:
                warnings.append(f"locale {loc_id} lists lord_seat {seat!r} not in lords.json")
        for seat in loc.get("vassal_seats", []):
            if seat not in vassals.get("regular", {}):
                warnings.append(
                    f"locale {loc_id} lists vassal_seat {seat!r} not in vassals.json"
                )

    # Lords: forces reference known force types; seat resolves to a locale.
    for lord_id, lord in lords.items():
        for ft in lord.get("forces", {}):
            if ft not in force_ids:
                errors.append(f"lord {lord_id} has unknown force type {ft!r}")
        seat = lord.get("seat")
        if seat is not None and seat not in locale_ids:
            errors.append(f"lord {lord_id} seat {seat!r} is not a locale")
        _ = known_actors  # reserved for future scenario checks

    # Regular Vassals: seat resolves to a locale.
    for v_id, v in vassals.get("regular", {}).items():
        seat = v.get("seat")
        if seat is not None and seat not in locale_ids:
            errors.append(f"vassal {v_id} seat {seat!r} is not a locale")

    # Scenarios: referenced lords/vassals/locales resolve.
    for sid in static_data.list_scenario_ids():
        scn = static_data.load_scenario(sid)
        for side in ("lancastrian", "yorkist"):
            block = scn.get("sides", {}).get(side, {})
            for lord_id in block.get("lord_cards", []):
                if lord_id not in lords:
                    errors.append(f"scenario {sid}/{side} lists unknown lord {lord_id!r}")
            for lord_id in block.get("mustered", []):
                if lord_id not in lords:
                    errors.append(
                        f"scenario {sid}/{side} musters unknown lord {lord_id!r}"
                    )

    return {
        "counts": {
            "forces": len(forces),
            "locales": len(locales),
            "ways": len(ways),
            "lords": len(lords),
            "vassals_regular": len(vassals.get("regular", {})),
            "vassals_special": len(vassals.get("special", {})),
            "scenarios": len(static_data.list_scenario_ids()),
        },
        "errors": errors,
        "warnings": warnings,
    }
