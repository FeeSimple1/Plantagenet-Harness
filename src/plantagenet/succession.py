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
    """Ranked Heir table for the current War: the War's own ``successions.heirs``
    list (rank by order) when present, else the global ranking (6.2.1)."""
    heirs = _succ(state, side).get("heirs")
    if heirs:
        return [{"rank": i + 1, "lord_ids": h if isinstance(h, list) else [h]}
                for i, h in enumerate(heirs)]
    return static_data.load_scenario("wars_of_the_roses").get("heirs", {}).get(side, [])


def heir_rank(state: GameState, side: str, lord_id: str) -> int | None:
    for entry in _heir_table(state, side):
        if lord_id in entry.get("lord_ids", []):
            return entry["rank"]
    return None


def is_global_heir(side: str, lord_id: str) -> bool:
    """Whether ``lord_id`` is a Heir under the grand scenario's 6.2.1 ranking
    (used for the cross-War -8 Influence penalty, which keys off the global
    Heir list -- e.g. Henry VI -- not any single War's per-War Heir list)."""
    table = static_data.load_scenario("wars_of_the_roses").get("heirs", {}).get(side, [])
    return any(lord_id in e.get("lord_ids", []) for e in table)


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
            if trig.get("on") == "while_remains":   # while_king is handled by _recompute
                lord = trig["lord"]
                ls = state.lords.get(lord)
                if ls is not None and ls.status in (
                        LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE):
                    for card in trig.get("cards", []):
                        _register_source(state, side, card, lord)
                    log["registered"].setdefault(side, []).append(lord)
    for side in ("lancastrian", "yorkist"):
        if not _succ(state, side).get("setup_only") and not (
                _current_war(state) or {}).get("successions", {}).get("setup_only"):
            _recompute(state, side)    # initial King while_king cards / count adds
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


# --------------------------------------------------------------- presence
_IN_PLAY = (LordStatus.MUSTERED, LordStatus.CALENDAR, LordStatus.EXILE)


def _present_heirs(state: GameState, side: str) -> list[str]:
    """Heir lord ids currently in play, highest rank first."""
    out = []
    for entry in sorted(_heir_table(state, side), key=lambda e: e["rank"]):
        if entry.get("third_war_only") and not _is_third_war(state):
            continue
        for lid in entry["lord_ids"]:
            ls = state.lords.get(lid)
            if ls is not None and ls.status in _IN_PLAY:
                out.append(lid)
                break
    return out


def _highest_present_heir(state: GameState, side: str) -> str | None:
    heirs = _present_heirs(state, side)
    return heirs[0] if heirs else None


def _fired(state: GameState) -> set:
    gs = state.grand_scenario
    return set(gs.setdefault("succession_fired", []))


def _mark_fired(state: GameState, key: str) -> None:
    gs = state.grand_scenario
    f = gs.setdefault("succession_fired", [])
    if key not in f:
        f.append(key)


def _apply_replace_in_place(state: GameState, side: str, old: str, new: str) -> None:
    """Replace Lord ``old`` with ``new`` in the same position (6.2): ``new`` takes
    ``old``'s status/location, ``old`` leaves play. ``new`` uses its own ratings."""
    statics = static_data.load_lords()
    o = state.lords.get(old)
    if o is None or new not in statics:
        return
    ns = statics[new]
    nstate = LordState(lord_id=new, side=side, status=o.status, location=o.location,
                       exile_box=o.exile_box, calendar_box=o.calendar_box,
                       calendar_exile=o.calendar_exile, ring=o.ring,
                       forces=dict(ns.get("forces", {})), assets=dict(ns.get("assets", {})),
                       vassals=list(o.vassals), capabilities=list(o.capabilities))
    state.lords[new] = nstate
    # ``old`` leaves play entirely (6.2): its Capabilities/Vassals/Forces now
    # belong to ``new``'s mat, so clear them from the REMOVED Lord. Leaving them
    # behind double-counts the cards (they later hit the discard pile while still
    # listed on the REMOVED mat -> card_in_deck_and_on_mat).
    o.status = LordStatus.REMOVED
    o.location = None
    o.exile_box = None
    o.capabilities = []
    o.vassals = []
    o.special_vassals = []
    o.forces = {}
    o.assets = {}


def _seat_in_place(state: GameState, side: str, new: str, at: dict) -> bool:
    """Seat ``new`` Mustered at a captured board position (6.2 REPLACE in place)."""
    statics = static_data.load_lords()
    if new not in statics:
        return False
    ns = statics[new]
    state.lords[new] = LordState(
        lord_id=new, side=side, status=LordStatus.MUSTERED,
        location=at.get("location"), exile_box=at.get("exile_box"), ring=at.get("ring"),
        forces=dict(ns.get("forces", {})), assets=dict(ns.get("assets", {})))
    return True


def _add_cards(state: GameState, side: str, cards, source: str) -> None:
    for c in cards:
        _register_source(state, side, c, source)


