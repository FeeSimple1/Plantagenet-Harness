"""State model: serialization round-trip and dice integration."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState


def test_save_load_round_trip(tmp_path):
    state = build_initial_state("henry_vi", seed=3)
    p = tmp_path / "g.state.json"
    state.save(p)
    reloaded = GameState.load(p)
    assert reloaded.model_dump() == state.model_dump()


def test_unknown_field_is_rejected(tmp_path):
    state = build_initial_state("towton", seed=1)
    data = json.loads(state.to_json())
    data["surprise_field"] = 1
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        GameState.load(p)


def test_dice_state_persists_through_save(tmp_path):
    state = build_initial_state("towton", seed=5)
    roller = state.dice()
    rolls = roller.roll(4)
    # A fresh roller from the same seed gives the same opening sequence.
    assert build_initial_state("towton", seed=5).dice().roll(4) == rolls


def test_committed_schema_matches_model():
    # The published JSON Schema must stay in lockstep with the model.
    # Regenerate with: python scripts/generate_schema.py
    import json
    from importlib import resources

    from plantagenet.state import GameState

    with resources.files("plantagenet.data.schema").joinpath("state.schema.json").open() as fh:
        committed = json.load(fh)
    schema = GameState.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://plantagenet-harness/state.schema.json"
    schema["title"] = "Plantagenet game state"
    assert committed == schema, "state.schema.json is stale; run scripts/generate_schema.py"
