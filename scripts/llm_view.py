"""Read-only, player-safe views. Raw engine state is a trusted referee interface.

No rule execution or strategic move selection belongs in this module. Future
plans, deck order, random state and an opponent's unplayed cards are not public.
"""
from __future__ import annotations

from copy import deepcopy

from plantagenet import ratings, static_data

SIDES = ("lancastrian", "yorkist")


def decision_side(state):
    if state.pending:
        inter = state.pending[0]
        offers = inter.get("offers", [])
        index = inter.get("idx", 0)
        if index < len(offers):
            return offers[index]["side"]
    if state.campaign and state.campaign.step == "plan":
        # The engine's Plan builder need not change active_side between submissions.
        for side in sorted(SIDES, key=lambda s: state.roles.get(s) != "rebel"):
            if not state.campaign.plan_built.get(side):
                return side
    return state.active_side


def pending_view(state, viewer):
    if state.pending:
        inter = state.pending[0]
        offers = inter.get("offers", [])
        idx = inter.get("idx", 0)
        offer = offers[idx] if idx < len(offers) else {}
        data = {"kind": "reaction", "trigger": inter.get("trigger"),
                "awaiting_side": offer.get("side")}
        # The reacting player needs the declared operation, not the opaque
        # continuation (which also contains tactical policies and rollback data).
        ctx = inter.get("ctx", {})
        public_keys = ("approaching_side", "dest", "target_lords", "actor", "side", "seas", "actor_side")
        data["context"] = {k: deepcopy(ctx[k]) for k in public_keys if k in ctx}
        finish = inter.get("finish_data", {})
        declared_keys = ("movers", "leader", "lord", "origin", "dest", "group", "target", "source", "via", "added", "way_cost", "extra", "into_sea")
        data["declared_operation"] = {k: deepcopy(finish[k]) for k in declared_keys if k in finish}
        if inter.get("trigger") == "after_successful_levy_action":
            data["levy_result"] = result_view(finish.get("result", {}), ctx.get("actor_side"), viewer, state)
        if viewer in ("referee", offer.get("side")):
            data["choice"] = deepcopy(offer)
            data["alternatives"] = "play this offer or pass; parameters via describe('react')"
        return data
    if state.pending_events:
        first = state.pending_events[0]
        data = {"kind": "drawn_event", "awaiting_side": first.get("side"),
                "count": len(state.pending_events)}
        if viewer in ("referee", first.get("side")):
            data["events"] = deepcopy(state.pending_events)
        return data
    if state.battle_setup and not state.battle_setup.complete:
        return {"kind": "bosworth_setup", "awaiting_side": state.active_side}
    if state.campaign and state.campaign.step == "plan":
        return {"kind": "campaign_plan", "awaiting_side": decision_side(state),
                "cards_required": state.campaign.cards_required,
                "construction": "ordered lord/pass entries, at most 3 per Mustered Lord"}
    return None


def visible_state(state, viewer):
    """Complete *visible* dynamic state, independent of how tersely it is printed."""
    data = state.model_dump(mode="json")
    for key in ("seed", "rng_state", "history", "grand_scenario", "pending"):
        data.pop(key, None)
    data["pending"] = pending_view(state, viewer)
    data["pending_events"] = [deepcopy(e) for e in state.pending_events
                              if viewer in ("referee", e.get("side"))]
    data["grand_scenario"] = None
    if state.grand_scenario:
        # The static setup tables include deck composition, but not live hidden
        # state. Keep current-War bookkeeping, inspect static rules separately.
        data["grand_scenario"] = deepcopy(state.grand_scenario)
    data["decks"] = {}
    for side, deck in state.decks.items():
        # Do not reveal the next draw, even to its owner. First-Levy assignment
        # options expose ONLY the already determined two-card draw, as the
        # existing engine API specifies (not the rest of the shuffled deck).
        data["decks"][side] = {p + "_count": len(cs) for p, cs in deck.items()}
        if viewer in ("referee", side):
            data["decks"][side]["held"] = list(deck.get("held", []))
            data["decks"][side]["set_aside"] = list(deck.get("set_aside", []))
    if state.campaign:
        c = state.campaign
        for side, plan in c.plans.items():
            if viewer not in ("referee", side):
                seen = c.plan_index.get(side, 0)
                if c.step == "activation" and state.active_side == side:
                    seen += 1  # the current card is already face up
                data["campaign"]["plans"][side] = {
                    "revealed": deepcopy(plan[:seen]), "unrevealed_count": len(plan[seen:])}
    if state.battle_setup and not state.battle_setup.complete and viewer != "referee":
        b = state.battle_setup
        data["battle_setup"] = {
            "complete": False,
            "capabilities": {viewer: deepcopy(b.capabilities.get(viewer, {}))},
            "arrays": {viewer: deepcopy(b.arrays[viewer])} if viewer in b.arrays else {},
            "committed_sides": list(b.arrays)}
    return data