# --------------------------------------------------------------- recompute
def _recompute(state: GameState, side: str) -> dict[str, Any]:
    """After any Heir change, fire count-threshold adds, refresh while_king deck
    sources for the current King, and apply on_becomes_highest_heir triggers."""
    out: dict[str, Any] = {}
    triggers = _succ(state, side).get("triggers", [])
    present = _present_heirs(state, side)
    count = len(present)

    for trig in triggers:
        if trig.get("on") == "heir_count_at_or_below":
            key = f"{side}:count<={trig['n']}:{trig.get('add_lord') or trig.get('add_cards')}"
            if count <= trig["n"] and key not in _fired(state):
                add_lord = trig.get("add_lord")
                if add_lord:
                    _enter_calendar(state, side, add_lord)
                    out.setdefault("added_lords", []).append(add_lord)
                _add_cards(state, side, trig.get("add_cards", []), _PERMANENT)
                _mark_fired(state, key)

    king = _highest_present_heir(state, side)
    prev_king = (state.grand_scenario.get("current_king", {}) or {}).get(side)
    if king != prev_king:
        # on_becomes_highest_heir FIRST: replace_lord_in_place / permanent ADDs
        # (once). Applied before we record the King so current_king names the
        # Lord actually in play after any in-place replacement (6.2).
        if king:
            for trig in triggers:
                if trig.get("on") == "becomes_highest_heir" and trig.get("lord") == king:
                    key = f"{side}:highest:{king}"
                    if key not in _fired(state):
                        rep = trig.get("replace_lord_in_place")
                        if rep:
                            _apply_replace_in_place(state, side, rep["old"], rep["new"])
                            out.setdefault("replaced", []).append(rep)
                        # "As long as <replacement> remains" (Scenario Ref E4): source the
                        # ADDs to the replacement Lord so they drop when it is removed, but
                        # survive King changes. Pure adds (no replacement) are permanent.
                        _src = rep["new"] if rep else _PERMANENT
                        _add_cards(state, side, trig.get("add_cards", []), _src)
                        _mark_fired(state, key)
        # Re-derive the King after any replacement: the highest present Heir is now
        # the replacement Lord (e.g. edward_iv), not the removed heir (march).
        king = _highest_present_heir(state, side)
        # Drop the previous King's while_king contribution, then register the
        # current King's while_king cards (ref-counted to the King).
        if prev_king:
            _drop_lord_sources(state, side, f"king:{prev_king}")
        if king:
            for trig in triggers:
                if trig.get("on") == "while_king" and trig.get("lord") == king:
                    _add_cards(state, side, trig.get("cards", []), f"king:{king}")
        state.grand_scenario.setdefault("current_king", {})[side] = king
        out["king"] = king
    return out


# --------------------------------------------------------------- removal
def on_heir_removed(state: GameState, lord_id: str,
                    removed_at: dict | None = None) -> dict[str, Any] | None:
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
    setup_only = (_current_war(state) or {}).get("successions", {}).get("setup_only", False)
    if setup_only:                       # War III: Heir removal affects only setup, not play
        return {"after": lord_id, "setup_only": True}

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
                rep = trig.get("replace_lord_in_place")
                if rep:                       # the dead Lord's slot passes to the replacement
                    at = removed_at or {}
                    if (at.get("location") or at.get("exile_box")) and \
                            _seat_in_place(state, side, rep["new"], at):
                        result["succession"] = rep["new"]
                        result["replaced_in_place"] = rep        # E5: in place, not the Calendar
                    else:
                        _enter_calendar(state, side, rep["new"])
                        result["succession"] = rep["new"]
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

    if not setup_only:
        rc = _recompute(state, side)
        if rc:
            result["recompute"] = rc

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
    if war.get("successions", {}).get("setup_only"):     # War III: removal is setup-only
        return None
    rules = war.get("successions", {}).get("automatic_victory", [])

    def gone(lid):
        ls = state.lords.get(lid)
        return ls is None or ls.status == LordStatus.REMOVED
    for rule in rules:                                   # scripted War-I automatic victories
        if all(gone(lid) for lid in rule["all_removed"]):
            return {"winner": rule["winner"], "rule": "Automatic War Victory (6.x)"}
    # General War Victory (Scenario Ref E2): a side with ALL its current-War Heirs
    # removed immediately loses that War.
    for side in ("lancastrian", "yorkist"):
        if not _present_heirs(state, side):
            winner = "yorkist" if side == "lancastrian" else "lancastrian"
            return {"winner": winner, "rule": "War Victory -- all Heirs removed (E2)"}
    return None


def set_aside_cards(state: GameState, lord_id: str) -> list[str]:
    """Capabilities to set aside (not discard) when ``lord_id`` Disbands (6.2)."""
    gs = state.grand_scenario or {}
    return list(gs.get("set_aside_on_disband", {}).get(lord_id, []))


def highest_heir_for_setup(state: GameState, side: str, removed: set) -> str | None:
    """The lord to seat as King at War setup: the highest-ranked Heir slot whose
    members are not removed (resolving a group to its surviving member, e.g.
    somerset_1 else somerset_2). Uses the current War's heir ranking."""
    for entry in sorted(_heir_table(state, side), key=lambda e: e["rank"]):
        for lid in entry["lord_ids"]:
            if lid not in removed:
                return lid
    return None


def _is_third_war(state: GameState) -> bool:
    return str((state.grand_scenario or {}).get("current_war", "")).startswith("war_iii")
