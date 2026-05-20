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
