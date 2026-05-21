"""Loaders for the static reference data shipped with the harness.

Static data lives as JSON under ``plantagenet/data/static/`` and
``plantagenet/data/scenarios/``. Every file is loaded once and cached.

This module is data plumbing only — it reads and validates the shape of
the reference data. It contains no game logic (no rule enforcement, no
action resolution). That arrives in later phases.

All data traces to the curated reference files in ``reference/`` and,
where those are silent, the Rules of Play / Errata PDFs in ``source/``.
The provenance for each datum is recorded in the JSON ``_source`` fields
and in the per-file headers.
"""

from __future__ import annotations

import json
from functools import cache
from importlib import resources
from typing import Any

_STATIC_PKG = "plantagenet.data.static"
_SCENARIO_PKG = "plantagenet.data.scenarios"


def _load_json(package: str, name: str) -> Any:
    with resources.files(package).joinpath(name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _strip_meta(d: dict[str, Any]) -> dict[str, Any]:
    """Drop top-level metadata keys (those beginning with ``_``)."""
    return {k: v for k, v in d.items() if not k.startswith("_")}



@cache
def load_forces() -> dict[str, Any]:
    """Force types and their Strike/Protection profiles (Forces table)."""
    return _strip_meta(_load_json(_STATIC_PKG, "forces.json"))


@cache
def load_locales() -> dict[str, Any]:
    """Map Locales: type, port flag, region, and Seat assignments."""
    return _strip_meta(_load_json(_STATIC_PKG, "locales.json"))


@cache
def load_ways() -> list[dict[str, Any]]:
    """Map Ways: undirected edges tagged with way type (Road/Highway/Path/Sea)."""
    doc = _load_json(_STATIC_PKG, "ways.json")
    return doc["ways"] if isinstance(doc, dict) else doc


@cache
def load_lords() -> dict[str, Any]:
    """Lord mats: ratings, starting Forces, Assets, Seat, Heir, Title."""
    return _strip_meta(_load_json(_STATIC_PKG, "lords.json"))


@cache
def load_vassals() -> dict[str, Any]:
    """Regular and Special Vassals: Seat, Loyalty, Service, special rules."""
    return _strip_meta(_load_json(_STATIC_PKG, "vassals.json"))


SCENARIO_ROSE = {"henry_vi": 1, "towton": 1, "somersets_return": 1,
                 "warwicks_rebellion": 2, "my_kingdom_for_a_horse": 3, "bosworth": 3}
# Per-scenario deck exclusions beyond the rose rule (Scenario Reference / Errata).
DECK_EXCLUDE = {("warwicks_rebellion", "lancastrian"): {"L4"}}   # II removes L4 (4.6.4 note)


@cache
def load_cards() -> dict[str, Any]:
    """Arts of War cards (Y1..Y37, L1..L37): each with an Event and a
    Capability, a rose group (0=all, 1=I, 2=II, 3=III), and metadata."""
    return _strip_meta(_load_json(_STATIC_PKG, "cards.json"))


def scenario_card_deck(scenario_id: str, side: str) -> list[str]:
    """Assemble a side's Arts of War deck for a standalone scenario (6.0):
    no-rose cards plus those whose rose matches the scenario number, minus
    any scenario-specific exclusions. Grand-scenario (Wars) decks are set by
    Succession (handled separately) and return []."""
    rose = SCENARIO_ROSE.get(scenario_id)
    if rose is None:
        return []
    excl = DECK_EXCLUDE.get((scenario_id, side), set())
    return sorted(
        cid for cid, c in load_cards().items()
        if c["side"] == side and c["rose"] in (0, rose) and cid not in excl
    )


@cache
def load_strongholds() -> dict[str, Any]:
    """Strongholds table: Levy-Troops / Supply / Tax / Pillage yields and the
    Tides-of-War award (with favour vs most-favour basis) per type (Q-003/D-004)."""
    return _strip_meta(_load_json(_STATIC_PKG, "strongholds.json"))


def stronghold_yields(locale_id: str) -> dict[str, Any]:
    """Return the Strongholds-table row for a Locale (by type, or by id for
    Special Strongholds). Raises KeyError if the Locale is not a Stronghold."""
    loc = load_locales()[locale_id]
    table = load_strongholds()
    typ = loc["type"]
    if typ == "special_stronghold":
        return table["special"][locale_id]
    return table["by_type"][typ]


@cache
def load_seas() -> dict[str, Any]:
    """Sea zones (Irish Sea / English Channel / North Sea), their Port and
    Exile-box membership, and zone adjacency for Sail (4.6.1 / FAQ #1)."""
    return _strip_meta(_load_json(_STATIC_PKG, "seas.json"))


@cache
def load_exile_boxes() -> dict[str, Any]:
    """Exile boxes (Scotland, France, Ireland, Burgundy, Calais) metadata."""
    return _strip_meta(_load_json(_STATIC_PKG, "exile_boxes.json"))


@cache
def list_scenario_ids() -> list[str]:
    index = _load_json(_SCENARIO_PKG, "index.json")
    return list(index["scenarios"])


@cache
def load_scenario(scenario_id: str) -> dict[str, Any]:
    """Load a single scenario setup file by id (e.g. ``"henry_vi"``)."""
    return _load_json(_SCENARIO_PKG, f"{scenario_id}.json")
