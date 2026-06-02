"""Regression tests for the June 2026 rules-audit fixes.

Each test pins a specific bug found during the audit; comments cite the rule and
the audit item. These exercise behaviour the prior suite did not cover.
"""

from __future__ import annotations

from plantagenet import actions, battle, campaign, events, influence, succession
from plantagenet import pay as pay_mod
from plantagenet.scenarios import build_initial_state
from plantagenet.state import LordState, LordStatus, VassalStatus


# --------------------------------------------------------------------------- #
# CRITICAL: Succession permanent ADD cards survive later King changes (6.2/E2)  #
# --------------------------------------------------------------------------- #
def _stage_iiy():
    s = build_initial_state("wars_of_the_roses", seed=1)
    gs = s.grand_scenario
    gs["current_war"] = "war_iiy"
    gs["deck_sources"] = {}
    gs["set_aside_on_disband"] = {}
    gs["succession_fired"] = []
    gs["current_king"] = {}
    for _lid, ls in s.lords.items():
        if ls.side == "yorkist":
            ls.status = LordStatus.AVAILABLE.value
    for lid in ("york", "march", "rutland", "gloucester_1"):
        if lid not in s.lords:
            s.lords[lid] = LordState(lord_id=lid, side="yorkist",
                                     status=LordStatus.AVAILABLE.value)
        s.lords[lid].status = LordStatus.MUSTERED.value
        s.lords[lid].location = "london"
    for lid in ("edward_iv", "richard_iii", "pembroke"):
        if lid not in s.lords:
            s.lords[lid] = LordState(lord_id=lid, side="yorkist",
                                     status=LordStatus.AVAILABLE.value)
    s.decks["yorkist"] = {"draw": [], "discard": [], "held": [], "set_aside": []}
    succession.apply_setup(s)
    return s


def _ydeck(s):
    d = s.decks["yorkist"]
    return set(d["draw"]) | set(d["discard"]) | set(d["held"])


def test_edward_iv_permanent_cards_survive_repeated_recompute():
    s = _stage_iiy()
    s.lords["york"].status = LordStatus.REMOVED.value     # March -> Edward IV (King)
    succession.on_heir_removed(s, "york")
    assert {"Y23", "Y24", "Y28", "Y31"} <= _ydeck(s)
    assert s.grand_scenario["current_king"]["yorkist"] == "edward_iv"
    succession._recompute(s, "yorkist")
    succession._recompute(s, "yorkist")
    assert {"Y23", "Y24", "Y28", "Y31"} <= _ydeck(s)


def test_richard_iii_cards_added_and_edward_iv_cards_drop_on_his_removal():
    # E4: Edward IV's adds last only "as long as Edward IV remains"; Richard III adds Y32-Y35.
    s = _stage_iiy()
    for lid in ("york", "rutland"):
        s.lords[lid].status = LordStatus.REMOVED.value
        succession.on_heir_removed(s, lid)
    assert {"Y23", "Y24", "Y28", "Y31"} <= _ydeck(s)        # present while Edward IV remains
    s.lords["edward_iv"].status = LordStatus.REMOVED.value  # Gloucester(1) -> Richard III
    succession.on_heir_removed(s, "edward_iv")
    assert s.grand_scenario["current_king"]["yorkist"] == "richard_iii"
    assert {"Y32", "Y33", "Y34", "Y35"} <= _ydeck(s)        # Richard III's adds present
    assert not ({"Y23", "Y24", "Y28", "Y31"} & _ydeck(s))   # Edward IV's adds dropped (E4)
    succession._recompute(s, "yorkist")
    assert {"Y32", "Y33", "Y34", "Y35"} <= _ydeck(s)        # ... and stay (Richard III remains)


# --------------------------------------------------------------------------- #
# HIGH: battle Losses must not disband a victorious Retinue-only Lord (4.4.3)   #
# --------------------------------------------------------------------------- #
def test_retinue_only_winner_not_disbanded():
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1}
    f = battle._Force(s, "york")
    res: dict = {}
    battle._losses(s, f, s.dice(), res)
    assert "loss_disbands" not in res
    assert s.lords["york"].status == LordStatus.MUSTERED


def test_winner_losing_all_troops_is_disbanded():
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1, "men_at_arms": 1}
    f = battle._Force(s, "york")
    f.routed["men_at_arms"] = 1
    s.lords["york"].forces["men_at_arms"] = 0
    res: dict = {}
    battle._losses(s, f, s.dice(), res)
    assert res.get("loss_disbands") == ["york"]


