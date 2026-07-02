# Plantagenet safety playthrough — LLM-readable chronological log

This is a condensed, LLM-readable version of the most recent completed grand-scenario playthrough. It is derived from `plantagenet_safety_grand_selfplay_seed181.json`, the final safety run using the latest harness at the time it was played.

## Metadata

- Scenario: `wars_of_the_roses`
- Seed: `181`
- Complete: `True`
- Applied actions: `347`
- Trace step labels: `1–349` with transition bookkeeping numbers `102` and `214` skipped
- War transitions: `2`
- Anomalies recorded: `0`
- Source SHA-256: `fb9cae2a28ce2fada8cc80b4d58563dceb74699fb9f8a466785a487c3ed218e4`

## War outcomes

| War | Turn box ended | Winner | Rule | Actions |
|---|---:|---|---|---:|
| `war_i` | 3 | Lancastrian | 5.1 | 101 |
| `war_iil` | 3 | Lancastrian | 5.1 | 111 |
| `war_iiil` | 7 | Lancastrian | 5.1 | 135 |

## Action counts

| Action type | Count |
|---|---:|
| `end_activation` | 108 |
| `levy_transport` | 33 |
| `supply` | 28 |
| `levy_capability` | 23 |
| `build_plan` | 20 |
| `draw` | 20 |
| `end_muster` | 20 |
| `levy_troops` | 16 |
| `march` | 14 |
| `pay` | 14 |
| `levy_lord` | 11 |
| `begin_campaign` | 10 |
| `end_campaign` | 10 |
| `agitators` | 6 |
| `parley` | 5 |
| `play_event` | 4 |
| `forage` | 2 |
| `tax` | 2 |
| `sail` | 1 |

## Battle summaries

- Step 132 / `war_iil`: Battle at Pembroke: Jasper Tudor 1 attacked Pembroke; winner=Lancastrian; deaths=Pembroke; disbands=none; exiles=none.
- Step 138 / `war_iil`: Battle at Wells: Devon attacked Somerset 1; winner=none; deaths=Devon; disbands=Somerset 1; exiles=none.

## Chronological action log

Format: `Step | War | Turn | Phase | Side | Action -> Result`.

### Step 001
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y13, Y21; deployed Y13 to York, Y21 to York

### Step 002
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L21, L5; deployed L21 to Henry Vi, L5 to Henry Vi

### Step 003
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies capability Y10
- Result: March gained Y10 AGITATORS
- Top scored options: March levies capability Y10 [12.5009]; March levies capability Y2 [11.5026]; March levies capability Y1 [11.5019]

### Step 004
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies capability Y2
- Result: March gained Y2 CULVERINS AND FALCONETS
- Top scored options: March levies capability Y2 [11.5007]; March levies capability Y1 [11.5003]; March levies capability Y14 [9.5015]

### Step 005
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies troops
- Result: at Ely: +1 Longbow, 1 Militia; locale now depleted
- Top scored options: York levies troops [6.0029]; York levies cart transport [1.1008]; Yorkist ends muster [0.101]

### Step 006
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies troops
- Result: at Ely: +1 Longbow, 1 Militia; locale now exhausted
- Top scored options: York levies troops [5.8528]; York levies cart transport [1.1006]; Yorkist ends muster [0.1014]

### Step 007
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies cart transport
- Result: York added 2 cart
- Top scored options: York levies cart transport [1.1018]; Yorkist ends muster [0.1015]; York parleys Bury St Edmunds [-7.5984]

### Step 008
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 009
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies capability L1
- Result: Somerset 1 gained L1 CULVERINS AND FALCONETS
- Top scored options: Somerset 1 levies capability L1 [11.5024]; Somerset 1 levies capability L2 [11.5023]; Somerset 1 levies capability L4 [10.5029]

### Step 010
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies capability L4
- Result: Somerset 1 gained L4 HERALDS
- Top scored options: Somerset 1 levies capability L4 [10.5005]; Somerset 1 levies troops [9.0022]; Henry Vi levies troops [9.0001]

### Step 011
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies troops
- Result: at London: +1 Men At Arms, 1 Longbow, 1 Militia; locale now depleted
- Top scored options: Henry Vi levies troops [9.002]; Henry Vi levies cart transport [1.1008]; Lancastrian ends muster [0.1017]

### Step 012
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies troops
- Result: at London: +1 Men At Arms, 1 Longbow, 1 Militia; locale now exhausted
- Top scored options: Henry Vi levies troops [8.8516]; Henry Vi levies cart transport [1.1029]; Lancastrian ends muster [0.103]

### Step 013
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete

### Step 014
- Context: war=`war_i`, turn_box=`1`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Jan-Feb-Mar; cards_required=4

### Step 015
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Somerset 1, Henry Vi, Henry Vi
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 016
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: York, March, York, York
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 017
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1528]; York marches to Lincoln [-1.098]; York marches to St Albans [-1.0987]

### Step 018
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1507]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9979]; Henry Vi marches to Oxford [-7.4476]

### Step 019
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March supplies from Ludlow
- Result: March +1 provender from Ludlow via stronghold; ways=0
- Top scored options: March supplies from Ludlow [3.852]; March uses Agitators at Worcester [2.7026]; March uses Agitators at Shrewsbury [2.701]

### Step 020
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March uses Agitators at Hereford
- Result: Hereford becomes depleted
- Top scored options: March uses Agitators at Hereford [2.7009]; March uses Agitators at Worcester [2.7007]; March uses Agitators at Shrewsbury [2.7003]

### Step 021
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 022
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1528]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.9978]; Somerset 1 marches to Oxford [-7.4476]

### Step 023
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1511]; York marches to Lincoln [-1.0972]; York marches to St Albans [-1.0998]

### Step 024
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.153]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.998]; Henry Vi marches to Oxford [-7.4474]

### Step 025
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1528]; York marches to Lincoln [-1.097]; York marches to St Albans [-1.0991]

### Step 026
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.1524]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9991]; Henry Vi marches to Oxford [-7.4474]

### Step 027
- Context: war=`war_i`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 12, 'yorkist': 9}; advance_to_turn=2; next_phase=levy; detail: yorkist +1 Lord in wales | lancastrian +2 Favour at london | yorkist +1 most Favour fortresss ({'lancastrian': 0, 'yorkist': 1}) | lancastrian +10 Lords' Influence | ...

### Step 028
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y11, Y22; held Y11

### Step 029
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L17, L13; held L13

### Step 030
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=['loc:ely', 'loc:ludlow']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=2; vassal_disbanded=[]

### Step 031
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=['loc:london']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=2; vassal_disbanded=[]

### Step 032
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies troops
- Result: at Ludlow: +1 Men At Arms, 1 Longbow; locale now exhausted
- Top scored options: March levies troops [7.6004]; March levies cart transport [1.9015]; York attempts to levy lord Salisbury [1.501]

### Step 033
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies cart transport
- Result: March added 2 cart
- Top scored options: March levies cart transport [1.901]; York attempts to levy lord Salisbury [1.502]; March attempts to levy lord Salisbury [1.5001]

### Step 034
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York attempts to levy lord Salisbury
- Result: target=Salisbury; success=False; roll=6 vs rating 5; spent=1
- Top scored options: York attempts to levy lord Salisbury [1.501]; York levies cart transport [0.3021]; Yorkist ends muster [0.101]

### Step 035
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York attempts to levy lord Salisbury
- Result: target=Salisbury; success=False; roll=6 vs rating 5; spent=1
- Top scored options: York attempts to levy lord Salisbury [1.5013]; York levies cart transport [0.3021]; Yorkist ends muster [0.1019]

### Step 036
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York attempts to levy lord Salisbury
- Result: target=Salisbury; success=False; roll=6 vs rating 5; spent=1
- Top scored options: York attempts to levy lord Salisbury [1.5025]; York levies cart transport [0.3001]; Yorkist ends muster [0.1023]

