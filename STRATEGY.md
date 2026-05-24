# Plantagenet: Cousins' War — Strategy Notes

## Scope and provenance

This document records strategic impressions from repeated AI playthroughs of
GMT's *Plantagenet: Cousins' War* driven through this harness — the short
**Henry VI** and **Towton** scenarios, the medium **My Kingdom for a Horse**,
and several **Wars of the Roses** grand-campaign runs, with the AI controlling
both sides and playing each active side to win.

These are working impressions, not settled doctrine. The play was bounded by
the harness interface, the model's limited strategic horizon, and the fact that
not every legal branch or card interaction was explored (see *Underexplored
areas*). Human players will likely find sharper lines, especially around card
timing.

> **Important caveat — provenance vs. the engine.** Most of these playthroughs
> predate the Phase 8 victory-logic fix. Before that fix, the engine reported
> the **5.1 Campaign Victory winner reversed** (awarding the game to the side
> that had *lost* its Lords) and did **not** count Exile-box Lords as presence.
> So any *specific game outcome* that was decided by 5.1 in those runs may have
> been mis-adjudicated and should be re-verified on the current engine. The
> strategic *principles* below — presence matters, Exile is a reserve, Calendar
> timing decides windows — are rules-correct and are now modeled correctly; it
> is the recorded win/loss of individual 5.1-decided games that warrants a
> fresh look.

## Central thesis

**Plantagenet is a game about aristocratic continuity under stress.** You are
not a modern state with a reliable command structure; you are a faction trying
to operate through powerful, limited, temporary, vulnerable Lords. Every action
spends time, Service, assets, position, and political capital.

Battle matters enormously, but it is only one way to produce the real strategic
result: the collapse, exhaustion, removal, exile, or delay of the enemy's
*usable* Lords. The side that wins is not always the one that looks strongest in
a single moment — it is the one that still has functioning political-military
machinery when the game asks, **"Who remains?"**

---

## Part I — Core strategic variables

### 1. Lord continuity is the deepest game

The most-repeated lesson: a faction can look healthy on the Influence track and
still lose if it has no viable Lord at the moment a victory check fires. A side
that trades its last effective map Lord for a flashy blow may be walking into
defeat.

This makes **Lord status** a central strategic variable — on map, in Exile, on
the Calendar, removed, available-but-unmustered, or mustered-but-too-distant /
undersupplied / nearly out of Service. The game constantly asks not "Who is
winning?" but "Who will still be able to act when the check happens?"

Before any battle or campaign, ask: if I win this fight, who remains on my
side? If my active Lord goes to the Calendar, do I have another ready? If the
enemy loses a key Lord, do they still have Exile survival? Will the next check
care more about Influence or presence?

*(This is rule 5.1 in mechanical form — see Part IV.)*

### 2. Battle is a political operation, not just a combat operation

In many wargames a favorable battle is automatically good. In Plantagenet a
favorable battle can still be strategically bad if it leaves the winner too
depleted, delayed, or absent. Treat battle as a political operation that spends
two resources — troops *and* Lord continuity.

Five questions before accepting battle:

1. **What does this battle actually win?** A critical seat, broken enemy
   presence, a victory threshold, a protected Lord — or nothing that moves a
   victory condition?
2. **Can I survive my own success?** If my leader is removed or sent to the
   Calendar, does my faction still function?
3. **Does the enemy have a backup plan?** Lords in Exile or arriving from the
   Calendar may survive a defeat that looks decisive.
4. **Will the battle change the relevant victory check?** A battle that doesn't
   move the check can be a glorious waste.
5. **Can I get the same result by position, Parley, or delay?** Sometimes the
   strongest move is refusing to fight.

The best battles destroy the opponent's ability to maintain Lord presence,
secure a key political/geographic condition, force a check on favorable terms,
or preserve your faction while exhausting the enemy.

### 3. Presence can matter more than Influence

A useful rule of thumb: **Influence wins when both factions remain functional;
presence wins when one faction ceases to function.** Do not chase the prettier
political number while letting every usable Lord vanish — that builds a
beautiful legal argument for a faction that no longer exists in practice. Treat
political advantage and operational continuity as *separate* requirements; you
usually need both.

### 4. Exile is a strategic reserve, not just a penalty

