"""Render output smoke tests (read-only views)."""

from __future__ import annotations

import json

from plantagenet import render
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState


def test_summary_has_key_sections():
    s = build_initial_state("henry_vi")
    out = render.render_summary(s)
    assert "Henry VI" in out
    assert "Lancastrian Lords" in out and "Yorkist Lords" in out
    assert "Influence" in out
    assert "Favour" in out


def test_verbose_is_valid_state_json():
    s = build_initial_state("warwicks_rebellion")
    out = render.render_verbose(s)
    GameState.model_validate(json.loads(out))  # parses back cleanly


def test_focus_lord_locale_calendar_influence():
    s = build_initial_state("henry_vi")
    assert "Ratings:" in render.render_focused(s, "henry_vi")
    assert "Ways:" in render.render_focused(s, "london")
    assert "Box 2:" in render.render_focused(s, "calendar")
    assert "Victory Check: 40" in render.render_focused(s, "influence")


def test_focus_unknown_target():
    s = build_initial_state("henry_vi")
    assert "Unknown focus target" in render.render_focused(s, "nonexistent")


def test_no_prescriptive_language_in_summary():
    # BRIEF: harness describes state, never advises.
    s = build_initial_state("my_kingdom_for_a_horse")
    out = render.render_summary(s).lower()
    for banned in ("should", "recommend", "you ought", "prefer to"):
        assert banned not in out
