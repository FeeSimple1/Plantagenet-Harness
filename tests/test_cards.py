"""Arts of War card-data layer (1.9.1; deck assembly 6.0)."""

from __future__ import annotations

from plantagenet import static_data


def test_seventy_four_cards_both_halves():
    cards = static_data.load_cards()
    assert len(cards) == 74
    y = [c for c in cards.values() if c["side"] == "yorkist"]
    assert len(y) == 37 and len(cards) - len(y) == 37
    for cid, c in cards.items():
        assert c["event"]["text"] and c["capability"]["text"], cid
        assert c["event"]["type"] in ("hold", "this_levy", "this_campaign", "immediate")


def test_rose_distribution_matches_scenario_reference():
    cards = static_data.load_cards()
    from collections import Counter
    counts = Counter((c["side"], c["rose"]) for c in cards.values())
    # 13 no-rose + 9 (I) + 9 (II) + 6 (III) per side.
    for side in ("yorkist", "lancastrian"):
        assert counts[(side, 0)] == 13
        assert counts[(side, 1)] == 9
        assert counts[(side, 2)] == 9
        assert counts[(side, 3)] == 6


def test_shared_text_cards():
    cards = static_data.load_cards()
    # Y3 & Y9 share the ESCAPE SHIP Event; Y1 & Y2 share CULVERINS AND FALCONETS.
    assert cards["Y3"]["event"]["text"] == cards["Y9"]["event"]["text"]
    assert cards["Y1"]["capability"]["text"] == cards["Y2"]["capability"]["text"]


def test_deck_sizes_match_scenario_reference():
    # Ia: 13 no-rose + 9 one-rose = 22 each.
    assert len(static_data.scenario_card_deck("henry_vi", "yorkist")) == 22
    assert len(static_data.scenario_card_deck("henry_vi", "lancastrian")) == 22
    # II: Lancastrian removes L4 (12 no-rose + 9 two-rose = 21); Yorkist 22.
    lanc = static_data.scenario_card_deck("warwicks_rebellion", "lancastrian")
    assert "L4" not in lanc and len(lanc) == 21
    assert len(static_data.scenario_card_deck("warwicks_rebellion", "yorkist")) == 22
    # III: 13 no-rose + 6 three-rose = 19 each.
    assert len(static_data.scenario_card_deck("my_kingdom_for_a_horse", "yorkist")) == 19


def test_deck_only_matching_rose():
    deck = static_data.scenario_card_deck("my_kingdom_for_a_horse", "yorkist")
    cards = static_data.load_cards()
    assert all(cards[cid]["rose"] in (0, 3) for cid in deck)


def test_capability_lords_parsed():
    cards = static_data.load_cards()
    assert cards["Y24"]["capability"]["title"] == "HASTINGS"     # Special Vassal capability
    assert cards["L35"]["capability"]["lords"]                    # Jasper Tudor or Henry Tudor
