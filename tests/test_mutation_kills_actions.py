"""Mutation-survivor killing tests for src/plantagenet/actions.py.

Each test targets specific surviving mutants from mutation-results/actions.py.jsonl
(site numbers cited). See mutation-results/actions.py.triage.md.
"""

from __future__ import annotations

import pytest

from plantagenet import actions
from plantagenet.errors import IllegalAction
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordState, LordStatus, VassalStatus


def _muster(seed=1, sid="henry_vi", side=None):
    s = build_initial_state(sid, seed=seed)
    s.levy_step = "muster"
    if side is not None:
        s.active_side = side
    return s


# sites 1616 (L173), 6476/7466 (L206), 7437 (L181), 8257/8369 (L182)
def test_parley_route_cost_ways_and_great_ships():
    s = _muster()
    # current-location Parley costs 0 Ways (3.4.1)
    assert actions._parley_route_cost(s, ("stronghold", "ely"), "ely", "yorkist", False) == 0
    # a two-Way Route through a Friendly intermediate costs 2
    s.locales["lynn"].favour = "yorkist"
    assert actions._parley_route_cost(s, ("stronghold", "ely"), "norwich", "yorkist", False) == 2
    # Great Ships connect all Ports unless the pair touches the blocked Sea
    cost = actions._parley_route_cost(s, ("stronghold", "lynn"), "dover", "yorkist", False,
                                      all_seas=True, block_sea="irish_sea")
    assert cost == 1
    blocked = actions._parley_route_cost(s, ("stronghold", "lynn"), "dover", "yorkist", False,
                                         all_seas=True, block_sea="north_sea")
    assert blocked is None


# site 5071 (L215): the undo snapshot must capture Vassal state for Y32 cancels
def test_kings_name_cancel_restores_vassal():
    s = _muster(side="lancastrian")
    s.lords["henry_vi"].location = "london"
    s.locales["leicester"].favour = "lancastrian"
    s.active_events.append({"card": "L37", "side": "lancastrian"})  # auto-succeed the Levy
    s.active_events.append({"card": "Y32", "side": "yorkist"})      # The King's Name
    s.lords["gloucester_1"] = LordState(lord_id="gloucester_1", side="yorkist",
                                        status=LordStatus.MUSTERED, location="york")
    r = actions.apply_action(s, {"type": "levy_vassal", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "dudley"})
    assert r["type"] == "pending_reactions"
    out = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y32"})
    assert out.get("cancelled") is True
    assert s.vassals["dudley"].status == VassalStatus.AT_SEAT      # vassal snapshot restored
    assert "dudley" not in s.lords["henry_vi"].vassals


# sites 733 (L292), 5205 (L294), 5207 (L295), 5177/6559 (L269), 5212 (L298), 737 (L301)
def test_parley_event_mods_usage_limits():
    s = _muster()
    s.active_events.append({"card": "L17", "side": "lancastrian"})  # MY CROWN (x2, Henry VI)
    m1 = actions._parley_event_mods(s, "henry_vi", "lancastrian")
    m2 = actions._parley_event_mods(s, "henry_vi", "lancastrian")
    m3 = actions._parley_event_mods(s, "henry_vi", "lancastrian")
    assert m1["free_lordship"] is True and m2["free_lordship"] is True
    assert m3["free_lordship"] is False                             # limit 2 exhausted
    # no An Honest Tale active: no Lancastrian Parley surcharge
    assert m1["discount"] == 0 and m3["discount"] == 0
    sw = build_initial_state("warwicks_rebellion")
    sw.active_events.append({"card": "Y28", "side": "yorkist"})     # GLOUCESTER AS HEIR (x3)
    mods = [actions._parley_event_mods(sw, "gloucester_1", "yorkist") for _ in range(4)]
    assert [m["free_lordship"] for m in mods] == [True, True, True, False]