# --------------------------------------------------------------------------- #
# HIGH: Bloody Thou Art (Y33) blocks upon-Death cards; routed Yorkists Disband  #
# --------------------------------------------------------------------------- #
def test_bloody_thou_art_blocks_escape_ship_and_disbands_yorkist():
    s = build_initial_state("henry_vi")
    s.lords["henry_vi"].location = "dover"
    s.locales["dover"].favour = "lancastrian"
    s.decks.setdefault("lancastrian", {}).setdefault("held", []).append("L3")
    s.lords["richard_iii"] = LordState(lord_id="richard_iii", side="yorkist",
                                       status=LordStatus.MUSTERED, location="dover",
                                       forces={"retinue": 1}, capabilities=["Y33"])
    f_rich = battle._Force(s, "richard_iii")
    f_hen = battle._Force(s, "henry_vi")
    f_hen.lord_routed = True
    f_york = battle._Force(s, "york")
    f_york.lord_routed = True
    forces = {"richard_iii": f_rich, "york": f_york, "henry_vi": f_hen}
    battle._ending(s, "dover", forces, ["richard_iii", "york"], ["henry_vi"], [], ["henry_vi"])
    assert s.lords["henry_vi"].status == LordStatus.REMOVED      # Died, not escaped
    assert "L3" in s.decks["lancastrian"]["held"]               # card NOT consumed
    assert s.lords["york"].status == LordStatus.CALENDAR        # routed Yorkist Disbands


# --------------------------------------------------------------------------- #
# HIGH/MEDIUM: Parley Influence discounts (Y4, Y18/L18) and An Honest Tale      #
# --------------------------------------------------------------------------- #
def test_check_influence_discount_can_reach_zero():
    s = build_initial_state("henry_vi")
    before = s.influence["track"]
    chk = influence.check_influence(s, "york", "yorkist", discount=1)
    assert chk["spent"] == 0
    assert s.influence["track"] == before


def test_an_honest_tale_raises_cost():
    s = build_initial_state("henry_vi")
    chk = influence.check_influence(s, "henry_vi", "lancastrian", discount=-1)
    assert chk["spent"] == 2


# --------------------------------------------------------------------------- #
# MEDIUM: Spoils at a Neutral locale total-then-halve, not per-loser (4.4.3)    #
# --------------------------------------------------------------------------- #
def test_spoils_neutral_total_then_halve():
    s = build_initial_state("henry_vi")
    s.locales["london"].favour = "neutral"
    s.lords["york"].location = "london"
    s.lords["york"].assets = {}
    s.lords["henry_vi"].assets = {"cart": 1, "provender": 0}
    s.lords["somerset_1"] = LordState(lord_id="somerset_1", side="lancastrian",
                                      status=LordStatus.MUSTERED, location="london",
                                      assets={"cart": 1, "provender": 0})
    winner = battle._Force(s, "york")
    res: dict = {}
    battle._spoils(s, "london", [winner], ["henry_vi", "somerset_1"], res)
    assert res["spoils"]["cart"] == 1                   # ceil(2/2), not 1+1
    assert s.lords["york"].assets.get("cart", 0) == 1


# --------------------------------------------------------------------------- #
# MEDIUM: London For York (Y15) never adds a third Favour marker                #
# --------------------------------------------------------------------------- #
def test_london_for_york_caps_at_second_marker():
    s = build_initial_state("henry_vi")
    s.locales["london"].favour = "yorkist"
    s.locales["london"].favour_extra = 0
    assert events._london_for_york(s, "yorkist", {})["second_favour"] is True
    assert s.locales["london"].favour_extra == 1
    assert events._london_for_york(s, "yorkist", {})["second_favour"] is False
    assert s.locales["london"].favour_extra == 1


# --------------------------------------------------------------------------- #
# HIGH: Special Vassal Hastings counted (L15) and targetable (L27)              #
# --------------------------------------------------------------------------- #
def test_l15_counts_special_vassal_hastings():
    s = build_initial_state("wars_of_the_roses")
    ed = s.lords.setdefault("edward_iv", LordState(lord_id="edward_iv", side="yorkist",
                                                   status=LordStatus.MUSTERED))
    ed.side = "yorkist"
    ed.status = LordStatus.MUSTERED
    ed.special_vassals = ["hastings"]
    t = s.influence["track"]
    before = (t.marker_side, t.marker_at)
    out = events._henry_pressures_parliament(s, "lancastrian", {})
    assert out["yorkist_influence_lost"] >= 1
    assert (t.marker_side, t.marker_at) != before        # Yorkist Influence moved


def test_l27_targets_special_vassal_hastings():
    s = build_initial_state("wars_of_the_roses")
    ed = s.lords.setdefault("edward_iv", LordState(lord_id="edward_iv", side="yorkist",
                                                   status=LordStatus.MUSTERED))
    ed.side = "yorkist"
    ed.status = LordStatus.MUSTERED
    ed.special_vassals = ["hastings"]
    ed.capabilities = ["Y24"]
    # Hastings is a legal target (no bad_vassal); a check is performed for it.
    out = events._luniverselle_aragne(s, "lancastrian", {"vassals": ["hastings"]})
    assert out["checks"][0]["vassal"] == "hastings"


def test_disband_special_vassal_discards_capability():
    s = build_initial_state("wars_of_the_roses")
    ed = s.lords.setdefault("edward_iv", LordState(lord_id="edward_iv", side="yorkist",
                                                   status=LordStatus.MUSTERED))
    ed.side = "yorkist"
    ed.status = LordStatus.MUSTERED
    ed.special_vassals = ["hastings"]
    ed.capabilities = ["Y24"]
    campaign._disband_special_vassal(s, ed, "hastings")   # 3.2.4 / 1.5.4
    assert "hastings" not in ed.special_vassals
    assert "Y24" not in ed.capabilities
    assert "Y24" in s.decks["yorkist"]["discard"]


