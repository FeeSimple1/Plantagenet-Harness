"""Independent reciprocity sweep of the Map Reference prose.

Parses the connection sentences directly from
`reference/Plantagenet Map Reference.txt` (NOT from the generated
ways.json) and reports any one-sided land edge: Locale A names B as a
connection but B does not name A back (or names it with a different Way
type). Read-only: reports, does not modify data.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Display-name -> id, taken from the map builder's canonical list.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_map_data import LOCALES  # noqa: E402

NAME_TO_ID = {name: lid for (lid, name, *_rest) in LOCALES}
# Longest names first so "Bury St. Edmunds" matches before "St. Albans" etc.
NAMES_BY_LEN = sorted(NAME_TO_ID, key=len, reverse=True)
WAY_RE = re.compile(r"\bby (Road|Highway|Path)\b")
SRC_RE = re.compile(r"\bof ([A-Z][\w. ]+?)(?= \(| is connected)")
REF = Path("reference/Plantagenet Map Reference.txt")


def parse_line(line: str):
    """Yield (src_id, dst_id, way) directed edges stated in one line."""
    if "is connected to" not in line:
        return
    m = SRC_RE.search(line)
    if not m:
        return
    src_name = m.group(1).strip()
    if src_name not in NAME_TO_ID:
        return
    src = NAME_TO_ID[src_name]
    conn = line[line.index("is connected to"):]
    prev = 0
    for wm in WAY_RE.finditer(conn):
        chunk = conn[prev:wm.start()]
        prev = wm.end()
        way = wm.group(1).lower()
        remaining = chunk
        for name in NAMES_BY_LEN:
            if name == src_name:
                continue
            if name in remaining:
                yield (src, NAME_TO_ID[name], way)
                remaining = remaining.replace(name, " " * len(name))


def main() -> int:
    text = REF.read_text()
    directed: set[tuple[str, str, str]] = set()
    for line in text.splitlines():
        for edge in parse_line(line):
            directed.add(edge)

    one_sided = []
    type_mismatch = []
    for a, b, t in sorted(directed):
        if (b, a, t) not in directed:
            # Same pair declared with a different way type from the other side?
            other = [tt for (x, y, tt) in directed if {x, y} == {a, b}]
            if t not in other or any(tt != t for tt in other if (b, a, tt) in directed):
                if any((b, a, tt) in directed and tt != t for tt in other):
                    type_mismatch.append((a, b, t))
                else:
                    one_sided.append((a, b, t))

    print(f"Parsed {len(directed)} directed edge statements "
          f"({len(directed)//2} reciprocal pairs expected).")
    if one_sided:
        print("\nONE-SIDED EDGES (A names B, B does not name A back):")
        for a, b, t in one_sided:
            print(f"  {a} -> {b} ({t})")
    if type_mismatch:
        print("\nWAY-TYPE MISMATCHES (both name each other but disagree on type):")
        for a, b, t in type_mismatch:
            print(f"  {a} -> {b} ({t})")
    if not one_sided and not type_mismatch:
        print("\nNo one-sided edges or type mismatches. Map Reference is fully reciprocal.")
    return 1 if (one_sided or type_mismatch) else 0


if __name__ == "__main__":
    sys.exit(main())
