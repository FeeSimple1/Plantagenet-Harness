# Grand-campaign regression fixtures

Source: interactive/instrumented Wars of the Roses campaign, seed 20261010,
revision 17cb0fe0aafb375659f4888b596d4853f5edb5fd.

These are real pre-action snapshots (43: Y22 draw; 80: Peterborough battle;
177: Commission of Array; 1099: Warwick last-Heir death), and the real
War-IIY ending state. Only `history` was stripped to avoid unrelated bulk.
The selected actions are unmodified. These are bug reproductions, not
golden outcomes to preserve after a rules correction.

The Exile tests explicitly advance the IIY-end fixture to the scheduled
Turn-10 Muster; the played War actually ended on Turn 8. The wrong-winner
variant explicitly changes Influence to Yorkist 25. Other mutations in tests
are identified boundary conditions rather than claimed playthrough events.

`campaign-actions.jsonl` retains all 1102 original actions. The integration test
adds one explicitly specified Y22 target selection (March) before original
zero-based action 44. It replays through action 1099, now terminal; the final
two historical actions are not applied. No engine policy or replay waiver
manufactures missing choices. Both fresh and JSON-loaded games must match on
every result, every semantic state, and complete final history.
