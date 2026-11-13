"""Collect each side's initial Array and Valour policy before a player Battle."""

from __future__ import annotations

from typing import Any, cast

from plantagenet import battle
from plantagenet.errors import IllegalAction
from plantagenet.state import GameState

OWNER_FIELDS = {"defender_positions", "attacker_positions", "valour"}


def _prompt(pending: dict[str, Any]) -> dict[str, Any]:
    return {"type": "pending_battle_choices", "awaiting_side": pending["side"],
            "locale": pending["locale"], "role": pending["role"]}


def begin(state: GameState, locale: str, attackers: list[str], defenders: list[str],
          decisions: dict[str, Any], *, movement: dict[str, Any] | None = None
          ) -> dict[str, Any]:
    # Discard Array and Valour input from older saved movement declarations.
    # For Bosworth the positions here come from its already committed setup.
    owner_fields = OWNER_FIELDS if movement is not None else {"valour"}
    pending = {"kind": "battle_choices", "side": state.lords[defenders[0]].side,
               "role": "defender", "locale": locale, "attackers": attackers,
               "defenders": defenders, "movement": movement,
               "decisions": {key: value for key, value in decisions.items()
                             if key not in owner_fields},
               "valour_lords": []}
    state.pending = [pending]
    return _prompt(pending)


def options(state: GameState, pending: dict[str, Any]) -> dict[str, Any]:
    role = pending["role"]
    decisions = pending["decisions"]
    lords = pending[f"{role}s"]
    info = {"lords": list(lords), "array_locked": pending["movement"] is None}
    defender_front = decisions.get("defender_positions")
    if defender_front is not None:
        info["defender_front"] = dict(defender_front)
    if not info["array_locked"]:
        available = lords
        if battle._norfolk_is_late(state, lords):
            available = [lid for lid in lords if lid != "norfolk"]
        info["array_lords"] = list(available)
        slots = (battle._FILL_ORDER if role == "defender" else
                 [i for i in battle._FILL_ORDER if str(i) in defender_front])
        info["front_slots"] = slots
        info["fronts_required"] = min(len(available), len(slots))
        info["default_positions"] = {str(i): lid for i, lid in
                                     battle._default_front(available, slots).items()}
    return info


def _valour_lords(raw: Any, lords: list[str]) -> list[str]:
    if isinstance(raw, bool):
        return list(lords) if raw else []
    if not isinstance(raw, list) or any(not isinstance(lid, str) or lid not in lords
                                       for lid in raw) or len(raw) != len(set(raw)):
        raise IllegalAction("bad_valour_owner",
                            "Valour must be a boolean or a list of your participating Lords")
    return [lid for lid in lords if lid in raw]


def respond(state: GameState, action: dict[str, Any]) -> dict[str, Any]:
    pending = state.pending[0]
    if action.get("side") != pending["side"]:
        raise IllegalAction("wrong_battle_side", "only the awaiting player may choose its tactics")
    if action.keys() - {"type", "side", "positions", "valour"}:
        raise IllegalAction("bad_battle_choices",
                            "choose_battle_tactics takes positions and valour")

    role = pending["role"]
    choices = options(state, pending)
    lords = choices["lords"]
    decisions = pending["decisions"]
    allowed_valour = _valour_lords(action.get("valour", True), lords)
    if choices["array_locked"]:
        if "positions" in action:
            raise IllegalAction("battle_array_locked", "Bosworth Arrays are already committed")
    else:
        positions = battle._array_positions(action.get("positions", choices["default_positions"]),
                                            choices["array_lords"])
        slots = choices["front_slots"]
        if (len(positions) != choices["fronts_required"] or 1 not in positions
                or positions.keys() - set(slots)):
            raise IllegalAction("bad_battle_array",
                                "fill center first and then the required eligible wing positions")
        # Use the same order and JSON keys before and after saving.
        decisions[f"{role}_positions"] = {str(i): positions[i] for i in slots if i in positions}

    pending["valour_lords"].extend(allowed_valour)
    attackers, defenders = pending["attackers"], pending["defenders"]
    if role == "defender":
        pending["role"] = "attacker"
        pending["side"] = state.lords[attackers[0]].side
        return _prompt(pending)

    decisions["valour"] = pending["valour_lords"]
    state.pending = []
    if pending["movement"] is None:
        from plantagenet.actions import _resolve_bosworth_battle

        return _resolve_bosworth_battle(state, pending["locale"], attackers, defenders, decisions)
    from plantagenet.commands import finish_approach_movement

    movement = cast(dict[str, Any], pending["movement"])
    movement["approach"]["battle"] = battle.resolve_battle(
        state, pending["locale"], attackers, defenders, decisions)
    return finish_approach_movement(state, movement)
