#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Launch Claude sub-processes to achieve 100% coverage on untested coverpoints.

Each sub-Claude gets a self-contained prompt with:
  - The exact coverpoint to work on
  - Commands for isolate → build → diagnose → fix → verify → restore
  - All accumulated knowledge about pitfalls and patterns
  - Instructions to update progress.json on completion

Usage:
    # Run all untested coverpoints sequentially
    python3 coverage_runner.py

    # Run a specific coverpoint
    python3 coverage_runner.py --coverpoint cp_custom_vfp_flags_nv_nx

    # Run all untested in a category
    python3 coverage_runner.py --category Vf

    # Dry run — show what would be launched
    python3 coverage_runner.py --dry-run

    # Set per-coverpoint budget
    python3 coverage_runner.py --max-budget 3.0

    # Set max iterations per coverpoint (build→diagnose→fix cycles)
    python3 coverage_runner.py --max-iterations 5
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[4]  # riscv-arch-test-cvw root
PROGRESS_FILE = SCRIPT_DIR / "progress.json"
KNOWLEDGE_FILE = SCRIPT_DIR / "knowledge.md"
COVERAGE_STATUS_FILE = SCRIPT_DIR / "coverage-status.md"

# Category → which CSV group and EFFEW suffixes
CATEGORY_MAP = {
    "VfCustom": "Vf",
    "VlsCustom": "Vls",
}


# ── Progress helpers ───────────────────────────────────────────────────────

def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {}


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2) + "\n")


def get_untested_coverpoints(progress: dict, category: str | None = None) -> list[tuple[str, str, dict]]:
    """Return list of (csv_group, coverpoint_name, entry) for untested/failed items."""
    results = []
    for csv_group, coverpoints in progress.items():
        if category and csv_group != category:
            continue
        cat = CATEGORY_MAP.get(csv_group)
        if not cat:
            continue
        for cp_name, entry in coverpoints.items():
            status = entry.get("status", "untested")
            if status in ("untested", "failed", "error"):
                results.append((csv_group, cp_name, entry))
    return results


# ── Prompt builder ─────────────────────────────────────────────────────────

def build_prompt(coverpoint_name: str, csv_group: str, category: str,
                 entry: dict, max_iterations: int) -> str:
    """Build the self-contained prompt for a sub-Claude."""

    # Load knowledge base
    knowledge = ""
    if KNOWLEDGE_FILE.exists():
        knowledge = KNOWLEDGE_FILE.read_text()

    prompt = f"""You are a coverage verification engineer working on RISC-V vector extension test coverage.

## Your Task

Achieve 100% coverage for coverpoint column **`{coverpoint_name}`** in the **{csv_group}** CSV.

**Category:** {category}
**CSV group:** {csv_group}
**Current status:** {entry.get("status", "untested")}

## Working Directory

All commands run from: `{REPO_ROOT}`

## Workflow (follow this exactly)

### Step 1: Read the guides
Read these files for essential context:
- `generators/testgen/scripts/custom/claude-scripts/knowledge.md` — pitfalls and patterns
- `generators/testgen/scripts/custom/GUIDE.md` — API reference for custom scripts

### Step 2: Isolate the coverpoint
```bash
python3 isolate_coverpoint.py {csv_group} {coverpoint_name}
```

### Step 3: Build and run coverage
```bash
make vector-testgen && make coverage
```

### Step 4: Analyze results
- If **build succeeds** and **100% coverage**: go to Step 6
- If **build fails**: read the error, find the source file causing it, fix it, go to Step 3
- If **coverage < 100%**: read the coverage report, check generated .S files, diagnose why bins are uncovered, fix the issue, go to Step 3

### Step 5: Diagnose and fix (up to {max_iterations} iterations)
When diagnosing failures:
1. **Build errors**: Read the error message carefully. Search for the pattern generating bad assembly in `generators/testgen/scripts/` using Grep. Common issues:
   - RV32 using RV64-only instructions (sd, ld) — fix the generator to use sw/lw when xlen=32
   - Missing data labels — check if custom data is registered properly
   - Register overlap — add try/except ValueError around randomizeVectorInstructionData calls

2. **Coverage gaps**: Check the generated .S test files in `tests/rv32i/{csv_group}*/` and `tests/rv64i/{csv_group}*/`. Verify:
   - The custom script (in `generators/testgen/scripts/custom/`) is generating the right test patterns
   - Coverage templates (in `generators/coverage/templates/`) are sampling the right fields
   - Data values match what the coverage bins expect

3. **Only modify files you understand**: Prefer targeted fixes. If you can't diagnose after {max_iterations} attempts, stop and document.

### Step 6: Update progress and restore

After achieving 100% (or exhausting iterations), update `{PROGRESS_FILE}`:

```python
import json
progress = json.loads(open("{PROGRESS_FILE}").read())
progress["{csv_group}"]["{coverpoint_name}"] = {{
    "status": "completed",  # or "failed" with details
    "coverage": "100%",     # or actual percentage
    "fix": "Brief description of what was fixed",
    "timestamp": "<current timestamp>"
}}
open("{PROGRESS_FILE}", "w").write(json.dumps(progress, indent=2) + "\\n")
```

Then restore testplans:
```bash
python3 isolate_coverpoint.py --restore {csv_group}
```

## Critical Rules

1. **ALWAYS restore testplans** when done, even if you fail. Run `python3 isolate_coverpoint.py --restore {csv_group}` as your last action.
2. **Do NOT modify files outside** `generators/testgen/scripts/` and `generators/coverage/templates/` unless the fix clearly requires it (e.g., a bug in vector_testgen_common.py).
3. **Stop after {max_iterations} failed iterations**. Write what you found to `{SCRIPT_DIR}/coverage_issues/{coverpoint_name}.md` and mark status as "failed" in progress.json.
4. **Never delete completed work** in progress.json — only update your own coverpoint's entry.
5. **Be efficient**: don't read massive files. Use Grep to find specific patterns. Read generated .S files only for the failing instruction.

## Knowledge Base

{knowledge}
"""
    return prompt


