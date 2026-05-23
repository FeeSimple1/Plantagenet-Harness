"""ChatGPT-in-sandbox play helper for the Plantagenet Harness.

Lets ChatGPT (GPT-5.x, etc.) play this harness in its own Python sandbox and
surface engine bugs -- no API key, no network. ChatGPT IS the player; this file
exposes start/show/apply/auto/findings_report/save and bakes in the bug
instrumentation (validated action palette + always-on board invariants + an
anomaly log).

Quick start (in the sandbox)::

    import sys; sys.path.insert(0, "src"); sys.path.insert(0, "scripts")
    import chatgpt_play_helper as nv
    nv.start("henry_vi", seed=1)      # pick a scenario id (nv.scenarios())
    nv.show()                         # active side's briefing + numbered moves
    nv.apply(0)                       # play move number 0
    ...
    nv.findings_report()              # the triage queue -- the goal of the run

This is the harness-agnostic template ported to Plantagenet. The PORTING guide
lives in CHATGPT_PLAY_PORTING_GUIDE.md. Everything below the ADAPTER block is
generic machinery; the ADAPTER block wires it to this engine.

NOTE on shape: unlike the generic template's ``{"type","args"}`` actions, the
Plantagenet enumerator emits *flat* action dicts (e.g.
``{"type":"parley","side":"yorkist","by_lord":"york","target":"lynn"}``) and
decides the active side itself, so ``legal_actions_for_side`` ignores its
``side`` argument and returns the engine's moves verbatim. The 4.1 Plan
(``build_plan``) is a free construction; the adapter expands it into one
concrete, ready-to-apply default plan and tells the player how to submit a
custom one via a raw action dict.
"""

from __future__ import annotations

import json
import sys
import traceback

# ===================== ADAPTER -- Plantagenet =====================
sys.path.insert(0, "src")

from plantagenet import actions, legal_moves, render, static_data  # noqa: E402
from plantagenet import invariants as _invariants_mod  # noqa: E402
from plantagenet.errors import IllegalAction  # noqa: E402
from plantagenet.scenarios import build_initial_state, renew_war  # noqa: E402
from plantagenet.state import GameState, LordStatus  # noqa: E402

# Exception type(s) that mean "this action was illegal" (NOT a crash).
ILLEGAL_EXCEPTIONS = (IllegalAction,)

# Display-only / internal keys never passed to apply_action.
_NON_ACTION_KEYS = {"note", "cards_required"}


def scenario_ids():
    """All playable scenario ids (start with a short one, e.g. 'henry_vi')."""
    return static_data.list_scenario_ids()


def load_scenario(scenario_id, seed=1):
    return build_initial_state(scenario_id, seed=seed)


def active_side(state):
    return state.active_side


def is_terminal(state):
    return state.phase == "over"


def determine_winner(state):
    return state.victory


def deep_copy(state):
    """Independent copy whose mutation cannot perturb `state`. Safe because the
    RNG lives in the state (seed + rng_state), so probing only advances the
    copy's dice -- the prerequisite for the validated palette."""
    return state.model_copy(deep=True)


def setup_actions(state):
    """build_initial_state is fully set up; no post-load confirmations needed."""
    return []


def briefing_for_side(state, side):
    """Full-board briefing. The player controls BOTH sides, so showing the whole
    position is correct here (and Plantagenet has no per-side hidden board
    state beyond drawn-card hands, which render_summary omits)."""
    head = (f"[active side: {side} | phase: {state.phase} | "
            f"levy step: {state.levy_step}]")
    return head + "\n" + render.render_summary(state)


def _default_plan(state, side, n):
    """A minimal legal 4.1 Plan: activate this side's Mustered Lords, padding
    with Pass to the required card count."""
    lords = [lid for lid, v in state.lords.items()
             if v.side == side and v.status == LordStatus.MUSTERED]
    plan = [{"lord": lid} for lid in lords][:n]
    while len(plan) < n:
        plan.append({"pass": True})
    return plan


