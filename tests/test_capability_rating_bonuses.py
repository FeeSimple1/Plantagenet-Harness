"""Card-capability rating bonuses (closes mutation survivors in ratings.py).

Coverage-guided mutation testing (scripts/mutation_cov.py) found a survivor
cluster in the capability rating helpers: the exact bonus VALUES and the
"... or in the same Exile box as <Lord>" alternative clauses (L24 Married to a
Neville, L28 Loyal Somerset) were never asserted, and neither were the Y22 / Y26
bonuses. These white-box tests pin each helper's output so a wrong value or a
flipped condition is caught.
"""

from __future__ import annotations

from plantagenet import ratings
from plantagenet.scenarios import build_initial_state


def _state():
    return build_initial_state("wars_of_the_roses", seed=1)


def _inject(state, src_id, new_id, **fields):
    ls = state.lords[src_id].model_copy(deep=True)
    ls.lord_id = new_id
    for k, v in fields.items():
        setattr(ls, k, v)
    state.lords[new_id] = ls
    return ls


# ------------------------------------------------- L28 Loyal Somerset (Margaret)
def test_loyal_somerset_same_exile_box_as_margaret():
    s = _state()
    s.lords["somerset_1"].location = None
    s.lords["somerset_1"].exile_box = "ireland"
    _inject(s, "somerset_1", "margaret", location=None, exile_box="ireland")
    assert ratings._cap_loyal_somerset(s, "somerset_1", None) == {"influence": 1, "valour": 1}


def test_loyal_somerset_different_exile_box_gives_nothing():
    s = _state()
    s.lords["somerset_1"].location = None
    s.lords["somerset_1"].exile_box = "ireland"
    _inject(s, "somerset_1", "margaret", location=None, exile_box="calais")
    assert ratings._cap_loyal_somerset(s, "somerset_1", None) == {}


# ------------------------------------------- L24 Married to a Neville (Warwick)
def test_married_to_a_neville_same_exile_box_as_warwick():
    s = _state()
    clarence = _inject(s, "somerset_1", "clarence", location=None, exile_box="ireland")
    clarence.side = "yorkist"
    s.lords["warwick_yorkist"].location = None
    s.lords["warwick_yorkist"].exile_box = "ireland"
    assert ratings._cap_married_to_a_neville(s, "clarence", None) == {
        "influence": 2, "command": 1}


def test_married_to_a_neville_apart_from_warwick_gives_nothing():
    s = _state()
    _inject(s, "somerset_1", "clarence", location=None, exile_box="ireland")
    s.lords["warwick_yorkist"].location = None
    s.lords["warwick_yorkist"].exile_box = "calais"
    assert ratings._cap_married_to_a_neville(s, "clarence", None) == {}


# ------------------------------------------------------- Y22 Fair Arbiter
def test_fair_arbiter_only_when_at_friendly_favour():
    s = _state()
    lid = "salisbury"
    s.lords[lid].status = "mustered"
    s.lords[lid].location = "london"
    s.locales["london"].favour = s.lords[lid].side
    assert ratings._cap_fair_arbiter(s, lid, None) == {"influence": 1, "lordship": 1}
    s.locales["london"].favour = ("yorkist" if s.lords[lid].side == "lancastrian"
                                  else "lancastrian")
    assert ratings._cap_fair_arbiter(s, lid, None) == {}


# ------------------------------------------------------- Y26 Fallen Brother
def test_fallen_brother_requires_clarence_removed():
    s = _state()
    _inject(s, "somerset_1", "clarence", status="removed")
    assert ratings._cap_fallen_brother(s, "warwick_yorkist", None) == {
        "influence": 2, "lordship": 1}
    s.lords["clarence"].status = "mustered"
    assert ratings._cap_fallen_brother(s, "warwick_yorkist", None) == {}


# ------------------------------------------------- Y5 Thomas Bourchier (Friendly City)
def test_thomas_bourchier_only_at_friendly_city():
    s = _state()
    lid = "salisbury"
    s.lords[lid].status = "mustered"
    s.lords[lid].location = "canterbury"            # a City
    s.locales["canterbury"].favour = s.lords[lid].side
    assert ratings._cap_thomas_bourchier(s, lid, None) == {"command": 1}
    s.locales["canterbury"].favour = "neutral"      # not Friendly -> nothing
    assert ratings._cap_thomas_bourchier(s, lid, None) == {}


# ------------------------------------------------- simple fixed-value capabilities
def test_fixed_value_capabilities():
    s = _state()
    assert ratings._cap_yorks_favoured_son(s, "salisbury", None) == {
        "influence": 1, "command": 1}
    assert ratings._cap_expert_counsellors(s, "salisbury", None) == {"valour": 2}
    assert ratings._cap_veteran_of_french_wars(s, "salisbury", None) == {"valour": 2}


def test_in_the_name_of_the_king_only_for_parley():
    s = _state()
    assert ratings._cap_in_the_name_of_the_king(s, "salisbury", "parley") == {"influence": 1}
    assert ratings._cap_in_the_name_of_the_king(s, "salisbury", "battle") == {}


# ------------------------------------------------- active-Event rating modifiers
def test_event_rating_modifiers():
    s = _state()
    ev = {"side": "yorkist", "card": "Y14"}
    assert ratings._ev_richard_of_york(s, ev, "salisbury", "parley") == {"influence": 1}
    assert ratings._ev_richard_of_york(s, ev, "salisbury", "battle") == {}
    assert ratings._ev_privy_council(s, ev, "salisbury", None) == {"influence": 1}
    assert ratings._ev_yorkist_parade(s, ev, "salisbury", None) == {"influence": 2}


def test_loyalty_and_trust_targets_one_lord():
    s = _state()
    assert ratings._ev_loyalty_and_trust(s, {"target": "salisbury"}, "salisbury", None) == {
        "lordship": 3}
    assert ratings._ev_loyalty_and_trust(s, {"target": "salisbury"}, "warwick_yorkist", None) == {}


def test_edward_v_promotes_only_gloucester():
    s = _state()
    assert ratings._ev_edward_v(s, {}, "gloucester_1", None) == {"lordship": 3}
    assert ratings._ev_edward_v(s, {}, "gloucester_2", None) == {"lordship": 3}
    assert ratings._ev_edward_v(s, {}, "salisbury", None) == {}


def test_loc_friendly_false_when_lord_has_no_location():
    """_loc_friendly returns False for a Lord not on the map (kills the
    `return False` -> `return True` mutant on the no-location guard)."""
    s = _state()
    s.lords["salisbury"].status = "mustered"
    s.lords["salisbury"].location = None
    s.lords["salisbury"].exile_box = None
    assert ratings._loc_friendly(s, "salisbury") is False
    assert ratings._cap_fair_arbiter(s, "salisbury", None) == {}


def test_loyal_somerset_co_located_with_margaret_on_the_map():
    """The location-based Loyal Somerset branch (Somerset at the same Locale as
    Margaret), distinct from the Exile-box branch above."""
    s = _state()
    s.lords["somerset_1"].status = "mustered"
    s.lords["somerset_1"].location = "london"
    s.lords["somerset_1"].exile_box = None
    _inject(s, "somerset_1", "margaret", status="mustered", location="london",
            exile_box=None)
    assert ratings._cap_loyal_somerset(s, "somerset_1", None) == {
        "influence": 1, "valour": 1}
    s.lords["margaret"].location = "york"          # apart -> no bonus
    assert ratings._cap_loyal_somerset(s, "somerset_1", None) == {}
