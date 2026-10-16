"""Parameter discovery, not a rules implementation or an exhaustive move generator.

Every custom payload still goes through the unchanged engine. Lists below name
parameters, not preset strategies. Full grammar and card text remain inspectable.
"""
from __future__ import annotations

import ast
import inspect
from copy import deepcopy

from plantagenet import static_data

CONTRACTS = {
    "build_plan": {
        "parameters": {"plan": "ordered list of {'lord': id} or {'pass': True}"},
        "constraints": "Exactly cards_required entries; only this side's Mustered Lords; at most 3 entries per Lord. Any ordering, repetition within that limit, and Pass placement are allowed.",
        "template": True,
    },
    "draw": {
        "parameters": {"assignments": "first Levy only: mapping each of the two drawn card IDs to an eligible Mustered Lord, or null when unassignable"},
        "constraints": "The menu contains all jointly legal maximum-deployment allocations. Two Capabilities per mat, no duplicate names; later Levies draw Events with no allocation.",
    },
    "parley": {
        "parameters": {"target": "Stronghold ID", "extra_spend": "0, 1 or 3 Influence", "use_parliament_votes": "bool; False saves the optional L18 benefit for later"},
        "constraints": "Phase-specific route, location, Influence and Lordship/Command requirements apply. Menu entries with no extra_spend mean 0, not the only allowed bid.",
    },
    "levy_lord": {
        "parameters": {"target": "Ready friendly Lord ID", "extra_spend": "0, 1 or 3 Influence", "fallback_seat": "chosen eligible alternative Seat when necessary"},
        "constraints": "Friendly muster location; eligible target/Seat and remaining Lordship. Engine decides legality, including fallback Seat.",
    },
    "levy_vassal": {
        "parameters": {"target": "regular Vassal ID", "extra_spend": "0, 1 or 3 Influence"},
        "constraints": "Friendly, Enemy-free Vassal Seat and other Levy requirements; effects may change cost/success.",
    },
    "levy_troops": {
        "parameters": {"levy_target": "own Stronghold or an eligible adjacent Stronghold with Commission of Array"},
        "constraints": "Friendly, Enemy-free and not Exhausted; special Irishmen/Stanley rules remain in the engine.",
    },
    "levy_transport": {"parameters": {"transport": "cart or ship"}},
    "levy_capability": {"parameters": {"card": "unused eligible Capability ID"},
                        "constraints": "Two cards per mat, no duplicate names; Held/pending/active Events unavailable."},
    "muster_exiles": {
        "parameters": {"lords": "nonempty list of Ready Exile-marked Lords", "exile_boxes": "optional mapping Lord -> current-War legal Exile box"},
        "constraints": "The menu offers single-Lord returns. Multiple eligible Lords can be submitted together. No duplicates; multiple destinations require a choice.",
    },
    "pay": {
        "parameters": {"pay_order": "ordered Lord IDs", "unpay_lords": "payment-priority preferences, not withholding available Coin", "disband_lords": "voluntary disbands", "pillage_by": "Pillage choices", "unpay_vassals": "Vassals to decline payment"},
        "constraints": "Sharing, Coin priority, Pay-before-Pillage, Influence and eligibility are validated by pay.py. Bare pay uses engine defaults, not forced choices.",
    },
    "march": {
        "parameters": {"to": "reachable Locale ID", "group": "chosen subset of eligible co-located friendly Lords", "decisions": "Approach/Intercept, Exile, tactical Battle and card choices (see combat help)"},
        "constraints": "Full-group examples do not exclude partial groups. Marshal/Lieutenant precedence, Haul, Path, Truce and special restrictions apply.",
    },
    "sail": {
        "parameters": {"to": "Port, Exile box or Sea zone", "share": "co-located friendly Lords lending transport", "group": "co-located friendly sailing Lords under command restrictions", "decisions": "Naval/tactical choices"},
        "constraints": "Ships/capacity, Sea adjacency, enemies and entire-card costs are checked by the engine.",
    },
    "supply": {"parameters": {"source": "Stronghold or Port", "use_ships": "bool", "share": "co-located friendly transport donors"}},
    "tax": {"parameters": {"target": "eligible Seat or Special Stronghold", "extra_spend": "0, 1 or 3 Influence"}},
    "end_activation": {"constraints": "Ends this Command card and Feeds both sides. Ending early is a choice, not automatically forced."},
    "end_campaign": {
        "parameters": {"decisions.discard_held": "side -> any subset of that side's Held Events; omitted/empty keeps all", "decisions.charity": "Capability holder -> 0/1/2 Provender, or {'pay': n, 'share': [donors]}", "decisions.disembark_land": "Lord -> legal Enemy-free Port for successful End-Campaign landing"},
        "constraints": "Each player owns its choices. stage_reset() collects private contributions; referee mode can submit the combined atomic payload. No Capability discard. Costs, Sharing and landing legality remain engine-validated.",
    },
    "play_event": {
        "parameters": {"card": "first pending drawn Event", "decisions": "card-specific object; inspect the card and resolver parameters below"},
        "constraints": "Resolve in draw order. No-effect preconditions remain legal; a selection template is not a forced no-decision action.",
    },
    "play_held_event": {
        "parameters": {"card": "currently playable Held Event", "decisions": "card-specific targets/allocations"},
        "constraints": "Optional, timing-limited; not mutually exclusive with ordinary commands. L28: four total Provender, nonnegative allocation among selected movers; L33: Sail-to-Port window. Inspect card text.",
    },
    "react": {
        "parameters": {"play": "current offered card ID", "pass": "True to decline", "decisions": "any effect-specific choices supported by the resolver"},
        "constraints": "Exactly the awaiting player may respond. Play and pass are both reachable. Private unplayed enemy reactions are not displayed.",
    },
    "resolve_battle": {"parameters": {"decisions": "tactical and card choices; see combat"},
                       "constraints": "In Bosworth, committed Arrays cannot be overridden. Other tactical choices remain available."},
    "choose_battle_capability": {"parameters": {"by_lord": "eligible Lord", "card": "Capability ID"},
                                 "constraints": "Four cards per side, two per mat, eligibility/no duplicates; hidden until both Arrays committed."},
    "array_battle": {"parameters": {"front": "three Lord IDs in Left/Center/Right order"},
                     "constraints": "Exactly all three Lords, no Reserve. The menu contains all six permutations."},
    "exile_pact": {"parameters": {"box": "legal Exile box"}},
    "agitators": {"parameters": {"target": "eligible adjacent Stronghold"}},
    "merchants": {"parameters": {"targets": "two depleted/exhausted targets if possible, otherwise one", "extra_spend": "Influence bid"}},
    "heralds": {"parameters": {"target": "friendly Calendar Lord", "extra_spend": "Influence bid"}},
    "concede": {"parameters": {"side": "conceding side"},
                "constraints": "MANUAL ADJUDICATION, deliberately not in menu: only before the last Heir's Death roll under 6.1.1. The engine does not model that timing window."},
}