def _expand(state, mv):
    """Expand a templated move into a concrete, apply-ready action. Currently
    only build_plan (a free construction) is templated: fill a default plan and
    annotate how to customize it."""
    if mv.get("type") == "build_plan" and "plan" not in mv:
        side = mv["side"]
        n = mv.get("cards_required", 0)
        mustered = [lid for lid, v in state.lords.items()
                    if v.side == side and v.status == LordStatus.MUSTERED]
        note = (f"default plan = activate {mustered} padded with Pass to "
                f"{n} cards. To customize, apply a raw dict: "
                f'{{"type":"build_plan","side":"{side}","plan":[{{"lord":"<id>"}}'
                f', {{"pass":true}}, ...]}} ({n} entries).')
        return {**mv, "plan": _default_plan(state, side, n), "note": note}
    if mv.get("type") == "play_event" and "decisions" not in mv:
        # A drawn immediate Event (3.1.3). Deterministic Events resolve with no
        # decisions; selection Events (e.g. Warwick's Propaganda) need a choice,
        # supplied as a raw dict so the player -- not a default -- chooses.
        note = ('resolve this drawn Event. Deterministic Events: apply as-is. '
                'Selection Events need decisions, e.g. a raw dict '
                f'{{"type":"play_event","side":"{mv.get("side")}",'
                f'"card":"{mv.get("card")}","decisions":{{...}}}}.')
        return {**mv, "note": note}
    return mv


def legal_actions_for_side(state, side):
    """Engine-driven; `side` is ignored (Plantagenet picks the active side and
    each move carries its own side). build_plan templates are expanded."""
    return [_expand(state, mv) for mv in legal_moves.legal_moves(state)]


def invariants(state):
    """Always-on board invariants as human-readable strings ([] = OK)."""
    return [f"{v.get('kind', 'invariant')}:"
            + json.dumps({k: x for k, x in v.items() if k != 'kind'}, default=str)
            for v in _invariants_mod.board_invariant_violations(state)]


VALIDATE = True  # validated palette on (deep_copy isolates the in-state RNG)
# ===================== END ADAPTER =====================

_S = {"state": None, "scenario": None, "seed": 1,
      "history": [], "findings": [], "turn": 0, "transitions": 0}


def _clean(a):
    """Strip display-only/internal keys before handing an action to the engine."""
    return {k: v for k, v in a.items()
            if k not in _NON_ACTION_KEYS and not k.startswith("_")}


def _concrete(side):
    acts = legal_actions_for_side(_S["state"], side)
    return [a for a in acts if isinstance(a, dict)]


def _validated(side, log_rejects=True):
    """LLM-safe menu: probe each candidate on a deep copy and keep only those
    the handler accepts; log filtered ones as over-enumeration diagnostics (the
    root enumerator bug to fix, not just hide)."""
    cands = _concrete(side)
    if not VALIDATE:
        return cands
    out = []
    for a in cands:
        if a.get("type") == "play_event" and "decisions" not in a:
            out.append(a)          # decisions template: keep, don't probe-reject
            continue
        minimal = _clean(a)
        probe = deep_copy(_S["state"])
        try:
            apply_action_local(probe, minimal)
            out.append(a)
        except ILLEGAL_EXCEPTIONS as e:
            if log_rejects:
                _S["findings"].append({"kind": "over_enum_filtered",
                                       "turn": _S["turn"], "side": side,
                                       "action": minimal, "code": getattr(e, "code", ""),
                                       "msg": str(e)[:160]})
        except Exception as e:
            if log_rejects:
                _S["findings"].append({"kind": "exception_in_probe",
                                       "turn": _S["turn"], "side": side,
                                       "action": minimal,
                                       "etype": type(e).__name__, "msg": str(e)[:200]})
    return out


def apply_action_local(state, action):
    """Thin pass-through so the probe and the real apply share one entry point."""
    return actions.apply_action(state, action)


def _check_invariants():
    bad = []
    try:
        bad = invariants(_S["state"]) or []
    except Exception as e:
        _S["findings"].append({"kind": "invariant_crash", "turn": _S["turn"],
                               "error": f"{type(e).__name__}: {e}"[:200]})
    for v in bad:
        _S["findings"].append({"kind": "invariant", "turn": _S["turn"],
                               "violation": v})
    return bad