# --------------------------------------------------------------------------- #
# MEDIUM: Forage from an Exile box Depletes/Exhausts and Grows back (4.6.2)     #
# --------------------------------------------------------------------------- #
def test_exile_box_depletion_grows_back():
    s = build_initial_state("wars_of_the_roses")
    box = "france"
    assert s.exile_depletion.get(box) is None
    s.exile_depletion[box] = "exhausted"
    campaign._grow(s)
    assert s.exile_depletion[box] == "depleted"
    campaign._grow(s)
    assert box not in s.exile_depletion


# --------------------------------------------------------------------------- #
# MEDIUM: Tides "Gain Lords Influence" includes Lords in Exile boxes (4.8.1)    #
# --------------------------------------------------------------------------- #
def test_tides_counts_exile_status_lords():
    s = build_initial_state("wars_of_the_roses")
    s.turn_box = 1
    lanc = [lid for lid, ld in s.lords.items()
            if ld.side == "lancastrian" and ld.status == LordStatus.MUSTERED][0]
    mustered = campaign.tides_of_war(s.model_copy(deep=True))
    s.lords[lanc].status = LordStatus.EXILE
    s.lords[lanc].exile_box = "france"
    exiled = campaign.tides_of_war(s.model_copy(deep=True))
    assert mustered["points"] == exiled["points"]       # Exile Lord still counts


# --------------------------------------------------------------------------- #
# MEDIUM: She-Wolf (Y17) may shift a service marker off-calendar (2.2.3)        #
# --------------------------------------------------------------------------- #
def test_she_wolf_shifts_off_calendar():
    s = build_initial_state("wars_of_the_roses")
    vid = next(iter(s.vassals))
    s.vassals[vid].status = VassalStatus.MUSTERED
    s.vassals[vid].service_box = 15
    s.vassals[vid].on_lord = [lid for lid, ld in s.lords.items() if ld.side == "yorkist"][0]
    events._she_wolf(s, "yorkist", {})
    assert s.vassals[vid].service_box == 16             # not clamped to 15


# --------------------------------------------------------------------------- #
# LOW: Pay-Troops honours the player's choice of which Lords go unpaid (3.2.1)   #
# --------------------------------------------------------------------------- #
def test_pay_troops_respects_unpay_lords_choice():
    s = build_initial_state("henry_vi")
    yk = [lid for lid, ld in s.lords.items()
          if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED][:2]
    a, b = yk
    for lid in (a, b):
        s.lords[lid].location = "london"
        s.lords[lid].forces = {"retinue": 1, "men_at_arms": 6}
        s.lords[lid].assets = {"coin": 0}
        s.lords[lid].vassals = []
    s.lords[a].assets["coin"] = 1
    s.locales["london"].depletion = "exhausted"
    res = pay_mod._pay_troops(s, "yorkist", {"unpay_lords": [b]})
    assert b in res["unpaid_disbanded"]
    assert s.lords[b].status == LordStatus.CALENDAR
    assert s.lords[a].status == LordStatus.MUSTERED


# --------------------------------------------------------------------------- #
# LOW: Captured King released onto the Calendar "as if Disbanded" (6 - Inf)     #
# --------------------------------------------------------------------------- #
def test_release_captive_uses_six_minus_influence():
    s = build_initial_state("wars_of_the_roses")
    holder = [lid for lid, ld in s.lords.items() if ld.side == "yorkist"][0]
    s.lords["henry_vi"].status = LordStatus.CAPTURED
    s.lords["henry_vi"].captured_by = holder
    s.turn_box = 3
    campaign._release_captive(s, holder)
    inf = influence.lord_influence_rating("henry_vi")
    assert s.lords["henry_vi"].calendar_box == 3 + (6 - inf)


# --------------------------------------------------------------------------- #
# LOW: Parley-mod peek (commit=False) must not consume a use (enumeration)      #
# --------------------------------------------------------------------------- #
def test_parley_event_mods_peek_does_not_consume():
    s = build_initial_state("wars_of_the_roses")
    m1 = actions._parley_event_mods(s, "york", "yorkist", commit=False)
    m2 = actions._parley_event_mods(s, "york", "yorkist", commit=False)
    assert m2["used"] == m1["used"]


# --------------------------------------------------------------------------- #
# Battle: Flee may be declared in any Round, not only Round 1 (4.4.2)           #
# --------------------------------------------------------------------------- #
def _two_armies(seed):
    s = build_initial_state("henry_vi", seed=seed)
    s.lords["york"].location = "london"
    s.lords["york"].forces = {"retinue": 1, "men_at_arms": 8}
    s.lords["henry_vi"].location = "london"
    s.lords["henry_vi"].forces = {"retinue": 1, "men_at_arms": 8}
    return s


