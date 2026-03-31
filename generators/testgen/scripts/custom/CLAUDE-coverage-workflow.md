# Vector Coverage Workflow

**Run first, read results, then fix.** Do not read scripts or templates until you have a coverage report.

**Verify by rerunning, not by reading.** After making a fix, rebuild and rerun coverage (steps 2–4) to confirm it worked. Do not read generated test files, assembly output, or framework source to guess whether a fix succeeded — the coverage report is the ground truth. Similarly, if a hole might exist in multiple instructions, rerun coverage to check rather than reading files to deduce the answer.

## Workflow

```bash
# 1. Isolate
python3 isolate_coverpoint.py <Category> <cp_column_name>

# 2. Build (should finish <30s for one coverpoint; if not, isolation failed)
make clean && make vector-tests

# 3. Coverage (isolated coverpoints should finish FAST — under 60s typically)
timeout 120s make coverage

# 4. Read results
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --uncovered
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --bins <instruction>

# 5. Fix scripts/templates based on report, then repeat 2-4 to verify (do NOT read files to check — rerun coverage)

# 6. Restore when done
python3 isolate_coverpoint.py --restore <Category>
```

## Hang Detection

Sail can run an **indefinite** number of tests — there is NO test count limit. If `make coverage` hangs
(build step stuck on a `.sig` file for >60s for an isolated coverpoint), a test is generating an illegal
instruction that causes an infinite trap loop. This is always a script bug, never a sail limitation.

**How to identify a hang**: The `make coverage` output shows the oldest running task, e.g.:

```
oldest: .../work/sail-rv32-max/build/rv32i/VfCustom64/VfCustom64-vfmv.s.f.sig
```

**How to fix**: Follow `guides/debugging-hangs.md` — find the ELF, run with `--inst-limit` and `--trace-instr`,
identify the illegal instruction, fix the script.

## What to read and when

| When                     | Read                                                                     |
| ------------------------ | ------------------------------------------------------------------------ |
| Planning next coverpoint | This file + `claude-scripts/progress.json`                               |
| Fixing a test script     | `GUIDE.md` + `claude-scripts/knowledge.md`                               |
| Fixing a template        | `generators/coverage/templates/GUIDE.md` + `claude-scripts/knowledge.md` |

## Isolation

`isolate_coverpoint.py` (repo root):

- Reads canonical backup from `working-testplans/duplicates/<Category>-save.csv`
- Strips rows without `x` in target column, strips other `cp_custom_*` columns
- Writes to `testplans/`, deletes other vector testplans, updates Makefile EXTENSIONS
- **Always restore** before isolating a different coverpoint

Manual EXTENSIONS if needed: `VfCustom16,VfCustom32,VfCustom64` or `VlsCustom8,VlsCustom16,VlsCustom32,VlsCustom64`

## Coverage Completion Requirement

**A coverpoint is complete ONLY when its custom bins reach 100% coverage.** Every custom bin defined in a template must be hit.

If a custom bin cannot be hit, **remove it from the template**. The goal is 100% across all custom bins: either write a test that hits the bin or delete it.

**Residual bins at 0% are acceptable.** Bins not defined in the template (framework-generated bins like `cp_asm_count`, `std_vec`, or precondition crosses) will be filled when the full suite runs. Do not investigate or fix these during isolated coverpoint work.

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