# sites 731 (L282), 3440/5190 (L284), 6613 (L313), 5230/6621 (L317),
# 1816/6623 (L318), 758 (L320)
def test_jack_cade_eligibility():
    s = _muster()
    s.active_events.append({"card": "Y4", "side": "yorkist"})       # JACK CADE
    # eligible: an adjacent Region (the North) entirely Yorkist
    s.lords["york"].location = "york"
    for loc in ("scarborough", "newcastle", "appleby", "carlisle", "hexham", "bamburgh"):
        s.locales[loc].favour = "yorkist"
    m = actions._parley_event_mods(s, "york", "yorkist")
    assert m["auto"] is True and m["free_lordship"] is True
    # ineligible: March at Ludlow -- Wales is not all Yorkist
    s2 = _muster()
    s2.active_events.append({"card": "Y4", "side": "yorkist"})
    m2 = actions._parley_event_mods(s2, "march", "yorkist")
    assert m2["auto"] is False and m2["free_lordship"] is False and m2["discount"] == 0


# sites 3535 (L333), 779/3538 (L334), 1859 (L336), 1868 (L340)
def test_parley_costs_and_unfriendly_location():
    s = _muster()  # york at ely: ely-lynn is one Way
    r = actions.apply_action(s, {"type": "parley", "side": "yorkist",
                                 "by_lord": "york", "target": "lynn"})
    assert r["way_cost"] == 1 and r["spent"] == 2                   # 1 base + 1 per Way
    # without a Ship there is no Sea hop: Scarborough is unreachable from Lynn
    s2 = _muster()
    s2.lords["york"].location = "lynn"
    s2.locales["lynn"].favour = "yorkist"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s2, {"type": "parley", "side": "yorkist",
                                  "by_lord": "york", "target": "scarborough"})
    assert e.value.code == "no_route"
    # ... while a Lord with a Ship may hop to a same-Sea Port (1.4.2)
    s5 = _muster()
    s5.lords["york"].location = "lynn"
    s5.locales["lynn"].favour = "yorkist"
    s5.lords["york"].assets["ship"] = 1
    r5 = actions.apply_action(s5, {"type": "parley", "side": "yorkist",
                                   "by_lord": "york", "target": "scarborough"})
    assert r5["way_cost"] == 1 and r5["spent"] == 2
    # at an unfriendly current location: Parley elsewhere still traces a Route ...
    s3 = _muster()
    s3.locales["ely"].favour = "neutral"
    r3 = actions.apply_action(s3, {"type": "parley", "side": "yorkist",
                                   "by_lord": "york", "target": "lynn"})
    assert r3["way_cost"] == 1 and r3["spent"] == 2
    # ... while Parley at that location itself costs 0 Ways
    s4 = _muster()
    s4.locales["ely"].favour = "neutral"
    r4 = actions.apply_action(s4, {"type": "parley", "side": "yorkist",
                                   "by_lord": "york", "target": "ely"})
    assert r4["way_cost"] == 0 and r4["spent"] == 1


# sites 3731 (L423), 866 (L426), 2050 (L434), 3778 (L438), 2057 (L438)
def test_levy_lord_costs_seat_favour_and_fallback():
    s = _muster(seed=2)
    s.lords["salisbury"].calendar_box = 1
    r = actions.apply_action(s, {"type": "levy_lord", "side": "yorkist",
                                 "by_lord": "york", "target": "salisbury"})
    assert r["success"] is True and r["spent"] == 1
    assert s.lords["york"].lordship_spent == 1
    assert s.lords["salisbury"].location == "york"
    assert s.locales["york"].favour == "yorkist"        # Mustering at the Seat flips it (3.4.2)
    assert s.lords["salisbury"].calendar_exile is False
    # Seat occupied by an Enemy Lord: Muster at a fallback Seat, no favour flip there
    s2 = _muster(seed=2)
    s2.lords["salisbury"].calendar_box = 1
    s2.lords["somerset_1"].location = "york"            # enemy on Salisbury's Seat
    r2 = actions.apply_action(s2, {"type": "levy_lord", "side": "yorkist",
                                   "by_lord": "york", "target": "salisbury"})
    assert r2["success"] is True
    assert s2.lords["salisbury"].location == "ely"      # fallback Friendly Seat
    assert s2.locales["york"].favour == "neutral"       # occupied Seat favour untouched