### Step 037
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 038
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi attempts to levy lord Northumberland Lancastrian
- Result: target=Northumberland Lancastrian; success=True; roll=1 vs rating 5; spent=1
- Top scored options: Henry Vi attempts to levy lord Northumberland Lancastrian [41.3026]; Somerset 1 attempts to levy lord Northumberland Lancastrian [41.3001]; Henry Vi levies cart transport [1.103]

### Step 039
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies cart transport
- Result: Henry Vi added 2 cart
- Top scored options: Henry Vi levies cart transport [1.1019]; Somerset 1 levies cart transport [1.1006]; Lancastrian ends muster [0.1011]

### Step 040
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies cart transport
- Result: Somerset 1 added 2 cart
- Top scored options: Somerset 1 levies cart transport [1.1028]; Lancastrian ends muster [0.1013]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.799]

### Step 041
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies cart transport
- Result: Somerset 1 added 2 cart
- Top scored options: Somerset 1 levies cart transport [0.3011]; Lancastrian ends muster [0.101]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7975]

### Step 042
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete
- Top scored options: Lancastrian ends muster [0.1002]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7995]; Henry Vi parleys Oxford [-7.5973]

### Step 043
- Context: war=`war_i`, turn_box=`2`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Apr-May; cards_required=6

### Step 044
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Somerset 1, Northumberland Lancastrian, Henry Vi, Henry Vi, Somerset 1
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 045
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: York, March, York, York, March, March
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 046
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1525]; York marches to St Albans [-1.0991]; York marches to Lincoln [-1.0997]

### Step 047
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.151]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9994]; Henry Vi marches to Guildford [-7.4471]

### Step 048
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March uses Agitators at Hereford
- Result: Hereford becomes exhausted
- Top scored options: March uses Agitators at Hereford [2.7024]; March uses Agitators at Worcester [2.701]; March uses Agitators at Shrewsbury [2.7008]

### Step 049
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March uses Agitators at Worcester
- Result: Worcester becomes depleted
- Top scored options: March uses Agitators at Worcester [2.7]; March uses Agitators at Shrewsbury [2.7]; Yorkist ends activation [0.1517]

### Step 050
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 051
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1529]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7995]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.9972]

### Step 052
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1508]; York marches to St Albans [-1.0988]; York marches to Lincoln [-1.0988]

### Step 053
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian supplies from Carlisle
- Result: Northumberland Lancastrian +2 provender from Carlisle via stronghold; ways=0
- Top scored options: Northumberland Lancastrian supplies from Carlisle [3.5524]; Northumberland Lancastrian taxes Carlisle [1.4518]; Northumberland Lancastrian forages [0.7505]

### Step 054
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian taxes Carlisle
- Result: Carlisle: +2 coin; success=True; roll=None; spent=0
- Top scored options: Northumberland Lancastrian taxes Carlisle [1.3017]; Northumberland Lancastrian supplies from Carlisle [0.4022]; Lancastrian ends activation [0.1509]

### Step 055
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1503]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.799]

### Step 056
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1516]; York marches to Lincoln [-1.0974]; York marches to St Albans [-1.0983]

### Step 057
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1508]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9976]; Henry Vi marches to St Albans [-7.4484]

### Step 058
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March uses Agitators at Shrewsbury
- Result: Shrewsbury becomes depleted
- Top scored options: March uses Agitators at Shrewsbury [2.701]; March uses Agitators at Worcester [2.7006]; Yorkist ends activation [0.1507]

### Step 059
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March uses Agitators at Worcester
- Result: Worcester becomes exhausted
- Top scored options: March uses Agitators at Worcester [2.7019]; March uses Agitators at Shrewsbury [2.7009]; Yorkist ends activation [0.1529]

### Step 060
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 061
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1522]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9984]; Henry Vi marches to Guildford [-7.4471]

### Step 062
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March uses Agitators at Shrewsbury
- Result: Shrewsbury becomes exhausted
- Top scored options: March uses Agitators at Shrewsbury [2.7016]; Yorkist ends activation [0.1517]; March marches to Shrewsbury [-1.7489]

### Step 063
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1504]; March marches to Shrewsbury [-1.7472]; March marches to Gloucester [-1.7488]

### Step 064
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.1523]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7978]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.9986]

### Step 065
- Context: war=`war_i`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 5, 'yorkist': 2}; advance_to_turn=3; next_phase=levy; detail: lancastrian +1 Lord in north | yorkist +1 Lord in wales | lancastrian +2 Favour at london | lancastrian +2 most Favour citys ({'lancastrian': 2, 'yorkist': 1}) | ...

### Step 066
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y14, Y18

### Step 067
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L11, L3; held L11, L3

### Step 068
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=[]; unpaid_disbanded=['york', 'march']; voluntary_disbanded=[]; influence_paid=0; vassal_disbanded=[]

### Step 069
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=['loc:carlisle']; unpaid_disbanded=['henry_vi']; voluntary_disbanded=[]; influence_paid=2; vassal_disbanded=[]

### Step 070
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 071
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Northumberland Lancastrian levies capability L2
- Result: Northumberland Lancastrian gained L2 CULVERINS AND FALCONETS
- Top scored options: Northumberland Lancastrian levies capability L2 [11.5011]; Northumberland Lancastrian levies capability L8 [8.9028]; Northumberland Lancastrian levies capability L21 [3.5028]

### Step 072
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Northumberland Lancastrian levies capability L8
- Result: Northumberland Lancastrian gained L8 HAY WAINS
- Top scored options: Northumberland Lancastrian levies capability L8 [8.9005]; Northumberland Lancastrian levies capability L12 [3.503]; Northumberland Lancastrian levies capability L6 [3.5026]

### Step 073
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 attempts to levy lord Exeter 1
- Result: target=Exeter 1; success=False; roll=6 vs rating 5; spent=1
- Top scored options: Somerset 1 attempts to levy lord Exeter 1 [1.5023]; Somerset 1 levies cart transport [0.3002]; Lancastrian ends muster [0.1026]

### Step 074
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 attempts to levy lord Exeter 1
- Result: target=Exeter 1; success=True; roll=2 vs rating 5; spent=1
- Top scored options: Somerset 1 attempts to levy lord Exeter 1 [40.902]; Somerset 1 levies cart transport [0.3005]; Lancastrian ends muster [0.1022]

### Step 075
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete
- Top scored options: Lancastrian ends muster [0.1027]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7977]

### Step 076
- Context: war=`war_i`, turn_box=`3`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Jun-Jul; cards_required=7

### Step 077
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Somerset 1, Northumberland Lancastrian, Exeter 1, Somerset 1, Somerset 1, Northumberland Lancastrian, Northumberland Lancastrian
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 078
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: —, —, —, —, —, —, —
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 079
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 080
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1521]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7989]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.9971]

### Step 081
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 082
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian marches to Appleby
- Result: Northumberland Lancastrian to Appleby by road; whole_card=False
- Top scored options: Northumberland Lancastrian marches to Appleby [0.4528]; Northumberland Lancastrian marches to Hexham [0.4528]; Lancastrian ends activation [0.1502]

### Step 083
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian marches to Newcastle
- Result: Northumberland Lancastrian to Newcastle by road; whole_card=False
- Top scored options: Northumberland Lancastrian marches to Newcastle [4.0527]; Northumberland Lancastrian parleys Appleby [2.152]; Northumberland Lancastrian marches to Lancaster [0.0009]

### Step 084
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Northumberland Lancastrian', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist
- Top scored options: Lancastrian ends activation [-1.3472]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7985]

### Step 085
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 086
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Exeter 1 supplies from Exeter
- Result: Exeter 1 +2 provender from Exeter via stronghold; ways=0
- Top scored options: Exeter 1 supplies from Exeter [5.3508]; Exeter 1 supplies from Wells [3.8522]; Exeter 1 marches to Wells [2.4518]