def action_view(move, viewer, state):
    out = deepcopy(move)
    if viewer == "referee":
        return out
    if "discard_held_options" in out:
        out["discard_held_options"] = {viewer: out["discard_held_options"].get(viewer, [])}
        out["_joint_decision"] = "Both players choose privately; stage_reset or referee payload."
    if isinstance(out.get("decisions"), dict) and "discard_held" in out["decisions"]:
        out["decisions"]["discard_held"] = {
            viewer: out["decisions"]["discard_held"].get(viewer, [])}
    if "battle_reactions" in out:
        # An enemy Capability is public, a Held Event is not. Do not leak even
        # the number or identity of the enemy's optional Held reactions.
        out["battle_reactions"] = [o for o in out["battle_reactions"]
            if o.get("side") == viewer or any(o.get("card") in lord.capabilities
                                             for lord in state.lords.values())]
    return out


def private_action(action, owner, viewer, state):
    """Safe historical action (not a replay artifact; replay is referee-only)."""
    if viewer in ("referee", owner):
        return action_view(action, viewer, state)
    typ = action.get("type")
    if typ in ("build_plan", "draw", "choose_battle_capability", "array_battle", "react"):
        return {"type": typ, "side": owner, "private_parameters": "withheld"}
    out = action_view(action, viewer, state)
    # Arbitrary decisions may contain private plans/choice submissions.
    out.pop("decisions", None)
    return out


def result_view(result, owner, viewer, state):
    """Restrict engine results before returning OR printing them.

    Full private results are available only to their owner or the explicit
    referee. Internal reaction continuations and other sides' declined cards
    must not leak through nested combat results.
    """
    if not isinstance(result, dict):
        return deepcopy(result)
    if viewer == "referee":
        return deepcopy(result)
    typ = result.get("type")
    if owner != viewer and typ in ("draw", "choose_battle_capability", "array_battle"):
        return {"type": typ, "side": owner, "private_result": "withheld"}

    def walk(obj):
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        if not isinstance(obj, dict):
            return obj
        if obj.get("passed"):
            # A pass does not reveal the opponent's unused Held Event.
            return {"passed": True}
        out = {}
        for k, v in obj.items():
            if k in ("undo", "resume_key", "finish_data", "offers", "rng_state", "seed"):
                continue
            if k == "remaining" and obj.get("type") == "pending_reactions":
                continue  # number of queued private reaction opportunities
            if k == "peek" and owner != viewer:
                out[k] = "private information revealed to the acting player"
            elif k == "awaiting" and isinstance(v, dict) and v.get("side") != viewer:
                out[k] = {"side": v.get("side"), "decision": "reaction"}
            elif k == "discarded_held" and isinstance(v, dict):
                out[k] = {s: cs if s == viewer else {"count": len(cs)} for s, cs in v.items()}
            elif k == "decisions" and owner != viewer:
                continue
            else:
                out[k] = walk(v)
        return out
    return walk(result)


def changes(before, after, path=""):
    """Lossless visible-state patch: leaves include before/after (including removals)."""
    if before == after:
        return {}
    if isinstance(before, dict) and isinstance(after, dict):
        out = {}
        for key in sorted(before.keys() | after.keys()):
            p = f"{path}.{key}" if path else str(key)
            if key not in before:
                out[p] = {"added": deepcopy(after[key])}
            elif key not in after:
                out[p] = {"removed": deepcopy(before[key])}
            else:
                out.update(changes(before[key], after[key], p))
        return out
    return {path: {"before": deepcopy(before), "after": deepcopy(after)}}


