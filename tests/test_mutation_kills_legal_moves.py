"""Mutation-survivor killers for legal_moves.py (see mutation-results/).

Each test pins menu contents the enumerator must emit (or suppress) in a
concrete reachable state; over-enumeration is behavioral (agents act on the
menu), so both missing and phantom entries are asserted against.
"""

from __future__ import annotations

from plantagenet import legal_moves
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordState, LordStatus


def _muster_state(seed=1):
    s = build_initial_state("henry_vi", seed=seed)
    s.phase = "levy"
    s.levy_step = "muster"
    s.active_side = "yorkist"
    return s


def _by(moves, lord_id, mtype=None):
    return [m for m in moves if m.get("by_lord") == lord_id
            and (mtype is None or m["type"] == mtype)]


def test_lord_that_already_mustered_this_segment_gets_no_levy_moves():
    # L79 bool Or->And: a Lord with mustered_this_segment set must be skipped.
    s = _muster_state()
    s.lords["york"].mustered_this_segment = True
    moves = legal_moves.legal_moves(s)
    assert _by(moves, "york") == []
    assert _by(moves, "march")            # the other Yorkist Lord still enumerates


def test_be_sent_for_allows_muster_exiles_from_later_boxes():
    # L88 cmp Eq->NotEq: BE SENT FOR (L4) is a Lancastrian-only relaxation.
    s = build_initial_state("wars_of_the_roses", seed=1)
    s.phase = "levy"
    s.levy_step = "muster"
    s.active_side = "lancastrian"
    som = s.lords["somerset_1"]
    som.status = LordStatus.CALENDAR
    som.location = None
    som.calendar_box = 5                  # later than turn_box 1
    som.calendar_exile = True
    assert not any(m["type"] == "muster_exiles" and m["lords"] == ["somerset_1"]
                   for m in legal_moves.legal_moves(s))
    s.active_events.append({"card": "L4", "side": "lancastrian"})   # BE SENT FOR
    assert any(m["type"] == "muster_exiles" and m["lords"] == ["somerset_1"]
               for m in legal_moves.legal_moves(s))


def test_stanley_free_levy_troops_with_lordship_exhausted():
    # L131 cmp Eq->NotEq / int 0->1: Thomas Stanley's free Levy Troops (L35)
    # must survive when the Lord has spent all Lordship at a Stronghold.
    s = _muster_state()
    york = s.lords["york"]
    york.lordship_spent = 99
    york.special_vassals.append("thomas_stanley")
    moves = legal_moves.legal_moves(s)
    assert _by(moves, "york", "levy_troops")


def test_levy_lord_targets_exactly_the_ready_friendly_calendar_lords():
    # L143 Eq->NotEq (side/status), L144 IsNot->Is + LtE->Lt, L146 Or->And.
    s = _muster_state()
    s.lords["salisbury"].calendar_box = 1              # ready exactly this box
    s.lords["northumberland_lancastrian"].calendar_box = 1   # enemy: never a target
    # An enemy Lord stands on Salisbury's Seat: the seat-fallback (a Friendly
    # Enemy-free Seat exists) must keep Salisbury levyable (3.4.2).
    s.lords["henry_vi"].location = "york"
    moves = legal_moves.legal_moves(s)
    targets = {m["target"] for m in moves if m["type"] == "levy_lord"}
    assert targets == {"salisbury"}


def test_levy_vassal_lancastrian_allowed_and_blocked_only_by_y7():
    # L155 bool And->Or / cmp Eq->NotEq (Yorkists Block Parliament, Y7).
    s = _muster_state()
    s.active_side = "lancastrian"
    s.locales["lincoln"].favour = "lancastrian"        # Beaumont's Seat friendly
    moves = legal_moves.legal_moves(s)
    assert any(m["type"] == "levy_vassal" and m["target"] == "beaumont" for m in moves)
    s.active_events.append({"card": "Y7", "side": "yorkist"})
    moves = legal_moves.legal_moves(s)
    assert not any(m["type"] == "levy_vassal" for m in moves)
    # Y7 does not block the Yorkists themselves.
    s.active_side = "yorkist"
    s.locales["dover"].favour = "yorkist"              # Fauconberg's Seat friendly
    moves = legal_moves.legal_moves(s)
    assert any(m["type"] == "levy_vassal" and m["target"] == "fauconberg" for m in moves)