### Step 087
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Exeter 1 supplies from Wells
- Result: Exeter 1 +1 provender from Wells via stronghold; ways=1
- Top scored options: Exeter 1 supplies from Wells [2.0528]; Exeter 1 supplies from Exeter [1.9024]; Exeter 1 taxes Exeter [1.302]

### Step 088
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1518]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7974]

### Step 089
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 090
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1511]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7973]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.998]

### Step 091
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 092
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1501]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7975]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.9972]

### Step 093
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 094
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian marches to York
- Result: Northumberland Lancastrian to York by highway; whole_card=False
- Top scored options: Northumberland Lancastrian marches to York [8.6503]; Northumberland Lancastrian parleys Newcastle [5.2108]; Northumberland Lancastrian forages [1.1004]

### Step 095
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian parleys York
- Result: York: york: Favour.NEUTRAL -> lancastrian; auto=True
- Top scored options: Northumberland Lancastrian parleys York [9.8514]; Northumberland Lancastrian forages [1.1001]; Lancastrian ends activation [-1.3497]

### Step 096
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Northumberland Lancastrian', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist
- Top scored options: Lancastrian ends activation [-1.3484]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7998]

### Step 097
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 098
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian supplies from York
- Result: Northumberland Lancastrian +2 provender from York via stronghold; ways=0
- Top scored options: Northumberland Lancastrian supplies from York [3.5525]; Northumberland Lancastrian forages [0.7523]; Lancastrian ends activation [0.1529]

### Step 099
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Northumberland Lancastrian supplies from York
- Result: Northumberland Lancastrian +2 provender from York via stronghold; ways=0
- Top scored options: Northumberland Lancastrian supplies from York [0.4011]; Lancastrian ends activation [0.1524]; Northumberland Lancastrian forages [-0.8991]

### Step 100
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.1507]; {"card": "L13", "side": "lancastrian", "type": "play_held_event"} [-1.7993]

### Step 101
- Context: war=`war_i`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 4, 'yorkist': 1}; advance_to_turn=3; next_phase=over; detail: lancastrian +2 Favour at london | lancastrian +2 most Favour citys ({'lancastrian': 4, 'yorkist': 1}) | yorkist +1 most Favour fortresss ({'lancastrian': 0, 'yorkist': 1}); VICTORY: Lancastrian by rule 5.1

### Step 103
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y8, Y11; deployed Y8 to Warwick Yorkist, Y11 to Warwick Yorkist

### Step 104
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L21, L11; deployed L21 to Henry Vi, L11 to Henry Vi

### Step 105
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Warwick Yorkist attempts to levy lord Devon
- Result: target=Devon; success=True; roll=4 vs rating 5; spent=1
- Top scored options: Warwick Yorkist attempts to levy lord Devon [43.7507]; Salisbury levies capability Y10 [12.5024]; Pembroke levies capability Y10 [12.5011]

### Step 106
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Pembroke levies capability Y10
- Result: Pembroke gained Y10 AGITATORS
- Top scored options: Pembroke levies capability Y10 [12.5027]; Salisbury levies capability Y10 [12.5019]; Salisbury levies capability Y2 [11.5025]

### Step 107
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Pembroke levies capability Y1
- Result: Pembroke gained Y1 CULVERINS AND FALCONETS
- Top scored options: Pembroke levies capability Y1 [11.5029]; Pembroke levies capability Y2 [11.5019]; Salisbury levies capability Y1 [11.5016]

### Step 108
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Salisbury levies capability Y2
- Result: Salisbury gained Y2 CULVERINS AND FALCONETS
- Top scored options: Salisbury levies capability Y2 [11.5006]; Warwick Yorkist levies troops [10.7512]; Salisbury levies capability Y17 [8.5012]

### Step 109
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Warwick Yorkist levies troops
- Result: at Calais: +2 Men At Arms, 1 Longbow; locale now depleted
- Top scored options: Warwick Yorkist levies troops [10.7516]; Salisbury levies capability Y17 [8.5025]; Salisbury levies troops [6.0029]

### Step 110
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Warwick Yorkist levies troops
- Result: at Calais: +2 Men At Arms, 1 Longbow; locale now exhausted
- Top scored options: Warwick Yorkist levies troops [10.6021]; Salisbury levies capability Y17 [8.5029]; Salisbury levies troops [6.0007]

### Step 111
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Salisbury levies capability Y17
- Result: Salisbury gained Y17 ALICE MONTAGU
- Top scored options: Salisbury levies capability Y17 [8.503]; Salisbury levies troops [6.001]; Salisbury levies capability Y12 [3.5028]

### Step 112
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Salisbury levies troops
- Result: at York: +1 Longbow, 1 Militia; locale now depleted
- Top scored options: Salisbury levies troops [6.0027]; Salisbury levies cart transport [1.9029]; Yorkist ends muster [0.1024]

### Step 113
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 114
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 1 levies capability L1
- Result: Jasper Tudor 1 gained L1 CULVERINS AND FALCONETS
- Top scored options: Jasper Tudor 1 levies capability L1 [11.5027]; Jasper Tudor 1 levies capability L2 [11.5019]; Somerset 1 levies capability L2 [11.5016]

### Step 115
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies capability L2
- Result: Somerset 1 gained L2 CULVERINS AND FALCONETS
- Top scored options: Somerset 1 levies capability L2 [11.5018]; Jasper Tudor 1 levies troops [10.553]; Somerset 1 levies capability L4 [10.5003]

### Step 116
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 1 levies troops
- Result: at Harlech: +1 Men At Arms, 2 Longbow; locale now depleted
- Top scored options: Jasper Tudor 1 levies troops [10.5521]; Jasper Tudor 1 levies capability L4 [10.5026]; Somerset 1 levies capability L4 [10.5022]

### Step 117
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies capability L4
- Result: Somerset 1 gained L4 HERALDS
- Top scored options: Somerset 1 levies capability L4 [10.5007]; Henry Vi levies troops [9.0027]; Somerset 1 levies capability L8 [8.901]

### Step 118
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies troops
- Result: at London: +1 Men At Arms, 1 Longbow, 1 Militia; locale now depleted
- Top scored options: Henry Vi levies troops [9.0025]; Henry Vi levies cart transport [1.1023]; Lancastrian ends muster [0.1023]

### Step 119
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies troops
- Result: at London: +1 Men At Arms, 1 Longbow, 1 Militia; locale now exhausted
- Top scored options: Henry Vi levies troops [8.8519]; Henry Vi levies cart transport [1.1018]; Lancastrian ends muster [0.1003]

### Step 120
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete

### Step 121
- Context: war=`war_iil`, turn_box=`1`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Jan-Feb-Mar; cards_required=4

### Step 122
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Jasper Tudor 1, Somerset 1, Henry Vi
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 123
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: Warwick Yorkist, Salisbury, Pembroke, Devon
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 124
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Warwick Yorkist supplies from Exeter
- Result: Warwick Yorkist +2 provender from Exeter via ship; ways=None
- Top scored options: Warwick Yorkist supplies from Exeter [3.9028]; Warwick Yorkist supplies from Truro [3.9021]; Warwick Yorkist supplies from Hastings [3.9018]

### Step 125
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Warwick Yorkist supplies from Southampton
- Result: Warwick Yorkist +2 provender from Southampton via ship; ways=None
- Top scored options: Warwick Yorkist supplies from Southampton [0.903]; Warwick Yorkist supplies from Truro [0.9029]; Warwick Yorkist supplies from Exeter [0.9024]

### Step 126
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 127
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Henry Vi supplies from Oxford
- Result: Henry Vi +2 provender from Oxford via stronghold; ways=1
- Top scored options: Henry Vi supplies from Oxford [3.5524]; Lancastrian ends activation [0.1506]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9971]