def test_flee_in_a_later_round():
    # seed 1 yields a >=2-round Battle with no early Rout.
    s = _two_armies(1)
    r = battle.resolve_battle(s, "london", "york", "henry_vi",
                              {"flee_rounds": {"york": 2}})
    assert len(r["rounds"]) >= 2
    assert "fled" not in r["rounds"][0]                 # fought Round 1
    assert r["rounds"][1].get("fled") == ["york"]       # fled at the start of Round 2


def test_flee_list_still_means_round_one():
    s = _two_armies(1)
    r = battle.resolve_battle(s, "london", "york", "henry_vi", {"flee": ["york"]})
    assert r["rounds"][0].get("fled") == ["york"]       # backward compatible


def test_flee_rounds_validates_participant_and_round():
    import pytest

    from plantagenet.errors import IllegalAction
    s = _two_armies(1)
    with pytest.raises(IllegalAction) as e1:
        battle.resolve_battle(s, "london", "york", "henry_vi",
                              {"flee_rounds": {"salisbury": 2}})
    assert e1.value.code == "bad_flee"
    s = _two_armies(1)
    with pytest.raises(IllegalAction) as e2:
        battle.resolve_battle(s, "london", "york", "henry_vi",
                              {"flee_rounds": {"york": 0}})
    assert e2.value.code == "bad_flee_round"


# --------------------------------------------------------------------------- #
# Tax: no per-Way Influence surcharge (Parley-only, 1.4.2); own-Seat auto (4.6.3) #
# --------------------------------------------------------------------------- #
def test_tax_does_not_charge_per_way_surcharge():
    from plantagenet import commands
    s = build_initial_state("henry_vi")
    # Resolve a (forced non-auto) Tax with a 3-Way route: the spend must be the
    # base 1 Influence, NOT 1 + 3 Ways. Per-Way is a Parley-only cost (1.4.2).
    data = {"lord": "york", "target": "ely", "auto": False, "way_cost": 3, "extra": 0}
    r = commands.tax_finish(s, data, cancelled=False)
    assert r["spent"] == 1


def test_tax_own_seat_auto_without_co_location():
    from plantagenet import actions
    from tests.test_commands import _to_campaign
    s = _to_campaign("henry_vi")                 # York's Seat is Ely
    s.locales["bury_st_edmunds"].favour = "yorkist"
    s.lords["york"].location = "bury_st_edmunds"   # NOT standing on its Seat
    track = s.influence["track"]
    before = (track.marker_side, track.marker_at)
    r = actions.apply_action(s, {"type": "tax", "side": "yorkist",
                                 "by_lord": "york", "target": "ely"})
    assert r["auto"] is True and r["spent"] == 0          # auto-success, 0 Influence
    assert (track.marker_side, track.marker_at) == before  # nothing spent (4.6.3 exception)


# --------------------------------------------------------------------------- #
# Highway 2-for-1 cannot bypass an Enemy Lord at the intermediate Stronghold     #
# --------------------------------------------------------------------------- #
def test_highway_chain_blocked_by_enemy_at_intermediate():
    from plantagenet import commands
    s = build_initial_state("henry_vi")
    # winchester -> guildford -> london is a 2-Highway chain (mid = guildford).
    assert commands._march_cost(s, "winchester", "london", "highway",
                                side="yorkist") == ("highway2", False)
    # Place an Enemy (Lancastrian) Lord at the intermediate: the chain is blocked.
    s.lords["somerset_1"].status = LordStatus.MUSTERED
    s.lords["somerset_1"].location = "guildford"
    assert commands._march_cost(s, "winchester", "london", "highway",
                                side="yorkist") is None


# --------------------------------------------------------------------------- #
# The King's Name (Y32) can cancel Levy Transport and Levy Capability (errata)   #
# --------------------------------------------------------------------------- #
def _levy_setup_with_kings_name(seed=1):
    from tests._helpers import to_muster
    s = build_initial_state("henry_vi", seed=seed)
    to_muster(s)
    s.active_side = "lancastrian"
    s.levy_step = "muster"
    lanc = [lid for lid, ld in s.lords.items()
            if ld.side == "lancastrian" and ld.status == LordStatus.MUSTERED][0]
    s.lords[lanc].location = "london"
    s.locales["london"].favour = "lancastrian"
    s.lords[lanc].capabilities = []
    s.lords["gloucester_1"] = LordState(lord_id="gloucester_1", side="yorkist",
                                        status=LordStatus.MUSTERED, location="york")
    s.active_events.append({"card": "Y32", "side": "yorkist"})   # The King's Name
    return s, lanc


def test_kings_name_cancels_levy_transport():
    from plantagenet import actions
    s, lanc = _levy_setup_with_kings_name()
    cart0 = s.lords[lanc].assets.get("cart", 0)
    r = actions.apply_action(s, {"type": "levy_transport", "side": "lancastrian",
                                 "by_lord": lanc, "transport": "cart"})
    assert r["type"] == "pending_reactions"           # Y32 window opens (was missing)
    out = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y32"})
    assert out.get("cancelled") is True
    assert s.lords[lanc].assets.get("cart", 0) == cart0   # transport reverted


