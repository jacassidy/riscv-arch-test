# Vector Coverage Workflow Guide

## Purpose

This guide covers the end-to-end workflow for working on vector custom coverpoints:
isolating a coverpoint → building/running coverage → reading results → fixing scripts/templates.

### What to read and when

| When                                         | Read                                                                     |
| -------------------------------------------- | ------------------------------------------------------------------------ |
| Checking progress / planning next coverpoint | This file + `claude-scripts/progress.json` — nothing else                |
| Writing or debugging a test script           | `CLAUDE-custom-testgen.md` + `claude-scripts/knowledge.md`               |
| Writing or debugging a coverage template     | `generators/coverage/templates/GUIDE.md` + `claude-scripts/knowledge.md` |

Do NOT read GUIDE.md, knowledge.md, or template files when the task is only to check progress or plan the next step.

---

## Directory Map

| Path                                                                | Role                                                                    |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `generators/testgen/scripts/custom/`                                | Custom cp\_\*.py scripts + this guide + CLAUDE-custom-testgen.md        |
| `generators/testgen/scripts/custom/claude-scripts/`                 | Automation tools, progress tracking, knowledge base                     |
| `generators/testgen/scripts/custom/claude-scripts/coverage_issues/` | Per-coverpoint `.md` files for blocked/unresolved coverage problems     |
| `working-testplans/`                                                | CSV definitions, norm mappings, and helper scripts                      |
| `working-testplans/duplicates/`                                     | Canonical backups of CSVs (VfCustom-save.csv, VlsCustom-save.csv, etc.) |
| `testplans/`                                                        | Live CSV testplans consumed by the framework (do NOT edit manually)     |
| `generators/coverage/templates/vector/`                             | `.sv` coverage templates (one per coverpoint)                           |
| `work/sail-rv64-max/reports/`                                       | Coverage report output for RV64 sail sim                                |
| `work/sail-rv32-max/reports/`                                       | Coverage report output for RV32 sail sim                                |

---

## Step 1: Isolation

Before running coverage for a single coverpoint, isolate it so only that column is active.

```bash
# Isolate one column (strips all other cp_custom columns, removes unrelated rows)
python3 isolate_coverpoint.py <Category> <cp_column_name>
# Example:
python3 isolate_coverpoint.py VfCustom cp_custom_vfp_flags

# Restore from canonical backup when done
python3 isolate_coverpoint.py --restore VfCustom
```

`isolate_coverpoint.py` is at the repo root. It:

1. Reads the canonical backup from `working-testplans/duplicates/<Category>-save.csv`
2. Strips all rows that don't have `x` in the target column
3. Strips all other `cp_custom_*` columns
4. Writes the isolated CSV to `testplans/<Category>.csv`
5. Updates `Makefile` EXTENSIONS line to only the relevant SEW categories

**Always restore** (`--restore`) before isolating a different coverpoint, or the live CSV stays in its stripped state.

### Manual Makefile EXTENSIONS

If `isolate_coverpoint.py` doesn't update the Makefile automatically, set EXTENSIONS manually:

- **VfCustom**: `VfCustom16,VfCustom32,VfCustom64`
- **VlsCustom**: `VlsCustom8,VlsCustom16,VlsCustom32,VlsCustom64`
- **All categories**: `VfCustom16,VfCustom32,VfCustom64,VlsCustom8,VlsCustom16,VlsCustom32,VlsCustom64`

---

## Step 2: Build and Run Coverage

```bash
make clean && make vector-tests && make coverage
```

- `make clean` — removes ALL generated tests AND covergroup files. Must use this (not `make clean-tests`) because covergroups must also be regenerated.
- `make vector-tests` — generates `.S` test files (`vector-testgen`) AND covergroup `.sv` files (`covergroupgen`). Run this, not `make vector-testgen` alone, unless you only want to regen test assembly.
- `make coverage` — compiles ELFs and runs sail simulation, then generates reports. **Do NOT use `-j16` here when debugging** — sequential mode stops on first failure and makes errors easy to read.

**Timing**: ~15 min per test file with sail. Expect:

- Small coverpoints (1–3 instructions): ~15–45 min
- Large coverpoints (101 instructions like cp_custom_vfp_NaN_input): ~10 hours

Reports land in:

- `work/sail-rv64-max/reports/` — RV64 results
- `work/sail-rv32-max/reports/` — RV32 results

---

## Step 3: Reading Coverage Reports

**Reading order**: `progress.json` → `_overall_summary.txt` (for high-level %) → targeted greps on `*_uncovered.txt`. Do NOT read report or uncovered files wholesale — they are thousands of lines.

### Report files

```
work/sail-rv64-max/reports/
  VfCustom16_report.txt        # Full report — do not read directly
  VfCustom32_report.txt        # Full report — do not read directly
  VfCustom64_report.txt        # Full report — do not read directly
  VfCustom16_uncovered.txt     # Uncovered bins only — use grep (see below)
  _overall_summary.txt         # High-level % per covergroup — safe to read
work/sail-rv32-max/reports/    # Same structure for RV32
```

If `<Category><SEW>_uncovered.txt` is absent, that SEW achieved 100% coverage.

### coverage_summary.py — use this first, not grep or file reads

`claude-scripts/coverage_summary.py` is the right tool for reading coverage state. Run from repo root.

```bash
# All instructions, compact table (SEW columns), sorted 0% first
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py

# Same but only show instructions not yet at 100%
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --uncovered

# Which specific bins are ZERO for one instruction (across all SEWs and rv32/rv64)
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --bins vfadd.vv
```

Output:

- `!` prefix = instruction at 0% (no tests generated or all fail)
- `???` = truncated line in report (line was too long for the reporter to print %)
- `n/a` = that SEW doesn't exist for this category
- `--bins` output groups missing bins by coverpoint name so you can see exactly what to fix

**Use `--uncovered` for planning. Use `--bins <inst>` before editing a script.**

### Reading uncovered.txt — use grep, not full reads

The uncovered files are large. **Never read them wholesale.** Use targeted greps to extract what you need:

```bash
# 1. Which instructions are fully zero (no coverage at all)?
grep -E "obj_VfCustom(16|32|64)_.*0\.00%" work/sail-rv64-max/reports/VfCustom16_uncovered.txt | grep "0\.00%" | head -30

# 2. Which bins are missing for a specific coverpoint across all instructions?
grep -A2 "cp_custom_vfp_flags_set" work/sail-rv64-max/reports/VfCustom16_uncovered.txt | grep "bin "

# 3. Quick per-instruction summary (instruction name + overall %)
grep -E "obj_VfCustom[0-9]+_" work/sail-rv64-max/reports/VfCustom16_uncovered.txt | grep -oP "obj_\S+\s+[\d.]+%"

# 4. Which specific bins are ZERO across the whole file?
grep "ZERO" work/sail-rv64-max/reports/VfCustom16_uncovered.txt | grep "bin " | sort -u

# 5. Check the same for RV32:
grep "ZERO" work/sail-rv32-max/reports/VfCustom16_uncovered.txt | grep "bin " | sort -u
```

Key things to look for:

- **`cp_asm_count` at 0%**: The instruction generated NO test cases — script returned early (sew > xlen guard, or instruction in NO_FLAG set)
- **`std_vec` at 0%**: Same — no tests generated at all for this instruction
- **Flag bins (NV/DZ/OF/UF/NX) at ZERO**: Script not generating inputs that trigger those flags for that instruction
- **`X1` bins (NV1/DZ1/NX1 etc.) at ZERO**: Transition "stays set" bin — the framework clears fflags (via `fsflagsi`) before each test case, so `SAMPLE_AFTER[i]` reflects only what test i produced from a clean state. To cover `NX1` (NX stays 1→1), you need **two consecutive NX-setting tests**: `SAMPLE_AFTER[i]=NX`, `SAMPLE_AFTER[i+1]=NX` → transition `(????1 => ????1)` ✓. Single tests only cover the `0→1` bin, not the `1→1` stays-set bin.
- **`mask_enabled`, `vfsqrt_flag_set`, `v0_element_1_active` all ZERO**: `cp_custom_vfp_flags_inactive_not_set` cross will be 0% — the masked test for that instruction hasn't run
- **Cross at 0% but coverpoints non-zero**: Conditions never fire simultaneously — fix the script to exercise them together