### Step 128
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Henry Vi supplies from Oxford
- Result: Henry Vi +2 provender from Oxford via stronghold; ways=1
- Top scored options: Henry Vi supplies from Oxford [0.4006]; Lancastrian ends activation [0.1512]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9992]

### Step 129
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist

### Step 130
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Salisbury supplies from York
- Result: Salisbury +2 provender from York via stronghold; ways=0
- Top scored options: Salisbury supplies from York [5.2029]; Salisbury taxes York [1.3029]; Salisbury forages [0.602]

### Step 131
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1508]; {"by_lord": "salisbury", "side": "yorkist", "type": "pass"} [-2.9999]; Salisbury marches to Newcastle [-4.8484]

### Step 132
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 1 marches to Pembroke
- Result: Jasper Tudor 1 to Pembroke by path; whole_card=True; Battle at Pembroke: Jasper Tudor 1 attacked Pembroke; winner=Lancastrian; deaths=Pembroke; disbands=none; exiles=none.
- Top scored options: Jasper Tudor 1 marches to Pembroke [49.3653]; Jasper Tudor 1 supplies from Harlech [1.9007]; Jasper Tudor 1 taxes Harlech [0.601]

### Step 133
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Jasper Tudor 1', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist

### Step 134
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 135
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Somerset 1 supplies from Wells
- Result: Somerset 1 +2 provender from Wells via stronghold; ways=0
- Top scored options: Somerset 1 supplies from Wells [3.5509]; Somerset 1 taxes Wells [1.452]; Lancastrian ends activation [0.1521]

### Step 136
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Somerset 1 taxes Wells
- Result: Wells: +2 coin; success=True; roll=None; spent=0
- Top scored options: Somerset 1 taxes Wells [1.3003]; Somerset 1 supplies from Wells [0.4014]; Lancastrian ends activation [0.1503]

### Step 137
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist

### Step 138
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Devon marches to Wells
- Result: Devon to Wells by highway; whole_card=False; Battle at Wells: Devon attacked Somerset 1; winner=none; deaths=Devon; disbands=Somerset 1; exiles=none.
- Top scored options: Devon marches to Wells [18.5878]; Devon supplies from Exeter [5.352]; Devon taxes Exeter [1.4501]

### Step 139
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: Yorkist feed: fed {'Lord': 'Devon', 'Fed': 0, 'Needed': 0}; disbanded none; next_side=Lancastrian

### Step 140
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.1515]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9974]; Henry Vi parleys Guildford [-6.3988]

### Step 141
- Context: war=`war_iil`, turn_box=`1`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 11, 'yorkist': 11}; advance_to_turn=2; next_phase=levy; detail: lancastrian +1 Lord in wales | lancastrian +2 Favour at london | yorkist +2 Favour at calais | lancastrian +1 Favour at harlech | ...

### Step 142
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y34, Y4

### Step 143
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist plays event Y34
- Result: card=Y34; active=True; next=king_draw

### Step 144
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L29, L19

### Step 145
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian plays event L29
- Result: card=L29; removed=[]
- Top scored options: Lancastrian plays event L29 [0.0023]; Lancastrian plays event L19 [0.002]

### Step 146
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian plays event L19
- Result: card=L19; next=pay

### Step 147
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=['loc:calais', 'loc:york']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=2; vassal_disbanded=[]

### Step 148
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=['loc:london', 'loc:pembroke']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=2; vassal_disbanded=[]

### Step 149
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Salisbury levies cart transport
- Result: Salisbury added 2 cart
- Top scored options: Salisbury levies cart transport [1.9007]; Warwick Yorkist levies cart transport [1.9003]; Yorkist ends muster [0.1007]

### Step 150
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Warwick Yorkist levies cart transport
- Result: Warwick Yorkist added 2 cart
- Top scored options: Warwick Yorkist levies cart transport [1.9008]; Salisbury levies cart transport [0.3016]; Yorkist ends muster [0.1021]

### Step 151
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Warwick Yorkist levies cart transport
- Result: Warwick Yorkist added 2 cart
- Top scored options: Warwick Yorkist levies cart transport [1.1029]; Salisbury levies cart transport [0.3005]; Yorkist ends muster [0.1002]

### Step 152
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Warwick Yorkist levies cart transport
- Result: Warwick Yorkist added 2 cart
- Top scored options: Warwick Yorkist levies cart transport [0.3008]; Salisbury levies cart transport [0.3004]; Yorkist ends muster [0.1021]

### Step 153
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Salisbury levies cart transport
- Result: Salisbury added 2 cart
- Top scored options: Salisbury levies cart transport [0.3028]; Yorkist ends muster [0.1019]; Salisbury parleys Newcastle [-3.7898]

### Step 154
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Salisbury levies cart transport
- Result: Salisbury added 2 cart
- Top scored options: Salisbury levies cart transport [0.3027]; Yorkist ends muster [0.1014]; Salisbury parleys Newcastle [-3.7893]

### Step 155
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 156
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi attempts to levy lord Exeter 1
- Result: target=Exeter 1; success=True; roll=3 vs rating 5; spent=1
- Top scored options: Henry Vi attempts to levy lord Exeter 1 [45.0024]; Henry Vi attempts to levy lord Somerset 1 [40.9019]; Henry Vi attempts to levy lord Oxford [40.3019]

### Step 157
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi attempts to levy lord Somerset 1
- Result: target=Somerset 1; success=True; roll=3 vs rating 5; spent=1
- Top scored options: Henry Vi attempts to levy lord Somerset 1 [40.901]; Henry Vi attempts to levy lord Oxford [40.3017]; Henry Vi levies cart transport [1.1009]

### Step 158
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete
- Top scored options: Lancastrian ends muster [0.1015]; Jasper Tudor 1 parleys Pembroke [-4.2372]

### Step 159
- Context: war=`war_iil`, turn_box=`2`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Apr-May; cards_required=6

### Step 160
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Somerset 1, Exeter 1, Jasper Tudor 1, Henry Vi, Henry Vi
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 161
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: Warwick Yorkist, Salisbury, Warwick Yorkist, Warwick Yorkist, Salisbury, Salisbury
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 162
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1515]; Warwick Yorkist supplies from Dover [-0.498]; Warwick Yorkist supplies from Plymouth [-0.498]

### Step 163
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1524]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9985]; Henry Vi marches to Oxford [-10.4485]

### Step 164
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1507]; Salisbury marches to Newcastle [-1.8484]; {"by_lord": "salisbury", "side": "yorkist", "type": "pass"} [-2.9973]

### Step 165
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Somerset 1 supplies from Exeter
- Result: Somerset 1 +2 provender from Exeter via stronghold; ways=1
- Top scored options: Somerset 1 supplies from Exeter [3.5513]; Somerset 1 marches to Exeter [1.5527]; Lancastrian ends activation [0.1516]

### Step 166
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Somerset 1 supplies from Exeter
- Result: Somerset 1 +2 provender from Exeter via stronghold; ways=1
- Top scored options: Somerset 1 supplies from Exeter [0.401]; Lancastrian ends activation [0.1503]; Somerset 1 marches to Exeter [-1.4471]

### Step 167
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist

### Step 168
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1509]; Warwick Yorkist supplies from Dorchester [-0.4974]; Warwick Yorkist supplies from Southampton [-0.4975]

### Step 169
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Exeter 1 marches to Wells
- Result: Exeter 1 to Wells by highway; whole_card=False
- Top scored options: Exeter 1 marches to Wells [2.4505]; Lancastrian ends activation [0.1513]; Exeter 1 marches to Salisbury [-1.0975]

### Step 170
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Exeter 1 marches to Exeter
- Result: Exeter 1 to Exeter by highway; whole_card=False
- Top scored options: Exeter 1 marches to Exeter [1.5501]; Exeter 1 marches to Winchester [-1.0979]; Lancastrian ends activation [-1.3475]