def test_levy_troops_offer_and_rising_wages_coin_gate():
    # L174 Eq->NotEq / int 0->1 / int 1->2; L175 And->Or, Lt->LtE, int 1->2, int 0->1.
    s = _muster_state()
    york = s.lords["york"]
    moves = legal_moves.legal_moves(s)
    assert _by(moves, "york", "levy_troops")           # plain offer at a Stronghold
    york.assets["coin"] = 0                            # broke, but no Rising Wages
    assert _by(legal_moves.legal_moves(s), "york", "levy_troops")
    s.active_events.append({"card": "L9", "side": "lancastrian"})   # RISING WAGES
    york.assets["coin"] = 1                            # exactly enough Coin
    assert _by(legal_moves.legal_moves(s), "york", "levy_troops")
    del york.assets["coin"]                            # no Coin at all
    assert not _by(legal_moves.legal_moves(s), "york", "levy_troops")


def test_levy_transport_ship_at_port_exile_and_pool_cap():
    # L204 Or->And + subscript ints; L206 Or->And, Gt->GtE, Lt->LtE, ints.
    def ship_offered(s):
        return any(m for m in _by(legal_moves.legal_moves(s), "york", "levy_transport")
                   if m.get("transport") == "ship")

    s = _muster_state()
    york = s.lords["york"]
    york.location = "bristol"                          # a Port
    s.locales["bristol"].favour = "yorkist"
    york.assets.pop("ship", None)
    assert ship_offered(s)
    york.location = None                               # Mustered in an Exile box
    york.exile_box = "ireland"
    assert ship_offered(s)
    york.exile_box = None
    york.location = "bristol"
    # Ship pool exhausted: 9 other Mustered Lords hold Ships (pool of 9).
    others = [lid for lid in s.lords if lid != "york"]
    for lid in others:
        ls = s.lords[lid]
        ls.status = LordStatus.MUSTERED
        ls.calendar_box = None
        if ls.location is None:
            ls.location = "london" if ls.side == "lancastrian" else "ludlow"
        ls.assets = {**ls.assets, "ship": 1}
    assert not ship_offered(s)                         # shipless York gets nothing
    york.assets["ship"] = 1                            # ... but a Lord holding one may
    s.lords[others[0]].assets["ship"] = 0              # (keep the pool at 9 total)
    assert ship_offered(s)


def test_enumeration_does_not_consume_jack_cade_uses():
    # L218 const False->True: the free-Lordship peek must not commit Event uses.
    s = _muster_state()
    york = s.lords["york"]
    york.location = "hereford"
    for lid in ("gloucester", "cardiff", "pembroke", "harlech",
                "shrewsbury", "ludlow", "hereford"):
        s.locales[lid].favour = "yorkist"              # all of Wales: Y4-eligible
    york.lordship_spent = 99
    ev = {"card": "Y4", "side": "yorkist"}             # JACK CADE
    s.active_events.append(ev)
    for _ in range(2):
        moves = legal_moves.legal_moves(s)
        assert _by(moves, "york", "parley")            # the free Parley is offered
    assert ev.get("used", {}) == {}                    # ... without consuming a use


def test_muster_parley_targets_from_a_port_without_ships():
    # L223 int 0->1 (has_ship default), L231 Eq->NotEq (skip filters).
    s = _muster_state()
    york = s.lords["york"]
    york.location = "bristol"
    s.locales["bristol"].favour = "yorkist"
    york.assets.pop("ship", None)
    mv = legal_moves._parley_moves(s, "york", york, "yorkist", True)
    assert {m["target"] for m in mv} == {"gloucester", "wells"}


