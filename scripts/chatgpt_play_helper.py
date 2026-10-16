"""Token-efficient, instrumented Plantagenet play interface.

    import chatgpt_play_helper as nv
    nv.start('henry_vi', seed=1)           # compact baseline + category counts
    page = nv.menu(action_type='draw')    # stable, state-bound IDs
    nv.apply(page['items'][0]['id'])       # result/delta + next category counts
    nv.describe('build_plan')             # constraints, never a prescribed plan
    nv.apply({...}, expected_version=nv.version())  # any custom engine action

show/menu/inspect/describe are READ ONLY. No inspection renews a War. Full
programmatic menus remain available through all_actions(); no output budget
limits legal choices. Use perspective='active' for both-side self-play (each
handoff emits a fresh baseline), a fixed side for player-restricted output, or
explicit perspective='referee' for trusted omniscient inspection. Save files
are trusted referee artifacts, NOT files to send to an opposing player.
"""
from __future__ import annotations

import hashlib
import inspect as _inspect
import json
import sys
import traceback
import uuid
from collections import Counter
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import llm_action_help as _help  # noqa: E402
import llm_view as _view  # noqa: E402

from plantagenet import actions, legal_moves, render, static_data  # noqa: E402
from plantagenet import invariants as _inv  # noqa: E402
from plantagenet.errors import IllegalAction  # noqa: E402
from plantagenet.scenarios import build_initial_state  # noqa: E402
from plantagenet.state import GameState  # noqa: E402

VALIDATE = True
SOFT_OUTPUT_CHARS = None  # advisory only: never truncates a result or excludes a choice
_NON_ACTION_KEYS = {"note", "cards_required", "discard_held_options", "battle_reactions"}
_S = {"state": None, "scenario": None, "seed": 1, "history": [], "findings": [],
      "turn": 0, "transitions": 0, "perspective": "active", "epoch": "", "revision": 0,
      "fingerprint": None, "catalog": None, "baseline": None, "receipts": [],
      "reset_choices": {}, "reset_fingerprint": None}


class Reply(dict):
    """Do not accidentally echo a full menu/result at the end of a notebook cell.

    This is an ordinary dict for programmatic access; repr is deliberately short.
    The explicit display (which can be captured/measured) contains the useful text.
    """
    def __repr__(self):
        return f"<Reply {self.get('kind', 'data')} version={self.get('version', '-')} (programmatic fields retained)>"


class StaleSelectionError(ValueError):
    pass


def _json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


def _emit(text):
    print(text)
    if SOFT_OUTPUT_CHARS is not None and len(text) > SOFT_OUTPUT_CHARS:
        print(f"[Soft budget {SOFT_OUTPUT_CHARS} chars exceeded; nothing truncated. Use filters/pages for detail.]")


def _state():
    if _S["state"] is None:
        raise RuntimeError("Call start(scenario, seed=...) or load(path) first.")
    return _S["state"]


def _fingerprint():
    # Includes RNG and history; never exposed to players (hashing a secret card
    # value into a public ID would permit dictionary attacks). IDs use counters.
    return hashlib.sha256(_state().model_dump_json().encode()).hexdigest()


def _touch():
    _S["revision"] += 1
    _S["catalog"] = None
    _S["fingerprint"] = _fingerprint()


def _sync():
    fp = _fingerprint()
    if fp != _S["fingerprint"]:
        # Referee/test code can change _S['state'] directly. Never reuse IDs after
        # such an edit, and require a baseline rather than computing a fake delta.
        _touch()
        _S["baseline"] = None
        _S["reset_choices"] = {}
    return f"v{_S['epoch']}.{_S['revision']}"


def version():
    """Current opaque version. Raw custom actions must carry this expectation."""
    return _sync()


def _viewer():
    p = _S["perspective"]
    return _view.decision_side(_state()) if p == "active" else p


def _baseline_key():
    s = _state()
    return (_viewer(), (s.grand_scenario or {}).get("current_war"), _S["epoch"])


def _clean(action):
    return {k: deepcopy(v) for k, v in action.items()
            if k not in _NON_ACTION_KEYS and not k.startswith("_")}