### Step 171
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Exeter 1', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist

### Step 172
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1506]; Warwick Yorkist supplies from Exeter [-0.4973]; Warwick Yorkist supplies from Dover [-0.4974]

### Step 173
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 1 marches to Harlech
- Result: Jasper Tudor 1 to Harlech by path; whole_card=True
- Top scored options: Jasper Tudor 1 marches to Harlech [4.0527]; Jasper Tudor 1 forages [1.451]; Jasper Tudor 1 parleys Pembroke [0.2618]

### Step 174
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Jasper Tudor 1', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist

### Step 175
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Salisbury supplies from Chester
- Result: Salisbury +2 provender from Chester via stronghold; ways=1
- Top scored options: Salisbury supplies from Chester [2.0503]; Yorkist ends activation [0.1524]; Salisbury marches to Newcastle [-1.8492]

### Step 176
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1516]; Salisbury supplies from Chester [-0.997]; Salisbury marches to Newcastle [-1.8485]

### Step 177
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1527]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9995]; Henry Vi marches to Guildford [-10.4476]

### Step 178
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1501]; Salisbury supplies from Chester [-0.9999]; Salisbury marches to Newcastle [-1.8474]

### Step 179
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.15]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9975]; Henry Vi marches to Oxford [-10.4471]

### Step 180
- Context: war=`war_iil`, turn_box=`2`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 5, 'yorkist': 3}; advance_to_turn=3; next_phase=levy; detail: lancastrian +1 Lord in wales | lancastrian +2 Favour at london | yorkist +2 Favour at calais | lancastrian +2 most Favour citys ({'lancastrian': 4, 'yorkist': 3}) | ...

### Step 181
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y6, Y5; held Y5

### Step 182
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L7, L6; held L7

### Step 183
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=[]; unpaid_disbanded=['warwick_yorkist', 'salisbury']; voluntary_disbanded=[]; influence_paid=0; vassal_disbanded=[]

### Step 184
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=['loc:wells', 'loc:exeter', 'loc:harlech']; unpaid_disbanded=['henry_vi']; voluntary_disbanded=[]; influence_paid=3; vassal_disbanded=[]

### Step 185
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 186
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 attempts to levy lord Oxford
- Result: target=Oxford; success=True; roll=2 vs rating 5; spent=1
- Top scored options: Somerset 1 attempts to levy lord Oxford [40.301]; Exeter 1 attempts to levy lord Oxford [40.3007]; Exeter 1 levies capability L2 [11.5028]

### Step 187
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Somerset 1 levies capability L2
- Result: Somerset 1 gained L2 CULVERINS AND FALCONETS
- Top scored options: Somerset 1 levies capability L2 [11.5022]; Exeter 1 levies capability L2 [11.5019]; Somerset 1 levies capability L1 [11.5013]

### Step 188
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Exeter 1 levies capability L1
- Result: Exeter 1 gained L1 CULVERINS AND FALCONETS
- Top scored options: Exeter 1 levies capability L1 [11.5011]; Exeter 1 levies capability L4 [10.5022]; Exeter 1 levies capability L8 [8.9001]

### Step 189
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete
- Top scored options: Lancastrian ends muster [0.1027]; Jasper Tudor 1 parleys Harlech [-3.0991]

### Step 190
- Context: war=`war_iil`, turn_box=`3`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Jun-Jul; cards_required=7

### Step 191
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Somerset 1, Oxford, Exeter 1, Jasper Tudor 1, Somerset 1, Somerset 1, Oxford
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 192
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: —, —, —, —, —, —, —
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 193
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 194
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1527]; Somerset 1 marches to Exeter [-1.4499]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.9977]

### Step 195
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 196
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Oxford marches to London
- Result: Oxford to London by highway; whole_card=False
- Top scored options: Oxford marches to London [14.452]; Lancastrian ends activation [0.1515]; Oxford marches to St Albans [0.0008]

### Step 197
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Oxford', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist
- Top scored options: Lancastrian ends activation [-1.3476]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9975]; Oxford marches to Oxford [-7.4479]

### Step 198
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 199
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Exeter 1 marches to Wells
- Result: Exeter 1 to Wells by highway; whole_card=False
- Top scored options: Exeter 1 marches to Wells [2.451]; Lancastrian ends activation [0.1523]; Exeter 1 marches to Salisbury [-1.0992]

### Step 200
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Exeter 1 marches to Exeter
- Result: Exeter 1 to Exeter by highway; whole_card=False
- Top scored options: Exeter 1 marches to Exeter [1.5515]; Exeter 1 marches to Winchester [-1.0981]; Exeter 1 marches to Bristol [-1.5477]

### Step 201
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed none; disbanded Exeter 1; next_side=Yorkist

### Step 202
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 203
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 1 parleys Harlech
- Result: Harlech: harlech: yorkist -> neutral; auto=True
- Top scored options: Jasper Tudor 1 parleys Harlech [5.2178]; Jasper Tudor 1 marches to Pembroke [0.4518]; Lancastrian ends activation [0.1509]

### Step 204
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 1 parleys Harlech
- Result: Harlech: harlech: neutral -> lancastrian; auto=True
- Top scored options: Jasper Tudor 1 parleys Harlech [5.2159]; Jasper Tudor 1 marches to Pembroke [0.4501]; Lancastrian ends activation [0.152]

### Step 205
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 1 marches to Pembroke
- Result: Jasper Tudor 1 to Pembroke by path; whole_card=True
- Top scored options: Jasper Tudor 1 marches to Pembroke [0.451]; Lancastrian ends activation [0.1511]; Jasper Tudor 1 marches to Chester [-2.2491]

### Step 206
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Jasper Tudor 1', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist

### Step 207
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 208
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1518]; Somerset 1 marches to Exeter [-1.4491]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.999]

### Step 209
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 210
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.151]; Somerset 1 marches to Exeter [-1.4487]; {"by_lord": "somerset_1", "side": "lancastrian", "type": "pass"} [-2.997]

### Step 211
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 212
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.153]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9975]; Oxford marches to Rochester [-7.4487]

### Step 213
- Context: war=`war_iil`, turn_box=`3`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 3, 'yorkist': 3}; advance_to_turn=3; next_phase=over; detail: lancastrian +1 Lord in wales | lancastrian +2 Favour at london | yorkist +2 Favour at calais | yorkist +1 most Favour fortresss ({'lancastrian': 0, 'yorkist': 2}); VICTORY: Lancastrian by rule 5.1

### Step 215
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y9, Y10; deployed Y9 to York, Y10 to York

### Step 216
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L4, L11; deployed L4 to Henry Vi, L11 to Henry Vi

### Step 217
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Norfolk levies capability Y2
- Result: Norfolk gained Y2 CULVERINS AND FALCONETS
- Top scored options: Norfolk levies capability Y2 [11.5027]; March levies capability Y2 [11.5013]; March levies capability Y1 [11.5013]

### Step 218
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies capability Y1
- Result: March gained Y1 CULVERINS AND FALCONETS
- Top scored options: March levies capability Y1 [11.5009]; March levies capability Y14 [9.5021]; Norfolk levies capability Y11 [9.5016]

### Step 219
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies capability Y14
- Result: March gained Y14 BURGUNDIANS
- Top scored options: March levies capability Y14 [9.502]; Norfolk levies capability Y11 [9.5006]; March levies capability Y11 [9.5005]

### Step 220
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Norfolk levies capability Y11
- Result: Norfolk gained Y11 YORKISTS NEVER WAIT
- Top scored options: Norfolk levies capability Y11 [9.5018]; Norfolk levies capability Y8 [8.5011]; Norfolk levies capability Y6 [3.5026]

### Step 221
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies ship transport
- Result: York added 1 ship
- Top scored options: York levies ship transport [1.2022]; Norfolk levies ship transport [1.2]; Norfolk levies cart transport [1.1025]