# sites 5499 (L464), 909/2111 (L469), 2133 (L477)
def test_levy_vassal_gates():
    # Yorkists Block Parliament (Y7) bars Lancastrian Vassal Levy
    s = _muster(side="lancastrian")
    s.lords["henry_vi"].location = "london"
    s.active_events.append({"card": "Y7", "side": "yorkist"})
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_vassal", "side": "lancastrian",
                                 "by_lord": "henry_vi", "target": "essex"})
    assert e.value.code == "blocked_parliament"
    # Margaret Beaufort (L35) relaxes Seat checks for Henry Tudor only
    s2 = _muster(side="lancastrian")
    s2.lords["henry_vi"].location = "london"
    s2.active_events.append({"card": "L35", "side": "lancastrian"})
    with pytest.raises(IllegalAction) as e2:
        actions.apply_action(s2, {"type": "levy_vassal", "side": "lancastrian",
                                  "by_lord": "henry_vi", "target": "suffolk"})
    assert e2.value.code == "seat_not_friendly"
    # a Mustered Vassal is not at its Seat and may not be Levied again
    s3 = _muster(side="lancastrian")
    s3.lords["henry_vi"].location = "london"
    s3.locales["st_albans"].favour = "lancastrian"
    s3.vassals["essex"].status = VassalStatus.MUSTERED
    with pytest.raises(IllegalAction) as e3:
        actions.apply_action(s3, {"type": "levy_vassal", "side": "lancastrian",
                                  "by_lord": "henry_vi", "target": "essex"})
    assert e3.value.code == "vassal_not_at_seat"


# sites 2088 (L453), 3815 (L455), 3875 (L486), 2150 (L489), 934 (L497),
# 2148/2149 (L488), 3877 (L488), 5591 (L503)
def test_levy_vassal_costs_loyalty_and_buckingham():
    s = _muster()
    s.locales["leicester"].favour = "yorkist"
    r = actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                 "by_lord": "york", "target": "dudley"})
    assert r["loyalty_mod"] == 0                        # Dudley has no Loyalty
    assert r["spent"] == 1                              # base cost only, no Buckingham +2
    assert s.lords["york"].lordship_spent == 1
    # white Loyalty adds for the Yorkist Levier
    s.locales["ipswich"].favour = "yorkist"
    r2 = actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                  "by_lord": "york", "target": "suffolk"})
    assert r2["loyalty_mod"] == 1
    # Buckingham's Plot Backfires (L34): Yorkist Vassal Levy costs +2 Influence
    s.active_events.append({"card": "L34", "side": "lancastrian"})
    s.locales["st_albans"].favour = "yorkist"
    r3 = actions.apply_action(s, {"type": "levy_vassal", "side": "yorkist",
                                  "by_lord": "york", "target": "essex"})
    assert r3["spent"] == 3
    # Alice Montagu (Y17): +1 Service, capped at Calendar box 15
    s4 = _muster(seed=2)
    s4.turn_box = 12
    s4.lords["york"].capabilities = ["Y17"]
    s4.locales["ipswich"].favour = "yorkist"
    r4 = actions.apply_action(s4, {"type": "levy_vassal", "side": "yorkist",
                                   "by_lord": "york", "target": "suffolk"})
    assert r4["success"] is True
    assert s4.vassals["suffolk"].service_box == 15