def test_kings_name_cancels_levy_capability_returns_card_to_deck():
    from plantagenet import actions, static_data
    s, lanc = _levy_setup_with_kings_name()
    cards = static_data.load_cards()
    deck = static_data.scenario_card_deck(s.scenario, "lancastrian")
    cand = next(cid for cid in (deck or [c for c in cards if cards[c]["side"] == "lancastrian"])
                if actions._capability_eligible(cid, lanc)
                and cid not in actions._capabilities_in_play(s, "lancastrian"))
    actions.apply_action(s, {"type": "levy_capability", "side": "lancastrian",
                             "by_lord": lanc, "card": cand})
    assert s.pending
    out = actions.apply_action(s, {"type": "react", "side": "yorkist", "play": "Y32"})
    assert out.get("cancelled") is True
    assert cand not in s.lords[lanc].capabilities
    assert any(cand in s.decks["lancastrian"].get(p, [])
               for p in ("draw", "discard", "held", "set_aside"))   # returned to deck


# --------------------------------------------------------------------------- #
# Battle player choices restored (collapsed-default audit, 4.4.2/4.4.3)         #
# --------------------------------------------------------------------------- #
class _SeqDice:
    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0

    def d6(self):
        v = self.seq[self.i % len(self.seq)]
        self.i += 1
        return v


def test_spoils_distributed_as_owner_chooses():
    s = build_initial_state("henry_vi")
    s.locales["london"].favour = "yorkist"               # Friendly -> take all (4.4.3)
    for lid in ("york", "march"):
        s.lords[lid].location = "london"
        s.lords[lid].assets = {}
    s.lords["henry_vi"].assets = {"cart": 2, "provender": 0}
    w1 = battle._Force(s, "york")
    w2 = battle._Force(s, "march")
    res: dict = {}
    battle._spoils(s, "london", [w1, w2], ["henry_vi"], res,
                   {"march": {"cart": 2, "provender": 0}})
    assert s.lords["march"].assets["cart"] == 2          # owner sent all to march
    assert s.lords["york"].assets.get("cart", 0) == 0    # not the default first winner


def test_spoils_split_must_total():
    import pytest

    from plantagenet.errors import IllegalAction
    s = build_initial_state("henry_vi")
    s.locales["london"].favour = "yorkist"
    for lid in ("york", "march"):
        s.lords[lid].location = "london"
        s.lords[lid].assets = {}
    s.lords["henry_vi"].assets = {"cart": 2, "provender": 0}
    w1 = battle._Force(s, "york")
    w2 = battle._Force(s, "march")
    with pytest.raises(IllegalAction) as e:
        battle._spoils(s, "london", [w1, w2], ["henry_vi"], {},
                       {"march": {"cart": 1}})           # 1 != 2 taken
    assert e.value.code == "bad_spoils_split"


def test_valour_reroll_can_be_withheld_per_lord():
    # A Lord excluded from the valour list does NOT reroll a failed Protection.
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1}
    f = battle._Force(s, "york")
    f.valour = 2
    log: list = []
    # roll sequence would fail then "save" on reroll; with york excluded, no reroll.
    battle._absorb_side([f], 1, _SeqDice([6, 1]), battle._ABSORB_DEFAULT,
                        set(), log, "melee")             # valour_lords = {} -> none reroll
    assert f.valour == 2                                 # unspent
    assert f.routed.get("retinue", 0) == 1               # routed (no reroll)
    assert "valour_reroll" not in log[0]


def test_final_charge_can_be_limited_to_chosen_rounds():
    s = build_initial_state("my_kingdom_for_a_horse")
    rid = "richard_iii"
    s.lords[rid].status = LordStatus.MUSTERED
    s.lords[rid].location = "leicester"
    s.lords[rid].capabilities = ["Y32"]                  # FINAL CHARGE
    foe = next(lo for lo, ls in s.lords.items() if ls.side == "lancastrian")
    s.lords[foe].status = LordStatus.MUSTERED
    s.lords[foe].location = "leicester"
    base = battle.resolve_battle(s, "leicester", rid, foe, {})
    base_m = next(st for st in base["rounds"][0]["engagements"][0]["strikes"]
                  if st["phase"] == "melee")["attacker_hits"]
    s2 = build_initial_state("my_kingdom_for_a_horse")
    s2.lords[rid].status = LordStatus.MUSTERED
    s2.lords[rid].location = "leicester"
    s2.lords[rid].capabilities = ["Y32"]
    s2.lords[foe].status = LordStatus.MUSTERED
    s2.lords[foe].location = "leicester"
    # Scheduled for Round 2 only -> Round 1 melee is NOT boosted.
    r = battle.resolve_battle(s2, "leicester", rid, foe, {"final_charge": {rid: [2]}})
    r_m = next(st for st in r["rounds"][0]["engagements"][0]["strikes"]
               if st["phase"] == "melee")["attacker_hits"]
    assert r_m == base_m                                 # +3 withheld in Round 1


