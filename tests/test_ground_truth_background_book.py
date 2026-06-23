"""Ground-truth replay: GMT Background Book "Examples of Play" (pp. 5-12).

This is the one validation that checks the harness against an AUTHORITATIVE
external source -- the published worked example of a complete turn of Scenario Ia
"Henry VI" -- rather than against the code's own reading of the rules. The Arts
of War draw and dice are randomised, so we verify the DETERMINISTIC outcomes the
example states (setup, ratings, table yields, action results, cost formulas).
Each assertion cites the Background Book.
"""

from __future__ import annotations

from plantagenet import actions, campaign, influence, ratings, static_data
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus
from tests._helpers import to_muster


# ----------------------------------------------------------------- setup
def test_initial_setup_matches_background_book():
    """p.5-6: Yorkists have York (Ely) and March (Ludlow) on the map; the
    Lancastrians have Henry VI and Somerset (both London); Northumberland and
    Rutland are on the Calendar, not the map."""
    s = build_initial_state("henry_vi", seed=1)
    on_map = {lid: v.location for lid, v in s.lords.items()
              if v.status == LordStatus.MUSTERED}
    assert on_map == {"york": "ely", "march": "ludlow",
                      "henry_vi": "london", "somerset_1": "london"}
    assert s.lords["northumberland_lancastrian"].status == LordStatus.CALENDAR
    assert s.lords["rutland"].status == LordStatus.CALENDAR


def test_printed_ratings_match_background_book():
    """Ratings cited through the example: York Ldr3/Cmd2/Val2, March Ldr2/Cmd2/
    Inf2/Val3, Henry VI Ldr2/Cmd2/Inf5/Val0, Somerset Ldr2/Inf5/Val2."""
    lords = static_data.load_lords()
    def r(lid):
        return lords[lid]["ratings"]
    assert (r("york")["lordship"], r("york")["command"], r("york")["valour"]) == (3, 2, 2)
    assert (r("march")["lordship"], r("march")["command"],
            r("march")["influence"], r("march")["valour"]) == (2, 2, 2, 3)
    assert (r("henry_vi")["lordship"], r("henry_vi")["command"],
            r("henry_vi")["influence"], r("henry_vi")["valour"]) == (2, 2, 5, 0)
    assert (r("somerset_1")["lordship"], r("somerset_1")["influence"],
            r("somerset_1")["valour"]) == (2, 5, 2)


# ----------------------------------------------------------- table yields
def test_stronghold_yields_match_background_book():
    """p.7,10-11: Ely (City) Levy Troops -> 1 Longbow + 1 Militia; Supply yields
    London 3 Provender, Winchester (City) 2 Provender."""
    assert static_data.stronghold_yields("ely")["levy_troops"] == {"longbow": 1, "militia": 1}
    assert static_data.stronghold_yields("london")["supply"]["provender"] == 3
    assert static_data.stronghold_yields("winchester")["supply"]["provender"] == 2


def test_force_profiles_match_background_book():
    """p.11-12: Longbowmen 2 Missile Hits each, Militia 1/2 Hit each; Men-at-Arms
    Protection 1-3, Retinue 1-4."""
    forces = static_data.load_forces()
    def archery(f):
        return next((st["count"] for st in forces[f]["strikes"]
                     if st["kind"] == "archery"), 0)
    assert archery("longbow") == 2
    assert archery("militia") == 0.5
    assert forces["men_at_arms"]["protection"] == [1, 3]
    assert forces["retinue"]["protection"] == [1, 4]


def test_missile_hit_total_matches_background_book():
    """p.11: 5 Longbowmen (2 each) + 4 Militia (1/2 each) = 12 Missile Hits."""
    forces = static_data.load_forces()
    lb = next(st["count"] for st in forces["longbow"]["strikes"] if st["kind"] == "archery")
    mi = next(st["count"] for st in forces["militia"]["strikes"] if st["kind"] == "archery")
    assert 5 * lb + 4 * mi == 12