def test_sail_menu_for_a_lord_at_sea_and_in_exile():
    # L277 And->Or, L283 Lt->LtE, L290 Or->And/Eq->NotEq/In->NotIn,
    # L294 Eq->NotEq, L300 Eq->NotEq, L503 IsNot->Is, L505 True->False,
    # L511 NotEq->Eq (exile Forage), L565 Eq->NotEq (exile Sail).
    s = _muster_state()
    york = s.lords["york"]
    york.location = None
    york.at_sea = "irish_sea"
    york.assets["ship"] = 2                            # 7 units -> exactly 2 needed
    cm = legal_moves._command_moves(s, "yorkist", "york")
    to = {m["to"] for m in cm if m["type"] == "sail"}
    assert {"bristol", "pembroke", "harlech"} <= to    # same-Sea Ports
    assert "calais" in to                              # adjacent-Sea Port (at Sea only)
    assert "newcastle" not in to                       # no cross-Sea Port hop (FAQ #1)
    assert "irish_sea" in to and "english_channel" in to and "north_sea" not in to
    # A Lord Mustered in an Exile box may Forage there and Sail its Sea's Ports.
    york.at_sea = None
    york.exile_box = "ireland"
    cm = legal_moves._command_moves(s, "yorkist", "york")
    assert any(m["type"] == "forage" for m in cm)
    assert {m["to"] for m in cm if m["type"] == "sail"} >= {"bristol", "pembroke"}


def test_sail_event_gates_and_ship_capacity():
    # L277 Eq->NotEq (French Fleet side), L285 Eq->NotEq (Owain side),
    # L282 int 2->3 (Cart shipping capacity).
    s = _muster_state()
    york, henry = s.lords["york"], s.lords["henry_vi"]
    for lord, sea in ((york, "irish_sea"), (henry, "english_channel")):
        lord.location = None
        lord.at_sea = sea
        lord.assets = {**lord.assets, "ship": 2}
    s.active_events.append({"card": "L21", "side": "lancastrian"})   # FRENCH FLEET
    assert not any(m["type"] == "sail"
                   for m in legal_moves._command_moves(s, "yorkist", "york"))
    assert any(m["type"] == "sail"
               for m in legal_moves._command_moves(s, "lancastrian", "henry_vi"))
    s.active_events[:] = [{"card": "Y25", "side": "yorkist"}]        # OWAIN GLYNDWR
    henry.at_sea = "irish_sea"
    to = {m["to"] for m in legal_moves._command_moves(s, "lancastrian", "henry_vi")
          if m["type"] == "sail"}
    assert "bristol" in to and "pembroke" not in to and "harlech" not in to
    s.active_events[:] = []
    york.assets["cart"] = 5                            # ceil(5/2)=3 Ships needed; has 2
    assert not any(m["type"] == "sail"
                   for m in legal_moves._command_moves(s, "yorkist", "york"))


def test_march_menu_wales_gate_and_no_empty_groups():
    # L522 And->Or / Eq->NotEq (Owain), L542 And->Or, L548 And->Or.
    s = _muster_state()
    henry = s.lords["henry_vi"]
    henry.location = "bristol"
    cm = legal_moves._command_moves(s, "lancastrian", "henry_vi")
    marches = [m for m in cm if m["type"] == "march"]
    assert any(m["to"] == "gloucester" for m in marches)   # Wales open without Y25
    assert not any(m.get("group") == [] for m in marches)  # no phantom group entries
    s.active_events.append({"card": "Y25", "side": "yorkist"})       # OWAIN GLYNDWR
    cm = legal_moves._command_moves(s, "lancastrian", "henry_vi")
    assert not any(m["type"] == "march" and m["to"] == "gloucester" for m in cm)
    york = s.lords["york"]
    york.location = "bristol"
    cm = legal_moves._command_moves(s, "yorkist", "york")
    assert any(m["type"] == "march" and m["to"] == "gloucester" for m in cm)


