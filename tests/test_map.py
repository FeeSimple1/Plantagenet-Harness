"""Map data fidelity and structural invariants (Map Reference)."""

from __future__ import annotations

import pytest

VALID_WAY_TYPES = {"road", "highway", "path", "sea"}


def test_every_way_endpoint_is_a_locale(ways, locales):
    for w in ways:
        assert w["from"] in locales, w
        assert w["to"] in locales, w
        assert w["type"] in VALID_WAY_TYPES, w


def test_ways_are_canonical_and_unique(ways):
    seen = set()
    for w in ways:
        a, b = w["from"], w["to"]
        assert a < b, f"way not in canonical order: {w}"
        key = (a, b, w["type"])
        assert key not in seen, f"duplicate way: {w}"
        seen.add(key)


def test_calais_has_no_land_ways(ways):
    # "The special stronghold of Calais is not connected ... by land."
    for w in ways:
        assert "calais" not in (w["from"], w["to"]), w


def test_disputed_edges_are_excluded_and_recorded():
    # Q-002: Leicester-Peterborough (road) and Leicester-Nottingham
    # (highway) are non-reciprocated in the reference; held out pending
    # adjudication.
    import json
    from importlib import resources

    with resources.files("plantagenet.data.static").joinpath("ways.json").open() as fh:
        doc = json.load(fh)
    disputed = {tuple(x) for x in doc["_meta"]["disputed_pending_adjudication"]}
    assert ("leicester", "peterborough", "road") in disputed
    assert ("leicester", "nottingham", "highway") in disputed
    for w in doc["ways"]:
        key = tuple(sorted((w["from"], w["to"]))) + (w["type"],)
        assert key not in disputed


def test_region_strongholds_match_scenario_reference(locales):
    # Scenario Reference: South Area has 9 Strongholds, North Area has 6.
    south = [k for k, v in locales.items() if v.get("region") == "south"]
    north = [k for k, v in locales.items() if v.get("region") == "north"]
    assert len(south) == 9
    assert len(north) == 6


@pytest.mark.parametrize("loc_id", ["london", "harlech", "calais"])
def test_special_strongholds_present(locales, loc_id):
    assert locales[loc_id]["type"] == "special_stronghold"
