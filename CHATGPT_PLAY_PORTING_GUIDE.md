# Playing Plantagenet through the compact LLM interface

The player chooses strategy. The helper handles state, navigation and diagnostics;
it does not rank moves, change rules, pick Campaign Plans, or silently advance Wars.
The entry point is `scripts/chatgpt_play_helper.py`.

## Start and navigate

```python
import sys
sys.path[:0] = ['src', 'scripts']
import chatgpt_play_helper as nv

overview = nv.start('henry_vi', seed=1)
page = nv.menu(action_type='draw', page=1, page_size=4)
# Read the choices, then copy the chosen row's entire ID:
receipt = nv.apply(page['items'][0]['id'])
```

`show()` prints a fresh compact position and **action categories/counts**, not
an expanded action list. Counts are menu entries, **not the number of legal
parameter combinations**. A `TEMPLATE` denotes a free construction; `*` denotes
additional supported parameters. A singleton category includes its full ID so
no extra browse request is needed merely to obtain that ID.

The compact baseline includes position/status, effective Influence/Lordship/
Command ratings, Lordship spent, Forces (`F`), Assets (`A`, including Provender,
Coin and transport), attached Capabilities and Vassals, Favour/depletion,
Influence, visible cards and Plans, active effects, Exile alignment, victory
and pending decisions. No numeric value is rounded or replaced by a heuristic.
Map/static data, precise bookkeeping and full card text remain inspectable.

### Filters and pagination

```python
page = nv.menu('parley', by_lord='york', page_size=6)
page = nv.menu(lord='march', page=2, page_size=6,
               expected_version=page['version'])
page = nv.menu('draw', **{'assignments.Y11': 'march'})
page = nv.menu('march', to='london')
page = nv.menu(query='provender', page_size=None)
```

The second example illustrates the continuation guard; in actual continuation,
retain **the same filters** used for page 1. Pages are one-based. `page_size=None`
means every matching entry, not an arbitrary upper limit. `lord` matches actors,
targets, groups, allocations and eligible Campaign Plan templates. `by_lord`
means the exact actor field. Any JSON field, including a dotted nested field,
can be matched exactly using keyword arguments; `query` searches the visible
JSON text case-insensitively. Missing concrete fields do not match: filtering
is navigation over the engine catalog, not a solver for parameter combinations.

`page['total']`, `pages`, `next_page`, `filters` and `version` make exhaustion
explicit. No page renumbers the underlying actions.

## Stable selections

An ID looks like `v0123abcd.7/26`: an opaque session namespace, a state revision,
and a slot in that revision's complete raw catalog. It is **not a local row
number**. Copy the whole ID. Sorting/filtering, different page sizes and changing
validation mode do not change what it means.

`apply(0)` is intentionally unsupported: an unversioned integer cannot prove
which observed menu was intended. An accepted action invalidates all old IDs,
even if it has no visible board effect. Direct external edits to the attached
GameState are detected by a private full-state fingerprint (including RNG and
history). Loading or changing perspective also invalidates IDs. Public IDs do
not encode a hash of hidden card contents.

A raw/custom action must include an explicit state expectation:

```python
observed_version = nv.version()
receipt = nv.apply({'type': 'parley', 'side': 'yorkist',
                    'by_lord': 'york', 'target': 'london', 'extra_spend': 3},
                   expected_version=observed_version)
```

Capture `observed_version` with the position being considered, not after making
an unrelated move. Stale IDs/actions/page continuations raise
`StaleSelectionError` without invoking the engine. Failed rule checks return a
small error receipt, not a full menu redisplay, and the engine's atomic rollback
preserves the state and RNG.

## Parameters are strategic choices, not defaults

```python
help_text = nv.describe('build_plan')
plan_row = nv.menu('build_plan')['items'][0]
# For a four-card season only; a different season requires its own length:
receipt = nv.apply(plan_row['id'], parameters={'plan': [
    {'lord': 'march'}, {'lord': 'march'}, {'pass': True}, {'lord': 'york'}
]})
```

**No default Plan is substituted.** Use exactly `cards_required` entries, any
ordering of this side's Mustered Lords and Passes, at most three cards per Lord.
The menu's template stands for the whole family, not a single example Plan.

`describe(type_or_id)` supplies parameter names, constraints and relevant card
text. Event descriptions also expose literal payload keys and the current
resolver's source constraints. `describe(..., source=True)` provides detailed
handler source; `inspect('grammar')` provides the full action grammar. These are
uncapped on-demand tools, not additional mechanics or alternative rule validators.

Parameterized choices remain accepted by the unchanged engine, including
Influence bids; partial Group Marches; shared transport; multi-Lord Exile returns;
Pay ordering/voluntary disbands; tactical Arrays, Flee, hit allocation, Valour and
card choices; mandatory selection Events; and optional Held Events. A dictionary
shown without optional parameters uses the engine defaults if applied as-is, but
those defaults are never described as the only legal option. The deliberately
manual-adjudicated `concede` timing remains documented, not newly enumerated.

