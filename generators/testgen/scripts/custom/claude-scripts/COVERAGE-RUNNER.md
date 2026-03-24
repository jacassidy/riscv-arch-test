# Coverage Runner — Manager Claude Guide

## What This Is

`coverage_runner.py` automates the coverage verification workflow by launching Claude sub-processes (via `claude -p`). Each sub-Claude handles one coverpoint end-to-end:

1. Reads the knowledge base and guides
2. Isolates the coverpoint CSV
3. Runs `make vector-testgen && make coverage`
4. If build/coverage fails: diagnoses the root cause, fixes it, retries
5. Updates `progress.json` with results
6. Restores testplans

The script processes coverpoints **sequentially** because CSV isolation requires exclusive access to testplan files.

## When to Use

Use this when the user asks to:
- "Run coverage on the remaining coverpoints"
- "Complete the untested entries in progress.json"
- "Get coverage for cp_custom_X"

## Quick Start

```bash
cd /home/jacassidy/cvw/addins/riscv-arch-test-cvw

# Preview what would run (always do this first)
python3 generators/testgen/scripts/custom/claude-scripts/coverage_runner.py --dry-run

# Run all untested coverpoints
python3 generators/testgen/scripts/custom/claude-scripts/coverage_runner.py

# Run one specific coverpoint
python3 generators/testgen/scripts/custom/claude-scripts/coverage_runner.py -c cp_custom_vfp_flags_nv_nx

# Run only VfCustom untested items
python3 generators/testgen/scripts/custom/claude-scripts/coverage_runner.py --category VfCustom

# Adjust budget and iterations
python3 generators/testgen/scripts/custom/claude-scripts/coverage_runner.py --max-budget 3.0 --max-iterations 3
```

## Arguments

| Arg | Default | Description |
|-----|---------|-------------|
| `--coverpoint`, `-c` | all untested | Run a specific coverpoint |
| `--category` | both | `VfCustom` or `VlsCustom` only |
| `--max-budget` | 5.0 | USD budget per sub-Claude |
| `--max-iterations` | 5 | Max build→fix cycles per coverpoint |
| `--timeout` | 1800 | Seconds before killing a sub-Claude |
| `--dry-run` | false | Preview without launching |

## How It Works

### Progress Tracking

All state lives in `progress.json`. Each entry looks like:

```json
{
  "VfCustom": {
    "cp_custom_vfp_flags_nv": {
      "status": "completed",
      "coverage": "100%",
      "fix": "Fixed sd->sw bug in vector_testgen_common.py for RV32 SEW64",
      "timestamp": "2026-03-24 12:00:00"
    }
  }
}
```

**Status values:**
- `untested` — never attempted (will be picked up by runner)
- `completed` — 100% coverage achieved
- `failed` — attempted but couldn't reach 100% (issue documented)
- `error` — sub-Claude crashed/timed out
- `partial` — known limitation prevents full coverage

The runner picks up `untested`, `failed`, and `error` items.

### Sub-Claude Prompt

Each sub-Claude receives:
- The specific coverpoint name and category
- The exact workflow steps (isolate → build → diagnose → fix → verify → restore)
- The full contents of `knowledge.md` (pitfalls, patterns, known bugs)
- Instructions to update `progress.json` and restore testplans
- A cap on iterations to prevent spinning

### Safety

- **Testplan restoration**: The runner force-restores testplans after each sub-Claude finishes, even if the sub-Claude fails to do so
- **Progress preservation**: Sub-Claudes only update their own coverpoint entry — never delete others
- **Iteration cap**: Sub-Claudes stop after N failed build→fix cycles and document what they found

## What the Manager Claude Should Do

### Before launching

1. Read `progress.json` to understand current state
2. Check `coverage-status.md` for the latest summary
3. Run `--dry-run` to confirm what will be processed
4. Decide on budget (more complex coverpoints may need $5+, simple ones $2-3)

### While running

The script outputs progress to stdout. Each coverpoint shows:
- Launch status
- SUCCESS/FAILED result with coverage percentage
- Duration

### After completion

1. Read the updated `progress.json` to see results
2. Check `coverage-status.md` for the full table
3. For failed coverpoints, check `coverage_issues/<name>.md` for diagnostics
4. Report results to the user

### Handling failures

If a sub-Claude fails:
1. Check the `coverage_issues/` directory for diagnostic notes
2. You can retry a specific coverpoint: `--coverpoint <name>`
3. If it keeps failing, read the issue file and attempt manual diagnosis
4. Some coverpoints are known to be blocked (e.g., VlsCustom sail timeouts) — don't retry these

## Architecture Notes

- **Sequential processing**: Required because CSV isolation modifies shared `testplans/` and `Makefile`
- **Sub-Claude independence**: Each sub-Claude is a fresh `claude -p` invocation with no shared context
- **Knowledge propagation**: All learned patterns go into `knowledge.md`, which is injected into every sub-Claude's prompt. When you learn something new, update knowledge.md BEFORE the next runner invocation so all future sub-Claudes benefit.

## Files

| File | Purpose |
|------|---------|
| `coverage_runner.py` | This orchestrator script |
| `progress.json` | Machine-readable status for all coverpoints |
| `coverage-status.md` | Human-readable summary (updated after each run) |
| `knowledge.md` | Accumulated pitfalls and patterns (injected into prompts) |
| `coverage_issues/` | Per-coverpoint failure diagnostics |
