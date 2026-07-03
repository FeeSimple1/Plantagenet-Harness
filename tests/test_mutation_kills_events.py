"""Mutation-survivor killing tests for src/plantagenet/events.py.

Each test targets specific surviving mutants from mutation-results/events.py.jsonl
(site numbers cited). See mutation-results/events.py.triage.md.
"""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordStatus, VassalState, VassalStatus


def _play(s, card, side, **decisions):
    return actions.apply_action(s, {"type": "play_event", "card": card, "side": side,
                                    "decisions": decisions})


def _net_lanc(s):
    t = s.influence["track"]
    return t.marker_at if t.marker_side == "lancastrian" else -t.marker_at


# sites 2152/3318 (L50), 1091/2169/3327 (L57), 1093/2175/3332 (L58)
def test_charles_the_bold_and_french_war_loans():
    s = build_initial_state("henry_vi", seed=1)
    del s.lords["march"].assets["provender"]
    r = _play(s, "Y23", "yorkist")
    assert "granted" in r
    assert s.lords["york"].assets["provender"] == 3      # 2 +1
    assert s.lords["march"].assets["provender"] == 1     # no key: 0 +1
    s2 = build_initial_state("henry_vi", seed=1)
    del s2.lords["somerset_1"].assets["coin"]
    del s2.lords["somerset_1"].assets["provender"]
    _play(s2, "L30", "lancastrian")
    assert s2.lords["henry_vi"].assets["coin"] == 5      # 4 +1
    assert s2.lords["henry_vi"].assets["provender"] == 3
    assert s2.lords["somerset_1"].assets["coin"] == 1    # no keys: 0 +1
    assert s2.lords["somerset_1"].assets["provender"] == 1


# sites 2197/3345/3349 (L68), 3296 (L36)
def test_earl_rivers_bounds_and_defaults():
    s = build_initial_state("henry_vi", seed=1)
    del s.lords["march"].forces["militia"]
    r = _play(s, "Y31", "yorkist", militia={"york": 0, "march": 2})
    assert "york" not in r["militia_added"]              # explicit 0 is legal
    assert s.lords["march"].forces["militia"] == 2       # exactly 2, no phantom base
    s2 = build_initial_state("henry_vi", seed=1)
    with pytest.raises(IllegalAction) as e:
        _play(s2, "Y31", "yorkist", militia={"york": 3})
    assert e.value.code == "bad_militia"
    # sites 1051/2120 (L34): a full pool blocks the Muster entirely (1.6)
    s3 = build_initial_state("henry_vi", seed=1)
    s3.lords["henry_vi"].forces["militia"] = 42          # 42+2+1 = pool of 45 in play
    _play(s3, "Y31", "yorkist")                          # default 2 Militia each
    assert s3.lords["york"].forces["militia"] == 2       # unchanged: pool exhausted
    assert s3.lords["march"].forces["militia"] == 1


# sites 3377 (L81), 2238 (L82)
def test_scots_adds_one_of_each():
    s = build_initial_state("henry_vi", seed=1)
    _play(s, "L14", "lancastrian", lords=["henry_vi"])
    assert s.lords["henry_vi"].forces["men_at_arms"] == 3    # 2 +1
    assert s.lords["henry_vi"].forces["militia"] == 5        # 4 +1


# sites 2259 (L91), 1179 (L98), 1186 (L101)
def test_french_troops_preconditions():
    s = build_initial_state("henry_vi", seed=1)          # no Lancastrian at a Port
    r = _play(s, "L22", "lancastrian", lord="henry_vi")
    assert "no Lancastrian Lord at a Port" in r["no_effect"]
    s2 = build_initial_state("henry_vi", seed=1)
    s2.lords["somerset_1"].location = "dover"            # a Lancastrian is at a Port ...
    with pytest.raises(IllegalAction) as e:              # ... but the named Lord is not
        _play(s2, "L22", "lancastrian", lord="henry_vi")
    assert e.value.code == "not_port"
    s2.lords["york"].location = "dover"
    with pytest.raises(IllegalAction) as e2:             # a Yorkist Lord is no target
        _play(s2, "L22", "lancastrian", lord="york")
    assert e2.value.code == "bad_lord"


