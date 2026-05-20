"""Lord and Vassal data fidelity (Lords and Vassals Reference)."""

from __future__ import annotations


def test_side_counts(lords):
    lanc = [k for k, v in lords.items() if v["side"] == "lancastrian"]
    york = [k for k, v in lords.items() if v["side"] == "yorkist"]
    assert len(lanc) == 14
    assert len(york) == 14


def test_henry_vi_profile(lords):
    h = lords["henry_vi"]
    assert h["ratings"] == {"influence": 5, "lordship": 2, "command": 2, "valour": 0}
    assert h["seat"] == "london"
    assert h["title"] == "marshal"
    assert h["heir"] == 1
    assert h["forces"] == {"retinue": 1, "men_at_arms": 2, "longbow": 2, "militia": 4}
    assert h["assets"] == {"provender": 2, "coin": 4, "cart": 2}


def test_edward_iv_valour_four(lords):
    assert lords["edward_iv"]["ratings"]["valour"] == 4


def test_warwick_yorkist_has_ships_no_cart(lords):
    # "Warwick (Yorkist) ... Assets: 2 Provender, 2 Coin, 2 Ship" (no Cart).
    a = lords["warwick_yorkist"]["assets"]
    assert a.get("ship") == 2
    assert "cart" not in a


def test_every_lord_seat_resolves(lords, locales):
    for lid, lord in lords.items():
        assert lord["seat"] in locales, lid


def test_regular_vassal_seats_resolve(vassals, locales):
    assert len(vassals["regular"]) == 13
    for vid, v in vassals["regular"].items():
        assert v["seat"] in locales, vid


def test_special_vassals_reference_capability_cards(vassals):
    expected = {"hastings", "edward_prince_of_wales", "montagu",
                "clifford", "thomas_stanley", "trollope"}
    assert set(vassals["special"]) == expected
    for vid, v in vassals["special"].items():
        assert v["capability_card"], vid
        assert v["side"] in ("lancastrian", "yorkist")
