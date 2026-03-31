# Vector Coverage Workflow

**Run first, read results, then fix.** Do not read scripts or templates until you have a coverage report.

**Verify by rerunning, not by reading.** After making a fix, rebuild and rerun coverage (steps 2–4) to confirm it worked. Do not read generated test files, assembly output, or framework source to guess whether a fix succeeded — the coverage report is the ground truth. Similarly, if a hole might exist in multiple instructions, rerun coverage to check rather than reading files to deduce the answer.

## Workflow

```bash
# 1. Isolate
python3 isolate_coverpoint.py <Category> <cp_column_name>

# 2. Build (should finish <30s for one coverpoint; if not, isolation failed)
make clean && make vector-tests

# 3. Coverage
timeout 120s make coverage

# 4. Read results
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --uncovered
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --bins <instruction>

# 5. Fix scripts/templates based on report, then repeat 2-4 to verify (do NOT read files to check — rerun coverage)

# 6. Restore when done
python3 isolate_coverpoint.py --restore <Category>
```

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

**A coverpoint is complete ONLY when it reaches 100% coverage.** Every bin defined in a template must be hit. There are no exceptions — a bin at 0% is never acceptable.

If a bin cannot be hit (e.g., the hardware will never produce that state), the bin must be **removed from the template**. Do not leave unfillable bins in place and call the coverpoint "done." The goal is 100% across all bins, which means either:

1. Write tests that hit the bin, **or**
2. Delete the bin from the template because it represents an unreachable state.

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
