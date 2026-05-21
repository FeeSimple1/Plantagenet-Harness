"""Generate locales.json and ways.json from the Map Reference.

Provenance: reference/Plantagenet Map Reference.txt. Each Locale's
connections are transcribed exactly as the reference states them, from
that Locale's point of view. The builder then VERIFIES that every edge
is declared from BOTH endpoints with the same way type (a symmetry
check that catches transcription slips), dedupes to undirected edges,
and emits the two JSON data files.

Sea adjacency between ports is NOT in the Map Reference text; it is
handled separately (see RULES_QUESTIONS.md Q-001) and is not fabricated
here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# (id, display name, type, port?, region, lord_seats, vassal_seats)
# type: town | city | fortress | special_stronghold
# region: None | "south" | "north" | "wales"
LOCALES = [
    ("truro", "Truro", "town", True, None, [], []),
    ("launceston", "Launceston", "city", False, None, [], ["bonville"]),
    ("plymouth", "Plymouth", "town", True, None, [], []),
    ("exeter", "Exeter", "city", True, None, ["devon", "exeter_1", "exeter_2"], ["devon"]),
    ("dorchester", "Dorchester", "town", True, None, [], []),
    ("wells", "Wells", "city", False, None, ["somerset_1", "somerset_2"], []),
    ("salisbury", "Salisbury", "city", False, "south", [], []),
    ("southampton", "Southampton", "town", True, "south", [], []),
    ("arundel", "Arundel", "town", False, "south", ["norfolk"], ["norfolk"]),
    ("winchester", "Winchester", "city", False, "south", [], []),
    ("guildford", "Guildford", "city", False, "south", [], []),
    ("hastings", "Hastings", "town", True, "south", [], []),
    ("dover", "Dover", "town", True, "south", [], ["fauconberg"]),
    ("canterbury", "Canterbury", "city", False, "south", ["rutland"], []),
    ("london", "London", "special_stronghold", False, None,
        ["henry_vi", "margaret", "henry_tudor", "edward_iv", "gloucester_2", "richard_iii"], []),
    ("rochester", "Rochester", "city", False, "south", [], []),
    ("bristol", "Bristol", "city", True, None, [], []),
    ("newbury", "Newbury", "town", False, None, [], []),
    ("oxford", "Oxford", "city", False, None, ["oxford"], ["oxford"]),
    ("st_albans", "St. Albans", "town", False, None, [], ["essex"]),
    ("bedford", "Bedford", "town", False, None, [], []),
    ("cambridge", "Cambridge", "town", False, None, [], []),
    ("bury_st_edmunds", "Bury St. Edmunds", "town", False, None, [], []),
    ("ipswich", "Ipswich", "town", True, None, [], ["suffolk"]),
    ("norwich", "Norwich", "city", False, None, [], []),
    ("ely", "Ely", "city", False, None, ["york"], []),
    ("lynn", "Lynn", "fortress", True, None, [], []),
    ("peterborough", "Peterborough", "city", False, None, [], []),
    ("northampton", "Northampton", "town", False, None, [], []),
    ("gloucester", "Gloucester", "city", False, "wales", ["gloucester_1"], []),
    ("cardiff", "Cardiff", "city", False, "wales", [], []),
    ("pembroke", "Pembroke", "fortress", True, "wales", ["jasper_tudor_2", "pembroke"], []),
    ("harlech", "Harlech", "special_stronghold", True, "wales", ["jasper_tudor_1"], []),
    ("chester", "Chester", "city", False, None, [], []),
    ("shrewsbury", "Shrewsbury", "city", False, "wales", [], ["shrewsbury"]),
    ("ludlow", "Ludlow", "fortress", False, "wales", ["march"], []),
    ("hereford", "Hereford", "city", False, "wales", [], []),
    ("worcester", "Worcester", "city", False, None, [], ["worcester"]),
    ("coventry", "Coventry", "city", False, None, ["buckingham"], []),
    ("lichfield", "Lichfield", "city", False, None, [], []),
    ("leicester", "Leicester", "town", False, None, [], ["dudley"]),
    ("derby", "Derby", "town", False, None, [], ["stanley"]),
    ("nottingham", "Nottingham", "town", False, None, [], []),
    ("lincoln", "Lincoln", "city", False, None, [], ["beaumont"]),
    ("ravenspur", "Ravenspur", "fortress", True, None, [], []),
    ("york", "York", "city", False, None, ["clarence", "salisbury"], []),
    ("scarborough", "Scarborough", "town", True, "north", [], []),
    ("newcastle", "Newcastle", "city", True, "north", [], []),
    ("appleby", "Appleby", "town", False, "north", [], ["westmorland"]),
    ("lancaster", "Lancaster", "town", False, None, [], []),
    ("carlisle", "Carlisle", "city", False, "north",
        ["northumberland_lancastrian", "northumberland_1", "northumberland_2"], []),
    ("hexham", "Hexham", "town", False, "north", [], []),
    ("bamburgh", "Bamburgh", "fortress", False, "north", [], []),
    ("calais", "Calais", "special_stronghold", True, None,
        ["warwick_lancastrian", "warwick_yorkist"], []),
]

# Connections as stated from each Locale. (neighbor, way_type)
ADJ = {
    "truro": [("launceston", "road"), ("plymouth", "road")],
    "launceston": [("truro", "road"), ("plymouth", "road"), ("exeter", "road")],
    "plymouth": [("truro", "road"), ("launceston", "road"), ("exeter", "road")],
    "exeter": [("launceston", "road"), ("plymouth", "road"), ("dorchester", "road"),
               ("wells", "highway")],
    "dorchester": [("exeter", "road"), ("wells", "road"), ("salisbury", "road")],
    "wells": [("bristol", "road"), ("dorchester", "road"), ("exeter", "highway"),
              ("salisbury", "highway")],
    "salisbury": [("dorchester", "road"), ("newbury", "road"), ("southampton", "road"),
                  ("wells", "highway"), ("winchester", "highway")],
    "southampton": [("salisbury", "road"), ("winchester", "road"), ("arundel", "road")],
    "arundel": [("southampton", "road"), ("hastings", "road")],
    "winchester": [("southampton", "road"), ("salisbury", "highway"), ("guildford", "highway")],
    "guildford": [("winchester", "highway"), ("london", "highway")],
    "hastings": [("arundel", "road"), ("rochester", "road"), ("dover", "road")],
    "dover": [("hastings", "road"), ("canterbury", "road")],
    "canterbury": [("dover", "road"), ("rochester", "road")],
    "london": [("rochester", "road"), ("guildford", "highway"), ("oxford", "highway"),
               ("st_albans", "highway")],
    "rochester": [("canterbury", "road"), ("london", "road"), ("hastings", "road")],
    "bristol": [("wells", "road"), ("gloucester", "highway")],
    "newbury": [("salisbury", "road"), ("oxford", "road")],
    "oxford": [("newbury", "road"), ("northampton", "road"), ("gloucester", "highway"),
               ("london", "highway")],
    "st_albans": [("ipswich", "road"), ("london", "highway"), ("bedford", "highway"),
                  ("cambridge", "highway")],
    "bedford": [("cambridge", "road"), ("northampton", "highway"), ("st_albans", "highway")],
    "cambridge": [("bedford", "road"), ("bury_st_edmunds", "road"), ("st_albans", "highway"),
                  ("ely", "highway")],
    "bury_st_edmunds": [("norwich", "road"), ("cambridge", "road"), ("ely", "road"),
                        ("ipswich", "road")],
    "ipswich": [("st_albans", "road"), ("bury_st_edmunds", "road"), ("norwich", "road")],
    "norwich": [("ipswich", "road"), ("bury_st_edmunds", "road"), ("lynn", "road")],
    "ely": [("lynn", "road"), ("bury_st_edmunds", "road"), ("cambridge", "highway"),
            ("peterborough", "highway")],
    "lynn": [("norwich", "road"), ("ely", "road")],
    "peterborough": [("northampton", "road"), ("leicester", "road"), ("ely", "highway"), ("lincoln", "highway")],
    "northampton": [("oxford", "road"), ("coventry", "road"), ("peterborough", "road"),
                    ("bedford", "highway"), ("leicester", "highway")],
    "gloucester": [("cardiff", "road"), ("oxford", "highway"), ("hereford", "highway"),
                   ("bristol", "highway"), ("worcester", "highway")],
    "cardiff": [("gloucester", "road"), ("pembroke", "path")],
    "pembroke": [("cardiff", "path"), ("harlech", "path")],
    "harlech": [("pembroke", "path"), ("chester", "path")],
    "chester": [("shrewsbury", "road"), ("harlech", "path"), ("lancaster", "path"),
                ("york", "path")],
    "shrewsbury": [("chester", "road"), ("lichfield", "road"), ("ludlow", "road")],
    "ludlow": [("shrewsbury", "road"), ("worcester", "road"), ("hereford", "highway")],
    "hereford": [("ludlow", "highway"), ("gloucester", "highway")],
    "worcester": [("lichfield", "road"), ("ludlow", "road"), ("gloucester", "highway")],
    "coventry": [("lichfield", "road"), ("northampton", "road")],
    "lichfield": [("shrewsbury", "road"), ("worcester", "road"), ("coventry", "road"),
                  ("leicester", "road"), ("derby", "road")],
    "leicester": [("peterborough", "road"), ("lichfield", "road"), ("nottingham", "highway"),
                  ("northampton", "highway")],
    "derby": [("nottingham", "road"), ("lichfield", "road")],
    "nottingham": [("lincoln", "road"), ("derby", "road"), ("leicester", "highway")],
    "lincoln": [("ravenspur", "road"), ("nottingham", "road"), ("peterborough", "highway"),
                ("york", "highway")],
    "ravenspur": [("lincoln", "road"), ("york", "road")],
    "york": [("ravenspur", "road"), ("scarborough", "road"), ("lincoln", "highway"),
             ("newcastle", "highway"), ("chester", "path")],
    "scarborough": [("york", "road"), ("newcastle", "road")],
    "newcastle": [("hexham", "road"), ("scarborough", "road"), ("appleby", "road"),
                  ("bamburgh", "highway"), ("york", "highway")],
    "appleby": [("newcastle", "road"), ("carlisle", "road"), ("lancaster", "path")],
    "lancaster": [("chester", "path"), ("appleby", "path")],
    "carlisle": [("hexham", "road"), ("appleby", "road")],
    "hexham": [("carlisle", "road"), ("newcastle", "road")],
    "bamburgh": [("newcastle", "highway")],
    "calais": [],
}



# Edges declared from one endpoint only in the Map Reference (an internal
# inconsistency in the source). Recorded as disputed and EXCLUDED from the
# emitted ways pending user adjudication. See RULES_QUESTIONS.md Q-001.
# Previously-disputed Leicester edges were confirmed bidirectional by user
# adjudication (RULES_DECISIONS.md D-002); they are now reciprocated in ADJ
# and emitted normally. No pending asymmetric edges remain.
PENDING_ASYMMETRIC = set()


def main() -> int:
    ids = [row[0] for row in LOCALES]
    id_set = set(ids)
    assert len(ids) == len(id_set), "duplicate locale id"

    # Symmetry check: every (a, b, type) must also be declared as (b, a, type).
    problems = []
    declared = set()
    for a, nbrs in ADJ.items():
        if a not in id_set:
            problems.append(f"ADJ key not a locale: {a}")
        for b, t in nbrs:
            if b not in id_set:
                problems.append(f"{a} -> unknown neighbor {b}")
                continue
            declared.add((a, b, t))
    disputed = []
    for a, b, t in list(declared):
        if (b, a, t) not in declared:
            if (a, b, t) in PENDING_ASYMMETRIC or (b, a, t) in PENDING_ASYMMETRIC:
                disputed.append({"from": a, "to": b, "type": t})
                continue
            problems.append(f"asymmetric edge: {a}-{b} ({t}) not declared from {b}")
    # also flag same pair declared with two different types from the two sides
    if problems:
        for p in problems:
            print("  PROBLEM:", p)
        return 1

    # Dedupe to undirected edges (canonical ordering by id).
    pending_norm = {(min(a, b), max(a, b), t) for (a, b, t) in PENDING_ASYMMETRIC}
    edges = sorted(
        {(min(a, b), max(a, b), t) for (a, b, t) in declared}
        - pending_norm
    )
    ways = [{"from": a, "to": b, "type": t} for (a, b, t) in edges]

    locales = {}
    for lid, name, typ, port, region, lseats, vseats in LOCALES:
        entry = {"name": name, "type": typ, "port": port}
        if region:
            entry["region"] = region
        if lseats:
            entry["lord_seats"] = lseats
        if vseats:
            entry["vassal_seats"] = vseats
        locales[lid] = entry

    out = {
        "_source": "reference/Plantagenet Map Reference.txt",
        "_note": "Only land Ways (Road/Highway/Path) are encoded here. Sea movement is zone-based (see seas.json), not point-to-point, per Rules 4.6.1 / FAQ #1.",
    }
    locales_doc = {"_source": "reference/Plantagenet Map Reference.txt", **locales}

    base = Path("src/plantagenet/data/static")
    (base / "locales.json").write_text(json.dumps(locales_doc, indent=2) + "\n")
    out["disputed_pending_adjudication"] = sorted(
        {(min(a, b), max(a, b), t) for (a, b, t) in PENDING_ASYMMETRIC}
    )
    ways_doc = {"_meta": out, "ways": ways}
    (base / "ways.json").write_text(json.dumps(ways_doc, indent=2) + "\n")

    print(f"locales: {len(locales)}  undirected ways: {len(ways)}")
    by_type = {}
    for w in ways:
        by_type[w["type"]] = by_type.get(w["type"], 0) + 1
    print("ways by type:", by_type)
    return 0


if __name__ == "__main__":
    sys.exit(main())
