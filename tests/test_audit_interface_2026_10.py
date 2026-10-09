"""October audit: action atomicity and Renewed War (6.1.2) consumer integration."""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from plantagenet import actions, legal_moves
from plantagenet.cli import app
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import GameState
from tests._helpers import to_muster
from tests.test_sail_cross_sea import _sailor_at


def test_invalid_parley_preserves_one_shot_event_and_references():
    """Y18's one Parley per Lord cannot be consumed by a rejected action."""
    s = build_initial_state('henry_vi')
    to_muster(s)
    s.active_side = 'yorkist'
    s.active_events = [{'card': 'Y18', 'side': 'yorkist', 'scope': 'this_levy'}]
    event = s.active_events[0]
    before = s.to_json()
    with pytest.raises(IllegalAction, match='unknown_target'):
        actions.apply_action(s, {'type': 'parley', 'side': 'yorkist',
                                 'by_lord': 'york', 'target': 'no_such_place'})
    assert s.to_json() == before
    assert event is s.active_events[0] and 'used' not in event


def test_invalid_action_preserves_held_event_window():
    """L28 remains playable after an invalid request, with no accepted move intervening."""
    s, lid = _sailor_at('bristol')
    actions.apply_action(s, {'type': 'sail', 'side': 'lancastrian',
                             'by_lord': lid, 'to': 'pembroke'})
    before = s.to_json()
    with pytest.raises(IllegalAction, match='unknown_action'):
        actions.apply_action(s, {'type': 'typo'})
    assert s.to_json() == before
    assert s.hold_window is not None


def test_partial_mutation_and_dice_are_rolled_back(monkeypatch):
    """The action contract restores board, RNG and log after rejection at any depth."""
    s = build_initial_state('henry_vi')
    lord = s.lords['york']
    assets = lord.assets
    history = s.history
    before = s.to_json()

    def reject_after_effects(state, action):
        state.lords['york'].assets['coin'] = 999
        roller = state.dice()
        roller.d6()
        state.store_dice(roller)
        state.history.append({'partial': True})
        raise IllegalAction('bad_choice', 'invalid follow-up choice')

    monkeypatch.setitem(actions._HANDLERS, 'test_rejection', reject_after_effects)
    with pytest.raises(IllegalAction, match='bad_choice'):
        actions.apply_action(s, {'type': 'test_rejection'})
    assert s.to_json() == before
    assert s.lords['york'] is lord and lord.assets is assets
    assert s.history is history


def test_renewed_war_action_preserves_history_and_survives_save(tmp_path):
    """6.1.2: decisive first and second Wars continue through the public action API."""
    s = build_initial_state('wars_of_the_roses', seed=12)
    for expected in ('war_iiy', 'war_iiiy'):
        actions.apply_action(s, {'type': 'concede', 'side': 'lancastrian'})
        old_history = list(s.history)
        assert legal_moves.legal_moves(s) == [{'type': 'renew_war'}]
        result = actions.apply_action(s, {'type': 'renew_war'})
        assert result['to_war'] == expected
        assert s.phase == 'levy' and s.victory is None
        assert s.history[:-1] == old_history
        path = tmp_path / 'state.json'
        s.save(path)
        s = GameState.load(path)
        assert s.grand_scenario['current_war'] == expected
        assert legal_moves.legal_moves(s)
    s.phase = 'over'
    s.victory = {'result': 'yorkist'}
    assert legal_moves.legal_moves(s) == []
    before = s.to_json()
    with pytest.raises(IllegalAction, match='game_over'):
        actions.apply_action(s, {'type': 'renew_war'})
    assert s.to_json() == before


def test_renew_war_rejects_unfinished_standalone_and_draw():
    """6.1.2: renew only a completed, decisive, nonfinal grand-scenario War."""
    s = build_initial_state('wars_of_the_roses')
    with pytest.raises(IllegalAction, match='war_not_over'):
        actions.apply_action(s, {'type': 'renew_war'})
    s.phase, s.victory = 'over', {'result': None}
    assert legal_moves.legal_moves(s) == []
    with pytest.raises(IllegalAction, match='no_winner'):
        actions.apply_action(s, {'type': 'renew_war'})
    s = build_initial_state('henry_vi')
    s.phase, s.victory = 'over', {'result': 'yorkist'}
    assert legal_moves.legal_moves(s) == []
    with pytest.raises(IllegalAction, match='not_grand'):
        actions.apply_action(s, {'type': 'renew_war'})


def test_renew_war_cli(tmp_path):
    """6.1.2: CLI persists the new War and its transition history."""
    s = build_initial_state('wars_of_the_roses')
    actions.apply_action(s, {'type': 'concede', 'side': 'lancastrian'})
    path = tmp_path / 'game.json'
    s.save(path)
    result = CliRunner().invoke(app, ['renew-war', str(path)])
    assert result.exit_code == 0, result.stdout
    assert json.loads(result.stdout)['to_war'] == 'war_iiy'
    reloaded = GameState.load(path)
    assert reloaded.grand_scenario['current_war'] == 'war_iiy'
    assert reloaded.history[-1]['action']['type'] == 'renew_war'


def test_immediate_events_offered_in_draw_order_only():
    """3.1.3: the move palette resolves the first pending Event before the second."""
    s = build_initial_state('henry_vi')
    s.pending_events = [{'side': s.active_side, 'card': 'Y23'},
                        {'side': s.active_side, 'card': 'Y31'}]
    assert legal_moves.legal_moves(s) == [
        {'type': 'play_event', 'side': s.active_side, 'card': 'Y23'}]
