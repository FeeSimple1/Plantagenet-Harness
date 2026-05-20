"""Forces table fidelity (reference/Plantagenet Reference info.md)."""

from __future__ import annotations


def test_force_set(forces):
    assert set(forces) == {
        "retinue", "vassal", "men_at_arms", "longbow",
        "militia", "mercenaries", "handgunners",
    }


def test_retinue_profile(forces):
    # "Retinue - three strikes, armor protects at 1-4."
    r = forces["retinue"]
    assert r["protection"] == [1, 4]
    assert sum(s["count"] for s in r["strikes"]) == 3
    assert {s["kind"] for s in r["strikes"]} == {"melee"}


def test_longbow_archery_only(forces):
    # "Longbowman - two archery strikes only, armor protects at 1."
    lb = forces["longbow"]
    assert lb["protection"] == [1, 1]
    assert lb["strikes"] == [{"kind": "archery", "count": 2}]


def test_militia_and_mercenaries_split_half_strikes(forces):
    # Both: half archery + half melee. Mercenaries protect 1-3; Militia at 1.
    for fid, prot in (("militia", [1, 1]), ("mercenaries", [1, 3])):
        f = forces[fid]
        assert f["protection"] == prot
        kinds = {s["kind"]: s["count"] for s in f["strikes"]}
        assert kinds == {"archery": 0.5, "melee": 0.5}


def test_handgunners_melee_and_gun(forces):
    # "Handgunners - one strike of melee, two strikes of gun, armor 1-3."
    hg = forces["handgunners"]
    assert hg["protection"] == [1, 3]
    kinds = {s["kind"]: s["count"] for s in hg["strikes"]}
    assert kinds == {"melee": 1, "gun": 2}
