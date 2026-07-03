"""6.2.2 REPLACE is a card swap of a living Lord, not a removal.

Rules basis (Rules of Play):
- 6.2.2 REMOVE: "An Heir (6.2.1) removed by Death or Shipwreck (4.4.3, 4.8.2)
  is permanently out of the game and may not return in future Wars."
- 6.2.2 REPLACE: "To replace a Lord 'in place', swap Lord cards on the mat
  currently in use, cylinders in place on the gameboard, and Command cards
  where they are..."
- 6.2.1 Heir #2: "March or Edward IV (eldest son of York)" -- one person, two
  cards; IIIL even swaps the card back ("If Edward IV is present from the
  second War, replace him with March").
- IIIY/IIIL Influence Tracks: "each Heir (6.2.1, not Warwick) removed in an
  earlier War by Death, Shipwreck, or Natural Causes ... costs that side -8" --
  REPLACE is not among the charging causes.

The engine retires a replaced card with LordStatus.REMOVED (mat bookkeeping),
so carry-over must use the replaced_cards ledger to tell a retired card from a
dead Heir. Regression for the 2026-07-02 adjudication.
"""

from __future__ import annotations

from plantagenet import battle, influence, succession
from plantagenet.scenarios import build_initial_state, renew_war
from plantagenet.state import LordStatus


def _iiy_after_york_died_in_war_i():
    s = build_initial_state("wars_of_the_roses", seed=3)
    s.lords["york"].status = LordStatus.REMOVED.value
    s.victory = {"result": "yorkist"}
    n = renew_war(s)                     # IIY: March highest Heir -> Edward IV King
    assert n.grand_scenario["current_war"] == "war_iiy"
    return n


def test_living_replace_is_recorded_and_edward_iv_reigns():
    n = _iiy_after_york_died_in_war_i()
    assert n.grand_scenario["replaced_cards"] == {"march": "edward_iv"}
    assert n.lords["edward_iv"].status == LordStatus.MUSTERED
    assert n.lords["edward_iv"].location == "london"
    assert n.lords["march"].status == LordStatus.REMOVED    # card retired, person alive


def test_replaced_march_keeps_the_heir_slot_and_pays_no_penalty_in_iiiy():
    n = _iiy_after_york_died_in_war_i()
    n.victory = {"result": "yorkist"}
    lanc_before = influence._net_lanc(n.influence["track"])
    nn = renew_war(n)                                        # IIIY
    assert nn.grand_scenario["current_war"] == "war_iiiy"
    # The March/Edward IV slot SURVIVES through Edward IV: he sets up as King.
    assert nn.lords["edward_iv"].status == LordStatus.MUSTERED
    assert nn.lords["edward_iv"].location == "london"
    # Only York (dead) costs -8. Before the fix, March was billed too (-16).
    lanc_after = influence._net_lanc(nn.influence["track"])
    assert lanc_after - lanc_before == 8                     # one Yorkist -8, not two


def test_general_next_heir_ignores_replaced_cards():
    n = _iiy_after_york_died_in_war_i()
    # Force the discriminating shape: Rutland off-map AVAILABLE. The rank-2
    # slot [march(replaced), edward_iv(Mustered)] must answer "Heir in play ->
    # nobody new enters", NOT skip to Rutland.
    n.lords["rutland"].status = LordStatus.AVAILABLE.value
    n.lords["rutland"].location = None
    assert succession._general_next_heir(n, "yorkist", "york") is None
    assert n.lords["rutland"].status == LordStatus.AVAILABLE  # not calendared


def test_death_triggered_replacement_keeps_the_dead_heir_removed():
    # IIL: "Any removal of Somerset (1) ... replaces Somerset (1) with
    # Somerset (2) in place (6.2.2)". The REPLACE here rides a real Death:
    # Somerset (1) must stay a removed Heir (and cost -8 at IIIL), while
    # Somerset (2) carries on.
    s = build_initial_state("wars_of_the_roses", seed=3)
    s.victory = {"result": "lancastrian"}
    n = renew_war(s)                                         # IIL
    assert n.lords["somerset_1"].status == LordStatus.MUSTERED
    battle._kill_lord(n, "somerset_1")
    assert n.lords["somerset_1"].status == LordStatus.REMOVED
    assert "somerset_1" not in (n.grand_scenario.get("replaced_cards") or {})
    n.victory = {"result": "lancastrian"}
    nn = renew_war(n)                                        # IIIL: starts at 0, then -8
    assert influence._net_lanc(nn.influence["track"]) == -8