def scenario_ids():
    return static_data.list_scenario_ids()


def scenarios():
    _emit("scenarios: " + _json(scenario_ids()))
    return scenario_ids()


def deep_copy(state):
    return state.model_copy(deep=True)


def apply_action_local(state, action):
    return actions.apply_action(state, action)


def legal_actions_for_side(state, side):
    """Trusted adapter: exact engine entries, including *unexpanded* templates."""
    return deepcopy(legal_moves.legal_moves(deep_copy(state)))


def _catalog():
    stamp = _sync()
    if _S["catalog"] is None:
        _S["catalog"] = [{"id": f"{stamp}/{i}", "action": a, "status": "unchecked"}
                         for i, a in enumerate(legal_actions_for_side(_state(), None))]
    return _S["catalog"]


def _validate_entries():
    # IDs were already assigned from the complete raw catalog. Validation only
    # annotates these slots; it never reorders, renumbers or modifies them.
    for entry in _catalog():
        if entry["status"] != "unchecked":
            continue
        a = entry["action"]
        if legal_moves._is_templated(a):
            entry["status"] = "template"
            continue
        try:
            apply_action_local(deep_copy(_state()), _clean(a))
            entry["status"] = "valid"
        except Exception as error:
            entry["status"] = "rejected"
            entry["error"] = {"code": getattr(error, "code", type(error).__name__),
                              "message": str(error)}
            _S["findings"].append({"kind": "over_enum_filtered" if isinstance(error, IllegalAction)
                                   else "exception_in_probe", "turn": _S["turn"],
                                   "side": a.get("side"), "action": _clean(a),
                                   "id": entry["id"], **entry["error"]})


def _visible_entry(entry):
    side = entry["action"].get("side")
    return _viewer() == "referee" or side is None or side == _viewer()


def all_actions(*, validated=None):
    """Complete player-visible programmatic catalog, no printing/paging.

    Each record has a state-bound id, the engine action (templates included),
    status and has_parameters. validated=False also retains rejected entries.
    In referee perspective actions exactly match the raw engine menu, including
    both players' metadata. Returned data are deep copies, not live menu slots.
    """
    validate = VALIDATE if validated is None else validated
    entries = _catalog()
    if validate:
        _validate_entries()
    out = []
    for entry in entries:
        if not _visible_entry(entry) or (validate and entry["status"] == "rejected"):
            continue
        e = deepcopy(entry)
        e["action"] = _view.action_view(e["action"], _viewer(), _state())
        e["has_parameters"] = e["action"].get("type") in _help.PARAMETERIZED
        out.append(e)
    return out


def _overview():
    entries = all_actions()
    counts = Counter(e["action"]["type"] for e in entries)
    categories = {}
    for typ in sorted(counts):
        items = [e for e in entries if e["action"]["type"] == typ]
        categories[typ] = {"count": len(items), "templates": sum(e["status"] == "template" for e in items),
                           "parameters": typ in _help.PARAMETERIZED}
        if len(items) == 1:
            categories[typ]["id"] = items[0]["id"]
    if not entries and not _catalog() and _state().phase != "over":
        if not any(f.get("version") == version() and f["kind"] == "no_legal_moves"
                   for f in _S["findings"]):
            _S["findings"].append({"kind": "no_legal_moves", "turn": _S["turn"],
                                   "side": _view.decision_side(_state()), "version": version()})
    return {"version": version(), "categories": categories, "total": len(entries),
            "acting_side": _view.decision_side(_state()), "perspective": _viewer(),
            "pending": _view.pending_view(_state(), _viewer()),
            "victory": deepcopy(_state().victory),
            "rejected_count": sum(e["status"] == "rejected" and _visible_entry(e) for e in _catalog())}