def test_flank_center_tie_honours_choice():
    # Front: attackers left/center/right (center has no opposite), defenders
    # left+right. The center attacker, equidistant, chooses which wing to join.
    s = build_initial_state("henry_vi")
    ids = ("york", "march", "salisbury", "henry_vi", "somerset_1")
    for lid in ids:
        s.lords[lid].status = LordStatus.MUSTERED
    forces = {lid: battle._Force(s, lid) for lid in ids}
    positions = {"attacker": {0: "york", 1: "march", 2: "salisbury"},
                 "defender": {0: "henry_vi", 2: "somerset_1"}}

    def eng_with_march(flank):
        engs = battle._engagements(positions, forces, {"march": flank})
        return next(e for e in engs if "march" in e["attacker"])

    assert "henry_vi" in eng_with_march("left")["defender"]      # joined the left wing
    assert "somerset_1" in eng_with_march("right")["defender"]   # joined the right wing


def test_absorb_lords_chooses_which_lord_absorbs_first():
    s = build_initial_state("henry_vi")
    for lid in ("york", "march"):
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].forces = {"retinue": 1}
    f1 = battle._Force(s, "york")
    f2 = battle._Force(s, "march")
    log: list = []
    # One failing Hit; owner directs march to absorb first (not the default york).
    battle._absorb_side([f1, f2], 1, _SeqDice([6]), battle._ABSORB_DEFAULT,
                        set(), log, "melee", ["march"])
    assert log[0]["lord"] == "march"
    assert f2.routed.get("retinue", 0) == 1
    assert f1.routed.get("retinue", 0) == 0


def _levy_lord_fallback_state(seed):
    from plantagenet import static_data
    from tests._helpers import to_muster
    s = build_initial_state("henry_vi", seed=seed)
    to_muster(s)
    s.active_side = "yorkist"
    s.levy_step = "muster"
    act = [lid for lid, ld in s.lords.items()
           if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED][0]
    s.lords[act].location = "ely"
    s.locales["ely"].favour = "yorkist"
    tgt = [lid for lid, ld in s.lords.items() if ld.side == "yorkist" and lid != act][0]
    seat = static_data.load_lords()[tgt]["seat"]
    s.lords[tgt].status = LordStatus.CALENDAR
    s.lords[tgt].calendar_box = s.turn_box
    enemy = [lid for lid, ld in s.lords.items() if ld.side == "lancastrian"][0]
    s.lords[enemy].status = LordStatus.MUSTERED
    s.lords[enemy].location = seat            # block the target's own Seat
    return s, act, tgt


def test_levy_lord_uses_chosen_fallback_seat():
    from plantagenet import actions
    for seed in range(1, 40):
        s, act, tgt = _levy_lord_fallback_state(seed)
        opts = actions._friendly_enemyfree_seats(s, "yorkist")
        r = actions.apply_action(s, {"type": "levy_lord", "side": "yorkist",
                                     "by_lord": act, "target": tgt,
                                     "fallback_seat": opts[0]})
        if r.get("success"):
            assert s.lords[tgt].location == opts[0]        # placed at the chosen Seat (3.4.2)
            return
    raise AssertionError("no successful levy_lord seed found")


def test_levy_lord_rejects_invalid_fallback_seat():
    import pytest

    from plantagenet import actions
    from plantagenet.errors import IllegalAction
    s, act, tgt = _levy_lord_fallback_state(1)
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "levy_lord", "side": "yorkist", "by_lord": act,
                                 "target": tgt, "fallback_seat": "london"})
    assert e.value.code == "bad_fallback_seat"


# --------------------------------------------------------------------------- #
# Group Sail (4.6.1): a Marshal/Lieutenant Sails with co-located Lords          #
# --------------------------------------------------------------------------- #
def test_group_sail_moves_shipless_passenger():
    from plantagenet import actions
    from tests.test_commands import _to_campaign
    s = _to_campaign("henry_vi")
    lead, passenger = "york", "salisbury"            # york is a Marshal
    s.active_side = "yorkist"
    s.campaign.active_lord = lead
    s.campaign.actions_remaining = 2
    for lid in (lead, passenger):
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].location = "bristol"            # Irish-Sea Port
        s.lords[lid].at_sea = None
        s.lords[lid].forces = {"retinue": 1}
    s.lords[passenger].assets = {"ship": 0}          # shipless -- can only go as passenger
    s.lords[lead].assets = {"ship": 2}               # leader carries the Group
    r = actions.apply_action(s, {"type": "sail", "side": "yorkist", "by_lord": lead,
                                 "to": "pembroke", "group": [passenger]})
    assert r["type"] == "sail"
    assert s.lords[passenger].location == "pembroke"     # passenger moved (was impossible)
    assert s.lords[passenger].moved_fought is True


def test_group_sail_requires_marshal_or_lieutenant():
    import pytest

    from plantagenet import actions, static_data
    from plantagenet.errors import IllegalAction
    from tests.test_commands import _to_campaign
    s = _to_campaign("henry_vi")
    nonlead = next(lid for lid, d in static_data.load_lords().items()
                   if d.get("title") not in ("marshal", "lieutenant")
                   and s.lords.get(lid) and s.lords[lid].side == "yorkist")
    s.active_side = "yorkist"
    s.campaign.active_lord = nonlead
    s.campaign.actions_remaining = 2
    for lid in (nonlead, "salisbury"):
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].location = "bristol"
        s.lords[lid].at_sea = None
    s.lords[nonlead].assets = {"ship": 2}
    with pytest.raises(IllegalAction) as e:
        actions.apply_action(s, {"type": "sail", "side": "yorkist", "by_lord": nonlead,
                                 "to": "pembroke", "group": ["salisbury"]})
    assert e.value.code == "not_group_leader"


