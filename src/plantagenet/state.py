"""Game-state model for the Plantagenet harness.

A single ``GameState`` holds the complete state of a game and serializes
to one JSON file (BRIEF: "A single JSON file holds complete game state").
Loading a state file fully reconstructs the game, including the seeded
dice (`rng.DiceRoller`).

Phase 1 scope: the model represents a faithfully-loaded scenario *setup*
and supports display. It carries no rules logic — no action handlers, no
turn-order enforcement, no victory math. Those arrive in later phases.
Fields are intentionally permissive (``extra="allow"`` is NOT set; unknown
keys are rejected) so that a typo in the loader fails loudly.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from plantagenet.rng import DiceRoller

SCHEMA_VERSION = 0


class Side(str, Enum):
    LANCASTRIAN = "lancastrian"
    YORKIST = "yorkist"


class Role(str, Enum):
    KING = "king"
    REBEL = "rebel"


class Favour(str, Enum):
    LANCASTRIAN = "lancastrian"
    YORKIST = "yorkist"
    NEUTRAL = "neutral"


class LordStatus(str, Enum):
    MUSTERED = "mustered"      # has a mat, cylinder on the map
    CALENDAR = "calendar"      # cylinder in a Calendar Turn box (awaiting entry)
    EXILE = "exile"            # cylinder in an Exile box
    AVAILABLE = "available"    # Lord card in the scenario, not yet in play
    REMOVED = "removed"        # permanently out of the game


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class LordState(_Model):
    lord_id: str
    side: Side
    status: LordStatus
    location: str | None = None        # locale id when MUSTERED on the map
    exile_box: str | None = None       # exile box id when EXILE
    calendar_box: int | None = None    # Turn box when CALENDAR
    calendar_exile: bool = False       # cylinder marked Exile on the Calendar
    ring: str | None = None            # "silver" | "gold" (Heir ring), if any
    forces: dict[str, int] = Field(default_factory=dict)
    assets: dict[str, int] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)
    vassals: list[str] = Field(default_factory=list)
    special_vassals: list[str] = Field(default_factory=list)
    # Per-Levy Muster bookkeeping (reset each Levy):
    lordship_spent: int = 0            # Levy actions taken this Muster (3.4)
    mustered_this_segment: bool = False  # brought on this Muster -> may not Levy (3.4)


class VassalStatus(str, Enum):
    AT_SEAT = "at_seat"        # marker pair on the map at its Seat
    MUSTERED = "mustered"      # Levied onto a Lord's mat; service marker on Calendar
    OFF_MAP = "off_map"        # not set up this scenario
    REMOVED = "removed"


class VassalState(_Model):
    vassal_id: str
    status: VassalStatus
    location: str | None = None        # seat locale when AT_SEAT
    on_lord: str | None = None         # lord id when MUSTERED
    service_box: int | None = None     # Calendar service-marker box when MUSTERED


class LocaleState(_Model):
    favour: Favour = Favour.NEUTRAL
    depletion: str | None = None   # None | "depleted" | "exhausted" (1.3.1, 3.4.4)


class StrongholdMarker(_Model):
    side: Side
    at: int


class InfluenceState(_Model):
    """Mirrors the scenario's Influence-track setup verbatim.

    The Influence/scoring *mechanics* are not interpreted in Phase 1; the
    values are stored as given so the display is faithful and later phases
    can build the scoring logic on top.
    """

    marker_at: int
    marker_side: Side
    stronghold_markers: dict[str, StrongholdMarker] = Field(default_factory=dict)
    victory_check: int | None = None


class CalendarState(_Model):
    levy_box: int | None = None
    end_box: int | None = None
    first_box: int | None = None
    last_box: int | None = None


class GameState(_Model):
    schema_version: int = SCHEMA_VERSION
    scenario: str
    title: str = ""
    seed: int
    rng_state: list[Any] | None = None
    active_side: Side
    turn_box: int
    phase: str = "levy"
    levy_step: str = "muster"   # arts_of_war | pay | exiles_vassals | muster | done
    grand_scenario: dict[str, Any] | None = None
    roles: dict[str, Role] = Field(default_factory=dict)   # side -> king/rebel
    lords: dict[str, LordState] = Field(default_factory=dict)
    vassals: dict[str, VassalState] = Field(default_factory=dict)
    locales: dict[str, LocaleState] = Field(default_factory=dict)
    exile_alignment: dict[str, Side] = Field(default_factory=dict)
    influence: dict[str, InfluenceState] = Field(default_factory=dict)
    calendar: CalendarState = Field(default_factory=CalendarState)
    arts_of_war: dict[str, str] = Field(default_factory=dict)   # side -> deck composition text
    history: list[dict[str, Any]] = Field(default_factory=list)
    pending: list[dict[str, Any]] = Field(default_factory=list)

    # -- dice -------------------------------------------------------------
    def dice(self) -> DiceRoller:
        """Reconstruct the seeded dice from stored state."""
        roller = DiceRoller(self.seed)
        if self.rng_state is not None:
            roller.set_state(self.rng_state)
        return roller

    def store_dice(self, roller: DiceRoller) -> None:
        self.rng_state = roller.get_state()

    # -- persistence ------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json() + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> GameState:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(data)
