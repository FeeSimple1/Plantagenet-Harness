"""Replay a recorded playthrough log against the current engine.

Parses the LLM-readable chronological log format (### Step N blocks with
Context / Action / Result lines), reconstructs each action by matching the
parsed intent against legal_moves() at the recorded state, applies it, and
compares the engine's result against the recorded Result line. Gaps in the
step numbering are War transitions (renew_war).

Usage: PYTHONPATH=src python scripts/replay_log.py tests/data/<log>.md \
           [-v] [--waive N,N,...]
A waived step is a KNOWN recorded-run bug: the harness asserts the recorded
action is (still) not offered by the current engine, skips it, and continues.

Vintage accommodation (--auto-culverins): the engine that produced the log
auto-fired the Culverins and Falconets Capability for every holder on both
sides of a Battle; the current engine makes firing an explicit decision
(4.4.1 "may"). With the flag, a march into Battle carries a culverins
decision for all capability holders present, replicating the recorded dice.
Exit code 0 = full replay; every compared oracle field matched and only
waived steps diverged.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

sys.path.insert(0, "src")
from plantagenet import actions, legal_moves, ratings  # noqa: E402
from plantagenet.scenarios import build_initial_state, renew_war  # noqa: E402


def norm(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def parse_log(path: str) -> tuple[str, int, list[dict[str, Any]]]:
    text = open(path, encoding="utf-8").read()
    scenario = re.search(r"- Scenario: `(\w+)`", text).group(1)
    seed = int(re.search(r"- Seed: `(\d+)`", text).group(1))
    steps = []
    for m in re.finditer(
            r"### Step (\d+)\n- Context: ([^\n]*)\n- Action: ([^\n]*)\n- Result: ([^\n]*)",
            text):
        steps.append({"n": int(m.group(1)), "ctx": m.group(2),
                      "action": m.group(3), "result": m.group(4)})
    return scenario, seed, steps


SIDE = {"yorkist": "yorkist", "lancastrian": "lancastrian"}


def intent(action: str) -> dict[str, Any]:
    """Parse an Action line into a move-matching intent."""
    a = action.strip()
    m = re.match(r"^(Yorkist|Lancastrian) draws Arts of War$", a)
    if m:
        return {"type": "draw", "side": norm(m.group(1))}
    m = re.match(r"^(Yorkist|Lancastrian) ends muster$", a)
    if m:
        return {"type": "end_muster", "side": norm(m.group(1))}
    m = re.match(r"^(Yorkist|Lancastrian) ends activation$", a)
    if m:
        return {"type": "end_activation", "side": norm(m.group(1))}
    m = re.match(r"^(Yorkist|Lancastrian) pays troops/lords$", a)
    if m:
        return {"type": "pay", "side": norm(m.group(1))}
    if a == "Begin campaign segment":
        return {"type": "begin_campaign"}
    if a == "End campaign segment":
        return {"type": "end_campaign"}
    m = re.match(r"^(Yorkist|Lancastrian) plays event ([YL]\d+)$", a)
    if m:
        return {"type": "play_event", "side": norm(m.group(1)), "card": m.group(2)}
    m = re.match(r"^(Yorkist|Lancastrian) builds plan: (.*)$", a)
    if m:
        entries = [e.strip() for e in m.group(2).split(",")]
        plan = [{"pass": True} if e in ("—", "-") else {"lord": norm(e)} for e in entries]
        return {"type": "build_plan", "side": norm(m.group(1)), "plan": plan}
    m = re.match(r"^(.+?) levies capability ([YL]\d+)$", a)
    if m:
        return {"type": "levy_capability", "by_lord": norm(m.group(1)), "card": m.group(2)}
    m = re.match(r"^(.+?) levies troops$", a)
    if m:
        return {"type": "levy_troops", "by_lord": norm(m.group(1))}
    m = re.match(r"^(.+?) levies (cart|ship) transport$", a)
    if m:
        return {"type": "levy_transport", "by_lord": norm(m.group(1)),
                "transport": m.group(2)}
    m = re.match(r"^(.+?) attempts to levy lord (.+)$", a)
    if m:
        return {"type": "levy_lord", "by_lord": norm(m.group(1)), "target": norm(m.group(2))}
    m = re.match(r"^(.+?) marches to (.+)$", a)
    if m:
        return {"type": "march", "by_lord": norm(m.group(1)), "to": norm(m.group(2))}
    m = re.match(r"^(.+?) supplies from (.+)$", a)
    if m:
        return {"type": "supply", "by_lord": norm(m.group(1)), "source": norm(m.group(2))}
    m = re.match(r"^(.+?) parleys (.+)$", a)
    if m:
        return {"type": "parley", "by_lord": norm(m.group(1)), "target": norm(m.group(2))}
    m = re.match(r"^(.+?) taxes (.+)$", a)
    if m:
        return {"type": "tax", "by_lord": norm(m.group(1)), "target": norm(m.group(2))}
    m = re.match(r"^(.+?) sails to (.+)$", a)
    if m:
        return {"type": "sail", "by_lord": norm(m.group(1)), "to": norm(m.group(2))}
    m = re.match(r"^(.+?) forages$", a)
    if m:
        return {"type": "forage", "by_lord": norm(m.group(1))}
    m = re.match(r"^(.+?) uses Agitators at (.+)$", a)
    if m:
        return {"type": "agitators", "by_lord": norm(m.group(1)), "target": norm(m.group(2))}
    raise ValueError(f"unrecognised action line: {a!r}")


def match_move(moves: list[dict[str, Any]], it: dict[str, Any]) -> dict[str, Any]:
    """The unique legal move consistent with the parsed intent."""
    if it["type"] == "build_plan":
        tmpl = [mv for mv in moves if mv["type"] == "build_plan" and mv["side"] == it["side"]]
        if not tmpl:
            raise LookupError("no build_plan template offered")
        return {"type": "build_plan", "side": it["side"], "plan": it["plan"]}
    cands = [mv for mv in moves
             if all(mv.get(k) == v for k, v in it.items())]
    if len(cands) > 1:                       # e.g. solo vs group march: prefer solo
        slim = [mv for mv in cands if "group" not in mv and not mv.get("use_ships")]
        if len(slim) == 1:
            cands = slim
    if len(cands) == 1:
        mv = dict(cands[0])
        # The enumerator attaches available battle reactions to the move; the
        # recorded log carries no reaction plays, so the replay strips them
        # (playing none is always legal).
        mv.pop("battle_reactions", None)
        return mv
    raise LookupError(f"{len(cands)} candidates for {it}")


def main() -> int:
    path = sys.argv[1]
    verbose = "-v" in sys.argv
    waived: set[int] = set()
    if "--waive" in sys.argv:
        waived = {int(x) for x in sys.argv[sys.argv.index("--waive") + 1].split(",")}
    auto_cul = "--auto-culverins" in sys.argv
    scenario, seed, steps = parse_log(path)
    state = build_initial_state(scenario, seed=seed)
    prev_n = 0
    divergences = []
    for st in steps:
        while st["n"] > prev_n + 1:          # numbering gap = War transition
            prev_n += 1
            state = renew_war(state)
            if verbose:
                print(f"-- step {prev_n}: renew_war -> {state.grand_scenario['current_war']}")
        prev_n = st["n"]
        it = intent(st["action"])
        moves = legal_moves.legal_moves(state)
        if st["n"] in waived:
            try:
                match_move(moves, it)
            except LookupError:
                print(f"step {st['n']}: WAIVED (recorded action not offered, as expected): "
                      f"{st['action']!r}")
                continue
            print(f"step {st['n']}: STALE WAIVER — the action IS offered now")
            return 2
        try:
            mv = match_move(moves, it)
        except LookupError as e:
            print(f"step {st['n']}: NO MATCH {e} | action={st['action']!r}")
            return 2
        if auto_cul and it["type"] == "march":
            cul = _culverins_holders(state, it["by_lord"], it["to"])
            if cul:
                mv = {**mv, "decisions": {"culverins": cul}}
        res = actions.apply_action(state, mv)
        d = compare(st, res)
        if d:
            divergences.append((st["n"], d))
            print(f"step {st['n']}: DIVERGE {d}")
            if verbose:
                print("   recorded:", st["result"])
                print("   engine  :", json.dumps(res, default=str)[:400])
    print(f"replayed {len(steps)} actions, {len(divergences)} divergences")
    return 1 if divergences else 0


def _culverins_holders(state: Any, mover: str, dest: str) -> list[str]:
    """Mover + enemy Lords at the destination holding Culverins (vintage
    auto-fire; see module docstring)."""
    mside = state.lords[mover].side
    out = []
    for lid, ls in state.lords.items():
        present = lid == mover or (ls.status == "mustered" and ls.location == dest
                                   and ls.side != mside)
        if present and ratings.has_capability(state, lid, "CULVERINS AND FALCONETS"):
            out.append(lid)
    return out


def compare(st: dict[str, Any], res: dict[str, Any]) -> str | None:
    """Compare the recorded Result line against the engine result for the
    strongest (RNG-dependent) oracle fields. Returns a description or None."""
    rec, t = st["result"], intent(st["action"])["type"]
    if t == "draw":
        m = re.search(r"drew ([^;]*)", rec)
        want = [c.strip() for c in m.group(1).split(",")]
        if res.get("drawn") != want:
            return f"drawn {res.get('drawn')} != {want}"
    elif t == "levy_lord":
        m = re.search(r"success=(\w+); roll=(\d+) vs rating (\d+); spent=(\d+)", rec)
        if m and (str(res.get("success")) != m.group(1) or str(res.get("roll")) != m.group(2)
                  or str(res.get("spent")) != m.group(4)):
            return f"levy_lord {res} != {rec}"
    elif t == "pay":
        for key in ("paid_groups", "unpaid_disbanded", "influence_paid"):
            m = re.search(rf"{key}=(\[[^\]]*\]|\d+)", rec)
            if m:
                want = eval(m.group(1))      # noqa: S307 - trusted log literal
                got = _dig(res, key)
                if got != want:
                    return f"{key} {got} != {want}"
    elif t == "march":
        m = re.search(r"winner=(\w+); deaths=([^;]*); disbands=([^;]*);", rec)
        if m:
            b = (res.get("battle") or (res.get("approach") or {}).get("battle") or {})
            want_w = None if m.group(1) == "none" else norm(m.group(1))
            got_w = b.get("winner_side")
            def names(s: str) -> list[str]:
                return [] if s.strip() == "none" else [norm(x) for x in s.split(",")]
            if (got_w != want_w or b.get("deaths") != names(m.group(2))
                    or b.get("disbands") != names(m.group(3))):
                return f"battle {got_w}/{b.get('deaths')}/{b.get('disbands')} != {rec}"
    elif t == "end_campaign":
        m = re.search(r"VICTORY: (\w+) by rule ([\d.]+)", rec)
        if m:
            v = (res.get("victory") or {})
            if norm(m.group(1)) != v.get("result") or m.group(2) != str(v.get("rule", "")):
                return f"victory {v} != {rec}"
        m = re.search(r"Tides=(\{[^}]*\})", rec)
        if m and res.get("tides") is not None:
            if res.get("tides") != eval(m.group(1)):   # noqa: S307
                return f"tides {res.get('tides')} != {m.group(1)}"
    return None


def _dig(res: dict[str, Any], key: str) -> Any:
    if key in res:
        return res[key]
    for v in res.values():
        if isinstance(v, dict) and key in v:
            return v[key]
    return None


if __name__ == "__main__":
    sys.exit(main())
