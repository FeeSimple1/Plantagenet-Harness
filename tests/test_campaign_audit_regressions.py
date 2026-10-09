"""Regression cases for the October 2026 campaign and Succession audit."""

from __future__ import annotations

import pytest

from plantagenet import actions, battle, campaign, succession
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import CampaignState, LordStatus


def _give_capability(state, lord_id, card):
    for deck in state.decks.values():
        for pile in deck.values():
            if card in pile:
                pile.remove(card)
    state.lords[lord_id].capabilities.append(card)


@pytest.mark.parametrize("scourers,expected", [(True, 1), (False, 0)])
def test_failed_forage_scourers_bonus_without_depletion(scourers, expected):
    """Y13 Tips / 4.6.2: failure adds the mandatory Scourers bonus, never Depletion."""
    state = build_initial_state("henry_vi", seed=1)
    state.phase = "campaign"
    state.active_side = "yorkist"
    state.campaign = CampaignState(step="activation", active_lord="york", actions_remaining=2)
    lord = state.lords["york"]
    lord.assets["provender"] = 0
    state.locales[lord.location].favour = "neutral"
    state.locales[lord.location].depletion = "depleted"
    if scourers:
        _give_capability(state, "york", "Y13")

    result = actions.apply_action(state, {"type": "forage", "side": "yorkist"})

    assert result["roll"] == 6 and result["success"] is False
    assert result["provender_added"] == expected
    assert state.lords["york"].assets["provender"] == expected
    assert state.locales[lord.location].depletion == "depleted"
    assert state.campaign.actions_remaining == 1


def _charity_position():
    state = build_initial_state("henry_vi")
    state.phase = "campaign"
    state.campaign = CampaignState(step="end")
    state.lords["march"].location = state.lords["york"].location
    _give_capability(state, "york", "Y4")
    state.lords["york"].assets["provender"] = 0
    state.lords["march"].assets["provender"] = 2
    return state


def test_charity_spends_explicitly_shared_provender_at_campaign_end():
    """Y4 / 1.5.3 / 4.8.1: Charity may spend a colocated Friendly Lord's Provender."""
    state = _charity_position()
    base = campaign.tides_of_war(state)["points"]["yorkist"]

    result = actions.apply_action(state, {
        "type": "end_campaign",
        "decisions": {"charity": {"york": {"pay": 2, "share": ["march"]}}},
    })

    tides = result["tides_of_war"]
    assert tides["points"]["yorkist"] == base + 2
    assert tides["charity"] == {"york": {"paid": 2, "from": {"march": 2}}}
    assert state.lords["york"].assets["provender"] == 0
    assert state.lords["march"].assets["provender"] == 0


def test_charity_consumes_holder_then_named_providers_and_reports_sources():
    """Y4 / 1.5.3: spend only the authorized amount, leaving surplus on its mat."""
    state = _charity_position()
    state.lords["york"].assets["provender"] = 1

    result = campaign.tides_of_war(state, {
        "charity": {"york": {"pay": 2, "share": ["march"]}},
    })

    assert state.lords["york"].assets["provender"] == 0
    assert state.lords["march"].assets["provender"] == 1
    assert result["charity"]["york"]["from"] == {"york": 1, "march": 1}


@pytest.mark.parametrize("provider,error", [
    ("salisbury", "share_not_co_located"),
    ("henry_vi", "bad_share"),
])
def test_charity_rejects_remote_and_enemy_sharing(provider, error):
    """Y4 / 1.5.3: only colocated Friendly Mustered Lords may Share."""
    state = _charity_position()
    state.lords["salisbury"].status = LordStatus.MUSTERED
    state.lords["salisbury"].calendar_box = None
    state.lords["salisbury"].location = "york"
    state.lords["henry_vi"].location = state.lords["york"].location
    before = {lid: dict(lord.assets) for lid, lord in state.lords.items()}

    with pytest.raises(IllegalAction) as exc:
        campaign.tides_of_war(state, {
            "charity": {"york": {"pay": 2, "share": [provider]}},
        })

    assert exc.value.code == error
    assert {lid: lord.assets for lid, lord in state.lords.items()} == before


@pytest.mark.parametrize("choice,error", [
    (2, "no_provender"),
    ({"pay": 2, "share": ["march", "march"]}, "bad_share"),
    ({"pay": 2, "share": "march"}, "bad_share"),
    ({"pay": 3, "share": ["march"]}, "bad_charity"),
])
def test_charity_requires_valid_explicit_sharing(choice, error):
    """Y4 / 1.5.3: sharing is optional, costs 0–2, and cannot count an Asset twice."""
    state = _charity_position()
    with pytest.raises(IllegalAction) as exc:
        campaign.tides_of_war(state, {"charity": {"york": choice}})
    assert exc.value.code == error
    assert state.lords["march"].assets["provender"] == 2


def _war_iiy():
    state = build_initial_state("wars_of_the_roses")
    state.victory = {"result": "yorkist"}
    state.phase = "over"
    return renew_war(state)


def test_war_iiy_margaret_arrival_adds_all_continuous_cards_once():
    """E4 Lancastrian Succession / 6.2.2: Margaret present adds L27, L28, L31."""
    state = _war_iiy()
    state.turn_box = 9
    henry = state.lords["henry_vi"]
    henry.status = LordStatus.MUSTERED
    henry.exile_box = "scotland"
    henry.calendar_box = None
    henry.calendar_exile = False
    battle._kill_lord(state, "henry_vi")

    assert state.lords["margaret"].status == LordStatus.CALENDAR
    assert state.lords["margaret"].calendar_box == 10
    for card in ("L27", "L28", "L31"):
        assert state.decks["lancastrian"]["draw"].count(card) == 1
        assert state.grand_scenario["deck_sources"]["lancastrian"][card] == ["margaret"]
    assert not any(card in pile for card in ("L17", "L18", "L20", "L21")
                   for pile in state.decks["lancastrian"].values())

    # E2 ARTS OF WAR: already-present cards remain in their current zones.
    state.decks["lancastrian"]["draw"].remove("L31")
    state.active_events.append({"card": "L31", "side": "lancastrian", "scope": "this_campaign"})
    succession._recompute(state, "lancastrian")
    assert all("L31" not in pile for pile in state.decks["lancastrian"].values())
    assert state.decks["lancastrian"]["draw"].count("L27") == 1