A Lord in Exile isn't winning local fights, but it preserves faction continuity
and a future threat — and it now counts as presence at a victory check (Part
IV). A faction with Exile Lords can survive disasters that would otherwise end
the war. This is especially significant for the Lancastrians in the late-war
scenarios: the Yorkists may remove or delay an on-map Lancastrian figure and
still fail to kill the faction if Tudor-aligned Lords remain in Exile.

When attacking, ask whether you are truly destroying the enemy or merely pushing
its political future off-map.

### 5. Calendar timing is a hidden victory condition

Calendar placement is a strategic clock, not bookkeeping. A Lord who returns too
late is as useless as a removed one if the decision window is short. A side with
several Lords on later Calendar boxes can be theoretically powerful but
practically dead for the current check. Every serious decision should weigh:
when does this Lord come back, will the war still be running then, and can the
enemy force a check before then?

### 6. Supply and logistics quietly decide what is possible

Strategy is often made before the battle. The ability to March, concentrate, and
fight depends on assets, Provender, transport, and Service. A strong plan
specifies how the Lord moves, how it stays supplied, whether it survives the
march sequence, whether it can still fight on arrival, and whether it has enough
Service left to exploit success. Avoid armies that look impressive but cannot
campaign coherently.

### 7. Parley is a quiet power move

Parley turns local presence into durable political advantage. Use it to secure
key strongholds without battle losses, create or deny local bases, support
Influence objectives, make enemy movement awkward, and force the opponent to
spend actions repairing political damage. A side that only fights and never
Parleys can win combats while losing the political structure of the war. *(The
harness now offers own-location Parley even on a non-Friendly Stronghold — see
Part IV.)*

### 8. London, York, and major seats are strategic arguments

Major locations are political anchors, not just map nodes. Distinguish locations
that merely aid movement from those that provide supply/staging, those that move
Favour/Influence, and those whose loss changes the war's political narrative.
The most important locations combine several of these. London in particular is a
legitimacy engine, a staging point, and a prize; York plays a comparable role in
northern-centered situations such as Towton.

---

## Part II — Faction doctrines

### Yorkist: tempo, crisis creation, survival discipline

The Yorkists are strongest seizing initiative and forcing a Lancastrian crisis
before the Lancastrian position can broaden and stabilize. They are the faction
of tempo: rapid pressure on key locations, concentration of dangerous Lords,
sudden political/military crises, exploitation of Henry VI's vulnerability, and
turning early action into a threshold or presence-based win.

Their characteristic failure is burning out — overextending for a decisive blow,
trading away their own remaining presence, mistaking battle success for
strategic security, or letting key Lords fall to the Calendar at the wrong time
and so winning the map locally while losing the continuity race.

> Yorkist doctrine: *"How do I make the Lancastrian position collapse before it
> becomes broad, patient, and resilient — and who will still be alive, present,
> or available after I create that crisis?"* The Yorkists are a tempo faction
> that must avoid self-destruction, not simply an attack faction.

### Lancastrian: resilience, consolidation, punishing overreach

The Lancastrians are less flashy but more resilient. Their path is to survive
the first Yorkist surge, preserve viable Lords, consolidate key Favour, and make
Yorkist aggression expensive. If the Yorkists attack recklessly, the
Lancastrians can win not by conquest but by remaining politically alive while
Yorkist Lords vanish, exhaust, or cycle away — Exile survival can compensate for
apparent tactical disaster.

Their characteristic failures are the opposite: becoming so passive they concede
a Yorkist threshold win, letting Henry VI (or another vulnerable royal asset)
become a decisive target, failing to broaden the Lord base, losing key political
locations before they stabilize, and treating legitimacy as a shield against
operational collapse.

> Lancastrian doctrine: *"How do I remain alive, legitimate, and difficult to
> finish until Yorkist tempo decays?"* A Lancastrian strategy need not look
> dramatic; if Yorkist aggression spends itself and the Lancastrians still have
> usable Lords, they may already be winning.

---

## Part III — Scenario notes

**Henry VI (short).** Yorkist tempo is very dangerous; the Yorkists should
create a crisis early rather than over-mustering a perfect force, and the
Lancastrians must avoid letting Henry VI become the focal point of a decisive
Yorkist blow. Yorkists: create a crisis quickly, don't over-muster.
Lancastrians: preserve the King, broaden the position, make the Yorkists spend
time.