def start(scenario, seed=1):
    ids = scenario_ids()
    if scenario not in ids:
        raise ValueError(f"unknown scenario {scenario!r}; choose from {ids}")
    s = load_scenario(scenario, seed=seed)
    for a in setup_actions(s):
        try:
            apply_action_local(s, _clean(a))
        except Exception:
            pass
    _S.update(state=s, scenario=scenario, seed=seed,
              history=[], findings=[], turn=0, transitions=0)
    print(f"started {scenario} (seed={seed}). Call nv.show().")
    return show()


def scenarios():
    print("scenarios:", scenario_ids())
    return scenario_ids()


def _maybe_renew():
    """Grand scenario: a decisive War victory continues into the next War."""
    s = _S["state"]
    if s.grand_scenario and (s.victory or {}).get("result") in ("lancastrian", "yorkist"):
        try:
            _S["state"] = renew_war(s)
            _S["transitions"] += 1
            print(f"--- War concluded; renewed to next War "
                  f"(transition #{_S['transitions']}). ---")
            return True
        except IllegalAction:
            return False  # final War concluded -> whole game over
    return False


def show():
    s = _S["state"]
    if is_terminal(s):
        if _maybe_renew():
            return show()
        print("GAME OVER:", determine_winner(s))
        return []
    side = active_side(s)
    acts = _validated(side)
    print(f"\n===== turn {_S['turn']} | active: {side} =====")
    print(briefing_for_side(s, side))
    print(f"\nLEGAL ACTIONS ({len(acts)}):")
    for i, a in enumerate(acts):
        params = {k: v for k, v in a.items() if k not in ("type", "note")}
        line = f"  [{i}] {a.get('type', '?')} {json.dumps(params, default=str)}"
        if a.get("note"):
            line += f"\n        // {a['note']}"
        print(line)
    if not acts:
        _S["findings"].append({"kind": "no_legal_moves", "turn": _S["turn"],
                               "side": side})
        print("!! no legal moves (stall) -- recorded")
    return acts


def _classify(action, acts):
    """How much the engine vouches for a submitted action, so apply() can tell a
    real enumerator/handler bug from an ordinary player mistake:

    - "vouched": this exact action is on the current validated menu (always true
      for an index pick). An IllegalAction here is a genuine validator/handler
      divergence -> notable.
    - "template": a build_plan free-construction while a build_plan template is
      offered. The engine vouches the *template*, not a specific plan, so a bad
      plan is player error and a good one is unremarkable.
    - "offmenu": not currently offered at all. Rejected -> player mistake; but if
      the handler *accepts* it, the menu under-enumerated a legal move -> notable.
    """
    if action.get("type") in ("build_plan", "play_event"):
        if any(a.get("type") == action.get("type") and a.get("side") == action.get("side")
               for a in acts):
            return "template"
        return "offmenu"
    for a in acts:
        if _clean(a) == action:
            return "vouched"
    return "offmenu"