def _overview_text(overview):
    items = []
    for typ, info in overview["categories"].items():
        items.append(f"{typ}:{info['count']}" + (f"[{info['id']}]" if "id" in info else "")
                     + (" TEMPLATE" if info["templates"] else "")
                     + ("*" if info["parameters"] else "")
                     + (" OPTIONAL" if typ == "play_held_event" else ""))
    lines = [f"Actions {overview['version']} ({overview['total']} entries): " + "; ".join(items)]
    if overview["rejected_count"]:
        lines.append(f"Rejected {overview['rejected_count']}: inspect('rejected') / all_actions(validated=False).")
    if not overview["total"]:
        if _state().phase == "over":
            lines.append("GAME OVER " + _json(_state().victory))
        elif _viewer() != "referee" and _viewer() != overview["acting_side"]:
            lines.append("Waiting for other player; private menu withheld.")
        else:
            lines.append("No offered actions: inspect('pending'/'state'); findings_report().")
    return "\n".join(lines)


def show(*, expanded=False):
    """Fresh compact position baseline plus category overview, never every move.

    expanded=True explicitly prints the entire safe menu. This and all other
    inspection calls do NOT apply actions, advance RNG, or auto-renew Wars.
    """
    overview = _overview()
    _emit(_view.briefing(_state(), _viewer(), _json) + "\n" + _overview_text(overview)
          + "\n* parameters/custom choices, NOT exhaustive combinations. menu(type,lord=...,page=1,page_size=12,**filters); describe(type/ID); inspect(topic).")
    _S["baseline"] = _baseline_key()
    if expanded:
        menu(page_size=None)
    return Reply(kind="overview", **overview)


def attach(state, *, perspective="active"):
    """Attach a trusted GameState to a fresh session (useful for resumed tests).

    Ownership transfers to the helper. No setup decisions are auto-applied.
    """
    if perspective not in (*_view.SIDES, "active", "referee"):
        raise ValueError("perspective must be active, lancastrian, yorkist or referee")
    _S.update(state=state, scenario=state.scenario, seed=state.seed, history=[], findings=[],
              turn=0, transitions=0, perspective=perspective, epoch=uuid.uuid4().hex[:8],
              revision=0, fingerprint=None, catalog=None, baseline=None, receipts=[],
              reset_choices={}, reset_fingerprint=None)
    _S["fingerprint"] = _fingerprint()
    return show()


def start(scenario, seed=1, *, perspective="active"):
    if scenario not in scenario_ids():
        raise ValueError(f"unknown scenario {scenario!r}; choose from {scenario_ids()}")
    return attach(build_initial_state(scenario, seed=seed), perspective=perspective)


def set_perspective(perspective):
    """Trusted host chooses a viewer; LLM-facing outputs never select this itself.

    A new view gets a baseline and invalidates selections from the old view.
    Perspective controls output, not authentication: code with access to _S or
    a save file is trusted and can read the engine's omniscient state.
    """
    if perspective not in (*_view.SIDES, "active", "referee"):
        raise ValueError("unknown perspective")
    _sync()
    _S["perspective"] = perspective
    _S["baseline"] = None
    _touch()
    return show()


