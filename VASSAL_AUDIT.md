# Vassal component audit — 19 October 2026

Baseline: `1210175` (main). The comparison found three corrections to harness
data. Each was reproduced with failing regression tests before changing the
data. Burgundy's correction was confirmed by the user and recorded as D-008.

## Source and method

- [Vassal module listing](https://vassalengine.org/library/projects/Plantagenet_Cousins_War_for_England_1459_-_1485)
- [Plantagenet_1.0.vmod](https://obj.vassalengine.org/images/c/c1/Plantagenet_1.0.vmod),
  version 1.0, published 7 August 2023; 120,983,533 bytes.
- SHA-256: `f4b5243ef2a0c29fdaa455d813cb4ffbb442ff4d1f530f7a39319873729abe01`.

Inspected the ZIP's `buildFile.xml`, printed artwork for all 28 Lord mats and
all 13 regular Vassals, and extracted text for all 74 Arts of War cards. Also
inspected the map and spot-checked positions in the five bundled saved setups.
Compared discrepancies with the repository's final rules PDF, curated
references, and static data. The module contains an older rules proof; that
proof does not override the final rules or errata in this repository.

This was a component and setup comparison, not a Vassal GUI playthrough or an
exhaustive check of combat, Events, or Capability execution. The module's
internal properties and saved setups are not consistently reliable enough to
serve as an automatic rules oracle.

## Confirmed harness defects

| Component | Previous harness value | Correct value | Evidence and effect |
| --- | --- | --- | --- |
| Clarence starting Assets | None | 2 Provender, 2 Coin, 1 Cart | `images/lclarence.png` and the `Mat Lancaster11` Muster prototype agree. Rule 1.5.3 uses printed starting Assets. Fixes Scenario II/War IIY setup and later Muster; rule 4.8.5 Waste now restores 2 Coin. |
| Norfolk Command | 3 | 2 | `images/ynorfolk.png`, module metadata, and the Norfolk illustration on final rulebook p.22 agree. Prevents a third unmodified Command action per activation (4.2.2). |
| Burgundy Sea | English Channel | North Sea | Burgundy's arrow on `images/Plantagenet table.jpg`, rule 1.3.1, and user correction D-008. Direct Sail destinations now use North Sea Ports; Supply and Parley routes use the corrected Sea. |

Corrected both runtime JSON and the corresponding curated references. D-001's
original wording is preserved with a superseding note pointing to D-008.
Clarified the stale explanatory note in `seas.json` to match existing FAQ #1
enforcement: direct Port/Exile-to-Port Sail requires the same Sea.

## Module discrepancies not imported

- Some internal rating properties disagree with the printed mats. For example,
  Henry VI's properties give Influence 1 / Valour 2, while the printed mat and
  harness use Influence 5 / Valour 0. Artwork and final rules take precedence
  over these stale properties.
- In the Henry VI saved setup, Somerset appears at Wells and Rutland at
  Canterbury. The final scenario setup instead places Somerset with Henry VI
  in London and Rutland on Calendar box 5. The harness's correct setup was
  retained.

These discrepancies are why the audit did not bulk-copy Vassal properties or
treat every module-versus-harness difference as a harness bug.

## Regression coverage and validation

`tests/test_vassal_component_audit.py` adds 14 regression cases:

- Clarence in Scenario II and renewed War IIY, public-action remuster, and Waste.
- Norfolk's rating in three scenarios and a public activation exhausted after
  two commands, with atomic rejection of a third command.
- Burgundy's exact direct-Sail menu, legal Sail to Ipswich, atomic rejection of
  direct Sail to Dover, Supply from Ipswich, one-Way Levy Parley to Ipswich, and
  atomic rejection of an unsupported route to Dover.

All eight Clarence/Norfolk cases failed before their data fixes; all six
Burgundy cases failed before the Sea reassignment. Existing Sea expectations
and the Clarence Waste test were corrected to the independently verified
component values. Historical replay fixtures were left intact.

Baseline: 1,074 tests passed. Final full-suite and static-check results are
recorded in the matching `SMOKE_TEST_FINDINGS.md` entry.

To reproduce with the project's development dependencies installed:

```sh
pytest -q
ruff check src tests
mypy src
plantagenet data-check
git -c core.whitespace=cr-at-eol diff --check
```

The whitespace setting respects the existing CRLF encoding of the Lords and
Vassals reference. No module binaries or copyrighted artwork were added to the
repository.

Existing saves retain their serialized Assets; this change does not silently
grant Clarence supplies in a game already underway. New setups, remusters, and
future Waste use the corrected values. Ratings and Sea membership are loaded
from static data and use the correction in resumed games as well.