COMBAT = {
    "notice": "These are parameter families, not an exhaustive set of combinations. Preserve each side's own choices. Full accepted payload and defaults are documented in ACTIONS.md and battle.py/commands.py; describe(..., source=True) exposes handler code without live hidden state.",
    "parameters": "attacker_positions/defender_positions (indices 0,1,2; JSON string indices accepted); flank_choice; engagement_order; absorb_order/absorb_lords/absorb_plan; reposition; flee/flee_rounds; valour; leeward; caltrops; ravine; suspicion; for_trust_not_him; culverins; yeomen; caltrops_split; regroup; vanguard; swift_maneuver/swift_maneuver_end; final_charge; patrick; warden; talbot; escape_ship; spoils_to; responses; blocked_ford; intercept/intercept_group/flank_attack",
    "constraints": "Only participating Lords in each side's Array. Troop/Vassal hit allocation, Reserve advances, Flee, Valour and card timing follow the engine and current card text. Replacing a menu example's decisions is allowed; it is not the only legal tactical policy.",
}

# Parameterized defaults must never be auto-executed merely because the engine
# emits one representative dictionary. Conservative stopping costs no freedom.
PARAMETERIZED = set(CONTRACTS) - {"levy_transport", "levy_capability", "choose_battle_capability", "array_battle", "agitators", "exile_pact"}


def resolver_parameters(function):
    """Literal payload reads from actual resolver source; not guessed schemas."""
    source = inspect.getsource(function)
    tree = ast.parse(source)
    params = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get" and isinstance(node.func.value, ast.Name)
                and node.func.value.id in ("d", "decisions", "action") and node.args
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
            params.add(node.func.value.id + "." + node.args[0].value)
    return {"payload_keys_read": sorted(params), "resolver": function.__name__,
            "constraints_from_source": source}


def contract(state, typ, move=None):
    info = deepcopy(CONTRACTS.get(typ, {"parameters": {}, "constraints": "Concrete engine action; apply_action is authoritative."}))
    info["action_type"] = typ
    info["raw_action"] = "apply({...}, expected_version=version()); IDs may be supplemented with parameters={...}."
    info["details"] = "inspect('grammar') and inspect('card', card='ID'); no output-size limit forbids detail."
    if typ == "build_plan":
        side = (move or {}).get("side", state.active_side)
        info["side"] = side
        info["cards_required"] = state.campaign.cards_required if state.campaign else None
        info["eligible_lords"] = [lid for lid, lord in state.lords.items()
                                  if lord.side == side and lord.status == "mustered"]
        info["example_policy"] = "No default plan is substituted. Choose any legal construction."
    if typ in ("march", "sail", "resolve_battle", "react"):
        info["combat"] = deepcopy(COMBAT)
    cid = (move or {}).get("card") or (move or {}).get("play")
    if cid in static_data.load_cards():
        info["card"] = deepcopy(static_data.load_cards()[cid])
        if typ in ("play_event", "play_held_event"):
            from plantagenet import events
            resolver = (events._IMMEDIATE if typ == "play_event" else events._HELD_PLAYS).get(cid)
            if resolver is not None:
                info["resolver_contract"] = resolver_parameters(resolver)
    return info
