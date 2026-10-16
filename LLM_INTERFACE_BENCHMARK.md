# LLM interface output benchmark — 2026-10-16

## Scope and method

The baseline is `scripts/chatgpt_play_helper.py` at commit `69f52dbab5280d5e18856316c4fbc7479bc9efe1`. The candidate is the compact interface in this change. No files in `src/` (engine, rules data, or game-state models) were changed.

The five representative sequences below contain **73 accepted actions**. They cover both sides, initial Capability choices, Muster, ordinary Campaign commands, custom Plans, sparse activation menus, a pending reaction/battle, and private Campaign Reset contributions. These are deterministic test trajectories built from scenario/test fixtures, **not a new full-game playtest**. Every action is applied to both interfaces, and the complete game state, history, and RNG must match before and after every action.

The measurement counts every emitted response plus the request code for every call. Added menu pages (four entries per page), parameter-help calls, matching card-text inspections, a detailed battle-result inspection, and all private Reset contributions and perspective switches are included. The baseline is credited its already printed full menu and uses its short integer selections wherever the exact action is offered; it uses raw dictionaries only for custom actions. Return values are assigned, so neither interface is charged an implicit notebook echo.

Counts use **tiktoken 0.14.0 / `o200k_base`** on Python 3.13.5. This is a named proxy tokenizer, not a claim about the tokenizer used by a particular ChatGPT deployment. Interface session UUIDs are derived from SHA-256 of each trajectory name for reproducibility; no engine function, state, RNG, or strategic choice is patched. Production UUIDs remain random, so exact production token counts vary slightly.

Tool protocol envelopes, shared instructions, model reasoning, latency, and repeated-context billing are not included; the counts measure actual request/response text, not a billing estimate. The baseline lacks some player-safe reporting and explicit constraint help, so it is not charged a hypothetical privacy retrofit. Those additional candidate costs remain in the comparison.

## Results

| Sequence | Actions | Requests, old → new | Output tokens, old → new | All text tokens, old → new | Output reduction |
|---|---:|---:|---:|---:|---:|
| opening_levy_both_sides | 15 | 18 → 31 | 12,960 → 8,099 | 13,128 → 8,890 | 37.5% |
| muster_and_campaign_both_sides | 33 | 36 → 54 | 25,162 → 16,162 | 25,521 → 17,566 | 35.8% |
| custom_plans_sparse_activations | 22 | 23 → 36 | 11,839 → 11,083 | 12,088 → 12,002 | 6.4% |
| approach_reaction_and_battle | 2 | 4 → 7 | 1,683 → 3,180 | 1,710 → 3,314 | -88.9% |
| private_campaign_reset | 1 | 2 → 6 | 642 → 1,553 | 688 → 1,649 | -141.9% |
| **Total** | **73** | **83 → 134** | **52,286 → 40,077** | **53,135 → 43,421** | **23.4%** |

The candidate makes **51 additional requests**. Output falls by **23.35%**. Including request text, total tokens fall by **18.28%**. Request tokens themselves increase from **849 to 3,344**.

Exact character counts: output 144,856 → 111,747; all request-plus-response text 147,312 → 121,325.

### Both-player accounting

| Player | Requests, old → new | Output tokens, old → new | All text tokens, old → new |
|---|---:|---:|---:|
| yorkist | 43 → 68 | 23,200 → 20,796 | 23,657 → 22,464 |
| lancastrian | 40 → 66 | 29,086 → 19,281 | 29,478 → 20,957 |

### Where savings do not occur

The pending reaction and private Reset sequences are deliberately retained despite costing more. They pay for action-parameter help, a fresh player baseline, meaningful reaction context, and private choice collection instead of exposing both hands in a single omniscient menu. Sparse alternating activations save little because fresh perspective baselines dominate. A user who asks for every page and every detailed inspection can spend more than the old expanded menu. There is no universal savings guarantee.

Budgets are **advisory only**. `SOFT_OUTPUT_CHARS` adds a warning; it never truncates information, removes a move, constrains a plan, or changes mechanics. Complete menus and detailed state/card/result inspection remain available.

## Navigation and fidelity checks

`tests/test_llm_interface.py` adds **44 regression cases**. Across seven representative menu fixtures, the combined type-filtered and paginated records reproduce the complete raw and validated legal-menu sets, including unexpanded templates and optional Events. Validation cannot renumber a selection. Returned data cannot mutate cached choices. Tests also cover custom repeated/pass Plans for both sides, partial Group Marches, Influence bids, event targets, stale ID and stale-page rejection, external state edits, pending responses, player information restrictions, authorized Aspielles information, save/resume, and both Renewed-War transitions.

Transition and custom-action tests compare against direct engine execution. Inspection and menu calls must not mutate game state or RNG; War renewal is explicit. Loading or changing perspective invalidates previous selections and emits a fresh baseline. The local full suite passes **1,074 tests**; Ruff passes, and the existing strict mypy configuration reports no issues in its 28 engine source files. The script modules are exercised by pytest and Ruff (they are outside the existing mypy target).

## Reproduce

```sh
git show 69f52dbab5280d5e18856316c4fbc7479bc9efe1:scripts/chatgpt_play_helper.py > /tmp/plantagenet-old-helper.py
python -m pip install -e ".[dev,parallel]"
python -m pip install tiktoken==0.14.0  # optional: exact named-tokenizer counts
PYTHONPATH=src:scripts python scripts/benchmark_llm_interface.py \
  --baseline /tmp/plantagenet-old-helper.py --out /tmp/plantagenet-interface-benchmark
PLANTAGENET_BASELINE_HELPER=/tmp/plantagenet-old-helper.py \
  PYTHONPATH=src:scripts pytest -q tests/test_llm_interface.py
pytest -q -n 2 -p no:cacheprovider
ruff check .
mypy
```

The benchmark writes a machine-readable summary and complete per-call old/new transcripts for each sequence. Without the optional tokenizer, byte/character counts remain exact and token fields are null. The recorded summary is in [`benchmarks/llm_interface_20261016.json`](benchmarks/llm_interface_20261016.json).