def briefing(state, viewer, dumps):
    """Compact fresh baseline. F=Forces, A=Assets; no count is rounded/capped."""
    view = visible_state(state, viewer)
    war = (state.grand_scenario or {}).get("current_war", "standalone")
    lines = [f"{state.scenario}/{war} box {state.turn_box} {state.phase}/{state.levy_step} "
             f"| acting {decision_side(state)} | view {viewer}"]

    def counts(items):
        return ",".join(f"{key}:{value}" for key, value in items.items()) or "none"

    inf = []
    for track in state.influence.values():
        inf.append(f"{track.marker_side}:{track.marker_at}; markers " +
                   ",".join(f"{key}:{m.side}:{m.at}" for key, m in track.stronghold_markers.items()) +
                   (f"; victory-check:{track.victory_check}" if track.victory_check is not None else ""))
    lines.append("Influence " + (" | ".join(inf) or "none") +
                 (" | VICTORY " + dumps(state.victory) if state.victory else ""))
    lines.append("F=forces; A=assets; I/L/C=effective Influence/Lordship/Command; used=Lordship spent.")
    for side in SIDES:
        lines.append(side + " (" + state.roles.get(side, "") + "):")
        off = []
        for lid, lord in state.lords.items():
            if lord.side != side:
                continue
            if lord.status == "mustered":
                loc = lord.location or lord.exile_box or lord.at_sea or "off-map"
                rs = "/".join(str(ratings.rating(state, lid, k)) for k in ("influence", "lordship", "command"))
                lines.append(f" {lid}@{loc} F[{counts(lord.forces)}] A[{counts(lord.assets)}] "
                             f"I/L/C={rs} used={lord.lordship_spent}"
                             + (" ring=" + lord.ring if lord.ring else "")
                             + (" caps=" + ",".join(lord.capabilities) if lord.capabilities else "")
                             + (" vassals=" + ",".join(lord.vassals + lord.special_vassals)
                                if lord.vassals or lord.special_vassals else "")
                             + (" Feed-due" if lord.moved_fought else "")
                             + (" new-muster" if lord.mustered_this_segment else "")
                             + (" skip-next-Feed" if lord.ignore_next_feed else ""))
            else:
                loc = lord.calendar_box if lord.calendar_box is not None else lord.exile_box
                off.append(f"{lid}:{lord.status}" + (f"@{loc}" if loc is not None else "")
                           + ("(Exile)" if lord.calendar_exile else "")
                           + (" ring=" + lord.ring if lord.ring else "")
                           + (" captured-by=" + lord.captured_by if lord.captured_by else ""))
        if off:
            lines.append(" " + "; ".join(off))
    # All non-default Favour/depletion is explicit; detail includes the complete
    # map and static geography, not a strategically filtered neighborhood.
    locs = []
    for side in SIDES:
        locs.append(side + "=" + ",".join(lid for lid, ls in state.locales.items() if ls.favour == side))
    for dep in ("depleted", "exhausted"):
        ids = [lid for lid, ls in state.locales.items() if ls.depletion == dep]
        if ids:
            locs.append(dep + "=" + ",".join(ids))
    extra = {lid: ls.favour_extra for lid, ls in state.locales.items() if ls.favour_extra}
    if extra:
        locs.append("extra=" + dumps(extra))
    lines.append("Locales (others neutral/un-depleted): " + "; ".join(locs))
    cards = []
    for side, deck in state.decks.items():
        counts_ = ",".join(p + ":" + str(len(cs)) for p, cs in deck.items() if p != "held")
        held = ",".join(deck.get("held", [])) or "none" if viewer in ("referee", side) else str(len(deck.get("held", []))) + " hidden"
        cards.append(f"{side} {counts_}; held[{held}]")
    lines.append("Cards " + " | ".join(cards))
    lines.append("Active effects " + dumps(view["active_events"]))
    lines.append("Exile " + counts(state.exile_alignment) +
                 ("; depletion=" + counts(state.exile_depletion) if state.exile_depletion else ""))
    if state.campaign:
        c = state.campaign
        plans = []
        for side, plan in view["campaign"]["plans"].items():
            hidden = plan.get("unrevealed_count", 0) if isinstance(plan, dict) else 0
            entries = plan.get("revealed", []) if isinstance(plan, dict) else plan
            seq = ",".join(e.get("lord", "Pass") for e in entries)
            plans.append(f"{side}=[{seq}]" + (f"+{hidden} hidden" if hidden else ""))
        lines.append(f"Campaign {c.step}; required={c.cards_required}; built={counts(c.plan_built)}; "
                     f"indices={counts(c.plan_index)}; active={c.active_lord}; commands={c.actions_remaining}; " + "; ".join(plans))
    if view["battle_setup"]:
        lines.append("Battle setup " + dumps(view["battle_setup"]))
    if view["flags"]:
        lines.append("Flags " + dumps(view["flags"]))
    if view["pending"]:
        lines.append("PENDING " + dumps(view["pending"]))
    if view["hold_window"]:
        lines.append("Optional Held window " + dumps(view["hold_window"]))
    return "\n".join(lines)


def change_text(delta, dumps):
    """Render the complete lossless patch compactly, without dropping changes."""
    lines = []
    for path, entry in delta.items():
        if "before" in entry:
            lines.append(f"{path}: {dumps(entry['before'])}->{dumps(entry['after'])}")
        elif "added" in entry:
            lines.append(f"{path}: +{dumps(entry['added'])}")
        else:
            lines.append(f"{path}: -{dumps(entry['removed'])}")
    return "; ".join(lines) or "none"


def card_text(card):
    return deepcopy(static_data.load_cards()[card])
