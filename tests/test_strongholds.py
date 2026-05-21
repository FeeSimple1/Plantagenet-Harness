"""Strongholds table fidelity (D-004; reference Strongholds Reference)."""

from __future__ import annotations

from plantagenet import static_data


def test_levy_yields_by_type():
    assert static_data.stronghold_yields("ely")["levy_troops"] == {"longbow": 1, "militia": 1}
    assert static_data.stronghold_yields("arundel")["levy_troops"] == {"militia": 2}
    assert static_data.stronghold_yields("ludlow")["levy_troops"] == {
        "men_at_arms": 1, "longbow": 1}


def test_special_stronghold_yields_by_id():
    assert static_data.stronghold_yields("london")["levy_troops"] == {
        "men_at_arms": 1, "longbow": 1, "militia": 1}
    assert static_data.stronghold_yields("calais")["levy_troops"] == {
        "men_at_arms": 2, "longbow": 1}
    assert static_data.stronghold_yields("harlech")["levy_troops"] == {
        "men_at_arms": 1, "longbow": 2}


def test_favour_vs_most_favour_basis():
    # User emphasis: regular types use Most Favour; Special use individual Favour.
    table = static_data.load_strongholds()
    for t in ("city", "town", "fortress"):
        assert table["by_type"][t]["tides_of_war"]["basis"] == "most_favour"
    for sp in ("london", "calais", "harlech"):
        assert table["special"][sp]["tides_of_war"]["basis"] == "favour"


def test_troop_pool_totals_128():
    forces = static_data.load_forces()
    assert sum(forces[f].get("pool", 0) for f in forces) == 128