# sites 2285/4402 (L103), 2291/4406 (L104): the "2" caps, not the defaults
def test_french_troops_amount_cap():
    s = build_initial_state("henry_vi", seed=1)
    s.lords["somerset_1"].location = "dover"
    r = _play(s, "L22", "lancastrian", lord="somerset_1", men_at_arms=9, militia=9)
    assert r["men_at_arms"] == 2 and r["militia"] == 2
    assert s.lords["somerset_1"].forces["men_at_arms"] == 4  # 2 +2
    assert s.lords["somerset_1"].forces["militia"] == 2      # no key: 0 +2


# sites 2131 (L42), 2305/3428 (L111), 2308/3431 (L112), 1226 (L113)
def test_yorkist_north_counts():
    s = build_initial_state("henry_vi", seed=1)
    s.locales["scarborough"].favour = "yorkist"
    s.locales["newcastle"].favour = "yorkist"
    s.lords["york"].location = "carlisle"                # one Yorkist Lord in the North
    s.lords["march"].status = LordStatus.CALENDAR        # none elsewhere on the map
    s.lords["march"].location = None
    r = _play(s, "Y27", "yorkist")
    assert r["influence"] == 3                           # 2 Strongholds + 1 Lord
    assert _net_lanc(s) == -3


# sites 2327/4428 (L120), 3448 (L125)
def test_henry_pressures_parliament_counts():
    s = build_initial_state("henry_vi", seed=1)
    s.vassals["suffolk"] = VassalState(vassal_id="suffolk", status=VassalStatus.MUSTERED,
                                       on_lord="march", service_box=4)
    s.lords["march"].vassals = ["suffolk"]
    s.lords["henry_vi"].special_vassals = ["trollope"]   # Lancastrian: must not count
    r = _play(s, "L15", "lancastrian")
    assert r["yorkist_influence_lost"] == 1
    assert _net_lanc(s) == 1


# sites 2349 (L134), 2384 (L153), 518 (L158)
def test_henry_released_and_sir_richard_leigh():
    s = build_initial_state("henry_vi", seed=1)          # London Favours Lancaster
    s.decks["lancastrian"]["discard"].append("L26")      # L26 is live in the deck
    r = _play(s, "L26", "lancastrian")
    assert r["lancastrian_influence"] == 5
    assert _net_lanc(s) == 5                             # exactly +5
    s2 = build_initial_state("henry_vi", seed=1)         # Y21 vs doubled Lancastrian London
    s2.locales["london"].favour_extra = 1
    _play(s2, "Y21", "yorkist")
    assert s2.locales["london"].favour == "lancastrian"  # one marker removed, one stays
    assert s2.locales["london"].favour_extra == 0
    s3 = build_initial_state("henry_vi", seed=1)         # Y21 on neutral London
    s3.locales["london"].favour = "neutral"
    _play(s3, "Y21", "yorkist")
    assert s3.locales["london"].favour == "yorkist"


# sites 2439/2440 (L182)
def test_henrys_proclamation_shifts_yorkist_vassals():
    s = build_initial_state("henry_vi", seed=1)
    s.vassals["suffolk"] = VassalState(vassal_id="suffolk", status=VassalStatus.MUSTERED,
                                       on_lord="march", service_box=9)
    s.lords["march"].vassals = ["suffolk"]
    r = _play(s, "L19", "lancastrian")
    assert r["shifted"] == ["suffolk"]
    assert s.vassals["suffolk"].service_box == s.turn_box


# sites 1368 (L194), 4512 (L198)
def test_dubious_clarence():
    s = build_initial_state("henry_vi", seed=1)          # neither Edward IV nor Clarence
    r = _play(s, "Y26", "yorkist")
    assert "no_effect" in r
    s2 = build_initial_state("warwicks_rebellion", seed=1)   # both on the map
    r2 = _play(s2, "Y26", "yorkist")
    assert r2["spent"] == 1                              # base spend, no extra by default