# sites 930 (L493), 2162/3895 (L494)
def test_levy_vassal_auto_success_events():
    def setup():
        s = _muster(seed=1, sid="warwicks_rebellion")   # seed 1: clarence rolls a natural fail
        s.locales["derby"].favour = "lancastrian"
        s.locales["york"].favour = "lancastrian"
        return s
    s = setup()                                          # no events: the check just fails
    r = actions.apply_action(s, {"type": "levy_vassal", "side": "lancastrian",
                                 "by_lord": "clarence", "target": "stanley"})
    assert r["success"] is False
    s2 = setup()                                         # Two Roses (L32): always succeeds
    s2.lords["clarence"].capabilities = ["L32"]
    r2 = actions.apply_action(s2, {"type": "levy_vassal", "side": "lancastrian",
                                   "by_lord": "clarence", "target": "stanley"})
    assert r2["success"] is True
    s3 = setup()                                         # The Earl of Richmond (L37): idem
    s3.active_events.append({"card": "L37", "side": "lancastrian"})
    r3 = actions.apply_action(s3, {"type": "levy_vassal", "side": "lancastrian",
                                   "by_lord": "clarence", "target": "stanley"})
    assert r3["success"] is True


# sites 4589/6148 (L845)
def test_concede_requires_heir():
    s = build_initial_state("wars_of_the_roses", seed=1)
    r = actions.apply_action(s, {"type": "concede", "side": "lancastrian"})
    assert r["winner"] == "yorkist" and s.victory["result"] == "yorkist"
    s2 = build_initial_state("wars_of_the_roses", seed=1)
    s2.lords["henry_vi"].status = LordStatus.AVAILABLE   # no Lancastrian Heir in play
    s2.lords["somerset_1"].status = LordStatus.AVAILABLE
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s2, {"type": "concede", "side": "lancastrian"})
    assert e.value.code == "no_heir_to_concede"


# sites 5638 (L530), 978/2267/4014 (L544), 981 (L545), 2259/4009 (L542)
def test_levy_transport_cart_ship_and_two_ship_cap():
    s = _muster()
    s.lords["york"].location = "lynn"
    s.locales["lynn"].favour = "yorkist"
    del s.lords["york"].assets["cart"]
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "cart"})
    assert s.lords["york"].assets["cart"] == 2          # 2 Carts even with no prior key
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "ship"})
    assert s.lords["york"].assets["ship"] == 1          # exactly one Ship added
    assert s.lords["york"].lordship_spent == 2
    s.lords["york"].assets["ship"] = 2
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                                 "by_lord": "york", "transport": "ship"})
    assert e.value.code == "two_ships"


_OTHERS = ("march", "salisbury", "warwick_yorkist", "rutland", "henry_vi",
           "somerset_1", "northumberland_lancastrian", "exeter_1", "buckingham")


def _ship_state(n_shipholders, actor_ship=None, extra_mustered=0):
    s = _muster()
    s.lords["york"].location = "lynn"
    s.locales["lynn"].favour = "yorkist"
    if actor_ship is not None:
        s.lords["york"].assets["ship"] = actor_ship
    for i, lid in enumerate(_OTHERS):
        ld = s.lords[lid]
        if i < n_shipholders:
            ld.status = LordStatus.MUSTERED
            ld.location = "london"
            ld.assets["ship"] = 1
        elif i < n_shipholders + extra_mustered:
            ld.status = LordStatus.MUSTERED
            ld.location = "london"
        else:
            ld.status = LordStatus.CALENDAR
            ld.location = None
    return s


# sites 3949 (L518), 5619/6867/6868/7665/8080 (L519), 4004/4005/5655/5658/6884 (L540)
def test_ship_limit_counting():
    # A: nine Mustered Lords, zero Ships in play: the ninth Ship is legal
    s = _ship_state(0, extra_mustered=8)
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "ship"})
    assert s.lords["york"].assets["ship"] == 1
    # B: nine Lords already hold a Ship: a ship-less Lord is blocked (3.4.5)
    s = _ship_state(9)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                                 "by_lord": "york", "transport": "ship"})
    assert e.value.code == "ship_limit"
    # C: five Ships in play leave room
    s = _ship_state(5)
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "ship"})
    assert s.lords["york"].assets["ship"] == 1
    # D: a Lord who already has a Ship may take its second despite the limit
    s = _ship_state(8, actor_ship=1)
    actions.apply_action(s, {"type": "levy_transport", "side": "yorkist",
                             "by_lord": "york", "transport": "ship"})
    assert s.lords["york"].assets["ship"] == 2