# --------------------------------------------------------- driven actions
def test_levy_transport_and_troops_match_background_book():
    """p.6-7: York's Levy Transport (not at a Port) adds 2 Carts; his Levy Troops
    at Ely (City) adds 1 Longbow + 1 Militia and Depletes Ely."""
    s = build_initial_state("henry_vi", seed=3)
    to_muster(s)
    york = s.lords["york"]
    carts0 = york.assets.get("cart", 0)
    before = dict(york.forces)
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "cart"})
    assert york.assets["cart"] == carts0 + 2
    actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    added = {k: york.forces.get(k, 0) - before.get(k, 0)
             for k in ("longbow", "militia")}
    assert added == {"longbow": 1, "militia": 1}
    assert s.locales["ely"].depletion == "depleted"


def test_feed_requirement_matches_background_book():
    """p.10: York Feeds 8 Troops with 2 Provender (1 Provender per 6 Troops,
    rounded up). Retinue does not count toward the requirement."""
    s = build_initial_state("henry_vi", seed=1)
    york = s.lords["york"]
    york.location = "ely"
    s.locales["ely"].favour = "yorkist"
    york.forces = {"retinue": 1, "men_at_arms": 8}      # 8 Troops (Retinue excluded)
    york.assets = {**york.assets, "provender": 2}
    york.moved_fought = True
    res = campaign._feed(s, "yorkist")
    fed = next(f for f in res["fed"] if f["lord"] == "york")
    assert fed["needed"] == 2
    assert york.assets.get("provender", 0) == 0          # exactly 2 consumed


def test_influence_check_costs_match_background_book():
    """p.7-10 cost formula (1 base + Ways + extra spend; Loyalty modifies the
    rating, not the cost):
      - March Parley Ludlow->Shrewsbury (1 Way, +1 extra) = 3 IP
      - March Levy Vassal Shrewsbury  (0 Ways, +3 extra, Loyalty -1) = 4 IP
      - Henry VI Parley St Albans     (1 Way, no extra) = 2 IP
      - Henry VI Tax St Albans        (0 Ways, no extra) = 1 IP
    """
    s = build_initial_state("henry_vi", seed=3)
    assert influence.check_influence(s, "march", "yorkist",
                                     way_cost=1, extra_spend=1)["spent"] == 3
    s = build_initial_state("henry_vi", seed=3)
    assert influence.check_influence(s, "march", "yorkist", way_cost=0,
                                     extra_spend=3, loyalty_mod=-1)["spent"] == 4
    s = build_initial_state("henry_vi", seed=3)
    assert influence.check_influence(s, "henry_vi", "lancastrian",
                                     way_cost=1, extra_spend=0)["spent"] == 2
    s = build_initial_state("henry_vi", seed=3)
    assert influence.check_influence(s, "henry_vi", "lancastrian",
                                     way_cost=0, extra_spend=0)["spent"] == 1


# ----------------------------------------------------- capability effects
def test_capability_effects_match_background_book():
    """p.6,9: Thomas Bourchier (Y5) raises York's Command from 2 to 3 when he
    starts at a Friendly City; York's Favoured Son (Y20) gives March +1 Influence
    and +1 Command."""
    s = build_initial_state("henry_vi", seed=1)
    york = s.lords["york"]
    york.status = LordStatus.MUSTERED
    york.location = "ely"                        # a City
    s.locales["ely"].favour = "yorkist"          # Friendly
    base_cmd = ratings.rating(s, "york", "command")
    york.capabilities = ["Y5"]
    assert ratings.rating(s, "york", "command") == base_cmd + 1 == 3

    march = s.lords["march"]
    march.capabilities = ["Y20"]
    assert ratings.rating(s, "march", "influence") == 2 + 1
    assert ratings.rating(s, "march", "command") == 2 + 1