`auto()` is conservative. It stops on templates, supported parameter families,
reactions, early Activation endings, Reset and War renewal. It does not call a
single parameterized representative a forced action. Each genuinely forced
unparameterized action still emits its consequences.

## Results and detailed inspection

`apply()` prints a concise result and the complete visible-state change patch,
plus newly pending decisions and next category counts. Large battles are allowed
to exceed a suggested output budget. A card's authorised information gain, such
as Aspielles' snapshot, is included rather than omitted as cosmetic detail.
The returned `Reply` retains the safe full result and structured changes.
Its short representation prevents a notebook from accidentally echoing a huge
programmatic menu. Assign replies to variables to avoid even that small echo.

```python
info = nv.inspect('influence')
info = nv.inspect('york')               # full mat, ratings/Seat/static data
info = nv.inspect('cards')              # owner's Held cards, public counts
info = nv.inspect('card', card='Y22')   # complete static card text
info = nv.inspect('effects')
info = nv.inspect('pending')
info = nv.inspect('result')            # full safe last engine result
info = nv.inspect('history')           # safe receipt history
info = nv.inspect('map')               # all locales/ways, not a local crop
info = nv.inspect('state')             # all player-visible state fields
```

A fresh baseline is forced after loading, perspective/active-player handoff,
external state edits, and Renewed-War transitions. `show()` always supplies a
baseline. Inspection never changes game state, draws dice, or renews a War.
After a decisive first/second War, select the explicit `renew_war` action.

## Player views and joint decisions

The default `perspective='active'` is for a trusted host controlling both sides:
it follows the player who actually owns the next decision, **including a
reactor different from `state.active_side`**. A handoff emits a fresh baseline.

For a single player's context, start with `perspective='yorkist'` or
`'lancastrian'`. That context sees only its own available decisions, Held Events,
unrevealed setup and future Plan. Enemy hidden state is not leaked through
menu annotations, return values, detailed inspection, previous receipts or
validation probes. Enemy public mats/Capabilities remain visible. Inspecting a
static card by ID never asserts that an opponent possesses it.

The trusted host may call `set_perspective(side)` to switch contexts. This is
**output separation, not authentication**: arbitrary Python code that can read
`_S`, import the engine or open a save file is already a referee. Do not give
such access to an untrusted opposing player. `perspective='referee'` deliberately
exposes omniscient programmatic menus/results and enables `inspect('raw')` and
`inspect('engine_history')` for debugging. Even normal card views do not print
the next shuffled card or RNG state.

Campaign Reset has one engine action containing both players' choices. In
restricted views, collect private contributions first:

```python
# In the Yorkist context:
nv.stage_reset({'discard_held': ['Y13']}, expected_version=nv.version())
# The trusted host then switches to the Lancastrian context:
overview = nv.set_perspective('lancastrian')
nv.stage_reset({}, expected_version=nv.version())  # explicitly keep/default
row = nv.menu('end_campaign')['items'][0]
receipt = nv.apply(row['id'])
```

The same transport accepts `charity` and `disembark_land`, keyed by the submitting
player's own Lords. Contributions stay sealed, are saved/resumed, and are combined
into **one unchanged atomic engine call**. They do not consume dice or execute
half a Reset. In referee mode, the full existing joint `decisions` payload can
be submitted directly. Omitted own choices retain the ordinary engine defaults;
another player's meaningful Reset choices require its contribution.

## Full menus, validation and diagnostics

`all_actions()` returns every safe validated record, without printing.
`all_actions(validated=False)` also retains rejected engine candidates; all
records keep the same IDs. In referee mode the action dictionaries correspond
exactly to `legal_moves(state)`, including metadata and unexpanded templates.
`show(expanded=True)` or `menu(page_size=None)` explicitly displays the full menu.

Enumeration and probes operate on isolated deep copies. Validation statuses are
cached per revision; templates are retained without pretending that an unspecified
choice has been validated. Rejected candidates stay accessible via
`inspect('rejected')`. `findings_report()` retains engine-divergence, rejection,
exception, invariant and genuine under-enumeration diagnostics; custom choices
inside supported parameter families are not mislabeled as under-enumeration.

`SOFT_OUTPUT_CHARS` is advisory only. Exceeding it prints a notice and **does not
truncate results, hide options, alter mechanics or prevent detailed inspection**.

## Save and resume

```python
nv.save('game.json')
overview = nv.load('game.json')
```

The checkpoint contains full referee state, exact RNG, diagnostics, receipts,
perspective and private staged contributions. Keep it private. Load creates a
new ID namespace and a fresh baseline; saved menu IDs intentionally do not survive.
A saved finished War remains finished until the player selects `renew_war`.

## Tests and output measurements

See `tests/test_llm_interface.py` and `LLM_INTERFACE_BENCHMARK.md`. The benchmark
compares the old helper against the new helper on identical engine trajectories,
counting added browse/help/detail requests as well as responses, and reports
expensive cases as well as savings. It is a diagnostic, not a hard output budget.