def _leaves(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _leaves(v)
    else:
        yield obj


def _get(obj, path):
    for k in path.split("."):
        if not isinstance(obj, dict) or k not in obj:
            return None
        obj = obj[k]
    return obj


def _matches(entry, action_type, lord, query, filters):
    a = entry["action"]
    if action_type is not None and a.get("type") != action_type:
        return False
    if lord is not None and lord not in set(x for x in _leaves(a) if isinstance(x, str)):
        candidate = _state().lords.get(lord)
        if not (a.get("type") == "build_plan" and candidate is not None
                and candidate.side == a.get("side") and candidate.status == "mustered"):
            return False
    if query is not None and query.casefold() not in _json(a).casefold():
        return False
    return all(_get(a, key) == value for key, value in filters.items())


def menu(action_type=None, lord=None, *, page=1, page_size=12, query=None,
         validated=None, expected_version=None, **filters):
    """Filter first, then page (1-based). IDs remain raw-catalog slots.

    lord matches any Lord occurrence (actor, target, group, assignment, plan),
    and build_plan templates for which that Lord is eligible.
    Use by_lord for actor-only; any exact JSON field or dotted nested field can
    be filtered via **{'decisions.target': 'id'}. query is a case-insensitive
    substring search. page_size=None prints ALL matches, never a hard cap.
    expected_version guards continuation across an intervening state change.
    """
    stamp = version()
    if expected_version is not None and expected_version != stamp:
        raise StaleSelectionError(f"page belongs to {expected_version}, current state is {stamp}")
    if isinstance(page, bool) or not isinstance(page, int) or page < 1:
        raise ValueError("page must be a positive integer")
    if page_size is not None and (isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1):
        raise ValueError("page_size must be a positive integer or None")
    entries = [e for e in all_actions(validated=validated)
               if _matches(e, action_type, lord, query, filters)]
    size = page_size or max(1, len(entries))
    start = (page - 1) * size
    items = entries[start:start + size]
    pages = max(1, (len(entries) + size - 1) // size)
    lines = [f"Menu {stamp}: {len(entries)} matches | page {page}/{pages} | {len(items)} shown"]
    for e in items:
        lines.append(f" [{e['id']}] {_json(e['action'])} ({e['status']}"
                     + ("; +parameters; describe(ID)" if e["has_parameters"] else "") + ")")
    if page < pages:
        lines.append(f"More: page={page + 1}, expected_version='{stamp}' with the same filters.")
    _emit("\n".join(lines))
    return Reply(kind="menu", version=stamp, items=items, total=len(entries), page=page,
                 pages=pages, next_page=page + 1 if page < pages else None,
                 filters={"action_type": action_type, "lord": lord, "query": query, **filters})


def _resolve_id(identifier):
    stamp = version()
    if not isinstance(identifier, str) or "/" not in identifier:
        raise ValueError("Use a state-bound ID from menu(), not an unversioned number.")
    prefix, slot = identifier.rsplit("/", 1)
    if prefix != stamp:
        raise StaleSelectionError(f"selection belongs to {prefix}, current state is {stamp}; refresh menu")
    for e in _catalog():
        if e["id"] == identifier:
            if not _visible_entry(e):
                raise PermissionError("This decision belongs to the other player.")
            return e
    raise ValueError(f"unknown selection {identifier!r}")


def describe(action_or_id, *, source=False):
    """Parameter constraints, current card text; source=True includes live code.

    This does not materialize combinations or choose a default plan. It is safe
    to call for an action type not on the menu; that does not assert legality.
    """
    if "/" in action_or_id:
        move = _resolve_id(action_or_id)["action"]
        typ = move["type"]
    else:
        typ = action_or_id
        move = next((e["action"] for e in all_actions() if e["action"]["type"] == typ), {})
    data = _help.contract(_state(), typ, move)
    if source:
        from plantagenet import battle, commands, events, pay
        modules = [actions, commands, battle] if typ in ("march", "sail", "react", "resolve_battle") else [actions]
        if typ in ("play_event", "play_held_event"):
            modules = [events]
        if typ == "pay":
            modules = [pay]
        # Complete source is a deliberate detailed inspection, not a token cap.
        data["source"] = {m.__name__: _inspect.getsource(m) for m in modules}
    _emit(_json(data))
    return Reply(kind="parameters", version=version(), **data)


def inspect(topic="state", *, target=None, card=None, index=-1):
    """Detailed player-safe inspection; 'raw'/'engine_history' require referee.

    state, influence, lords, vassals, locales, campaign, decks/cards, effects,
    victory, calendar, pending, grand_scenario, flags, map, grammar, result,
    history, rejected, or a Lord/Locale ID. No details are hard-truncated.
    """
    s = _state()
    stamp = version()
    view = _view.visible_state(s, _viewer())
    if topic in ("raw", "engine_history"):
        if _viewer() != "referee":
            raise PermissionError("Raw state/history contains hidden information; referee access only.")
        data = s.model_dump(mode="json") if topic == "raw" else deepcopy(s.history)
    elif topic == "grammar":
        data = (ROOT / "ACTIONS.md").read_text(encoding="utf-8")
    elif topic == "map":
        data = {"static": static_data.load_locales(), "ways": static_data.load_ways(),
                "current": view["locales"]}
    elif topic == "card":
        data = _view.card_text(card or target)
    elif topic == "result":
        record = _S["receipts"][index]
        data = _view.result_view(record["result"], record["side"], _viewer(), s)
    elif topic == "history":
        data = [{"action": _view.private_action(r["action"], r["side"], _viewer(), s),
                 "result": _view.result_view(r["result"], r["side"], _viewer(), s)}
                for r in _S["receipts"]]
    elif topic == "rejected":
        _validate_entries()
        data = [e for e in all_actions(validated=False) if e["status"] == "rejected"]
    elif topic in s.lords or (topic == "lord" and target in s.lords):
        lid = target if topic == "lord" else topic
        data = {"mat": view["lords"][lid], "static": static_data.load_lords()[lid],
                "focus": render.render_focused(s, lid)}
    elif topic in s.locales or (topic == "locale" and target in s.locales):
        lid = target if topic == "locale" else topic
        data = {"state": view["locales"][lid], "focus": render.render_focused(s, lid)}
    elif topic == "state":
        data = view
    else:
        key = {"cards": "decks", "effects": "active_events"}.get(topic, topic)
        if key not in view:
            raise ValueError(f"unknown topic {topic!r}; inspect.__doc__ lists topics")
        data = view[key]
    _emit(data if isinstance(data, str) else _json(data))
    return Reply(kind="inspection", version=stamp, topic=topic, data=deepcopy(data))


def _classify(action, entries):
    for e in entries:
        base = _clean(e["action"])
        if base == action:
            return "template" if e["status"] == "template" else "vouched"
    # Parameterized examples are not exhaustive. Different plans, extra_spend,
    # partial Groups, Pay preferences, and tactical choices are NOT under-enum.
    for e in entries:
        a = e["action"]
        if a.get("type") != action.get("type") or a.get("side") != action.get("side"):
            continue
        if a.get("type") in _help.PARAMETERIZED:
            return "template"
    return "offmenu"


def _check_invariants():
    try:
        bad = _inv.board_invariant_violations(_state())
    except Exception as error:
        _S["findings"].append({"kind": "invariant_crash", "turn": _S["turn"],
                               "message": str(error)})
        return [{"kind": "invariant_crash", "message": str(error)}]
    _S["findings"].extend({"kind": "invariant", "turn": _S["turn"], "violation": v} for v in bad)
    return bad


def _reset_required_sides():
    s = _state()
    return {side for side in _view.SIDES if s.decks.get(side, {}).get("held") or any(
        lord.side == side and (lord.at_sea or any(static_data.load_cards()[c]["capability"]["title"] ==
            "WE DONE DEEDS OF CHARITY" for c in lord.capabilities)) for lord in s.lords.values())}


def stage_reset(decisions, *, expected_version):
    """Collect this player's private End-Campaign choices without advancing play.

    decisions uses engine keys, except discard_held is this side's list:
      {'discard_held': ['Y13'], 'charity': {'york': 1}}
    Switch perspective for the other player's contribution, then apply the
    current end_campaign ID. The engine receives a single unchanged atomic
    payload. Empty contributions explicitly choose the normal defaults.
    """
    if version() != expected_version:
        raise StaleSelectionError("Reset contribution belongs to an old version")
    viewer = _viewer()
    if viewer == "referee":
        raise ValueError("Referee may submit the combined engine payload directly.")
    if not any(e["action"]["type"] == "end_campaign" for e in _catalog()):
        raise ValueError("Not at Campaign Reset")
    d = deepcopy(decisions)
    if not isinstance(d, dict) or set(d) - {"discard_held", "charity", "disembark_land"}:
        raise ValueError("Use discard_held, charity, or disembark_land")
    held = d.get("discard_held", [])
    if not isinstance(held, list) or len(set(held)) != len(held) or any(
            c not in _state().decks.get(viewer, {}).get("held", []) for c in held):
        raise ValueError("discard_held must be a distinct subset of your Held Events")
    for key in ("charity", "disembark_land"):
        if not isinstance(d.get(key, {}), dict) or any(
            lid not in _state().lords or _state().lords[lid].side != viewer for lid in d.get(key, {})):
            raise ValueError(f"{key} must be keyed by your own Lords")
    _S["reset_choices"][viewer] = d
    _touch()
    _emit(f"Reset contribution stored for {viewer}; version {version()}. No game action applied.")
    return Reply(kind="reset_contribution", version=version(), side=viewer)


def _reset_action(action):
    if action["type"] != "end_campaign" or _viewer() == "referee":
        return action
    viewer = _viewer()
    d = deepcopy(action.get("decisions", {}))
    for side in d.get("discard_held", {}):
        if side != viewer:
            raise PermissionError("Stage each player's Reset choice privately, or use referee mode.")
    for key in ("charity", "disembark_land"):
        for lid in d.get(key, {}):
            if lid in _state().lords and _state().lords[lid].side != viewer:
                raise PermissionError("Cannot choose another player's Reset parameters.")
    needed = _reset_required_sides() - {viewer} - _S["reset_choices"].keys()
    if needed:
        raise ValueError("Private Reset choices required from " + ", ".join(sorted(needed))
                         + "; use stage_reset({}, expected_version=version()) even to keep/default.")
    combined = {}
    for side, choice in _S["reset_choices"].items():
        for key, value in choice.items():
            combined.setdefault(key, {}).update({side: value} if key == "discard_held" else value)
    for key, value in d.items():
        if isinstance(value, dict) and isinstance(combined.get(key), dict):
            combined[key].update(value)
        else:
            combined[key] = value
    return {**action, "decisions": combined}


def apply(choice, *, expected_version=None, parameters=None):
    """Apply a stable ID, or a custom action with an explicit expected_version.

    parameters supplements/overrides the ID's parameterized fields. It may not
    change type or side; use a raw dict for a different action. Integer/page
    indices are intentionally rejected. On error there is no redisplay flood.
    """
    stamp = version()
    if expected_version is not None and expected_version != stamp:
        raise StaleSelectionError(f"expected {expected_version}, current {stamp}")
    entries = _catalog()
    if isinstance(choice, str):
        entry = _resolve_id(choice)
        action = _clean(entry["action"])
    elif isinstance(choice, dict):
        if expected_version is None:
            raise StaleSelectionError("Custom actions require expected_version=version() from the observed state.")
        action = _clean(choice)
    else:
        raise TypeError("Use the full state-bound action ID, not a page/index number.")
    if parameters:
        if {"type", "side"} & parameters.keys():
            raise ValueError("parameters cannot change action type or side")
        action.update(deepcopy(parameters))
    viewer = _viewer()
    side = action.get("side", viewer if viewer != "referee" else _view.decision_side(_state()))
    if viewer != "referee" and side != viewer:
        raise PermissionError("This action belongs to the other player.")
    # End-Campaign accepts joint owner choices; their sealed contribution is
    # a host-level transport, not an additional game mechanic.
    action = _reset_action(action)
    cls = _classify(action, entries)
    s = _state()
    before = _view.visible_state(s, viewer)
    before_key = _baseline_key()
    result_owner = side
    try:
        raw_result = apply_action_local(s, action)
    except Exception as error:
        kind = ("illegal_action" if cls == "vouched" else "player_illegal") if isinstance(error, IllegalAction) else "exception"
        _S["findings"].append({"kind": kind, "turn": _S["turn"], "side": side,
                               "action": action, "code": getattr(error, "code", ""),
                               "message": str(error), "tb": traceback.format_exc()})
        _sync()
        data = {"code": getattr(error, "code", type(error).__name__), "message": str(error)}
        _emit("Rejected " + _json(data) + "; state " + version())
        return Reply(kind="error", version=version(), error=data)
    _S["history"].append({"turn": _S["turn"], "side": side, "action": deepcopy(action)})
    _S["receipts"].append({"side": result_owner, "action": deepcopy(action), "result": deepcopy(raw_result)})
    _S["turn"] += 1
    if action["type"] == "renew_war":
        _S["transitions"] += 1
    if action["type"] in ("end_campaign", "renew_war"):
        _S["reset_choices"] = {}
    if cls == "offmenu" and action.get("type") != "concede":
        _S["findings"].append({"kind": "under_enum_accepted", "turn": _S["turn"],
                               "side": side, "action": deepcopy(action)})
    _touch()
    bad = _check_invariants()
    after_key = _baseline_key()
    # Receipt belongs to the requester, not automatically to the next actor.
    result = _view.result_view(raw_result, result_owner, viewer, s)
    delta = _view.changes(before, _view.visible_state(s, viewer))
    overview = _overview()
    scalar = {k: v for k, v in result.items() if not isinstance(v, (list, dict))}
    if result.get("peek") and viewer in ("referee", result_owner):
        scalar["peek"] = result["peek"]  # authorised information gains are consequential
    lines = [f"Applied {action['type']} ({side}); {overview['version']} | result {_json(scalar)}"]
    fresh_baseline = before_key != after_key or _S["baseline"] != before_key
    if fresh_baseline:
        lines.append("FRESH BASELINE (new view/War or no prior baseline)")
        lines.append(_view.briefing(s, _viewer(), _json))
        # Delta was computed under the requester's view; do not return private
        # state changes to a new player after an automatic handoff.
        returned_delta = {}
    else:
        lines.append("Changes " + _view.change_text(delta, _json))
        returned_delta = delta
    if overview["pending"]:
        lines.append("PENDING " + _json(overview["pending"]))
    if bad:
        lines.append("INVARIANT FINDINGS " + _json(bad))
    lines.append(_overview_text(overview))
    lines.append("Detail: menu(...), describe(ID), inspect('result'/'state'/'cards'/'effects'/Lord ID).")
    _emit("\n".join(lines))
    _S["baseline"] = after_key
    # The safe full result returned is still requester-specific; no raw hidden
    # continuation state is ever exposed by a menu, receipt or its repr.
    return Reply(kind="result", version=version(), result=result, changes=returned_delta,
                 baseline_required=fresh_baseline, overview=overview)


def auto(max_steps=300):
    """Conservative forced-only advancement. Never choose a plan, optional
    parameter family, reaction, early end_activation, or War renewal for a player.
    Every applied result is still emitted, so no consequences vanish in a batch.
    """
    n = 0
    while n < max_steps:
        entries = all_actions()
        if len(entries) != 1:
            break
        entry = entries[0]
        a = entry["action"]
        if entry["status"] == "template" or entry["has_parameters"] or a["type"] == "renew_war":
            break
        if apply(entry["id"]).get("kind") == "error":
            break
        n += 1
    _emit(f"auto: {n} unparameterized forced action(s); no strategic defaults selected.")
    return Reply(kind="auto", version=version(), steps=n, overview=_overview())


def findings_report():
    viewer = _viewer()
    findings = [f for f in _S["findings"] if viewer == "referee" or f.get("side") in (None, viewer)]
    notable = [f for f in findings if f["kind"] != "player_illegal"]
    _emit(f"Findings: {len(notable)} notable / {len(findings)} visible total\n" + _json(notable))
    return deepcopy(findings)


def save(path="chatgpt_game.json"):
    """Trusted full-state checkpoint, never an opponent-safe export."""
    _sync()
    keys = ("scenario", "seed", "history", "findings", "turn", "transitions", "perspective",
            "receipts", "reset_choices")
    data = {k: _S[k] for k in keys}
    data["state_json"] = _state().model_dump_json()
    Path(path).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    _emit(f"Saved referee checkpoint: {path}")


def load(path="chatgpt_game.json", *, perspective=None):
    """Restore state/RNG and staged decisions, but mint a fresh session epoch.

    Old menu IDs are rejected even when the saved board is identical. Every
    load prints a baseline. Restoring no longer silently renews a finished War.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    s = GameState.model_validate_json(data["state_json"])
    _S.update(state=s, scenario=s.scenario, seed=s.seed, history=data.get("history", []),
              findings=data.get("findings", []), turn=data.get("turn", len(data.get("history", []))),
              transitions=data.get("transitions", 0),
              perspective=perspective or data.get("perspective", "active"),
              epoch=uuid.uuid4().hex[:8], revision=0, fingerprint=None, catalog=None,
              baseline=None, receipts=data.get("receipts", []),
              reset_choices=data.get("reset_choices", {}))
    if _S["perspective"] not in (*_view.SIDES, "active", "referee"):
        raise ValueError("unknown saved perspective")
    _S["fingerprint"] = _fingerprint()
    _emit(f"Loaded {path}; new selection namespace.")
    return show()