# sites 2493/2494 (L211), 1405 (L216), 1412 (L221)
def test_aragne_targets_and_need():
    s = build_initial_state("henry_vi", seed=2)
    s.vassals["suffolk"] = VassalState(vassal_id="suffolk", status=VassalStatus.MUSTERED,
                                       on_lord="march", service_box=4)
    s.lords["march"].vassals = ["suffolk"]
    s.lords["henry_vi"].special_vassals = ["trollope"]   # Lancastrian: not a target
    r = _play(s, "L27", "lancastrian", vassals=["suffolk"])
    assert len(r["checks"]) == 1                         # one Yorkist Vassal -> need 1
    s2 = build_initial_state("henry_vi", seed=2)
    for vid, on in (("suffolk", "march"), ("oxford", "march"), ("dudley", "york")):
        s2.vassals[vid] = VassalState(vassal_id=vid, status=VassalStatus.MUSTERED,
                                      on_lord=on, service_box=4)
    r2 = _play(s2, "L27", "lancastrian", vassals=["suffolk", "oxford"])
    assert len(r2["checks"]) == 2                        # need stays min(2, available)
    # site 2544 (L231): a failed check Disbands the regular Vassal (3.2.4)
    s3 = build_initial_state("henry_vi", seed=1)         # seed 1: March's check fails
    s3.vassals["suffolk"] = VassalState(vassal_id="suffolk", status=VassalStatus.MUSTERED,
                                        on_lord="march", service_box=4)
    s3.lords["march"].vassals = ["suffolk"]
    r3 = _play(s3, "L27", "lancastrian", vassals=["suffolk"])
    assert r3["checks"][0]["disbanded"] is True
    assert s3.vassals["suffolk"].status == VassalStatus.DISBANDED
    assert "suffolk" not in s3.lords["march"].vassals


# sites 2586 (L251), 3690 (L257)
def test_warwicks_propaganda():
    s = build_initial_state("henry_vi", seed=1)          # Yorkist Favour: ely, ludlow
    with pytest.raises(IllegalAction) as e:              # London Favours Lancaster
        _play(s, "L23", "lancastrian", strongholds={"ely": "remove", "london": "remove"})
    assert e.value.code == "not_yorkist"
    s2 = build_initial_state("henry_vi", seed=1)
    s2.locales["ely"].favour_extra = 1
    _play(s2, "L23", "lancastrian", strongholds={"ely": "remove", "ludlow": "remove"})
    assert s2.locales["ely"].favour == "yorkist"         # extra marker removed first
    assert s2.locales["ely"].favour_extra == 0
    assert s2.locales["ludlow"].favour == "neutral"


# sites 3725/4632/4633/5248 (L277), 4636 (L278), 5605 (L287)
def test_welsh_rebellion_removes_two_troops_or_disbands():
    s = build_initial_state("henry_vi", seed=1)          # March at Ludlow (Wales)
    r = _play(s, "L25", "lancastrian")
    assert r["troops_removed"] == {"march": 2}
    f = s.lords["march"].forces
    assert f["men_at_arms"] == 0 and f["longbow"] == 1 and f["militia"] == 1
    assert s.lords["march"].status == LordStatus.MUSTERED
    s2 = build_initial_state("henry_vi", seed=1)         # left without Troops: Disbands
    s2.lords["march"].forces = {"retinue": 1, "militia": 2}
    r2 = _play(s2, "L25", "lancastrian")
    assert r2.get("disbanded") == ["march"]
    assert s2.lords["march"].status != LordStatus.MUSTERED


# sites 648 (L294), 1522/2660 (L296), 1524 (L298), 2668 (L300)
def test_welsh_rebellion_favour_branch():
    s = build_initial_state("henry_vi", seed=1)
    s.lords["march"].status = LordStatus.CALENDAR        # no Yorkist in Wales
    s.lords["march"].location = None
    s.locales["cardiff"].favour = "yorkist"              # Wales: cardiff, ludlow, hereford
    s.locales["hereford"].favour = "yorkist"
    s.locales["shrewsbury"].favour = "lancastrian"
    r = _play(s, "L25", "lancastrian")
    assert r["favour_removed"] == 2
    assert s.locales["cardiff"].favour == "neutral"
    assert s.locales["ludlow"].favour == "neutral"
    assert s.locales["hereford"].favour == "yorkist"     # only two markers removed
    assert s.locales["shrewsbury"].favour == "lancastrian"


