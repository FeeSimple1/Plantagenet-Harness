"""Player-selected, unrevealed Bosworth Capabilities and Arrays (Scenario IIIb).

Setup is not a Muster: neither Influence nor Lordship is spent. Each side
selects four eligible cards and one three-Lord Front before either side's
Capabilities are revealed on the mats. The public action palette enumerates
all individual card assignments and all six Arrays, not a strategy default.
"""
from __future__ import annotations

from itertools import permutations
from typing import Any, cast

from plantagenet import static_data
from plantagenet.errors import IllegalAction
from plantagenet.state import BattleSetupState, GameState, LordStatus, Side

SIDES = ("yorkist", "lancastrian")
CARDS_REQUIRED = 4


def _require(condition: object, code: str, message: str) -> None:
    if not condition:
        raise IllegalAction(code, message)


def _setup(state: GameState, side: str) -> BattleSetupState:
    _require(state.phase == "battle" and state.victory is None,
             "not_battle_setup", "Bosworth setup is available only before its Battle")
    setup = state.battle_setup
    _require(setup is not None and not setup.complete, "battle_setup_closed",
             "Bosworth Capability selection and Array are already complete")
    assert setup is not None
    _require(side in SIDES and side == state.active_side, "not_active_side",
             "only the active side may choose its Bosworth setup")
    _require(side not in setup.arrays, "battle_array_locked",
             "this side has already committed its Capability selection and Array")
    return setup


def _lords(state: GameState, side: str) -> list[str]:
    return [lid for lid, lord in state.lords.items()
            if lord.side == side and lord.status == LordStatus.MUSTERED]


def _count(setup: BattleSetupState, side: str) -> int:
    return sum(len(cards) for cards in setup.capabilities.get(side, {}).values())


def _check_card(state: GameState, setup: BattleSetupState,
                side: str, lord_id: Any, card: Any) -> None:
    from plantagenet.actions import _capability_eligible

    _require(isinstance(lord_id, str) and lord_id in _lords(state, side),
             "wrong_side_lord", "select a Mustered Lord of your side for the Capability")
    _require(_count(setup, side) < CARDS_REQUIRED, "four_capabilities",
             "each Bosworth player selects exactly four Capabilities")
    cards = static_data.load_cards()
    _require(isinstance(card, str) and card in cards and cards[card]["side"] == side,
             "unknown_card", "select an Arts of War card belonging to your side")
    _require(card in static_data.scenario_card_deck(state.scenario, side),
             "card_not_in_scenario", "Bosworth uses only no-rose and three-rose cards")
    _require(card in state.decks.get(side, {}).get("draw", []),
             "card_in_play", "this Capability has already been selected or is unavailable")
    _require(_capability_eligible(card, lord_id), "ineligible_lord",
             "this Lord's Livery Badge does not permit the selected Capability (3.4.6)")
    chosen = setup.capabilities.get(side, {}).get(lord_id, [])
    _require(len(chosen) < 2, "two_capabilities", "a Lord may hold at most two Capabilities")
    title = cards[card]["capability"]["title"]
    _require(all(cards[c]["capability"]["title"] != title for c in chosen),
             "duplicate_capability", "a Lord cannot hold two Capabilities of the same name")


def choose_capability(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = cast(str, action.get("side"))
    setup = _setup(state, side)
    lord_id, card = cast(str, action.get("by_lord")), cast(str, action.get("card"))
    _check_card(state, setup, side, lord_id, card)
    setup.capabilities.setdefault(side, {}).setdefault(lord_id, []).append(card)
    state.decks[side]["draw"].remove(card)
    return {"type": "choose_battle_capability", "side": side,
            "selected": _count(setup, side), "required": CARDS_REQUIRED}


def array_battle(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    side = cast(str, action.get("side"))
    setup = _setup(state, side)
    _require(_count(setup, side) == CARDS_REQUIRED, "battle_setup_incomplete",
             "choose and distribute four Capabilities before committing the Array")
    front = action.get("front")
    lords = _lords(state, side)
    _require(isinstance(front, list) and len(front) == len(lords) == 3
             and all(isinstance(lid, str) for lid in front)
             and sorted(front) == sorted(lords), "bad_battle_array",
             "front must list all three Lords exactly once, in Left, Center, Right order")
    setup.arrays[side] = list(cast(list[str], front))
    if all(sd in setup.arrays for sd in SIDES):
        from plantagenet.actions import _muster_special_vassal

        # Simultaneous reveal: no selected card or Special Vassal appeared on
        # either side's mats while the opposing side was still choosing.
        for sd in SIDES:
            for lid, cards in setup.capabilities[sd].items():
                lord = state.lords[lid]
                for card in cards:
                    lord.capabilities.append(card)
                    _muster_special_vassal(state, lord, card)
        setup.capabilities.clear()   # cards now occupy the mat zone, not setup
        setup.complete = True
    else:
        state.active_side = cast(Side, next(sd for sd in SIDES if sd not in setup.arrays))
    return {"type": "array_battle", "side": side, "setup_complete": setup.complete}


def legal_moves(state: GameState) -> list[dict[str, Any]]:
    if state.victory is not None:
        return []
    setup = state.battle_setup
    if setup is None:
        return []
    if setup.complete:
        return [{"type": "resolve_battle"}]
    side = state.active_side
    if _count(setup, side) == CARDS_REQUIRED:
        return [{"type": "array_battle", "side": side, "front": list(front)}
                for front in permutations(_lords(state, side))]
    moves = []
    for lord_id in _lords(state, side):
        for card in state.decks.get(side, {}).get("draw", []):
            try:
                _check_card(state, setup, side, lord_id, card)
            except IllegalAction:
                continue
            moves.append({"type": "choose_battle_capability", "side": side,
                          "by_lord": lord_id, "card": card})
    return moves


def battle_decisions(state: GameState, decisions: Any) -> dict[str, Any]:
    """Validate the setup gate and inject the two committed, full Fronts."""
    setup = state.battle_setup
    _require(setup is not None and setup.complete, "battle_setup_incomplete",
             "both Bosworth players must choose four Capabilities and commit their Arrays")
    assert setup is not None
    _require(isinstance(decisions, dict), "bad_battle_decisions",
             "battle decisions must be a JSON object")
    out = dict(decisions)
    for side in SIDES:
        lords = _lords(state, side)
        front = setup.arrays.get(side, [])
        _require(len(front) == len(lords) == 3 and sorted(front) == sorted(lords)
                 and sum(len(state.lords[lid].capabilities) for lid in lords) == CARDS_REQUIRED,
                 "battle_setup_incomplete",
                 "Bosworth needs four Capabilities and three Front Lords")
        key = "attacker_positions" if state.roles[side] == "rebel" else "defender_positions"
        _require(key not in out, "battle_array_locked",
                 "Arrays were already committed with array_battle; do not override them")
        out[key] = dict(enumerate(front))
    return out