# sites 4067 (L573), 5705/7695 (L574)
def test_irishmen_levy():
    s = _muster()                                        # Irish-Sea Port: 5 Militia, no Deplete
    s.lords["york"].capabilities = ["Y18"]
    s.lords["york"].location = "harlech"
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert r["added"] == {"militia": 5}
    assert s.locales["harlech"].depletion is None
    s2 = _muster()                                       # non-Ireland Exile box: illegal
    s2.lords["york"].capabilities = ["Y18"]
    s2.lords["york"].location = None
    s2.lords["york"].exile_box = "scotland"
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s2, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert e.value.code == "in_exile_box"
    s3 = _muster()                                       # non-Irish-Sea Port: normal Levy
    s3.lords["york"].capabilities = ["Y18"]
    s3.lords["york"].location = "lynn"
    s3.locales["lynn"].favour = "yorkist"
    r3 = actions.apply_action(s3, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert r3["added"] == {"men_at_arms": 1, "longbow": 1}
    assert s3.locales["lynn"].depletion == "depleted"


# sites 4094 (L587), 4036 (L558), 2414 (L640)
def test_commission_target_and_chamberlains():
    s = _muster(side="lancastrian")
    s.lords["somerset_1"].capabilities = ["L12"]         # Commission of Array
    with pytest.raises(IllegalAction) as e:              # adjacent but not Friendly
        actions.apply_action(s, {"type": "levy_troops", "side": "lancastrian",
                                 "by_lord": "somerset_1", "levy_target": "guildford"})
    assert e.value.code == "bad_commission_target"
    s2 = _muster()                                       # Chamberlains at own Vassal's Seat
    s2.lords["york"].capabilities = ["L10"]
    s2.lords["york"].vassals = ["dudley"]
    s2.lords["york"].location = "leicester"
    s2.locales["leicester"].favour = "yorkist"
    actions.apply_action(s2, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert s2.locales["leicester"].depletion is None     # no Depletion (L10)
    s3 = _muster()                                       # Vassal Seat without Chamberlains
    s3.lords["york"].vassals = ["dudley"]
    s3.lords["york"].location = "leicester"
    s3.locales["leicester"].favour = "yorkist"
    actions.apply_action(s3, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert s3.locales["leicester"].depletion == "depleted"


# sites 4121/5750/6953 (L601)
def test_rising_wages_coin():
    s = _muster()
    s.active_events.append({"card": "L9", "side": "lancastrian"})   # RISING WAGES
    s.lords["york"].assets["coin"] = 1
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert r["added"] == {"longbow": 1, "militia": 1}
    assert s.lords["york"].assets["coin"] == 0           # exactly 1 Coin paid
    s2 = _muster()
    s2.active_events.append({"card": "L9", "side": "lancastrian"})
    del s2.lords["york"].assets["coin"]
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s2, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert e.value.code == "rising_wages_no_coin"


def _reset_levy(s):
    s.lords["york"].lordship_spent = 0
    s.locales["ely"].depletion = None
    s.locales["lynn"].depletion = None


# sites 1039 (L610), 5770 (L611), 4145/5772/5776 (L612), 6968 (L614)
def test_the_commons_extras():
    s = _muster()                                        # no Event: commons_extra is ignored
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                 "by_lord": "york", "commons_extra": 2})
    assert r["added"]["militia"] == 1
    _reset_levy(s)
    s.active_events.append({"card": "Y16", "side": "yorkist"})      # THE COMMONS
    r2 = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist", "by_lord": "york"})
    assert r2["added"]["militia"] == 1                   # default extra is 0
    _reset_levy(s)
    r3 = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                  "by_lord": "york", "commons_extra": 2})
    assert r3["added"]["militia"] == 3                   # 1 from the table +2
    _reset_levy(s)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                 "by_lord": "york", "commons_extra": 3})
    assert e.value.code == "bad_commons"
    _reset_levy(s)                                       # Lynn's table has no Militia line
    s.lords["york"].location = "lynn"
    s.locales["lynn"].favour = "yorkist"
    before = s.lords["york"].forces.get("militia", 0)
    r4 = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                  "by_lord": "york", "commons_extra": 2})
    assert r4["added"]["militia"] == 2
    assert s.lords["york"].forces["militia"] == before + 2


