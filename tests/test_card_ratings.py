"""Wave A: Capability and active-Event effective-rating modifiers (1.9.1).

These exercise ratings.rating, which sums printed + Special-Vassal +
Capability + active-Event modifiers, with an optional ``action`` context for
Parley-scoped mods.
"""

from __future__ import annotations

from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus


def _put(state, lord_id, location, favour=None):
    ls = state.lords[lord_id]
    ls.status = LordStatus.MUSTERED.value
    ls.location = location
    if favour is not None:
        state.locales[location].favour = favour


def test_thomas_bourchier_command_plus_one():
    from plantagenet import ratings
    s = build_initial_state("henry_vi")
    base = ratings.rating(s, "somerset_1", "command")
    s.lords["somerset_1"].capabilities = ["Y5"]   # THOMAS BOURCHIER
    assert ratings.rating(s, "somerset_1", "command") == base + 1


def test_yorks_favoured_son_influence_and_command():
    from plantagenet import ratings
    s = build_initial_state("warwicks_rebellion")
    bi = ratings.rating(s, "gloucester_1", "influence")
    bc = ratings.rating(s, "gloucester_1", "command")
    s.lords["gloucester_1"].capabilities = ["Y20"]  # YORK'S FAVOURED SON
    assert ratings.rating(s, "gloucester_1", "influence") == bi + 1
    assert ratings.rating(s, "gloucester_1", "command") == bc + 1


def test_fair_arbiter_only_at_friendly_locale():
    from plantagenet import ratings
    s = build_initial_state("henry_vi")
    s.lords["salisbury"].capabilities = ["Y22"]     # FAIR ARBITER (Salisbury)
    base = build_initial_state("henry_vi")
    base_inf = ratings.rating(base, "salisbury", "influence")
    # Not at a Friendly Locale -> no bonus.
    _put(s, "salisbury", "york", favour="yorkist")  # salisbury is Yorkist here? check side
    side = s.lords["salisbury"].side
    s.locales["york"].favour = side
    assert ratings.rating(s, "salisbury", "influence") == base_inf + 1
    # Flip the Locale to neutral -> bonus gone.
    s.locales["york"].favour = "neutral"
    assert ratings.rating(s, "salisbury", "influence") == base_inf


def test_fallen_brother_requires_clarence_removed():
    from plantagenet import ratings
    s = build_initial_state("warwicks_rebellion")
    s.lords["gloucester_1"].capabilities = ["Y26"]  # FALLEN BROTHER
    base = ratings.rating(build_initial_state("warwicks_rebellion"),
                          "gloucester_1", "influence")
    assert ratings.rating(s, "gloucester_1", "influence") == base   # Clarence alive
    s.lords["clarence"].status = LordStatus.REMOVED.value
    assert ratings.rating(s, "gloucester_1", "influence") == base + 2


def test_in_the_name_of_the_king_is_parley_scoped():
    from plantagenet import ratings
    s = build_initial_state("henry_vi")
    s.lords["somerset_1"].capabilities = ["L11"]    # IN THE NAME OF THE KING
    base = ratings.rating(build_initial_state("henry_vi"), "somerset_1", "influence")
    assert ratings.rating(s, "somerset_1", "influence") == base          # generic
    assert ratings.rating(s, "somerset_1", "influence", action="parley") == base + 1


def test_expert_counsellors_and_veteran_valour_plus_two():
    from plantagenet import ratings
    s = build_initial_state("henry_vi")
    base = ratings.rating(build_initial_state("henry_vi"), "somerset_1", "valour")
    s.lords["somerset_1"].capabilities = ["L13"]    # EXPERT COUNSELLORS
    assert ratings.rating(s, "somerset_1", "valour") == base + 2
    s.lords["somerset_1"].capabilities = ["L20"]    # VETERAN OF FRENCH WARS
    assert ratings.rating(s, "somerset_1", "valour") == base + 2


def test_married_to_a_neville_needs_friendly_locale_with_warwick():
    from plantagenet import ratings
    s = build_initial_state("warwicks_rebellion")
    clar = s.lords["clarence"]
    clar.capabilities = ["L24"]                     # MARRIED TO A NEVILLE
    base = ratings.rating(build_initial_state("warwicks_rebellion"),
                          "clarence", "influence")
    loc = clar.location
    s.locales[loc].favour = clar.side               # Friendly Locale
    assert ratings.rating(s, "clarence", "influence") == base   # no Warwick yet
    _put(s, "warwick_lancastrian", loc, favour=clar.side)       # Warwick joins
    assert ratings.rating(s, "clarence", "influence") == base + 2
    assert ratings.rating(s, "clarence", "command") == \
        ratings.rating(build_initial_state("warwicks_rebellion"), "clarence", "command") + 1


def test_loyal_somerset_same_locale_as_margaret():
    from plantagenet import ratings
    s = build_initial_state("warwicks_rebellion")
    som = s.lords["somerset_2"]
    som.capabilities = ["L28"]                      # LOYAL SOMERSET
    base = ratings.rating(build_initial_state("warwicks_rebellion"),
                          "somerset_2", "valour")
    _put(s, "somerset_2", "york")
    assert ratings.rating(s, "somerset_2", "valour") == base    # Margaret elsewhere
    _put(s, "margaret", "york")
    assert ratings.rating(s, "somerset_2", "valour") == base + 1


def test_active_event_richard_of_york_parley_only():
    from plantagenet import ratings
    s = build_initial_state("warwicks_rebellion")
    side = s.lords["gloucester_1"].side
    base = ratings.rating(s, "gloucester_1", "influence")
    s.active_events.append({"card": "Y14", "side": side})   # RICHARD OF YORK
    assert ratings.rating(s, "gloucester_1", "influence") == base            # generic
    assert ratings.rating(s, "gloucester_1", "influence", action="parley") == base + 1


def test_active_event_privy_council_all_influence():
    from plantagenet import ratings
    s = build_initial_state("warwicks_rebellion")
    side = s.lords["gloucester_1"].side
    base = ratings.rating(s, "gloucester_1", "influence")
    s.active_events.append({"card": "Y35", "side": side})   # PRIVY COUNCIL
    assert ratings.rating(s, "gloucester_1", "influence") == base + 1
    # ...but not for the opposing side.
    other = next(lo for lo in s.lords if s.lords[lo].side != side)
    base_o = ratings.rating(build_initial_state("warwicks_rebellion"), other, "influence")
    assert ratings.rating(s, other, "influence") == base_o
