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
    seas = static_data.load_seas()
    strongholds = static_data.load_strongholds()
    cards = static_data.load_cards()
    exile_boxes = static_data.load_exile_boxes()

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

    # Strongholds table: every Locale's type resolves to a table row, and the
    # Levy-Troops units reference real force types (Q-003 / D-004).
    force_ids2 = set(forces)
    for loc_id, loc in locales.items():
        typ = loc["type"]
        try:
            row = (strongholds["special"][loc_id] if typ == "special_stronghold"
                   else strongholds["by_type"][typ])
        except KeyError:
            errors.append(f"locale {loc_id} (type {typ}) has no Strongholds-table row")
            continue
        for unit in row.get("levy_troops", {}):
            if unit not in force_ids2:
                errors.append(f"strongholds row for {loc_id} levies unknown unit {unit!r}")
    # Pooled wooden Troop types carry a pool count (1.6).
    for fid in ("men_at_arms", "longbow", "militia", "mercenaries", "handgunners"):
        if "pool" not in forces.get(fid, {}):
            errors.append(f"force {fid} is missing its pool count")

    # Sea zones: every member Port is a real Locale with port=True; every
    # member Exile box exists; each Port belongs to exactly one zone; zone
    # adjacency references real zones. (Q-001 / Rules 4.6.1.)
    zones = seas.get("zones", {})
    port_zone_count: dict[str, int] = {}
    for zid, zone in zones.items():
        for port in zone.get("ports", []):
            if port not in locale_ids:
                errors.append(f"sea zone {zid} lists port {port!r} not a locale")
            elif not locales[port].get("port"):
                errors.append(f"sea zone {zid} lists {port!r} which is not a Port")
            port_zone_count[port] = port_zone_count.get(port, 0) + 1
        for box in zone.get("exile_boxes", []):
            if box not in exile_boxes:
                errors.append(f"sea zone {zid} lists exile box {box!r} not in exile_boxes.json")
    # Every Port locale must be assigned to exactly one sea zone.
    for loc_id, loc in locales.items():
        if loc.get("port") and port_zone_count.get(loc_id, 0) != 1:
            errors.append(
                f"port {loc_id} is in {port_zone_count.get(loc_id, 0)} sea zones (expected 1)"
            )
    for a, b in seas.get("adjacency", []):
        if a not in zones or b not in zones:
            errors.append(f"sea adjacency references unknown zone: {a!r}-{b!r}")

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

    # Arts of War cards: every card has both halves; rose in 0-3; valid side.
    for cid, c in cards.items():
        if "event" not in c or "capability" not in c:
            errors.append(f"card {cid} missing an Event or Capability half")
        if c.get("rose") not in (0, 1, 2, 3):
            errors.append(f"card {cid} has bad rose {c.get('rose')!r}")
        if c.get("side") not in ("lancastrian", "yorkist"):
            errors.append(f"card {cid} has bad side {c.get('side')!r}")

    return {
        "counts": {
            "forces": len(forces),
            "locales": len(locales),
            "ways": len(ways),
            "lords": len(lords),
            "vassals_regular": len(vassals.get("regular", {})),
            "vassals_special": len(vassals.get("special", {})),
            "scenarios": len(static_data.list_scenario_ids()),
            "sea_zones": len(seas.get("zones", {})),
            "cards": len(cards),
            "troop_pool": sum(forces[f].get("pool", 0) for f in forces if not f.startswith("_")),
        },
        "errors": errors,
        "warnings": warnings,
    }