### Step 222
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Norfolk levies ship transport
- Result: Norfolk added 1 ship
- Top scored options: Norfolk levies ship transport [1.2019]; York levies ship transport [1.2015]; Norfolk levies cart transport [1.102]

### Step 223
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies ship transport
- Result: York added 1 ship
- Top scored options: York levies ship transport [1.2002]; York levies cart transport [1.1002]; Yorkist ends muster [0.1003]

### Step 224
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies cart transport
- Result: York added 2 cart
- Top scored options: York levies cart transport [1.1006]; Yorkist ends muster [0.103]; York parleys Calais [-1.7735]

### Step 225
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 226
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies capability L1
- Result: Oxford gained L1 CULVERINS AND FALCONETS
- Top scored options: Oxford levies capability L1 [11.5028]; Jasper Tudor 2 levies capability L1 [11.5028]; Oxford levies capability L2 [11.5019]

### Step 227
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 2 levies capability L2
- Result: Jasper Tudor 2 gained L2 CULVERINS AND FALCONETS
- Top scored options: Jasper Tudor 2 levies capability L2 [11.5026]; Henry Vi levies troops [9.0023]; Oxford levies capability L8 [8.9025]

### Step 228
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies troops
- Result: at London: +1 Men At Arms, 1 Longbow, 1 Militia; locale now depleted
- Top scored options: Henry Vi levies troops [9.0025]; Jasper Tudor 2 levies capability L8 [8.9022]; Oxford levies capability L8 [8.9]

### Step 229
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies capability L8
- Result: Oxford gained L8 HAY WAINS
- Top scored options: Oxford levies capability L8 [8.9004]; Jasper Tudor 2 levies capability L8 [8.9002]; Henry Vi levies troops [8.8518]

### Step 230
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies troops
- Result: at London: +1 Men At Arms, 1 Longbow, 1 Militia; locale now exhausted
- Top scored options: Henry Vi levies troops [8.8525]; Jasper Tudor 2 levies troops [7.7524]; Jasper Tudor 2 levies capability L10 [3.503]

### Step 231
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 2 levies troops
- Result: at Pembroke: +1 Men At Arms, 1 Longbow; locale now depleted
- Top scored options: Jasper Tudor 2 levies troops [7.7508]; Jasper Tudor 2 levies capability L5 [3.5029]; Jasper Tudor 2 levies capability L36 [3.5029]

### Step 232
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 2 levies troops
- Result: at Pembroke: +1 Men At Arms, 1 Longbow; locale now exhausted
- Top scored options: Jasper Tudor 2 levies troops [7.6007]; Jasper Tudor 2 levies capability L21 [3.5029]; Jasper Tudor 2 levies capability L5 [3.5029]

### Step 233
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete

### Step 234
- Context: war=`war_iiil`, turn_box=`4`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Aug-Sep; cards_required=6

### Step 235
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Jasper Tudor 2, Oxford, Henry Vi, Henry Vi, Jasper Tudor 2
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 236
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: Norfolk, York, March, Norfolk, Norfolk, York
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 237
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Norfolk supplies from Calais
- Result: Norfolk +1 provender from Calais via ship; ways=None
- Top scored options: Norfolk supplies from Calais [2.4023]; Norfolk supplies from Dover [2.4013]; Norfolk supplies from Plymouth [2.4012]

### Step 238
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Norfolk supplies from Truro
- Result: Norfolk +1 provender from Truro via ship; ways=None
- Top scored options: Norfolk supplies from Truro [2.4015]; Norfolk supplies from Dover [2.4015]; Norfolk supplies from Calais [2.4013]

### Step 239
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Norfolk supplies from Southampton
- Result: Norfolk +1 provender from Southampton via ship; ways=None
- Top scored options: Norfolk supplies from Southampton [0.9026]; Norfolk supplies from Truro [0.9022]; Norfolk supplies from Hastings [0.9022]

### Step 240
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 241
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Henry Vi supplies from Oxford
- Result: Henry Vi +2 provender from Oxford via stronghold; ways=1
- Top scored options: Henry Vi supplies from Oxford [3.5511]; Lancastrian ends activation [0.1515]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9976]

### Step 242
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Henry Vi supplies from Oxford
- Result: Henry Vi +2 provender from Oxford via stronghold; ways=1
- Top scored options: Henry Vi supplies from Oxford [0.4019]; Lancastrian ends activation [0.1503]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9998]

### Step 243
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist

### Step 244
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: York sails to Calais
- Result: York to Calais; sea english_channel->english_channel; group=none
- Top scored options: York sails to Calais [10.0021]; York sails to Exeter [7.0027]; York supplies from Hastings [3.9029]

### Step 245
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: Yorkist feed: fed {'Lord': 'York', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Lancastrian

### Step 246
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 2 marches to Harlech
- Result: Jasper Tudor 2 to Harlech by path; whole_card=True
- Top scored options: Jasper Tudor 2 marches to Harlech [4.0507]; Lancastrian ends activation [0.1522]; Jasper Tudor 2 marches to Cardiff [-1.7988]

### Step 247
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Jasper Tudor 2', 'Fed': 2, 'Needed': 2}; disbanded none; next_side=Yorkist

### Step 248
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March forages
- Result: at Burgundy: success=True; +1 provender; roll=None
- Top scored options: March forages [1.1016]; Yorkist ends activation [0.1522]; {"by_lord": "march", "side": "yorkist", "type": "pass"} [-2.998]

### Step 249
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March forages
- Result: at Burgundy: success=True; +1 provender; roll=None
- Top scored options: March forages [1.1006]; Yorkist ends activation [0.1526]; {"by_lord": "march", "side": "yorkist", "type": "pass"} [-2.998]

### Step 250
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 251
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Oxford marches to London
- Result: Oxford to London by highway; whole_card=False
- Top scored options: Oxford marches to London [14.4505]; Lancastrian ends activation [0.1517]; Oxford marches to Guildford [0.0026]

### Step 252
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: Lancastrian feed: fed {'Lord': 'Oxford', 'Fed': 1, 'Needed': 1}; disbanded none; next_side=Yorkist
- Top scored options: Lancastrian ends activation [-1.3492]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9982]; Oxford parleys Rochester [-6.3994]

### Step 253
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1505]; Norfolk supplies from Truro [-0.497]; Norfolk supplies from Exeter [-0.4971]

### Step 254
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1512]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9993]; Henry Vi parleys Guildford [-6.3987]

### Step 255
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1503]; Norfolk supplies from Dorchester [-0.4975]; Norfolk supplies from Truro [-0.4981]

### Step 256
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1519]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9975]; Henry Vi parleys Rochester [-6.3975]

### Step 257
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: York parleys Calais
- Result: Calais: calais: neutral -> yorkist; auto=True
- Top scored options: York parleys Calais [7.2268]; York forages [1.1024]; York sails to Exeter [0.5001]

### Step 258
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: York supplies from Calais
- Result: York +3 provender from Calais via stronghold; ways=0
- Top scored options: York supplies from Calais [6.8529]; York supplies from Truro [5.7028]; York supplies from Hastings [5.7021]

### Step 259
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 260
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 2 parleys Harlech
- Result: Harlech: harlech: neutral -> lancastrian; auto=True
- Top scored options: Jasper Tudor 2 parleys Harlech [6.0671]; Jasper Tudor 2 forages [1.1016]; Jasper Tudor 2 marches to Pembroke [0.4511]

### Step 261
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 2 supplies from Harlech
- Result: Jasper Tudor 2 +1 provender from Harlech via stronghold; ways=0
- Top scored options: Jasper Tudor 2 supplies from Harlech [3.8504]; Jasper Tudor 2 forages [0.7512]; Jasper Tudor 2 marches to Pembroke [0.4512]

