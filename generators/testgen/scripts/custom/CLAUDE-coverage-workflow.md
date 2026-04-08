# Vector Coverage Workflow

**Run first, read results, then fix.** Do not read scripts or templates until you have a coverage report.

**Verify by rerunning, not by reading.** After making a fix, rebuild and rerun coverage (steps 2–4) to confirm it worked. Do not read generated test files, assembly output, or framework source to guess whether a fix succeeded — the coverage report is the ground truth. Similarly, if a hole might exist in multiple instructions, rerun coverage to check rather than reading files to deduce the answer.

## Workflow

```bash
# 1. Isolate
python3 isolate_coverpoint.py <Category> <cp_column_name>

# 2. Build (should finish <30s for one coverpoint; if not, isolation failed)
make clean && make vector-tests

# 3. Coverage — always use FAST=True for normal runs (skips objdump, much faster)
FAST=True timeout 120s make coverage

# 4. Read results
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --uncovered
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --bins <instruction>

# 5. Fix scripts/templates based on report, then repeat 2-4 to verify (do NOT read files to check — rerun coverage)

# 6. Restore when done
python3 isolate_coverpoint.py --restore <Category>
```

## Hang Detection

| Scope                   | Expected time |
| ----------------------- | ------------- |
| Isolated coverpoint     | < 30 seconds  |
| Full Vf suite           | ~3 minutes    |
| Full V suite (all of V) | ~50 minutes   |

**If coverage is slow relative to these benchmarks, assume a hang immediately.** The `make coverage` output shows the oldest running task — if the same file stays as "oldest" across multiple runs, it's hanging. Follow `guides/debugging-hangs.md` to diagnose and fix.

**Incremental progress**: Skipping `make clean` saves progress. Run `FAST=True timeout 30s make coverage` in intervals to confirm `.sig` files are completing. If no new files complete between intervals, investigate immediately.

## Incremental Rebuild After Testgen Fix

After fixing a bug in a testgen script, you do **not** need `make clean`. The build system
tracks `.sig` files and only re-simulates tests that are missing them. This workflow saves
significant time (~2 min recompile vs 5–10+ min full rebuild + simulation):

```bash
# 1. Fix the bug in the testgen script (e.g. vector-testgen-unpriv.py or cp_custom_*.py)

# 2. Regenerate test .S files (no clean needed, ~30s)
make vector-tests

# 3. Delete .sig files for affected tests so they get re-simulated
#    Delete specific tests:
rm work/sail-rv64-max/build/rv64i/<Ext>/<test>.sig
#    Or delete all sigs for an extension:
rm work/sail-rv64-max/build/rv64i/<Ext>/*.sig work/sail-rv32-max/build/rv32i/<Ext>/*.sig

# 4. Run coverage — only missing .sig files are re-simulated (~2 min recompile + sim time)
FAST=True make coverage
```

**Key details:**

- If .S content is unchanged (same seed, same logic), `act` detects this and skips
  everything (completes in ~2s).
- If .S content changed, `.elf` files are recompiled (~2 min for all VF), but only
  tests with missing `.sig` files are re-simulated by Sail.
- **Always delete `.sig` files for tests you want re-simulated** — stale sigs will not
  be automatically invalidated by new .S content.

## Debugging with Trace Files

Use `DEBUG=True` (without FAST) to generate trace files. **Trace files grow extremely fast** — use max 10s timeout (1s is usually enough).

```bash
DEBUG=True timeout 1s make coverage    # preferred — short burst
DEBUG=True timeout 10s make coverage   # max allowed
```

**Switch back to `FAST=True` immediately after** collecting traces.

## What to read and when

| When                     | Read                                                                                                   |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| Planning next coverpoint | This file + `claude-scripts/progress.json`                                                             |
| Fixing a test script     | `GUIDE.md` + `claude-scripts/knowledge.md`                                                             |
| Fixing a template        | `claude-scripts/knowledge.md` + templates in `generators/coverage/src/covergroupgen/templates/vector/` |

## Isolation

`isolate_coverpoint.py` (repo root):

- Reads canonical backup from `working-testplans/duplicates/<Category>-save.csv`
- Strips rows without `x` in target column, strips other `cp_custom_*` columns
- Writes to `testplans/`, deletes other vector testplans, updates Makefile EXTENSIONS
- **Always restore** before isolating a different coverpoint

Manual EXTENSIONS if needed: `Vf16,Vf32,Vf64` (VfCustom is now part of Vf) or `Vls8,Vls16,Vls32,Vls64` (VlsCustom is now merged into Vls)

## Coverage Completion Requirement

**A coverpoint is complete ONLY when its custom bins reach 100% coverage.** Every custom bin defined in a template must be hit.

If a custom bin cannot be hit, **remove it from the template**. The goal is 100% across all custom bins: either write a test that hits the bin or delete it.

**Residual bins at 0% are acceptable.** Bins not defined in the template (framework-generated bins like `cp_asm_count`, `std_vec`, or precondition crosses) will be filled when the full suite runs. Do not investigate or fix these during isolated coverpoint work.

**Entire covergroups at 0% are also residual when the instruction has NO custom marks.** Many instructions in Vls (e.g., `vle32.v`, `vlse8.v`, `vse16.v`, `vlseg*`, `vlsseg*`, `vsseg*`, `vssseg*`) have no `cp_custom_*` columns marked in the CSV. Their covergroups only contain `cp_asm_count` and `std_vec` — both framework-generated. These show as 0%/ZERO in reports but are **not** coverage holes. They will be covered when the full non-custom test suite runs. Only instructions with `cp_custom_*` marks need custom test scripts.

**Note:** VlsCustom has been merged into Vls. The single `Vls.csv` testplan now contains both custom and non-custom coverpoints. When updating `testplans/Vls.csv`, also update the canonical backup at `working-testplans/duplicates/Vls-save.csv`.

## Reading Coverage Reports

Use `coverage_summary.py` — not grep or file reads:

- `--uncovered` — compact table of instructions not at 100%
- `--bins <instruction>` — specific missing bins grouped by coverpoint

Report files: `work/sail-rv64-max/reports/` and `work/sail-rv32-max/reports/`

- `_overall_summary.txt` — safe to read for high-level %
- `*_uncovered.txt` — large, use coverage_summary.py instead

If `<Category><SEW>_uncovered.txt` is absent, that SEW is at 100%.

## Progress Tracking

`claude-scripts/progress.json` — per-coverpoint status (`completed`, `in_progress`, `blocked`, `not_started`).
`claude-scripts/coverage-status.md` — flat summary for quick review.

## If stuck

After 2 failed attempts, write a note to `claude-scripts/coverage_issues/<coverpoint_name>.md` and stop.