# ── Claude launcher ────────────────────────────────────────────────────────

def run_claude(prompt: str, max_budget_usd: float = 5.0,
               timeout_seconds: int = 1800) -> tuple[bool, str, float]:
    """Launch claude CLI with the given prompt.

    Returns: (success, output, duration_seconds)
    """
    cmd = [
        "claude",
        "-p", prompt,
        "--dangerously-skip-permissions",
        "--max-budget-usd", str(max_budget_usd),
    ]

    # Strip env vars that prevent nested Claude CLI sessions
    env = os.environ.copy()
    for key in ["CLAUDECODE", "CLAUDE_CODE_SSE_PORT", "CLAUDE_CODE_ENTRYPOINT"]:
        env.pop(key, None)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(REPO_ROOT),
            env=env,
        )
        duration = time.time() - start
        output = result.stdout + "\n---STDERR---\n" + result.stderr
        return result.returncode == 0, output, duration
    except subprocess.TimeoutExpired:
        return False, f"Claude CLI timed out after {timeout_seconds}s", time.time() - start
    except FileNotFoundError:
        return False, "Claude CLI not found. Ensure 'claude' is in PATH.", 0.0


# ── Safety: ensure testplans are restored ──────────────────────────────────

def force_restore():
    """Safety net: restore testplans from Python in case Claude didn't."""
    try:
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "isolate_coverpoint.py"), "--restore", "VfCustom"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=30
        )
    except Exception:
        pass


# ── Main orchestrator ──────────────────────────────────────────────────────