### Step 262
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 2 supplies from Harlech
- Result: Jasper Tudor 2 +1 provender from Harlech via stronghold; ways=0
- Top scored options: Jasper Tudor 2 supplies from Harlech [3.7005]; Jasper Tudor 2 forages [0.6029]; Jasper Tudor 2 marches to Pembroke [0.4503]

### Step 263
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—

### Step 264
- Context: war=`war_iiil`, turn_box=`4`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 13, 'yorkist': 13}; advance_to_turn=5; next_phase=levy; detail: lancastrian +1 Lord in wales | lancastrian +2 Favour at london | yorkist +2 Favour at calais | lancastrian +1 Favour at harlech | ...

### Step 265
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y3, Y6; held Y3

### Step 266
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L25, L10

### Step 267
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian plays event L25
- Result: card=L25; next=pay

### Step 268
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=['loc:calais', 'exile:burgundy']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=5; vassal_disbanded=[]

### Step 269
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=['loc:london', 'loc:harlech']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=3; vassal_disbanded=[]

### Step 270
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies troops
- Result: at Calais: +2 Men At Arms, 1 Longbow; locale now exhausted
- Top scored options: York levies troops [10.6014]; Norfolk levies cart transport [1.1006]; Yorkist ends muster [0.1018]

### Step 271
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies cart transport
- Result: March added 2 cart
- Top scored options: March levies cart transport [1.9012]; March levies ship transport [1.2006]; Yorkist ends muster [0.1019]

### Step 272
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Norfolk levies ship transport
- Result: Norfolk added 1 ship
- Top scored options: Norfolk levies ship transport [1.2011]; Norfolk levies cart transport [1.1029]; Yorkist ends muster [0.1009]

### Step 273
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies ship transport
- Result: March added 1 ship
- Top scored options: March levies ship transport [1.2008]; March levies cart transport [0.3018]; Yorkist ends muster [0.1013]

### Step 274
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Norfolk levies cart transport
- Result: Norfolk added 2 cart
- Top scored options: Norfolk levies cart transport [1.1025]; York levies cart transport [0.3004]; Yorkist ends muster [0.102]

### Step 275
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies cart transport
- Result: York added 2 cart
- Top scored options: York levies cart transport [0.301]; Norfolk levies cart transport [0.3002]; Yorkist ends muster [0.1009]

### Step 276
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: York levies cart transport
- Result: York added 2 cart
- Top scored options: York levies cart transport [0.303]; Norfolk levies cart transport [0.3013]; Yorkist ends muster [0.1021]

### Step 277
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Norfolk levies cart transport
- Result: Norfolk added 2 cart
- Top scored options: Norfolk levies cart transport [0.3008]; Yorkist ends muster [0.1027]; Norfolk parleys Exeter [-3.4977]

### Step 278
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 279
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 2 levies capability L37
- Result: Jasper Tudor 2 gained L37 MADAME LA GRANDE
- Top scored options: Jasper Tudor 2 levies capability L37 [3.5029]; Jasper Tudor 2 levies capability L9 [3.5027]; Jasper Tudor 2 levies capability L25 [3.5026]

### Step 280
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies cart transport
- Result: Oxford added 2 cart
- Top scored options: Oxford levies cart transport [1.1027]; Jasper Tudor 2 levies cart transport [1.1005]; Lancastrian ends muster [0.1028]

### Step 281
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 2 levies ship transport
- Result: Jasper Tudor 2 added 1 ship
- Top scored options: Jasper Tudor 2 levies ship transport [1.2024]; Henry Vi levies cart transport [1.1004]; Lancastrian ends muster [0.1027]

### Step 282
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies cart transport
- Result: Oxford added 2 cart
- Top scored options: Oxford levies cart transport [0.302]; Lancastrian ends muster [0.1021]; Oxford parleys Rochester [-6.3972]

### Step 283
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Jasper Tudor 2 levies ship transport
- Result: Jasper Tudor 2 added 1 ship
- Top scored options: Jasper Tudor 2 levies ship transport [1.2029]; Henry Vi levies cart transport [1.1028]; Jasper Tudor 2 levies cart transport [1.1012]

### Step 284
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies cart transport
- Result: Henry Vi added 2 cart
- Top scored options: Henry Vi levies cart transport [1.1009]; Lancastrian ends muster [0.1001]; Henry Vi parleys Guildford [-6.3973]

### Step 285
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Henry Vi levies cart transport
- Result: Henry Vi added 2 cart
- Top scored options: Henry Vi levies cart transport [0.3015]; Lancastrian ends muster [0.1022]; Henry Vi parleys Guildford [-6.3983]

### Step 286
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete

### Step 287
- Context: war=`war_iiil`, turn_box=`5`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Oct-Nov-Dec; cards_required=4

### Step 288
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Jasper Tudor 2, Oxford, Henry Vi
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 289
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: York, Norfolk, March, York
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 290
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: York supplies from Plymouth
- Result: York +2 provender from Plymouth via ship; ways=None
- Top scored options: York supplies from Plymouth [0.9028]; York supplies from Southampton [0.9026]; York supplies from Exeter [0.9014]

### Step 291
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.15]; York supplies from Dorchester [-0.4972]; York supplies from Exeter [-0.4974]

### Step 292
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1504]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9972]; Henry Vi parleys Rochester [-6.3971]

### Step 293
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1507]; Norfolk supplies from Dorchester [-0.4985]; Norfolk supplies from Exeter [-0.4988]

### Step 294
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 2 supplies from Pembroke
- Result: Jasper Tudor 2 +2 provender from Pembroke via ship; ways=None
- Top scored options: Jasper Tudor 2 supplies from Pembroke [3.9016]; Jasper Tudor 2 supplies from Bristol [3.9009]; Jasper Tudor 2 sails to Pembroke [0.453]

### Step 295
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Jasper Tudor 2 supplies from Bristol
- Result: Jasper Tudor 2 +2 provender from Bristol via ship; ways=None
- Top scored options: Jasper Tudor 2 supplies from Bristol [0.9022]; Jasper Tudor 2 supplies from Pembroke [0.901]; Jasper Tudor 2 sails to Pembroke [0.4524]

### Step 296
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1505]; Jasper Tudor 2 supplies from Pembroke [-0.4978]; Jasper Tudor 2 supplies from Bristol [-0.4987]

### Step 297
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March supplies from Truro
- Result: March +1 provender from Truro via ship; ways=None
- Top scored options: March supplies from Truro [2.4027]; March supplies from Dorchester [2.4025]; March supplies from Dover [2.4015]

### Step 298
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: March supplies from Southampton
- Result: March +1 provender from Southampton via ship; ways=None
- Top scored options: March supplies from Southampton [0.9029]; March supplies from Exeter [0.9029]; March supplies from Dover [0.9022]

### Step 299
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 300
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1521]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9971]; Oxford parleys Guildford [-6.3976]

### Step 301
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1506]; York supplies from Dover [-0.4974]; York supplies from Truro [-0.4976]

### Step 302
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.1514]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9978]; Henry Vi parleys Rochester [-6.3996]

### Step 303
- Context: war=`war_iiil`, turn_box=`5`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 5, 'yorkist': 3}; advance_to_turn=6; next_phase=levy; detail: lancastrian +1 Lord in wales | lancastrian +2 Favour at london | yorkist +2 Favour at calais | lancastrian +1 Favour at harlech | ...

### Step 304
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y12, Y36; held Y12, Y36

### Step 305
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L36, L34; held L36

### Step 306
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=[]; unpaid_disbanded=['york', 'norfolk']; voluntary_disbanded=[]; influence_paid=2; vassal_disbanded=[]

### Step 307
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=[]; unpaid_disbanded=['henry_vi', 'jasper_tudor_2']; voluntary_disbanded=[]; influence_paid=1; vassal_disbanded=[]

### Step 308
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies ship transport
- Result: March added 1 ship
- Top scored options: March levies ship transport [1.2008]; March levies cart transport [0.3019]; Yorkist ends muster [0.1022]

