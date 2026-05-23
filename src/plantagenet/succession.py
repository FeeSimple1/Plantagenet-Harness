"""Succession (6.2-6.3) for the Wars of the Roses grand scenario.

Implements both the general mechanic (6.2.2 -- a Heir removed by Death or
Shipwreck brings the next-ranked Heir to the next Calendar box) and the
*structured per-War* triggers encoded in ``wars_of_the_roses.json`` under each
War's ``successions`` block.

Trigger conditions (``on``): ``setup``, ``remove`` (a named Heir leaves),
``muster`` (a named Lord Musters), ``while_remains`` / ``while_king``
(continuous deck contributions).  Effects: ``to_calendar`` (a Lord enters the
next Calendar box), ``add_cards_to_deck`` (permanent), ``cards``
(while_remains/while_king ref-counted contribution), ``assign_capability``
(free/mandatory Capability to a mat, optionally ``on_disband: set_aside``).

Deck membership of Succession-managed cards is **reference-counted by source**
(``grand_scenario['deck_sources'][side][card] = [source, ...]``): a card stays
in the deck while it has >=1 source.  Cards repeated from one Lord to the next
therefore stay put (errata: e.g. Y20 in War IIL).  Cards added permanently use
the source ``"__permanent__"``.
"""

from __future__ import annotations

from typing import Any

from plantagenet import static_data
from plantagenet.state import GameState, LordState, LordStatus

_PERMANENT = "__permanent__"
_DECK_PILES = ("draw", "discard", "held")


# --------------------------------------------------------------- data access
def _current_war(state: GameState) -> dict[str, Any] | None:
    gs = state.grand_scenario or {}
    wid = gs.get("current_war")
    scn = static_data.load_scenario("wars_of_the_roses")
    for w in scn.get("wars", []):
        if w["war_id"] == wid:
            return w
    return None


def _succ(state: GameState, side: str) -> dict[str, Any]:
    war = _current_war(state) or {}
    return war.get("successions", {}).get(side, {})


def _heir_table(state: GameState, side: str) -> list[dict[str, Any]]:
    return static_data.load_scenario("wars_of_the_roses").get("heirs", {}).get(side, [])


def heir_rank(state: GameState, side: str, lord_id: str) -> int | None:
    for entry in _heir_table(state, side):
        if lord_id in entry.get("lord_ids", []):
            return entry["rank"]
    return None


# --------------------------------------------------------------- deck sources
def _sources(state: GameState) -> dict[str, dict[str, list[str]]]:
    gs = state.grand_scenario
    return gs.setdefault("deck_sources", {})


def _deck_has(state: GameState, side: str, card: str) -> bool:
    d = state.decks.get(side, {})
    return any(card in d.get(p, []) for p in _DECK_PILES)


def _add_to_deck(state: GameState, side: str, card: str) -> None:
    if not _deck_has(state, side, card):
        state.decks.setdefault(side, {}).setdefault("draw", []).append(card)


def _remove_from_deck(state: GameState, side: str, card: str) -> None:
    d = state.decks.get(side, {})
    for p in _DECK_PILES:
        if card in d.get(p, []):
            d[p].remove(card)


def _register_source(state: GameState, side: str, card: str, source: str) -> None:
    src = _sources(state).setdefault(side, {}).setdefault(card, [])
    if source not in src:
        src.append(source)
    _add_to_deck(state, side, card)


def _drop_lord_sources(state: GameState, side: str, lord_id: str) -> list[str]:
    """Remove ``lord_id`` as a source; pull any now-unsourced managed cards from
    the deck. Returns the removed card ids."""
    removed = []
    for card, src in list(_sources(state).get(side, {}).items()):
        if lord_id in src:
            src.remove(lord_id)
        if not src:
            _remove_from_deck(state, side, card)
            removed.append(card)
            _sources(state)[side].pop(card, None)
    return removed


# --------------------------------------------------------------- setup
def apply_setup(state: GameState) -> dict[str, Any]:
    """Register continuous (while_remains / while_king) deck contributions for
    Heirs currently in play, at War setup."""
    log: dict[str, Any] = {"registered": {}}
    if not state.grand_scenario:
        return log
    for side in ("lancastrian", "yorkist"):
        for trig in _succ(state, side).get("triggers", []):
            if trig.get("on") in ("while_remains", "while_king"):
                lord = trig["lord"]
                ls = state.lords.get(lord)
                if ls is not None and ls.status in (
                        LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE):
                    for card in trig.get("cards", []):
                        _register_source(state, side, card, lord)
                    log["registered"].setdefault(side, []).append(lord)
    return log


