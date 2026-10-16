"""Reproducible end-to-end interface-output benchmark (soft budgets only).

Run from the repository root:
  git show 69f52db:scripts/chatgpt_play_helper.py > /tmp/old_helper.py
  PYTHONPATH=src:scripts python scripts/benchmark_llm_interface.py \
      --baseline /tmp/old_helper.py --out /tmp/interface-benchmark

Counts every explicitly emitted response AND request text, including added
menu pages, parameter-help, card/result inspections and all private Reset contributions. Return values are assigned, so neither
interface is charged an implicit notebook repr.
Baseline gets credit for its printed complete menu and short integer selections
where the exact action is offered: no extra browse requests.
All actions are predetermined test trajectories; no gameplay engine is patched.
Each pair must end in exactly the same complete engine state/history/RNG.
Session UUIDs derive from trajectory names solely for repeatable token counts;
no engine function, state, RNG, or decision is patched.

Optional tiktoken adds o200k_base token counts (a named proxy tokenizer, NOT a
claim about any particular ChatGPT deployment). Without it, bytes/characters
are exact and token fields are null. This script never asserts a hard budget.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import uuid
from collections import Counter
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import chatgpt_play_helper as nv  # noqa: E402
import llm_view  # noqa: E402

from plantagenet import actions, legal_moves, scenarios, static_data  # noqa: E402
from tests._helpers import fill_event_decisions, to_muster  # noqa: E402
from tests.test_card_lifecycle_2026_10 import campaign_reset_state  # noqa: E402
from tests.test_llm_interface import plan_state  # noqa: E402
from tests.test_reactions import _approach_setup  # noqa: E402


class Traffic:
    def __init__(self):
        self.calls = []

    def request(self, side, code, fn, *args, **kwargs):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = fn(*args, **kwargs)
        # Return values are assigned; only the explicit printed response is counted.
        self.calls.append({"side": side, "request": code, "output": out.getvalue()})
        return result

    def stats(self, tokenizer=None):
        def count(calls):
            response = "".join(c["output"] for c in calls)
            inputs = "\n".join(c["request"] for c in calls)
            return {"requests": len(calls), "output_chars": len(response),
                    "request_chars": len(inputs), "total_chars": len(response) + len(inputs),
                    "output_utf8_bytes": len(response.encode()),
                    "output_tokens": sum(len(tokenizer.encode(c["output"])) for c in calls) if tokenizer else None,
                    "request_tokens": sum(len(tokenizer.encode(c["request"])) for c in calls) if tokenizer else None,
                    "total_tokens": sum(len(tokenizer.encode(c["request"])) + len(tokenizer.encode(c["output"])) for c in calls) if tokenizer else None}
        return {**count(self.calls), "by_side": {side: count([c for c in self.calls if c["side"] == side])
                                               for side in ("lancastrian", "yorkist", "referee")}}


def materialize(state, move):
    if move["type"] == "build_plan":
        ids = [lid for lid, lord in state.lords.items() if lord.side == move["side"] and lord.status == "mustered"]
        n = state.campaign.cards_required
        # Explicit benchmark policy, NOT an interface default: repeated Lord
        # activations with a Pass first, exercising custom construction.
        plan = [{"pass": True}]
        for lid in reversed(ids):
            plan.extend([{"lord": lid}] * min(3, n - len(plan)))
        plan += [{"pass": True}] * (n - len(plan))
        return {"type": "build_plan", "side": move["side"], "plan": plan}
    if move["type"] == "play_event" and "decisions" not in move:
        return {**move, "decisions": fill_event_decisions(state, move["card"], move["side"])}
    return nv._clean(move)


def routine_sequence(state, limit):
    state = state.model_copy(deep=True)
    records = []
    musters = Counter()
    command = Counter()
    for _ in range(limit):
        if state.phase == "over":
            break
        raw = legal_moves.legal_moves(state.model_copy(deep=True))
        side = llm_view.decision_side(state)
        moves = [m for m in raw if m.get("side", side) == side]
        if not moves:
            break
        typ = {m["type"] for m in moves}
        if "end_campaign" in typ:
            break  # Reset has a dedicated, both-owner contribution benchmark
        if "end_muster" in typ:
            key = (state.turn_box, side)
            substantive = [m for m in moves if m["type"] in ("levy_troops", "levy_capability", "levy_transport", "parley", "play_held_event")]
            if musters[key] >= 5 or not substantive:
                move = next(m for m in moves if m["type"] == "end_muster")
            else:
                priorities = ("levy_capability", "parley", "levy_troops", "levy_transport", "play_held_event")
                wanted = priorities[musters[key] % len(priorities)]
                choices = [m for m in substantive if m["type"] == wanted] or substantive
                move = choices[-1]  # includes later pages, not only first-row selections
                musters[key] += 1
        elif "end_activation" in typ:
            key = (state.active_side, tuple(sorted(state.campaign.plan_index.items())))
            choices = [m for m in moves if m["type"] in ("forage", "supply", "tax", "parley")]
            if command[key] >= 2 or not choices:
                move = next(m for m in moves if m["type"] == "end_activation")
            else:
                move = choices[-1]
                command[key] += 1
        else:
            move = moves[-1]
        move = materialize(state, move)
        actions.apply_action(state, deepcopy(move))
        records.append(move)
    return records


def trajectories():
    opening = scenarios.build_initial_state("wars_of_the_roses", seed=20261016)
    middle = scenarios.build_initial_state("warwicks_rebellion", seed=23)
    to_muster(middle)
    planning = plan_state()
    battle, atk, _ = _approach_setup(seed=4)
    reset = campaign_reset_state()
    return [
        ("opening_levy_both_sides", opening, routine_sequence(opening, 15), "active"),
        ("muster_and_campaign_both_sides", middle, routine_sequence(middle, 50), "active"),
        ("custom_plans_sparse_activations", planning, routine_sequence(planning, 28), "active"),
        ("approach_reaction_and_battle", battle, [
            {"type": "march", "side": "yorkist", "by_lord": atk, "to": "lincoln"},
            {"type": "react", "side": "lancastrian", "pass": True}], "active"),
        ("private_campaign_reset", reset, [{"type": "end_campaign", "decisions": {
            "discard_held": {"yorkist": ["Y13"], "lancastrian": ["L11"]}}}], "yorkist"),
    ]


def load_baseline(path):
    spec = importlib.util.spec_from_file_location("plantagenet_benchmark_baseline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def emit(value):
    print(json.dumps(value, ensure_ascii=False, default=str))


def compare(name, initial, sequence, perspective, old, directory, tokenizer):
    legacy = Traffic()
    modern = Traffic()
    base_state = initial.model_copy(deep=True)
    new_state = initial.model_copy(deep=True)
    old._S.update(state=base_state, scenario=base_state.scenario, seed=base_state.seed,
                  history=[], findings=[], turn=0, transitions=0)
    side = llm_view.decision_side(initial)
    legacy_menu = legacy.request(side, "menu = nv.show()", old.show)
    # Stable pseudo-random-looking namespaces make transcripts/token counts
    # reproducible. This changes only the interface ID generator, never the game.
    session_id = uuid.UUID(hashlib.sha256(name.encode()).hexdigest()[:32])
    with patch.object(nv.uuid, "uuid4", return_value=session_id):
        modern.request(side, "overview = nv.attach(state, perspective=" + repr(perspective) + ")",
                       nv.attach, new_state, perspective=perspective)
    described = set()
    cards_seen = set()
    for a in sequence:
        side = a.get("side", llm_view.decision_side(new_state))
        typ = a["type"]
        before_legacy = base_state.model_dump_json()
        assert before_legacy == new_state.model_dump_json(), (name, typ, "pre-state mismatch")
        # Both interfaces are asked for identical full card text when a choice
        # first references a card. Baseline show only printed its ID.
        cid = a.get("card")
        if cid and cid not in cards_seen:
            legacy.request(side, f"print(static_data.load_cards()[{cid!r}])", emit,
                           static_data.load_cards()[cid])
            modern.request(side, f"info = nv.inspect('card', card={cid!r})", nv.inspect, "card", card=cid)
            cards_seen.add(cid)
        if typ == "end_campaign" and perspective != "referee":
            modern.request("yorkist", "ack = nv.stage_reset({'discard_held':['Y13']}, expected_version=nv.version())",
                           nv.stage_reset, {"discard_held": ["Y13"]}, expected_version=nv.version())
            modern.request("lancastrian", "overview = nv.set_perspective('lancastrian')", nv.set_perspective, "lancastrian")
            modern.request("lancastrian", "ack = nv.stage_reset({'discard_held':['L11']}, expected_version=nv.version())",
                           nv.stage_reset, {"discard_held": ["L11"]}, expected_version=nv.version())
        modern_side = nv._viewer()
        entries = [e for e in nv.all_actions() if e["action"]["type"] == typ]
        if len(entries) > 1:
            page = 1
            chosen = None
            kwargs = {"by_lord": a["by_lord"]} if "by_lord" in a else {}
            while chosen is None:
                code = f"page = nv.menu({typ!r}, page={page}, page_size=4, expected_version={nv.version()!r}, **{kwargs!r})"
                data = modern.request(modern_side, code, nv.menu, typ, page=page, page_size=4,
                                      expected_version=nv.version(), **kwargs)
                for entry in data["items"]:
                    sample = nv._clean(entry["action"])
                    if sample == a or (typ in ("play_event", "build_plan") and sample.get("side") == a.get("side")):
                        chosen = entry
                        break
                if chosen is None and data["next_page"] is None:
                    raise AssertionError((name, "chosen action not navigable", a))
                page += 1
        else:
            chosen = entries[0]
        if typ in ("build_plan", "play_event", "pay", "end_campaign", "march") and (side, typ) not in described:
            modern.request(modern_side, f"help = nv.describe({chosen['id']!r})", nv.describe, chosen["id"])
            described.add((side, typ))
        legacy_choice = next((i for i, sample in enumerate(legacy_menu or [])
                              if old._clean(sample) == a), deepcopy(a))
        legacy_menu = legacy.request(side, f"menu = nv.apply({legacy_choice!r})",
                                     old.apply, legacy_choice)
        parameters = {k: v for k, v in a.items() if k not in ("type", "side")
                      and nv._clean(chosen["action"]).get(k) != v}
        if typ == "end_campaign" and perspective != "referee":
            parameters = {}  # both private contributions already staged
        reply = modern.request(modern_side, f"receipt = nv.apply({chosen['id']!r}, parameters={parameters!r})",
                               nv.apply, chosen["id"], parameters=parameters)
        assert reply["kind"] == "result", (name, a, reply)
        assert base_state.model_dump_json() == new_state.model_dump_json(), (name, typ, "post-state mismatch")
        if typ == "react":
            # Tactical detail requested in addition to concise default receipts.
            legacy.request(side, "print(state.history[-1]['result'])", emit, base_state.history[-1]["result"])
            modern.request(side, "details = nv.inspect('result')", nv.inspect, "result")
    old_stats, new_stats = legacy.stats(tokenizer), modern.stats(tokenizer)
    result = {"name": name, "actions": len(sequence), "state_history_rng_identical": True,
              "baseline": old_stats, "new": new_stats,
              "output_char_reduction_pct": round(100 * (1 - new_stats["output_chars"] / old_stats["output_chars"]), 2),
              "total_char_reduction_pct": round(100 * (1 - new_stats["total_chars"] / old_stats["total_chars"]), 2)}
    (directory / f"{name}.baseline.json").write_text(json.dumps(legacy.calls, indent=2), encoding="utf-8")
    (directory / f"{name}.new.json").write_text(json.dumps(modern.calls, indent=2), encoding="utf-8")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    tokenizer = None
    try:
        import tiktoken
        tokenizer = tiktoken.get_encoding("o200k_base")
    except (ImportError, OSError):
        pass
    old = load_baseline(args.baseline)
    rows = [compare(*case, old, args.out, tokenizer) for case in trajectories()]
    summary = {"baseline_revision": "69f52dbab5280d5e18856316c4fbc7479bc9efe1",
               "tokenizer": "o200k_base" if tokenizer else None,
               "session_ids": "UUID derived from SHA256(trajectory name); interface-only, for reproducibility",
               "method": "All printed responses plus actual request code, including extra pages, help, card/result inspections and private Reset contributions. Return values assigned (no notebook echo). Equal full engine states after every action. Baseline receives its complete menu without extra requests and uses integer selections whenever offered. No output cap.",
               "sequences": rows}
    totals = {}
    for kind in ("baseline", "new"):
        totals[kind] = {key: sum(row[kind][key] for row in rows)
                        for key in ("requests", "output_chars", "request_chars", "total_chars")}
        if tokenizer:
            totals[kind].update({key: sum(row[kind][key] for row in rows)
                                for key in ("output_tokens", "request_tokens", "total_tokens")})
    summary["total"] = totals
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