# sites 1541/2683 (L308), 2706 (L317), 1592/2738 (L334)
def test_wilful_disobedience_and_robins_rebellion():
    def base():
        s = build_initial_state("henry_vi", seed=1)
        s.lords["march"].status = LordStatus.CALENDAR
        s.lords["march"].location = None
        s.locales["guildford"].favour = "yorkist"
        s.locales["rochester"].favour = "yorkist"
        return s
    s = base()                                           # two targets are legal (L29)
    r = _play(s, "L29", "lancastrian", strongholds=["guildford", "rochester"])
    assert r["removed"] == ["guildford", "rochester"]
    s2 = base()
    s2.locales["st_albans"].favour = "yorkist"
    with pytest.raises(IllegalAction) as e:              # three targets are not
        _play(s2, "L29", "lancastrian",
              strongholds=["guildford", "rochester", "st_albans"])
    assert e.value.code == "bad_count"
    s3 = base()                                          # near a Yorkist Lord: illegal
    s3.lords["march"].status = LordStatus.MUSTERED
    s3.lords["march"].location = "guildford"
    with pytest.raises(IllegalAction) as e2:
        _play(s3, "L29", "lancastrian", strongholds=["guildford"])
    assert e2.value.code == "bad_target"
    # Robin's Rebellion (L31): up to 3 markers, no fourth
    s4 = build_initial_state("henry_vi", seed=1)
    for loc in ("bamburgh", "carlisle", "newcastle"):
        s4.locales[loc].favour = "yorkist"
    ops = [{"locale": "bamburgh"}, {"locale": "carlisle"},
           {"locale": "hexham", "side": "lancastrian"}]
    r4 = _play(s4, "L31", "lancastrian", favour=ops)
    assert len(r4["changes"]) == 3
    assert s4.locales["bamburgh"].favour == "neutral"
    assert s4.locales["hexham"].favour == "lancastrian"
    s5 = build_initial_state("henry_vi", seed=1)
    for loc in ("bamburgh", "carlisle", "newcastle"):
        s5.locales[loc].favour = "yorkist"
    with pytest.raises(IllegalAction) as e3:
        _play(s5, "L31", "lancastrian",
              favour=ops + [{"locale": "newcastle"}])
    assert e3.value.code == "too_many"


# sites 2789/2791 (L361/L363), 3112/4172 (L544)
def test_tudor_banners_and_yorkist_parade():
    s = build_initial_state("my_kingdom_for_a_horse", seed=1)
    ht = s.lords["henry_tudor"]
    ht.location, ht.exile_box = "harlech", None
    s.locales["harlech"].favour = "lancastrian"
    r = _play(s, "L32", "lancastrian")
    assert set(r["marked"]) == {"chester", "pembroke"}
    assert s.locales["chester"].favour == "lancastrian"
    # Yorkist Parade (Y20): York or Warwick must be at a Friendly London
    s2 = build_initial_state("henry_vi", seed=1)
    s2.locales["london"].favour = "yorkist"
    s2.lords["york"].location = "london"
    s2.decks["yorkist"]["held"] = ["Y20"]
    actions.apply_action(s2, {"type": "play_held_event", "card": "Y20", "side": "yorkist"})
    assert any(e["card"] == "Y20" for e in s2.active_events)
    s3 = build_initial_state("henry_vi", seed=1)         # other Lords at London do not count
    s3.locales["london"].favour = "yorkist"
    s3.decks["yorkist"]["held"] = ["Y20"]
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s3, {"type": "play_held_event", "card": "Y20", "side": "yorkist"})
    assert e.value.code == "no_york_or_warwick"


# sites 1679 (L386), 3940 (L391), 1689 (L392), 3949 (L394), 3989 (L411)
def test_tax_collectors():
    s = build_initial_state("henry_vi", seed=2)          # seed 2: York's checks succeed
    s.lords["york"].location = "ipswich"
    s.lords["york"].vassals = ["suffolk"]
    del s.lords["york"].assets["coin"]
    r = _play(s, "Y10", "yorkist", lords=["york", "henry_vi"],
              tax_targets={"york": "ipswich", "henry_vi": "london"})
    assert r["taxes"]["york"] == {"target": "ipswich", "coin": 2, "success": True}
    assert s.lords["york"].assets["coin"] == 2           # double Tax, no phantom base
    assert s.lords["henry_vi"].assets["coin"] == 4       # Lancastrians never Tax here
    assert s.locales["ipswich"].depletion == "depleted"
    s2 = build_initial_state("henry_vi", seed=2)         # London is a listed Tax target
    s2.lords["york"].location = "london"
    r2 = _play(s2, "Y10", "yorkist", lords=["york"], tax_targets={"york": "london"})
    assert r2["taxes"]["york"]["coin"] == 6
    s3 = build_initial_state("henry_vi", seed=2)         # a Lord in Exile cannot Tax
    s3.lords["march"].location = None
    s3.lords["march"].exile_box = "france"
    r3 = _play(s3, "Y10", "yorkist", lords=["march"], tax_targets={"march": "ludlow"})
    assert r3["taxes"] == {}
    assert s3.lords["march"].assets.get("coin", 0) == 1  # unchanged