def process_coverpoint(csv_group: str, cp_name: str, entry: dict,
                       category: str, max_budget: float,
                       max_iterations: int, timeout: int) -> dict:
    """Process a single coverpoint by launching a Claude sub-process."""
    result = {
        "coverpoint": cp_name,
        "csv_group": csv_group,
        "status": "unknown",
        "duration_s": 0,
    }

    prompt = build_prompt(cp_name, csv_group, category, entry, max_iterations)

    print(f"  Launching Claude CLI (budget=${max_budget:.2f}, timeout={timeout}s)...")
    success, output, duration = run_claude(prompt, max_budget, timeout)
    result["duration_s"] = round(duration, 1)

    # Safety: always restore testplans
    force_restore()

    # Check if progress.json was updated by the sub-Claude
    updated_progress = load_progress()
    cp_entry = updated_progress.get(csv_group, {}).get(cp_name, {})
    new_status = cp_entry.get("status", "unknown")

    if new_status == "completed":
        result["status"] = "completed"
        result["coverage"] = cp_entry.get("coverage", "unknown")
        result["fix"] = cp_entry.get("fix", "")
        print(f"  SUCCESS: {cp_name} → {result['coverage']}")
    elif new_status == "failed":
        result["status"] = "failed"
        result["coverage"] = cp_entry.get("coverage", "unknown")
        print(f"  FAILED: {cp_name} → {result['coverage']}")
    else:
        # Sub-Claude didn't update progress — check output for clues
        result["status"] = "error" if not success else "unknown"
        result["output_tail"] = output[-1000:] if output else ""
        print(f"  {'ERROR' if not success else 'UNKNOWN'}: Claude {'failed' if not success else 'finished without updating progress'}")

        # Mark as failed in progress so we don't re-attempt without noticing
        if csv_group not in updated_progress:
            updated_progress[csv_group] = {}
        updated_progress[csv_group][cp_name] = {
            "status": "error",
            "coverage": "unknown",
            "fix": f"Sub-Claude {'timed out' if 'timed out' in output else 'did not update progress'}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_progress(updated_progress)

    return result


def update_status_file(results: list[dict]) -> None:
    """Update coverage-status.md with latest run results."""
    progress = load_progress()

    lines = ["# Coverage Work Status\n"]
    lines.append(f"## Last Run: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    if results:
        lines.append("### Results from this run\n")
        lines.append("| Coverpoint | Status | Coverage | Duration |")
        lines.append("|---|---|---|---|")
        for r in results:
            lines.append(f"| {r['coverpoint']} | {r['status']} | {r.get('coverage', 'N/A')} | {r['duration_s']}s |")
        lines.append("")

    for csv_group, coverpoints in progress.items():
        lines.append(f"### {csv_group}\n")
        lines.append("| Coverpoint | Status | Coverage |")
        lines.append("|---|---|---|")
        for cp_name, entry in coverpoints.items():
            status = entry.get("status", "untested")
            coverage = entry.get("coverage", "")
            lines.append(f"| {cp_name} | {status} | {coverage} |")
        lines.append("")

    lines.append("## Workflow Reminder\n")
    lines.append("1. `python3 coverage_runner.py` — run all untested coverpoints")
    lines.append("2. `python3 coverage_runner.py --coverpoint <name>` — run one specific")
    lines.append("3. `python3 coverage_runner.py --dry-run` — preview what would run")
    lines.append("")

    COVERAGE_STATUS_FILE.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Claude sub-processes to verify coverage on untested coverpoints"
    )
    parser.add_argument("--coverpoint", "-c", type=str, default=None,
                        help="Run a specific coverpoint (must exist in progress.json)")
    parser.add_argument("--category", type=str, default=None, choices=["VfCustom", "VlsCustom"],
                        help="Only process coverpoints in this CSV group")
    parser.add_argument("--max-budget", type=float, default=5.0,
                        help="Max budget in USD per Claude invocation (default: 5.0)")
    parser.add_argument("--max-iterations", type=int, default=5,
                        help="Max build→fix cycles per coverpoint (default: 5)")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="Timeout in seconds per Claude invocation (default: 1800)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be launched without running")
    args = parser.parse_args()

    progress = load_progress()

    # Determine what to process
    if args.coverpoint:
        # Find the specific coverpoint
        found = False
        for csv_group, coverpoints in progress.items():
            if args.coverpoint in coverpoints:
                category = CATEGORY_MAP.get(csv_group, "Vf")
                targets = [(csv_group, args.coverpoint, coverpoints[args.coverpoint])]
                found = True
                break
        if not found:
            print(f"ERROR: Coverpoint '{args.coverpoint}' not found in progress.json")
            print(f"Available: {[cp for cps in progress.values() for cp in cps]}")
            sys.exit(1)
    else:
        targets = get_untested_coverpoints(progress, args.category)

    if not targets:
        print("No untested coverpoints found. All done!")
        return

    print(f"Found {len(targets)} coverpoint(s) to process:")
    for csv_group, cp_name, entry in targets:
        status = entry.get("status", "untested")
        print(f"  [{csv_group}] {cp_name} ({status})")

    if args.dry_run:
        print("\n--- DRY RUN — no Claude processes launched ---")
        return

    print(f"\nSettings: budget=${args.max_budget:.2f}/cp, iterations={args.max_iterations}, timeout={args.timeout}s")
    print("=" * 70)

    # Process sequentially (isolation requires exclusive testplan access)
    results = []
    for i, (csv_group, cp_name, entry) in enumerate(targets):
        category = CATEGORY_MAP.get(csv_group, "Vf")
        print(f"\n[{i + 1}/{len(targets)}] {csv_group}/{cp_name}")

        result = process_coverpoint(
            csv_group, cp_name, entry, category,
            args.max_budget, args.max_iterations, args.timeout
        )
        results.append(result)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    completed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] in ("failed", "error", "unknown"))
    total_time = sum(r["duration_s"] for r in results)
    print(f"  Completed: {completed}/{len(results)}")
    print(f"  Failed:    {failed}/{len(results)}")
    print(f"  Total time: {total_time:.0f}s ({total_time / 60:.1f}m)")

    for r in results:
        status_icon = "OK" if r["status"] == "completed" else "FAIL"
        print(f"  [{status_icon}] {r['coverpoint']}: {r.get('coverage', 'N/A')} ({r['duration_s']}s)")

    # Update status file
    update_status_file(results)
    print(f"\nStatus file updated: {COVERAGE_STATUS_FILE}")


if __name__ == "__main__":
    main()