**Towton (Test of Arms).** The scenario's *Test of Arms* special rule pushes the
game toward a decisive confrontation centered on York: each Battle at York sets
York's Favour to the winner, and the side holding York's Favour at Campaign end
wins (draw if neither holds it). The battle is not the only issue — the political
condition around York is. A side that cannot force the right collision can lose
through the scenario rule rather than battlefield collapse. *(In current-engine
replays where neither side ends holding York, the result is correctly a draw.)*

**My Kingdom for a Horse.** This produced the clearest single lesson: the
Yorkists removed Henry Tudor but lost because their own effective Lord presence
collapsed while Lancastrian Lords survived in Exile. Yorkists: killing Henry
Tudor is not enough if it destroys Yorkist continuity. Lancastrians: Exile
survival and faction continuity can offset tactical disaster. *(Note: this
outcome was observed before the Phase 8 fix; the principle is sound and the
Exile-as-presence interaction is now modeled correctly, but the specific
recorded result is worth re-confirming on the current engine.)*

**Wars of the Roses (grand campaign).** Individual War victories do not settle
the strategic story — winning one War shapes the next, but the campaign is about
maintaining faction life across cycles of mobilization, exile, return, and
collapse. It rewards continuity management over single-War brilliance; a side can
win early and still be brittle.

---

## Part IV — How the principles map to the harness rules

The strategic emphasis on *presence* is not a metaphor; it is the literal shape
of several victory rules the engine adjudicates.

- **5.1 Campaign Victory.** At a victory check, a side with no Lords on the map
  (*including none in Exile boxes*) and no Lord cylinder marked Exile arriving in
  the next Turn's Calendar box loses immediately — the other side wins regardless
  of Influence; if it applies to both, the game is a draw. This is exactly
  "presence wins when one faction ceases to function." The engine now applies it
  correctly: it awards the side that *retains* presence, and it counts Exile-box
  Lords as presence. (Both were wrong before the Phase 8 fix — hence the
  provenance caveat at the top.)
- **5.2 Threshold Victory.** A side that reaches a Turn's Influence threshold
  after a Campaign's Tides of War / Disembark steps wins immediately. This is the
  Influence-wins-when-both-functional path and underwrites the Yorkist
  "threshold win" tempo line.
- **5.3 Scenario End.** On the final Turn with both sides still present and no
  threshold met, the higher Influence wins (draw if equal). This is where
  Part I §3's "you usually need both" bites.
- **Test of Arms (Towton).** A scenario-specific override decided by York's
  Favour at Campaign end, as described above.
- **Calendar and Service.** A Lord's return box and remaining Service are real
  state the engine tracks; "a delayed Lord is as useless as a removed one in a
  short window" is a direct consequence.

Because 5.1, 5.2, and 5.3 are checked in that order, **presence is checked
before Influence** — which is the mechanical reason a side can be ahead on the
track and still lose outright.

---

## Part V — Rules of thumb

**General**

1. Do not fight merely because you can.
2. Do not let your last functioning Lord disappear.
3. Influence matters, but Lord continuity can matter more.
4. Exile can preserve a faction.
5. Calendar timing can decide the war.
6. A winning battle may be strategically losing if it leaves you absent.
7. Parley is often a quiet power move.
8. Supply determines whether plans are real.
9. The best move may be the one that makes the enemy's next turn awkward.
10. Think in terms of faction survival, not just army strength.

**Yorkist**

1. Use tempo to create a crisis.
2. Don't let aggression become self-destruction.
3. Preserve at least one viable Lord through the decision window.
4. Be wary of trading operational structure for one dramatic kill.
5. Exploit Lancastrian fragility before it stabilizes.

**Lancastrian**

1. Survive the Yorkist surge.
2. Keep the faction broad enough that one disaster isn't fatal.
3. Use legitimacy and Favour, but don't hide behind them.
4. Punish overextended Yorkist Lords.
5. Treat Exile and Calendar timing as part of the defensive structure.

---

## Part VI — Underexplored areas

Because the harness menu and heuristic play favored ordinary legal actions,
these runs probably underexplored the most sophisticated parts of the game:
advanced card timing, unusual capabilities, event-driven strategy, deliberately
refusing obvious campaigns, feints and inefficient-looking positioning, fine
control of Service expiration, fine-grained tactical battle decisions, and
highly scenario-specific openings. These are the most promising places to look
for sharper lines — and, given the recent enumeration fixes (marches into
contact, Group March, own-location Parley are now offered), the most promising
places for the next round of AI play to find both better strategy and further
engine findings.