# sites 3000 (L483), 4096/1839 (L485/L487), 1840 (L487)
def test_rebel_supply_depot():
    s = build_initial_state("henry_vi", seed=1)
    s.lords["henry_vi"].location = "dover"
    s.hold_window = {"side": "lancastrian", "action": "march", "lords": ["henry_vi"]}
    s.decks["lancastrian"]["held"] = ["L28"]
    del s.lords["henry_vi"].assets["provender"]
    r = actions.apply_action(s, {"type": "play_held_event", "card": "L28",
                                 "side": "lancastrian",
                                 "decisions": {"lords": ["henry_vi"]}})
    assert r["provender_each"] == 4 and r["ignore_next_feed"] is True
    assert s.lords["henry_vi"].assets["provender"] == 4  # exactly +4
    assert s.lords["henry_vi"].ignore_next_feed is True
    s2 = build_initial_state("henry_vi", seed=1)         # mover not at a Port: illegal
    s2.hold_window = {"side": "lancastrian", "action": "march", "lords": ["somerset_1"]}
    s2.decks["lancastrian"]["held"] = ["L28"]
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s2, {"type": "play_held_event", "card": "L28",
                                  "side": "lancastrian",
                                  "decisions": {"lords": ["somerset_1"]}})
    assert e.value.code == "not_at_port"


# sites 1896 (L516), 931 (L533)
def test_sun_in_splendour_musters_edward():
    s = build_initial_state("warwicks_rebellion", seed=1)
    s.decks["yorkist"]["held"] = ["Y24"]
    with pytest.raises(IllegalAction) as e:              # Edward already Mustered
        actions.apply_action(s, {"type": "play_held_event", "card": "Y24", "side": "yorkist",
                                 "decisions": {"target": "burgundy"}})
    assert e.value.code == "edward_unavailable"
    s2 = build_initial_state("warwicks_rebellion", seed=1)
    ed = s2.lords["edward_iv"]
    ed.status, ed.location = LordStatus.CALENDAR, None
    ed.calendar_box, ed.calendar_exile = 1, True
    s2.decks["yorkist"]["held"] = ["Y24"]
    actions.apply_action(s2, {"type": "play_held_event", "card": "Y24", "side": "yorkist",
                              "decisions": {"target": "burgundy"}})
    assert ed.status == LordStatus.MUSTERED and ed.exile_box == "burgundy"
    assert ed.calendar_exile is False and ed.forces


# sites 3214 (L593), 3261/4296 (L622)
def test_play_event_pending_scope_and_first_levy():
    s = build_initial_state("henry_vi", seed=1)          # a standalone play while another
    s.pending_events = [{"card": "Y27", "side": "yorkist"}]   # Event is pending
    before = s.decks["yorkist"]["draw"].count("Y15")
    _play(s, "Y15", "yorkist")
    assert s.decks["yorkist"]["draw"].count("Y15") == before  # not returned to the deck
    assert s.pending_events == [{"card": "Y27", "side": "yorkist"}]
    s2 = build_initial_state("henry_vi", seed=1)         # first Levy: draw -> muster
    s2.pending_events = [{"card": "L26", "side": "lancastrian"}]
    r2 = _play(s2, "L26", "lancastrian")
    assert r2["next"] == "muster" and s2.levy_step == "muster"
    s3 = build_initial_state("henry_vi", seed=1)         # later Levy: draw -> pay
    s3.turn_box = 2
    s3.pending_events = [{"card": "L26", "side": "lancastrian"}]
    r3 = _play(s3, "L26", "lancastrian")
    assert r3["next"] == "pay" and s3.levy_step == "pay"
