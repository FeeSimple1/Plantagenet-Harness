"""Parse the Arts of War Reference into cards.json.

Each card (Y1..Y37, L1..L37) has an EVENT (top half) and a CAPABILITY
(bottom half). The reference groups them by side (Yorkist/Lancastrian),
half (Events/Capabilities), and rose group (ALL=0, Ia/Ib/Ic=1, II=2,
III=3 — the scenario-number roses used for deck assembly, 6.0). Some cards
share text under a combined header (e.g. "Y3 & Y9", "Y1 & Y2"); the text is
applied to each listed id.

Stores verbatim Event/Capability text plus structured metadata: side, rose,
titles, the Event type tag (hold / this_levy / this_campaign / immediate),
and the Capability's eligible-Lords line. Effects are implemented in later
Phase-4 increments; this file is the data layer.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REF = Path("reference/Plantagenet Arts of War Reference.txt")
ROSE = {"ALL SCENARIOS": 0, "SCENARIOS Ia, Ib, & Ic": 1, "SCENARIO II": 2,
        "SCENARIOS III & III(B)": 3}
HEADER = re.compile(r"^([YL]\d+(?:\s*&\s*[YL]?\d+)*)\.\s+(.+)$")
SECTION = re.compile(r"^(YORKIST|LANCASTRIAN) (EVENTS|CAPABILITIES)")


def _expand_ids(raw: str, side: str) -> list[str]:
    out = []
    for part in re.split(r"\s*&\s*", raw):
        part = part.strip()
        if part and part[0] not in "YL":
            part = side[0] + part   # "Y9" written as "9" after the &
        out.append(part)
    return out


def _event_type(text: str) -> str:
    head = text.lstrip()
    if head.startswith("Hold"):
        return "hold"
    if head.startswith("This Levy"):
        return "this_levy"
    if head.startswith("This Campaign"):
        return "this_campaign"
    return "immediate"


def _lords_line(text: str) -> str | None:
    m = re.search(r"^Lords:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def main() -> int:
    lines = REF.read_text(encoding="utf-8").splitlines()
    cards: dict[str, dict] = {}
    side = kind = None
    rose = 0
    cur_ids: list[str] | None = None
    cur_title = ""
    buf: list[str] = []

    def flush():
        if not cur_ids:
            return
        text = "\n".join(buf).strip()
        for cid in cur_ids:
            c = cards.setdefault(cid, {"id": cid, "side": side, "rose": rose})
            c["rose"] = rose
            c["side"] = side
            if kind == "EVENTS":
                c["event"] = {"title": cur_title, "text": text, "type": _event_type(text)}
            else:
                c["capability"] = {"title": cur_title, "text": text,
                                   "lords": _lords_line(text)}

    for ln in lines:
        sm = SECTION.match(ln)
        if sm:
            flush()
            cur_ids = None
            side = "yorkist" if sm.group(1) == "YORKIST" else "lancastrian"
            kind = sm.group(2)
            rose = 0
            continue
        if ln.startswith("---- ") and ln.rstrip().endswith(" ----"):
            flush()
            cur_ids = None
            rose = ROSE.get(ln.strip().strip("- ").strip(), rose)
            continue
        hm = HEADER.match(ln)
        if hm and side and kind:
            flush()
            cur_ids = _expand_ids(hm.group(1), side)
            cur_title = hm.group(2).strip()
            buf = []
            continue
        if cur_ids is not None:
            buf.append(ln)
    flush()

    doc = {"_source": "reference/Plantagenet Arts of War Reference.txt (parsed). "
                      "Effects implemented in later Phase-4 increments.",
           "_rose": "0=no-rose (all scenarios), 1=I (Ia/Ib/Ic), 2=II, 3=III (6.0)."}
    for cid in sorted(cards, key=lambda x: (x[0], int(x[1:]))):
        doc[cid] = cards[cid]
    Path("src/plantagenet/data/static/cards.json").write_text(json.dumps(doc, indent=2) + "\n")

    real = [c for c in cards.values()]
    y = [c for c in real if c["side"] == "yorkist"]
    no_event = [c["id"] for c in real if "event" not in c]
    no_cap = [c["id"] for c in real if "capability" not in c]
    print(f"cards: {len(real)} (yorkist {len(y)}, lancastrian {len(real)-len(y)})")
    print(f"missing event: {no_event}")
    print(f"missing capability: {no_cap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