# --------------------------------------------------------------------------- #
# Per-Round Reposition (4.4.2): owner chooses which wing fills the empty center  #
# --------------------------------------------------------------------------- #
def test_reposition_center_fill_choice():
    s = build_initial_state("henry_vi")
    for lid in ("york", "march", "salisbury"):
        s.lords[lid].status = LordStatus.MUSTERED
    forces = {lid: battle._Force(s, lid) for lid in ("york", "march", "salisbury")}
    positions = {"attacker": {0: "york", 2: "march"}, "defender": {0: "salisbury"}}
    reserves = {"attacker": [], "defender": []}
    battle._reposition(positions, reserves, forces,
                       repo={"attacker": {"center_from": 2}})   # pull right wing to center
    assert positions["attacker"].get(1) == "march"              # chosen wing filled center


def test_reposition_advance_choice():
    s = build_initial_state("henry_vi")
    for lid in ("york", "march", "salisbury"):
        s.lords[lid].status = LordStatus.MUSTERED
    forces = {lid: battle._Force(s, lid) for lid in ("york", "march", "salisbury")}
    positions = {"attacker": {}, "defender": {0: "salisbury"}}
    reserves = {"attacker": ["york", "march"], "defender": []}
    battle._reposition(positions, reserves, forces,
                       repo={"attacker": {"advance": {2: "march"}}})  # march to right slot
    assert positions["attacker"][2] == "march"


# --------------------------------------------------------------------------- #
# Per-Hit absorption (4.4.2 "Hit by Hit"): owner directs an individual Hit       #
# --------------------------------------------------------------------------- #
def test_absorb_plan_directs_individual_hit():
    s = build_initial_state("henry_vi")
    for lid in ("york", "march"):
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].forces = {"retinue": 1}
    f1 = battle._Force(s, "york")
    f2 = battle._Force(s, "march")
    log: list = []
    # Default would hit york first; the plan directs the Hit to march's Retinue.
    battle._absorb_side([f1, f2], 1, _SeqDice([6]), battle._ABSORB_DEFAULT, set(),
                        log, "melee", None, [{"lord": "march", "unit": "retinue"}])
    assert log[0]["lord"] == "march"
    assert f2.routed.get("retinue", 0) == 1
    assert f1.routed.get("retinue", 0) == 0


# --------------------------------------------------------------------------- #
# Group-March Haul Sharing (4.3.2) and Caltrops split (Y19)                      #
# --------------------------------------------------------------------------- #
def test_group_march_haul_shares_carts():
    from plantagenet import actions
    from tests.test_commands import _to_campaign
    s = _to_campaign("henry_vi")
    lead, passenger = "york", "salisbury"
    s.active_side = "yorkist"
    s.campaign.active_lord = lead
    s.campaign.actions_remaining = 2
    for lid in (lead, passenger):
        s.lords[lid].status = LordStatus.MUSTERED
        s.lords[lid].location = "ely"
        s.lords[lid].forces = {"retinue": 1}
    # Passenger has surplus Provender but no Carts; leader has spare Carts.
    s.lords[passenger].assets = {"provender": 3, "cart": 0}
    s.lords[lead].assets = {"provender": 0, "cart": 4}
    # Ely -> Cambridge by Highway; group march.
    actions.apply_action(s, {"type": "march", "side": "yorkist", "by_lord": lead,
                             "to": "cambridge", "group": [passenger]})
    # Group Carts (4) cover the group's Provender (3): nothing discarded (was: passenger
    # would lose all 3 for having 0 Carts).
    assert s.lords[passenger].assets["provender"] == 3


def test_caltrops_split_limits_hits_this_engagement():
    s = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s.lords[lid].location = "cambridge"
        s.lords[lid].forces = {"retinue": 1, "men_at_arms": 4}
    s.decks["yorkist"]["held"] = ["Y19"]                 # Yorkist holds Caltrops
    base = battle.resolve_battle(s, "cambridge", "york", "henry_vi", {"caltrops": ["yorkist"]})
    base_m = next(st for st in base["rounds"][0]["engagements"][0]["strikes"]
                  if st["phase"] == "melee")["attacker_hits"]
    s2 = build_initial_state("henry_vi")
    for lid in ("york", "henry_vi"):
        s2.lords[lid].location = "cambridge"
        s2.lords[lid].forces = {"retinue": 1, "men_at_arms": 4}
    s2.decks["yorkist"]["held"] = ["Y19"]
    # Direct only 1 of the +2 to this (only) Engagement.
    r = battle.resolve_battle(s2, "cambridge", "york", "henry_vi",
                              {"caltrops": ["yorkist"], "caltrops_split": {1: {"yorkist": [1]}}})
    r_m = next(st for st in r["rounds"][0]["engagements"][0]["strikes"]
               if st["phase"] == "melee")["attacker_hits"]
    assert r_m == base_m - 1                              # +1 here instead of the full +2