def apply(choice):
    s = _S["state"]
    side = active_side(s)
    acts = _validated(side, log_rejects=False)
    if isinstance(choice, int):
        if not (0 <= choice < len(acts)):
            print(f"index {choice} out of range; pass a valid index or an action dict")
            return show()
        action = _clean(acts[choice])
        # A play_event with no decisions is a template (selection Events need a
        # choice); a bare apply that the engine rejects is player error, not a
        # vouched-move divergence.
        cls = ("template" if action.get("type") == "play_event"
               and "decisions" not in action else "vouched")
    elif isinstance(choice, dict):
        action = _clean(choice)
        cls = _classify(action, acts)
    else:
        raise TypeError("choice must be an int index or an action dict")
    try:
        apply_action_local(s, action)
    except ILLEGAL_EXCEPTIONS as e:
        if cls == "vouched":
            # the validated menu vouched this exact move but apply rejected it:
            # a genuine validator/handler divergence (the bug class we hunt).
            _S["findings"].append({"kind": "illegal_action", "turn": _S["turn"],
                                   "side": side, "action": action,
                                   "code": getattr(e, "code", ""), "msg": str(e)[:160]})
            print(f"!! ILLEGAL -- engine divergence (recorded): {str(e)[:160]}")
        else:
            # a move not on the current menu (raw dict / bad custom plan): an
            # ordinary player mistake, not an engine defect -- non-notable.
            _S["findings"].append({"kind": "player_illegal", "turn": _S["turn"],
                                   "side": side, "action": action,
                                   "code": getattr(e, "code", ""), "msg": str(e)[:160]})
            print(f"not a currently-legal move ({getattr(e, 'code', '')}); "
                  f"call nv.show() for the current menu.")
        return show()
    except Exception as e:
        _S["findings"].append({"kind": "exception", "turn": _S["turn"],
                               "side": side, "action": action,
                               "etype": type(e).__name__, "msg": str(e)[:200],
                               "tb": traceback.format_exc()[-700:]})
        print(f"!! EXCEPTION (recorded): {type(e).__name__}: {e}")
        return
    if cls == "offmenu":
        # the handler accepted a move the menu never offered: under-enumeration
        # (the enumerator missed a legal move) -- a real engine defect.
        _S["findings"].append({"kind": "under_enum_accepted", "turn": _S["turn"],
                               "side": side, "action": action})
        print("note: applied a LEGAL move that was not on the menu "
              "(under-enumeration; recorded).")
    _S["history"].append({"turn": _S["turn"], "side": side, "action": action})
    _S["turn"] += 1
    if _check_invariants():
        print("!! INVARIANT VIOLATION (recorded)")
    print(f"applied: {action.get('type')} ({action.get('side', side)})")
    return show()


def auto(max_steps=300):
    """Auto-apply purely-forced turns (exactly one legal action) so you skip
    boilerplate; stop at the next real choice or game end."""
    s = _S["state"]
    n = 0
    while n < max_steps:
        s = _S["state"]
        if is_terminal(s):
            if _maybe_renew():
                continue
            break
        side = active_side(s)
        acts = _validated(side)
        if len(acts) != 1:
            break
        action = _clean(acts[0])
        try:
            apply_action_local(s, action)
        except Exception as e:
            _S["findings"].append({"kind": "exception", "turn": _S["turn"],
                                   "side": side, "action": action,
                                   "etype": type(e).__name__, "msg": str(e)[:200],
                                   "tb": traceback.format_exc()[-700:]})
            print(f"!! EXCEPTION during auto (recorded): {type(e).__name__}: {e}")
            return
        _S["history"].append({"turn": _S["turn"], "side": side, "action": action})
        _S["turn"] += 1
        n += 1
        _check_invariants()
    print(f"auto-advanced {n} forced turn(s).")
    return show()


def findings_report():
    notable = [f for f in _S["findings"] if f["kind"] in (
        "illegal_action", "over_enum_filtered", "under_enum_accepted",
        "exception", "exception_in_probe", "no_legal_moves",
        "invariant", "invariant_crash")]
    # player_illegal (an off-menu move the engine correctly rejected) is a
    # player mistake, not an engine defect -- kept in the log but not notable.
    print(f"\n===== FINDINGS: {len(_S['findings'])} total, "
          f"{len(notable)} notable =====")
    for f in notable:
        print("  ", json.dumps(f, default=str)[:240])
    if not notable:
        print("  (none -- no engine anomalies on this trajectory)")
    return _S["findings"]


def save(path="chatgpt_game.json"):
    import pathlib
    s = _S["state"]
    blob = getattr(s, "model_dump_json", None)
    data = {"scenario": _S["scenario"], "seed": _S["seed"],
            "history": _S["history"], "findings": _S["findings"],
            "transitions": _S["transitions"],
            "state_json": blob() if blob else None}
    pathlib.Path(path).write_text(json.dumps(data, indent=2, default=str))
    print("saved ->", path)


def load(path="chatgpt_game.json"):
    """Restore a checkpoint written by save() (sandbox resets are ephemeral)."""
    import pathlib
    data = json.loads(pathlib.Path(path).read_text())
    _S.update(state=GameState.model_validate_json(data["state_json"]),
              scenario=data["scenario"], seed=data.get("seed", 1),
              history=data["history"], findings=data["findings"],
              turn=len(data["history"]), transitions=data.get("transitions", 0))
    print(f"loaded <- {path} ({_S['scenario']}, {_S['turn']} turns played)")
    return show()