# sites 6979 (L619), 6999 (L630)
def test_soldiers_of_fortune():
    s = _muster()
    s.lords["york"].capabilities = ["Y12"]
    del s.lords["york"].assets["coin"]
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                 "by_lord": "york", "soldiers_of_fortune": True})
    assert e.value.code == "no_coin"
    s.lords["york"].assets["coin"] = 1
    r = actions.apply_action(s, {"type": "levy_troops", "side": "yorkist",
                                 "by_lord": "york", "soldiers_of_fortune": True})
    assert r["added"]["mercenaries"] == 2
    assert s.lords["york"].forces["mercenaries"] == 2    # no phantom starting Mercenary
    assert s.lords["york"].assets["coin"] == 0


# sites 2522 (L701), 8154 (L748), 6009 (L749), 7153 (L750), 8167 (L752)
def test_levy_capability_wrong_side_and_hastings_pool():
    s = _muster()
    with pytest.raises(IllegalAction) as e:              # enemy-side card
        actions.apply_action(s, {"type": "levy_capability", "side": "yorkist",
                                 "by_lord": "york", "card": "L7"})
    assert e.value.code == "unknown_card"
    # Hastings (Y24): +2 Men-at-Arms, pool-limited (pool 35)
    s2 = _muster()
    s2.lords["york"].forces = {"retinue": 1}
    s2.lords["henry_vi"].forces["men_at_arms"] = 31      # 31 + 2 + 1 in play -> 1 free
    sv = actions._muster_special_vassal(s2, s2.lords["york"], "Y24")
    assert sv == "hastings" and "hastings" in s2.lords["york"].special_vassals
    assert s2.lords["york"].forces.get("men_at_arms", 0) == 1
    s3 = _muster()
    s3.lords["york"].forces = {"retinue": 1}
    s3.lords["henry_vi"].forces["men_at_arms"] = 32      # pool full -> nothing added
    actions._muster_special_vassal(s3, s3.lords["york"], "Y24")
    assert s3.lords["york"].forces.get("men_at_arms", 0) == 0


# sites 2820 (L863), 4628 (L864)
def test_end_muster_resets_only_own_side_flags():
    s = _muster()
    s.lords["york"].mustered_this_segment = True
    s.lords["henry_vi"].mustered_this_segment = True
    r = actions.apply_action(s, {"type": "end_muster", "side": "yorkist"})
    assert r["next"] == "king_muster"
    assert s.lords["york"].mustered_this_segment is False
    assert s.lords["march"].mustered_this_segment is False


# sites 6194 (L885), 6198 (L886), 6204 (L888), 6211 (L890), 2874 (L891)
def test_resolve_battle_sides_and_combatants():
    s = build_initial_state("bosworth", seed=1)
    r = actions.apply_action(s, {"type": "resolve_battle"})
    assert set(r["attackers"]) == {"henry_tudor", "jasper_tudor_2", "oxford"}
    assert set(r["defenders"]) == {"richard_iii", "northumberland_2", "norfolk"}
    s2 = build_initial_state("bosworth", seed=1)
    for _lid, ld in s2.lords.items():
        if ld.side == "yorkist":
            ld.status = LordStatus.CALENDAR
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s2, {"type": "resolve_battle"})
    assert e.value.code == "no_combatants"