# --------------------------------------------------------------------------- #
# Full rules audit (2026-06) — batch 1 regressions                              #
# --------------------------------------------------------------------------- #
def test_effective_lordship_raises_the_levy_action_cap():
    # Y22 Loyalty and Trust gives a chosen Lord +3 Lordship; the action cap (3.4)
    # must use effective, not printed, Lordship (1.5.2/1.9.1).
    from plantagenet import actions, ratings, static_data
    s = build_initial_state("henry_vi")
    lid = "york"
    printed = static_data.load_lords()[lid]["ratings"]["lordship"]
    s.active_events.append({"card": "Y22", "side": "yorkist", "target": lid})
    assert ratings.rating(s, lid, "lordship") == printed + 3
    s.lords[lid].location = "ely"
    s.locales["ely"].favour = "yorkist"
    s.lords[lid].lordship_spent = printed            # would be "exhausted" under printed cap
    # _active_lord must NOT raise -- the Lord still has 3 effective Lordship left.
    s.active_side = "yorkist"
    s.levy_step = "muster"
    actions._active_lord(s, {"by_lord": lid, "side": "yorkist"}, require_lordship=True)


def test_pay_charges_exile_pact_lord_two_influence():
    # 3.2.2: Lords in Exile boxes cost 2 Influence; a Y8 (EXILE-status) Lord must be charged.
    from plantagenet import pay
    s = build_initial_state("henry_vi")
    yk = [lid for lid, ld in s.lords.items()
          if ld.side == "yorkist" and ld.status == LordStatus.MUSTERED]
    for lid in yk:                                   # clear the board to isolate the cost
        s.lords[lid].status = LordStatus.CALENDAR
    lid = yk[0]
    s.lords[lid].status = LordStatus.EXILE
    s.lords[lid].exile_box = "ireland"
    s.lords[lid].location = None
    track = s.influence["track"]
    before = (track.marker_side, track.marker_at)
    pay._pay_lords(s, "yorkist", {})
    assert (track.marker_side, track.marker_at) != before   # the 2-Influence cost was charged


def test_grand_scenario_threshold_is_flat_per_war():
    from plantagenet import campaign
    s = build_initial_state("wars_of_the_roses")
    s.grand_scenario["current_war"] = "war_i"
    thr = s.grand_scenario["victory_threshold"]
    for box in (1, 7, 12):                            # flat across the War, not henry_vi 40/35/30
        s.turn_box = box
        assert campaign._current_threshold(s) == thr


def test_routed_vassal_of_unrouted_winner_disbands():
    from plantagenet.state import VassalStatus
    s = build_initial_state("henry_vi", seed=1)
    vid = next(v for v in s.vassals)
    s.vassals[vid].status = VassalStatus.MUSTERED
    s.vassals[vid].on_lord = "york"
    s.lords["york"].vassals = [vid]
    s.lords["york"].location = "london"
    s.lords["henry_vi"].location = "london"
    f_y = battle._Force(s, "york")
    f_h = battle._Force(s, "henry_vi")
    f_h.lord_routed = True                            # Henry VI loses
    f_y.routed["vassal"] = 1                           # York wins but his Vassal Routed
    res = battle._ending(s, "london", {"york": f_y, "henry_vi": f_h},
                         ["york"], ["henry_vi"], [], [])
    assert res.get("vassal_disbands") == [vid]
    assert s.vassals[vid].status == VassalStatus.DISBANDED


def test_losses_do_not_remove_more_than_mat_troops():
    # Battle-local (Capability-added) Troops that Rout vanish; they must not drive
    # mat Troop Losses beyond the Lord's persistent count (4.4.3).
    s = build_initial_state("henry_vi")
    s.lords["york"].forces = {"retinue": 1, "men_at_arms": 1}   # 1 mat MaA
    f = battle._Force(s, "york")
    f.count["men_at_arms"] = 3                          # +2 battle-local (e.g. Escape-Ship adds)
    f.routed["men_at_arms"] = 3                          # all 3 routed
    res: dict = {}
    battle._losses(s, f, _SeqDice([6]), res)             # 6 always fails Protection here
    assert res["losses"]["york"]["lost"] <= 1            # at most the 1 mat MaA, not 3
    assert s.lords["york"].forces.get("men_at_arms", 0) == 0


def test_capability_eligibility_restricts_to_named_lord():
    # Single-Lord Capabilities (cards.json capability.lords == null) are restricted
    # via the "Lord:" line in the card text (3.4.6), not permitted for any Lord.
    from plantagenet import actions
    assert actions._capability_eligible("Y15", "warwick_yorkist") is True   # Naval Blockade
    assert actions._capability_eligible("Y15", "york") is False
    assert actions._capability_eligible("Y22", "salisbury") is True         # Fair Arbiter
    assert actions._capability_eligible("Y22", "york") is False
    assert actions._capability_eligible("L14", "northumberland_lancastrian") is True
    assert actions._capability_eligible("L14", "somerset_1") is False
    assert actions._capability_eligible("L21", "somerset_1") is True        # My Father: Any
