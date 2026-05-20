"""Generate the standalone scenario setup files.

Provenance: reference/Plantagenet Scenario Reference.txt (errata applied
where the reference marks [ERRATA APPLIED]). Static setup is structured;
nuanced scenario special rules are stored verbatim so nothing is lost
ahead of the phases that implement them. Favour entries given by Area in
the reference ("all nine Strongholds within the South Area") are expanded
to explicit Locale ids using the region data in locales.json.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE = Path("src/plantagenet/data/static")
SCN = Path("src/plantagenet/data/scenarios")
LOC = {k: v for k, v in json.loads((BASE / "locales.json").read_text()).items()
       if not k.startswith("_")}
REGION = {r: sorted(k for k, v in LOC.items() if v.get("region") == r)
          for r in ("south", "north", "wales")}


def fav(*items):
    """Expand favour tokens: 'south_area'/'north_area' -> region locale ids."""
    out = []
    for it in items:
        if it == "south_area":
            out += REGION["south"]
        elif it == "north_area":
            out += REGION["north"]
        else:
            assert it in LOC, f"favour locale {it!r} not a locale"
            out.append(it)
    return sorted(dict.fromkeys(out))


def write(sid, doc):
    (SCN / f"{sid}.json").write_text(json.dumps(doc, indent=2) + "\n")


# ---------------------------------------------------------------- Ia
write("henry_vi", {
    "id": "henry_vi",
    "title": "Scenario Ia. Henry VI, 1459-1461",
    "years": "1459-1461",
    "turns": {"first_box": 1, "last_box": 15, "levy_box": 1},
    "arts_of_war": "Each side: its 13 no-rose and 9 one-rose Arts of War cards.",
    "sides": {
        "lancastrian": {"role": "king",
            "lord_cards": ["henry_vi", "somerset_1", "northumberland_lancastrian",
                           "exeter_1", "buckingham"],
            "mustered": ["henry_vi", "somerset_1"]},
        "yorkist": {"role": "rebel",
            "lord_cards": ["york", "march", "salisbury", "warwick_yorkist", "rutland"],
            "mustered": ["york", "march"]},
    },
    "setup": {
        "exile_alignment": {"scotland": "lancastrian", "france": "lancastrian",
                            "ireland": "yorkist", "burgundy": "yorkist"},
        "favour": {"lancastrian": fav("london", "wells"),
                   "yorkist": fav("ely", "ludlow")},
        "vassals_on_map": {"mode": "all"},
        "on_map": [
            {"lord": "henry_vi", "locale": "london", "color": "red"},
            {"lord": "somerset_1", "locale": "london", "color": "red", "ring": "silver"},
            {"lord": "york", "locale": "ely", "color": "white"},
            {"lord": "march", "locale": "ludlow", "color": "white"},
        ],
        "calendar": [
            {"box": 1, "markers": ["levy"]},
            {"box": 2, "lords": [{"lord": "northumberland_lancastrian", "color": "red"},
                                  {"lord": "salisbury", "color": "white"}]},
            {"box": 3, "lords": [{"lord": "exeter_1", "color": "red"},
                                  {"lord": "warwick_yorkist", "color": "white"}]},
            {"box": 5, "lords": [{"lord": "buckingham", "color": "red"},
                                  {"lord": "rutland", "color": "white"}]},
        ],
        "influence": {"marker_at": 0, "marker_side": "lancastrian",
                      "stronghold_markers": {"fortress": {"side": "yorkist", "at": 1},
                                             "town": {"side": "yorkist", "at": 0},
                                             "city": {"side": "yorkist", "at": 0}},
                      "victory_check": 40},
    },
    "allied_networks": {
        "scotland": ["henry_vi", "somerset_1"],
        "france": ["northumberland_lancastrian", "exeter_1", "buckingham"],
        "ireland": ["york", "rutland"],
        "burgundy": ["march", "warwick_yorkist", "salisbury"],
    },
    "special_rules": [
        {"name": "Capture of the King",
         "text": "If Yorkists win a Battle against Henry VI, they add +10 Influence "
                 "points. Instead of checking for Henry VI's Death, Disband him; the "
                 "Yorkists place his cylinder on the mat of any Unrouted Yorkist Lord at "
                 "the Battle (instead of on the Calendar). While a Yorkist Lord holds him, "
                 "Henry VI cannot Muster and does not count as on map. If that Lord goes "
                 "into Exile, Disbands, or Dies, place Henry VI on the Calendar as if just "
                 "Disbanded; Lancastrians add +10 Influence points."},
    ],
    "victory_thresholds": [
        {"turns": "1-5", "influence": 40},
        {"turns": "6-10", "influence": 35},
        {"turns": "11-15", "influence": 30},
    ],
})

# ---------------------------------------------------------------- Ib
write("towton", {
    "id": "towton",
    "title": "Scenario Ib. Towton, 1461",
    "years": "1461",
    "turns": {"first_box": 1, "last_box": 1, "levy_box": 1, "end_marker_box": 2},
    "arts_of_war": "Each side: its 13 no-rose and 9 one-rose Arts of War cards.",
    "sides": {
        "lancastrian": {"role": "king",
            "lord_cards": ["somerset_1", "exeter_1", "northumberland_lancastrian"],
            "mustered": ["somerset_1", "exeter_1", "northumberland_lancastrian"]},
        "yorkist": {"role": "rebel",
            "lord_cards": ["march", "norfolk", "warwick_yorkist"],
            "mustered": ["march", "norfolk", "warwick_yorkist"]},
    },
    "setup": {
        "exile_alignment": {},
        "_exile_note": "No need to mark Exile boxes; the scenario is too short for Lords to end up there.",
        "favour": {
            "lancastrian": fav("st_albans", "north_area"),
            "yorkist": fav("london", "calais", "hereford", "gloucester", "oxford", "south_area"),
        },
        "vassals_on_map": {"mode": "all_except", "except": ["fauconberg", "norfolk"],
                           "on_lord_mat": [{"vassal": "fauconberg", "lord": "march"}]},
        "on_map": [
            {"lord": "somerset_1", "locale": "newcastle", "color": "red", "ring": "silver"},
            {"lord": "exeter_1", "locale": "newcastle", "color": "red"},
            {"lord": "northumberland_lancastrian", "locale": "carlisle", "color": "red"},
            {"lord": "march", "locale": "london", "color": "white"},
            {"lord": "norfolk", "locale": "london", "color": "white"},
            {"lord": "warwick_yorkist", "locale": "london", "color": "white"},
        ],
        "calendar": [
            {"box": 1, "markers": ["levy"]},
            {"box": 2, "markers": ["end"]},
            {"box": 4, "vassals": ["fauconberg"]},
        ],
        "influence": {"marker_at": 0, "marker_side": "yorkist", "stronghold_markers": {}},
    },
    "special_rules": [
        {"name": "Norfolk is Late",
         "text": "In the first Battle that includes Norfolk and any other Yorkist Lord(s), "
                 "Norfolk Arrays and stays in Reserve until Round 2."},
        {"name": "Test of Arms",
         "text": "After each and any Battle at York, set it to Favour the winning side. A "
                 "side with Favour at York at the end of the Campaign wins the Scenario. "
                 "The sides draw if neither has Favour there."},
    ],
    "victory_thresholds": [],
})

# ---------------------------------------------------------------- Ic
write("somersets_return", {
    "id": "somersets_return",
    "title": "Scenario Ic. Somerset's Return, 1463-1464",
    "years": "1463-1464",
    "turns": {"first_box": 5, "last_box": 7, "levy_box": 5, "end_marker_box": 8},
    "arts_of_war": "Each side: its 13 no-rose and 9 one-rose Arts of War cards.",
    "sides": {
        "yorkist": {"role": "king",
            "lord_cards": ["march", "warwick_yorkist"],
            "mustered": ["march", "warwick_yorkist"]},
        "lancastrian": {"role": "rebel",
            "lord_cards": ["henry_vi", "somerset_1"],
            "mustered": ["somerset_1"]},
    },
    "setup": {
        "exile_alignment": {"burgundy": "yorkist", "scotland": "lancastrian"},
        "favour": {
            "yorkist": fav("ludlow", "hereford", "london", "calais", "south_area"),
            "lancastrian": fav("harlech", "pembroke", "cardiff", "chester", "lancaster", "north_area"),
        },
        "vassals_on_map": {"mode": "all"},
        "on_map": [
            {"lord": "march", "locale": "london", "color": "white"},
            {"lord": "warwick_yorkist", "locale": "london", "color": "white",
             "capability": "L23", "special_vassal": "montagu"},
            {"lord": "somerset_1", "locale": "bamburgh", "color": "red", "ring": "silver"},
        ],
        "calendar": [
            {"box": 5, "markers": ["levy"],
             "lords": [{"lord": "henry_vi", "color": "red", "exile": True}]},
            {"box": 8, "markers": ["end"]},
        ],
        "influence": {"marker_at": 6, "marker_side": "lancastrian",
                      "stronghold_markers": {"fortress": {"side": "lancastrian", "at": 1},
                                             "town": {"side": "lancastrian", "at": 0},
                                             "city": {"side": "yorkist", "at": 2}},
                      "victory_check": 25},
    },
    "special_rules": [
        {"name": "Montagu",
         "text": "Warwick - even though a Yorkist - sets up with the Lancastrian 2-rose "
                 "MONTAGU Capability card (L23) and its Special Vassal. Disband or removal "
                 "of Warwick or Montagu removes the card from play."},
        {"name": "Brief Rebellion", "text": "Skip Waste (4.8.5)."},
    ],
    "victory_thresholds": [{"turns": "all", "influence": 25}],
})

# ---------------------------------------------------------------- II
write("warwicks_rebellion", {
    "id": "warwicks_rebellion",
    "title": "Scenario II. Warwick's Rebellion, 1469-1471",
    "years": "1469-1471",
    "turns": {"first_box": 1, "last_box": 15, "levy_box": 1},
    "arts_of_war": "12 or 13 no-rose and 9 two-rose cards per deck. For the Lancastrian "
                   "deck, REMOVE card L4 BE SENT FOR/HERALDS from this scenario.",
    "sides": {
        "yorkist": {"role": "king",
            "lord_cards": ["edward_iv", "pembroke", "devon", "gloucester_1", "northumberland_1"],
            "mustered": ["edward_iv", "pembroke"]},
        "lancastrian": {"role": "rebel",
            "lord_cards": ["warwick_lancastrian", "clarence", "jasper_tudor_1", "margaret",
                           "somerset_2", "exeter_2", "oxford"],
            "mustered": ["warwick_lancastrian", "clarence", "jasper_tudor_1"]},
    },
    "setup": {
        "exile_alignment": {"burgundy": "yorkist", "france": "lancastrian"},
        "favour": {
            "yorkist": fav("london", "ely", "ludlow", "carlisle", "pembroke", "exeter"),
            "lancastrian": fav("calais", "harlech", "york", "coventry", "wells"),
        },
        "vassals_on_map": {"mode": "all_except", "except": ["devon", "oxford"]},
        "on_map": [
            {"lord": "edward_iv", "locale": "london", "color": "white"},
            {"lord": "pembroke", "locale": "pembroke", "color": "white"},
            {"lord": "warwick_lancastrian", "locale": "calais", "color": "red"},
            {"lord": "clarence", "locale": "york", "color": "red"},
            {"lord": "jasper_tudor_1", "locale": "harlech", "color": "red"},
        ],
        "calendar": [
            {"box": 1, "markers": ["levy"], "lords": [{"lord": "devon", "color": "white"}]},
            {"box": 9, "lords": [
                {"lord": "gloucester_1", "color": "white", "ring": "silver"},
                {"lord": "northumberland_1", "color": "white"},
                {"lord": "margaret", "color": "red", "exile": True},
                {"lord": "somerset_2", "color": "red", "exile": True},
                {"lord": "oxford", "color": "red", "exile": True},
                {"lord": "exeter_2", "color": "red", "exile": True}]},
        ],
        "influence": {"marker_at": 0, "marker_side": "yorkist",
                      "stronghold_markers": {"fortress": {"side": "yorkist", "at": 2},
                                             "town": {"side": "yorkist", "at": 0},
                                             "city": {"side": "yorkist", "at": 0}},
                      "victory_check": 40},
    },
    "special_rules": [
        {"name": "Foreign Haven", "errata_applied": True,
         "text": "Whenever Warwick goes into Exile upon Yorkist Approach (4.3.5) OR DIES AS "
                 "A DEFENDER (4.4.3), shift all Lancastrian Lords on the Calendar (including "
                 "Warwick) leftward (only) to the current Turn; then shift all Yorkists on "
                 "the Calendar leftward (only) to the next Turn. Whenever Edward IV is Routed "
                 "in Battle while Margaret is NOT on map, he may go into Exile (4.3.5) "
                 "instead of checking for Death."},
        {"name": "Shaky Allies",
         "text": "Upon placing Margaret in the France Exile box, permanently remove Clarence "
                 "(return his mat's items to their pools and his cylinder, Lord card, and "
                 "Seat marker to the game box). Margaret and Warwick may never enter the "
                 "same Stronghold."},
        {"name": "Queen Regent",
         "text": "Each Tides of War that Margaret is at London, Lancastrians add +3 Influence."},
    ],
    "victory_thresholds": [
        {"turns": "1-5", "influence": 40},
        {"turns": "6-10", "influence": 35},
        {"turns": "11-15", "influence": 30},
    ],
})

# ---------------------------------------------------------------- III
write("my_kingdom_for_a_horse", {
    "id": "my_kingdom_for_a_horse",
    "title": "Scenario III. My Kingdom for a Horse, 1484-1485",
    "years": "1484-1485",
    "turns": {"first_box": 3, "last_box": 9, "levy_box": 3, "end_marker_box": 10},
    "arts_of_war": "13 no-rose and 6 three-rose cards per deck.",
    "sides": {
        "yorkist": {"role": "king",
            "lord_cards": ["gloucester_2", "northumberland_2", "norfolk", "richard_iii"],
            "mustered": ["gloucester_2", "northumberland_2", "norfolk"]},
        "lancastrian": {"role": "rebel",
            "lord_cards": ["henry_tudor", "jasper_tudor_2", "oxford"],
            "mustered": ["henry_tudor", "jasper_tudor_2", "oxford"]},
    },
    "setup": {
        "exile_alignment": {"burgundy": "yorkist", "france": "lancastrian"},
        "favour": {
            "yorkist": fav("london", "calais", "carlisle", "arundel", "gloucester", "york"),
            "lancastrian": fav("oxford", "harlech", "pembroke"),
        },
        "vassals_on_map": {"mode": "all_except", "except": ["oxford", "norfolk"]},
        "on_map": [
            {"lord": "gloucester_2", "locale": "london", "color": "white", "ring": "gold"},
            {"lord": "northumberland_2", "locale": "carlisle", "color": "white"},
            {"lord": "norfolk", "locale": "arundel", "color": "white"},
            {"lord": "henry_tudor", "exile_box": "france", "color": "red"},
            {"lord": "jasper_tudor_2", "exile_box": "france", "color": "red"},
            {"lord": "oxford", "exile_box": "france", "color": "red"},
        ],
        "calendar": [
            {"box": 3, "markers": ["levy"]},
            {"box": 10, "markers": ["end"]},
        ],
        "influence": {"marker_at": 0, "marker_side": "yorkist",
                      "stronghold_markers": {"fortress": {"side": "lancastrian", "at": 1},
                                             "town": {"side": "yorkist", "at": 1},
                                             "city": {"side": "yorkist", "at": 2}}},
    },
    "special_rules": [
        {"name": "King Richard",
         "text": "The Yorkist player, at setup or during any Muster (3.4) with Gloucester at "
                 "London, may replace the Gloucester Lord card in place with Richard III, "
                 "affecting various Arts of War."},
        {"name": "Ravaged Land", "text": "Skip all Grow and Waste (4.8.4 - 4.8.5)."},
    ],
    "victory_thresholds": [{"turns": "all", "influence": 45}],
})

# ---------------------------------------------------------------- III(B)
write("bosworth", {
    "id": "bosworth",
    "title": "Scenario III(B). Bosworth, 22 August 1485",
    "years": "1485",
    "battle_only": True,
    "_note": "Battle-only mini-scenario. Does NOT use the game board, the Hidden Mats "
             "option, or the Command deck. Ignore map, Calendar, and Influence track.",
    "arts_of_war": "13 no-rose and 6 three-rose cards per deck. Each player secretly "
                   "chooses four Capability cards and distributes them among the Lords.",
    "sides": {
        "yorkist": {"role": "king",
            "lord_cards": ["richard_iii", "northumberland_2", "norfolk"],
            "mustered": ["richard_iii", "northumberland_2", "norfolk"]},
        "lancastrian": {"role": "rebel",
            "lord_cards": ["henry_tudor", "jasper_tudor_2", "oxford"],
            "mustered": ["henry_tudor", "jasper_tudor_2", "oxford"]},
    },
    "special_rules": [
        {"name": "On Bosworth Field",
         "text": "Each player, working behind a screen, secretly chooses four Capability "
                 "cards. Distribute the Capabilities among the Lords. Then Array the mats, "
                 "one Lord at Front Center, one at Front Left, and one at Front Right, "
                 "placing each Lord's Valour tokens (4.4.1). Finally, reveal Arrays and "
                 "begin the Battle with Round 1 (4.4.2)."},
        {"name": "Victory",
         "text": "The winner of the Battle wins the scenario. If all Lords on both sides "
                 "Rout, the game is a draw."},
    ],
    "victory_thresholds": [],
})

# ---------------------------------------------------------------- index
index = {
    "_source": "reference/Plantagenet Scenario Reference.txt",
    "scenarios": [
        "henry_vi", "towton", "somersets_return", "warwicks_rebellion",
        "my_kingdom_for_a_horse", "bosworth", "wars_of_the_roses",
    ],
}
(SCN / "index.json").write_text(json.dumps(index, indent=2) + "\n")
print("standalone scenarios + index written")