# --------------------------------------------------------------- muster
def on_muster_lord(state: GameState, lord_id: str) -> dict[str, Any] | None:
    """Apply ``on: muster`` Succession triggers for ``lord_id`` (assign free
    mandatory Capabilities, e.g. L26 EDWARD to Margaret)."""
    if not state.grand_scenario:
        return None
    side = state.lords[lord_id].side
    out = []
    for trig in _succ(state, side).get("triggers", []):
        if trig.get("on") == "muster" and trig.get("lord") == lord_id:
            spec = trig.get("assign_capability")
            if spec and spec["lord"] == lord_id:
                card = spec["card"]
                if card not in state.lords[lord_id].capabilities:
                    state.lords[lord_id].capabilities.append(card)
                if spec.get("on_disband") == "set_aside":
                    sa = state.grand_scenario.setdefault("set_aside_on_disband", {})
                    sa.setdefault(lord_id, [])
                    if card not in sa[lord_id]:
                        sa[lord_id].append(card)
                out.append({"assign_capability": card, "lord": lord_id})
    return {"muster_triggers": out} if out else None


# --------------------------------------------------------------- removal
def on_heir_removed(state: GameState, lord_id: str) -> dict[str, Any] | None:
    """Apply Succession when ``lord_id`` is removed by Death/Shipwreck (6.2.2).
    Runs the War's structured ``on: remove`` triggers (to_calendar, deck adds),
    drops the Lord's continuous deck contributions, then falls back to the
    general next-ranked-Heir rule if no explicit ``to_calendar`` fired. Also
    reports an Automatic War Victory if the removal completes one."""
    if not state.grand_scenario:
        return None
    side = state.lords[lord_id].side
    if heir_rank(state, side, lord_id) is None:
        return None
    setup_only = _current_war(state).get("successions", {}).get("setup_only", False) \
        if _current_war(state) else False

    result: dict[str, Any] = {"after": lord_id}
    explicit = False
    if not setup_only:
        for trig in _succ(state, side).get("triggers", []):
            if trig.get("on") == "remove" and trig.get("lord") == lord_id:
                tc = trig.get("to_calendar")
                if tc:
                    _enter_calendar(state, side, tc)
                    result["succession"] = tc
                    result["to_box"] = state.turn_box + 1
                    explicit = True
                for card in trig.get("add_cards_to_deck", []):
                    _register_source(state, side, card, _PERMANENT)
                    result.setdefault("added_cards", []).append(card)

    removed_cards = _drop_lord_sources(state, side, lord_id)
    if removed_cards:
        result["removed_cards"] = removed_cards

    if not explicit and not setup_only:
        gen = _general_next_heir(state, side, lord_id)
        if gen:
            result.update(gen)

    av = _automatic_victory(state)
    if av:
        result["automatic_victory"] = av
    return result


def _enter_calendar(state: GameState, side: str, lord_id: str) -> None:
    ls = state.lords.get(lord_id)
    if ls is None:
        statics = static_data.load_lords()
        if lord_id in statics:
            state.lords[lord_id] = LordState(lord_id=lord_id, side=side,
                                             status=LordStatus.CALENDAR,
                                             calendar_box=state.turn_box + 1)
        return
    if ls.status == LordStatus.AVAILABLE:
        ls.status = LordStatus.CALENDAR
        ls.calendar_box = state.turn_box + 1


def _general_next_heir(state: GameState, side: str, lord_id: str) -> dict[str, Any] | None:
    rank = heir_rank(state, side, lord_id)
    lords_static = static_data.load_lords()
    for entry in sorted(_heir_table(state, side), key=lambda e: e["rank"]):
        if entry["rank"] <= rank:
            continue
        if entry.get("third_war_only") and not _is_third_war(state):
            continue
        for cand in entry["lord_ids"]:
            ls = state.lords.get(cand)
            if ls is not None and ls.status == LordStatus.AVAILABLE:
                ls.status = LordStatus.CALENDAR
                ls.calendar_box = state.turn_box + 1
                return {"succession": cand, "to_box": ls.calendar_box}
            if ls is None and cand in lords_static:
                state.lords[cand] = LordState(lord_id=cand, side=side,
                                              status=LordStatus.CALENDAR,
                                              calendar_box=state.turn_box + 1)
                return {"succession": cand, "to_box": state.turn_box + 1, "added": True}
    return None


def _automatic_victory(state: GameState) -> dict[str, Any] | None:
    war = _current_war(state) or {}
    rules = war.get("successions", {}).get("automatic_victory", [])

    def gone(lid):
        ls = state.lords.get(lid)
        return ls is None or ls.status == LordStatus.REMOVED
    for rule in rules:
        if all(gone(lid) for lid in rule["all_removed"]):
            return {"winner": rule["winner"], "rule": "Automatic War Victory (6.x)"}
    return None


def set_aside_cards(state: GameState, lord_id: str) -> list[str]:
    """Capabilities to set aside (not discard) when ``lord_id`` Disbands (6.2)."""
    gs = state.grand_scenario or {}
    return list(gs.get("set_aside_on_disband", {}).get(lord_id, []))


def _is_third_war(state: GameState) -> bool:
    return str((state.grand_scenario or {}).get("current_war", "")).startswith("war_iii")