### Step 309
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: March levies cart transport
- Result: March added 2 cart
- Top scored options: March levies cart transport [0.3023]; Yorkist ends muster [0.1025]; March parleys Exeter [-3.4995]

### Step 310
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 311
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies cart transport
- Result: Oxford added 2 cart
- Top scored options: Oxford levies cart transport [0.3023]; Lancastrian ends muster [0.1017]; Oxford parleys Guildford [-6.3997]

### Step 312
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies cart transport
- Result: Oxford added 2 cart
- Top scored options: Oxford levies cart transport [0.3015]; Lancastrian ends muster [0.1028]; Oxford parleys Rochester [-6.3972]

### Step 313
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete

### Step 314
- Context: war=`war_iiil`, turn_box=`6`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Jan-Feb-Mar; cards_required=4

### Step 315
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Oxford, Oxford, Oxford, —
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 316
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: March, March, March, —
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 317
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1519]; March supplies from Dorchester [-0.4972]; March supplies from Exeter [-0.4973]

### Step 318
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.151]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-3.0]; Oxford parleys Rochester [-6.3975]

### Step 319
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1513]; March supplies from Calais [-0.4973]; March supplies from Truro [-0.4985]

### Step 320
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1508]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9995]; Oxford parleys Rochester [-6.3983]

### Step 321
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian
- Top scored options: Yorkist ends activation [0.1504]; March supplies from Hastings [-0.4971]; March supplies from Plymouth [-0.4972]

### Step 322
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1506]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-3.0]; Oxford parleys Rochester [-6.3977]

### Step 323
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 324
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—

### Step 325
- Context: war=`war_iiil`, turn_box=`6`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 6, 'yorkist': 5}; advance_to_turn=7; next_phase=levy; detail: lancastrian +2 Favour at london | yorkist +2 Favour at calais | lancastrian +1 Favour at harlech | yorkist +1 most Favour towns ({'lancastrian': 0, 'yorkist': 1}) | ...

### Step 326
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`arts_of_war`, active_side=`yorkist`
- Action: Yorkist draws Arts of War
- Result: drew Y4, Y5; held Y5

### Step 327
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`arts_of_war`, active_side=`lancastrian`
- Action: Lancastrian draws Arts of War
- Result: drew L3, L5; held L3, L5

### Step 328
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`pay`, active_side=`yorkist`
- Action: Yorkist pays troops/lords
- Result: paid_groups=[]; unpaid_disbanded=['march']; voluntary_disbanded=[]; influence_paid=0; vassal_disbanded=[]

### Step 329
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`pay`, active_side=`lancastrian`
- Action: Lancastrian pays troops/lords
- Result: paid_groups=['loc:london']; unpaid_disbanded=[]; voluntary_disbanded=[]; influence_paid=1; vassal_disbanded=[]

### Step 330
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`muster`, active_side=`yorkist`
- Action: Yorkist ends muster
- Result: next=king_muster

### Step 331
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford attempts to levy lord Henry Vi
- Result: target=Henry Vi; success=True; roll=2 vs rating 2; spent=1
- Top scored options: Oxford attempts to levy lord Henry Vi [57.9029]; Oxford levies cart transport [0.3004]; Lancastrian ends muster [0.1003]

### Step 332
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Oxford levies cart transport
- Result: Oxford added 2 cart
- Top scored options: Oxford levies cart transport [0.3026]; Lancastrian ends muster [0.1016]; Oxford parleys Rochester [-6.3996]

### Step 333
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`muster`, active_side=`lancastrian`
- Action: Lancastrian ends muster
- Result: next=levy_complete

### Step 334
- Context: war=`war_iiil`, turn_box=`7`, phase=`levy`, levy_step=`done`, active_side=`lancastrian`
- Action: Begin campaign segment
- Result: season=Apr-May; cards_required=6

### Step 335
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian builds plan: Henry Vi, Oxford, Henry Vi, Henry Vi, Oxford, Oxford
- Result: built={'lancastrian': True, 'yorkist': False}; campaign_step=plan

### Step 336
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Yorkist builds plan: —, —, —, —, —, —
- Result: built={'lancastrian': True, 'yorkist': True}; campaign_step=activation

### Step 337
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 338
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1503]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9972]; Henry Vi parleys Guildford [-6.3978]

### Step 339
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 340
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1528]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9991]; Oxford parleys Rochester [-6.399]

### Step 341
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 342
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1514]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9999]; Henry Vi parleys Rochester [-6.3976]

### Step 343
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 344
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1526]; {"by_lord": "henry_vi", "side": "lancastrian", "type": "pass"} [-2.9987]; Henry Vi parleys Rochester [-6.3976]

### Step 345
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 346
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=Yorkist
- Top scored options: Lancastrian ends activation [0.1509]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9981]; Oxford parleys Rochester [-6.3985]

### Step 347
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`yorkist`
- Action: Yorkist ends activation
- Result: next_side=Lancastrian

### Step 348
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: Lancastrian ends activation
- Result: next_side=—
- Top scored options: Lancastrian ends activation [0.152]; {"by_lord": "oxford", "side": "lancastrian", "type": "pass"} [-2.9978]; Oxford parleys Rochester [-6.3983]

### Step 349
- Context: war=`war_iiil`, turn_box=`7`, phase=`campaign`, levy_step=`done`, active_side=`lancastrian`
- Action: End campaign segment
- Result: Tides={'lancastrian': 4, 'yorkist': 3}; advance_to_turn=7; next_phase=over; detail: lancastrian +2 Favour at london | yorkist +2 Favour at calais | lancastrian +1 Favour at harlech | yorkist +1 most Favour towns ({'lancastrian': 0, 'yorkist': 1}) | ...; VICTORY: Lancastrian by rule 5.1

## Final lord states

| Lord | Side | Status | Position | Forces | Assets | Capabilities |
|---|---|---|---|---|---|---|
| `henry_vi` | Lancastrian | mustered | london | retinue:1, men_at_arms:2, longbow:2, militia:4 | provender:2, coin:4, cart:2 | none |
| `jasper_tudor_2` | Lancastrian | calendar | calendar:10 | none | none | none |
| `margaret` | Lancastrian | available | none | none | none | none |
| `oxford` | Lancastrian | mustered | london | retinue:1, men_at_arms:2, longbow:2, militia:2 | provender:1, cart:12 | L1, L8 |
| `somerset_1` | Lancastrian | available | none | none | none | none |
| `somerset_2` | Lancastrian | available | none | none | none | none |
| `gloucester_1` | Yorkist | available | none | none | none | none |
| `gloucester_2` | Yorkist | available | none | none | none | none |
| `march` | Yorkist | calendar | calendar:11 | none | none | none |
| `norfolk` | Yorkist | calendar | calendar:9 | none | none | none |
| `rutland` | Yorkist | available | none | none | none | none |
| `salisbury` | Yorkist | available | none | none | none | none |
| `warwick_yorkist` | Yorkist | available | none | none | none | none |
| `york` | Yorkist | calendar | calendar:7 | none | none | none |

## Notable final locale states

| Locale | Favour | Depletion |
|---|---|---|
| `arundel` | yorkist | None |
| `calais` | yorkist | exhausted |
| `ely` | yorkist | None |
| `harlech` | lancastrian | exhausted |
| `london` | lancastrian | exhausted |
| `oxford` | lancastrian | exhausted |
| `pembroke` | lancastrian | exhausted |

## Notes for another LLM

- The `.jsonl` companion file contains one compact JSON object per applied action, including the chosen action, concise action/result text, and up to three top-scored alternatives.
- The raw original log remains available separately as `plantagenet_safety_grand_selfplay_seed181.json`.
- This derived log intentionally omits full dice-roll arrays inside battles to keep the document readable; the key battle outcomes are preserved above.