def test_tax_supply_and_parley_menus_at_a_port():
    # L584 In->NotIn, L586 int 0->1, L588 NotIn->In, L614 GtE->Gt / int 1->2,
    # L617 int 0->1, L621 NotEq->Eq, L629 int 0->1, L646 NotIn->In, L649 NotEq->Eq.
    s = _muster_state()
    york = s.lords["york"]
    york.location = "dover"
    s.locales["dover"].favour = "yorkist"
    s.locales["canterbury"].favour = "yorkist"         # a Friendly Source, 1 Way out
    york.vassals.append("fauconberg")                  # Seat: Dover
    york.assets = {"coin": 2, "cart": 1, "provender": 2}
    cm = legal_moves._command_moves(s, "yorkist", "york")
    tax = {m["target"] for m in cm if m["type"] == "tax"}
    assert "dover" in tax                              # own Vassal's Seat, in place
    assert "calais" not in tax                         # no Sea hop without a Ship
    supply = [m for m in cm if m["type"] == "supply"]
    assert any(m["source"] == "dover" for m in supply)
    assert any(m["source"] == "canterbury" for m in supply)   # 1 Cart, 1 Way
    assert not any(m.get("use_ships") for m in supply)
    parley = {m["target"] for m in cm if m["type"] == "parley"}
    assert "truro" not in parley                       # same-Sea Port needs a Ship
    york.assets["ship"] = 1
    cm = legal_moves._command_moves(s, "yorkist", "york")
    assert any(m["type"] == "supply" and m["source"] == "truro"
               and m.get("use_ships") for m in cm)
    assert "truro" in {m["target"] for m in cm if m["type"] == "parley"}


def test_agitators_and_merchants_target_menus():
    # L344 And->Or, L358 And->Or, L360 int 2->3.
    s = _muster_state()
    york = s.lords["york"]
    york.capabilities.extend(["Y10", "L30"])           # AGITATORS + MERCHANTS
    s.locales["cambridge"].favour = "yorkist"
    s.locales["cambridge"].depletion = "depleted"
    s.locales["bury_st_edmunds"].depletion = "depleted"
    s.locales["lynn"].depletion = "exhausted"
    out = legal_moves._capability_command_moves(
        s, "yorkist", "york", york, ("stronghold", "ely"))
    agit = {m["target"] for m in out if m["type"] == "agitators"}
    assert agit == {"bury_st_edmunds", "peterborough"}
    merch = {frozenset(m["targets"]) for m in out if m["type"] == "merchants"}
    assert merch == {frozenset(p) for p in (
        ("bury_st_edmunds", "cambridge"), ("bury_st_edmunds", "lynn"),
        ("cambridge", "lynn"))}


def test_sun_in_splendour_targets_and_validated_build_plan():
    # L443 Eq->NotEq, L447 And->Or (Y24 targets); L686 NotIn->In (build_plan
    # must be kept, not probed, by validated_legal_moves).
    s = build_initial_state("henry_vi", seed=1)
    s.decks["yorkist"]["held"] = ["Y24"]
    s.lords["edward_iv"] = LordState(lord_id="edward_iv", side="yorkist",
                                     status=LordStatus.CALENDAR, calendar_box=5)
    out = legal_moves._held_event_moves(s, "yorkist")
    targets = {m["decisions"]["target"] for m in out
               if m.get("card") == "Y24" and "decisions" in m}
    assert {"ireland", "burgundy", "ely"} <= targets   # Yorkist boxes + Friendly Locale
    assert "scotland" not in targets and "france" not in targets
    assert "truro" not in targets                      # Neutral Locale is no target

    from plantagenet import actions
    from tests._helpers import to_muster
    s2 = build_initial_state("henry_vi", seed=1)
    to_muster(s2)
    actions.apply_action(s2, {"type": "end_muster", "side": "yorkist"})
    actions.apply_action(s2, {"type": "end_muster", "side": "lancastrian"})
    actions.apply_action(s2, {"type": "begin_campaign"})
    vm = legal_moves.validated_legal_moves(s2)
    assert any(m["type"] == "build_plan" for m in vm["moves"])
    assert any(m["type"] == "build_plan" for m in vm["unvalidated"])