---

## Step 4: Fixing Scripts and Templates

### What to fix

After reading uncovered.txt, identify whether the issue is in:

1. **The test generation script** (`cp_custom_*.py`) — wrong data, missing edge cases
2. **The coverage template** (`generators/coverage/templates/vector/cp_custom_*.sv`) — wrong register field, wrong bin values, wrong CSR name

### Script fix pattern

Read `CLAUDE-custom-testgen.md` for the API. Read `claude-scripts/knowledge.md` for common pitfalls. After fixing:

- Re-run `make clean && make vector-tests && make coverage`
- Compare new report to old report

### Template fix pattern

Templates are `.sv` files in `generators/coverage/templates/vector/`. Common bugs:

- `ins.current.vs1` should be `ins.current.vs2` for VVM unary ops (vfrsqrt7, vfrec7, vfsqrt, vfclass)
- `get_vr_element_zero()` gets element 0 at OUTPUT SEW — for narrowing ops, use `ins.current.vs2_val[63:0]` directly
- `get_csr_val(...)` with `"frm", "frm"` returns 0 — use `"fcsr", "frm"` instead
- Bin values in templates must match actual data generated by the script (verify in generated `.S` file)
- **NEVER use `ins.current.insn == "some_mnemonic"` in a coverpoint.** `ins.current.insn` is the raw 32-bit instruction encoding, not a string. The comparison is always false. The framework already routes to the correct per-instruction covergroup — no identity check is needed. If you need to check the _previous_ instruction, use `ins.prev.inst_name` (a string, as done in `cp_custom_sc.sv`).
- `v0_element_1_active` coverpoints testing "inactive element" scenarios must use `bins target = {0}` (inactive = mask bit 0), not `{1}` (active).

### When coverage is unexpectedly 0% or stuck

1. Read the generated `.S` file for a small test: `tests/rv64i/VfCustom32/VfCustom32-<instruction>.S`
2. Check: are the right instructions present? correct register fields? correct data values?
3. Read the template `.sv` to see what conditions it checks
4. If you can't figure it out after 2 attempts, write a note to `claude-scripts/coverage_issues/<coverpoint_name>.md` and stop — a human will review it

---

## Automation Tools

All tools are in `generators/testgen/scripts/custom/claude-scripts/`.

### coverage_summary.py — Quick read of coverage state

```bash
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --uncovered
python3 generators/testgen/scripts/custom/claude-scripts/coverage_summary.py --bins <instruction>
```

Use this at the start of any session to see current state without reading raw report files.

### orchestrator.py — Fully automated multi-coverpoint loop

```bash
# Process all Vf coverpoints
python3 orchestrator.py --category Vf

# Process specific range (0-indexed)
python3 orchestrator.py --category Vf --start 0 --end 5

# Resume from last completed
python3 orchestrator.py --category Vf --resume

# Dry run (show what would be processed)
python3 orchestrator.py --category Vf --dry-run
```

Orchestrator reads the definitions CSV, launches a Claude CLI subprocess for each coverpoint, runs coverage, and iterates. Uses `progress.json` to track status. Can be interrupted and resumed.

### run_coverage.py — Single coverpoint coverage run

```bash
# Run coverage for one coverpoint (handles isolation + build + restore)
python3 claude-scripts/run_coverage.py cp_custom_vfp_flags Vf
python3 claude-scripts/run_coverage.py cp_custom_masked_v0_operand Vls
```

Handles the full isolate → build → run → restore cycle. Returns structured JSON result.

### coverage_parser.py — Parse coverage reports

Parses `*_report.txt` and `*_uncovered.txt` files into structured Python dicts. Used by orchestrator and run_coverage internally. Also useful for manual analysis (see Step 3 above).

---

## Progress Tracking

### progress.json

`claude-scripts/progress.json` tracks per-coverpoint status:

```json
{
  "cp_custom_vfp_flags": {
    "status": "completed",
    "coverage": "100%",
    "timestamp": "2026-02-25 04:25:00"
  },
  "cp_custom_vfredosum_NAN_vl0": {
    "status": "blocked",
    "coverage": "55.55%",
    "timestamp": "2026-03-01 12:00:00"
  }
}
```

Valid statuses: `completed`, `in_progress`, `blocked`, `not_started`.

### coverage_status.csv

`claude-scripts/coverage_status.csv` provides a flat summary across all coverpoints for quick review.

---

## SELF-MAINTENANCE RULE — Keep This Guide Current

**Whenever a new script, tool, directory, or workflow step is added that is part of the vector coverage pipeline, update this guide before finishing.**

This applies to:

- New automation scripts in `claude-scripts/` (add to the Automation Tools section)
- New directory locations relevant to coverage (add to Directory Map)
- New build commands or make targets (add to Step 2)
- New categories (e.g., a new extension beyond VfCustom/VlsCustom) (add to Isolation section)
- New report locations or formats (add to Step 3)

Do NOT add low-level script details or specific bin values here — those belong in `knowledge.md`. This guide covers **what exists and how to invoke it**. `knowledge.md` covers **why things work and what can go wrong**.

---

## knowledge.md — MUST Update When You Learn Something New

`claude-scripts/knowledge.md` is the persistent knowledge base for this project. It contains:

- Common pitfalls (e.g., `vs1` vs `vs2` for unary ops, SEW > XLEN guard)
- Known bug patterns (e.g., RVVI fsflagsi CSR alias, `vs2_val` vs `vs2_val_pointer`)
- Per-coverpoint coverage outcomes and explanations

**Rule**: If you discover a new pattern, fix, or pitfall that isn't already in `knowledge.md`, add it before finishing your session. The next Claude instance will read this file and must not repeat your mistakes.

---

## Definitions CSVs (Source of Truth for Goals)

`working-testplans/Vf_custom_definitions.csv` and `working-testplans/Vls_custom_definitions.csv` define what each custom coverpoint is supposed to test:

- **coverpoint name** (matches CSV column in testplans/)
- **goal** — what architectural behavior is being tested
- **bins** — expected coverage bins
- **notes** — implementation notes, known issues

Read the relevant definitions CSV row before writing or debugging a script to understand what the coverpoint is meant to exercise.

---

## Known Limitations

### VlsCustom: Sail timeout

All VlsCustom test files are ~4300 lines due to `SIGUPD_COUNT 50000`. Sail consistently times out even at 600s, even for files with only 1–2 test cases. **VlsCustom coverpoints are intended for RTL (Wally) simulation only, not sail.** Do not attempt to debug coverage failures for VlsCustom using sail results.

### Cross bin saturation

Some crosses require many combinations (e.g., 32 vd registers × 4 LMULs = 128 bins). Sail can handle ~35 test cases per file before running out of simulation headroom. Scripts optimized for sail hit ~85% on the cross, with full coverage deferred to RTL sim.

### writeTest(vl=0) prevents data loading

When `writeTest(vl=0)` is used, VL=0 is set **before** vector register loads (`vle*.v`). Since loads respect VL, they load 0 elements. Pre-loading vs1/vs2 data for VL=0 tests is impossible with the current framework.

### RVVI fsflagsi CSR alias

`fsflagsi` writes CSR 001 (fflags) but NOT CSR 003 (fcsr). Templates using `get_csr_val("fcsr", "fflags")` see stale values. Fix: add spacer tests using non-flag-setting inputs after flag-setting FP instructions to force CSR 003 to be written with 0. See `knowledge.md` for details.

---

## Quick Reference: Full Cycle for One Coverpoint

```bash
# 1. Isolate
python3 isolate_coverpoint.py VfCustom cp_custom_vfp_flags

# 2. Build and run coverage
make clean && make vector-tests && make coverage

# 3. Read results
cat work/sail-rv64-max/reports/VfCustom16_uncovered.txt
cat work/sail-rv32-max/reports/VfCustom16_uncovered.txt

# 4. Fix script or template, then repeat steps 2-3

# 5. Restore CSV when done
python3 isolate_coverpoint.py --restore VfCustom

# 6. Update knowledge.md with anything new learned
```
