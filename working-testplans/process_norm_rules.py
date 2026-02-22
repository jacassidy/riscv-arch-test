#!/usr/bin/env python3
"""
Process normative rule ↔ coverpoint pairings by launching fresh Claude instances.

Phase 1: For each coverpoint CSV row, match it to normative rules.
Phase 2: For each normative rule, assess coverage completeness.

Each row is processed by a completely independent Claude session.

Usage:
    python process_norm_rules.py --phase 1 [options]
    python process_norm_rules.py --phase 2 [options]

Examples:
    python process_norm_rules.py --phase 1                    # Phase 1: all rows in all coverpoint CSVs
    python process_norm_rules.py --phase 1 --line 5           # Phase 1: only line 5
    python process_norm_rules.py --phase 1 --start 5 --end 10 # Phase 1: lines 5-10
    python process_norm_rules.py --phase 2                    # Phase 2: all normative rules
    python process_norm_rules.py --phase 2 --line 3           # Phase 2: only norm rule on line 3
    python process_norm_rules.py --dry-run --phase 1          # Show what would be processed
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

# ===== USER CONFIGURATION =====
NORM_CSV = ""  # e.g. "norm_rules.csv" - normative rule CSV in working-testplans/
COVERPOINT_CSVS = []  # e.g. ["Vector - SsstrictV.csv", "Vx.csv"] - coverpoint CSVs
# ===============================

WORKING_TESTPLANS = Path(__file__).parent
REPO_ROOT = WORKING_TESTPLANS.parent


# ---------------------------------------------------------------------------
# CSV I/O helpers
# ---------------------------------------------------------------------------


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    """Read CSV, return (fieldnames, rows). Each row dict has '_line_number'."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = []
        for i, row in enumerate(reader, start=2):  # line 1 = header
            row["_line_number"] = i
            rows.append(row)
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    """Write rows back to CSV, stripping internal '_' keys."""
    clean_fields = [f for f in fieldnames if not f.startswith("_")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=clean_fields)
        writer.writeheader()
        for row in rows:
            clean_row = {k: v for k, v in row.items() if not k.startswith("_")}
            writer.writerow(clean_row)


def resolve_csv_path(name: str) -> Path:
    """Resolve a CSV name to a full path in working-testplans/."""
    p = WORKING_TESTPLANS / name
    if p.exists():
        return p
    # Try adding .csv
    p2 = WORKING_TESTPLANS / f"{name}.csv"
    if p2.exists():
        return p2
    return p  # return original, caller checks existence


def get_field(row: dict, *candidates: str) -> str:
    """Get field value trying multiple possible column names (case-insensitive partial match)."""
    for candidate in candidates:
        for key in row:
            if key.startswith("_"):
                continue
            if candidate.lower() in key.lower():
                val = (row[key] or "").strip()
                if val:
                    return val
    return ""


# ---------------------------------------------------------------------------
# Normative rule CSV helpers
# ---------------------------------------------------------------------------


def read_norm_csv() -> tuple[Path, list[str], list[dict]]:
    """Read the normative rule CSV. Returns (path, fieldnames, rows)."""
    path = resolve_csv_path(NORM_CSV)
    if not path.exists():
        print(f"ERROR: Normative rule CSV not found: {path}")
        sys.exit(1)
    fieldnames, rows = read_csv(path)
    return path, fieldnames, rows


def get_norm_name(row: dict) -> str:
    """Extract normative rule name from row."""
    return get_field(row, "name", "rule", "norm")


def get_norm_description(row: dict) -> str:
    """Extract normative rule description/spec text from row."""
    return get_field(row, "description", "spec", "text", "quote")


def get_existing_coverpoint_pairs(row: dict) -> list[tuple[str, str]]:
    """Extract existing (cp_name, coverage_desc) pairs from a norm rule row."""
    pairs = []
    i = 1
    while True:
        cp_key = f"cp_name_{i}"
        desc_key = f"coverage_desc_{i}"
        cp_val = row.get(cp_key, "").strip()
        desc_val = row.get(desc_key, "").strip()
        if not cp_val and not desc_val:
            break
        if cp_val:
            pairs.append((cp_val, desc_val))
        i += 1
    return pairs


def add_coverpoint_to_norm_row(
    norm_path: Path,
    fieldnames: list[str],
    rows: list[dict],
    norm_rule_name: str,
    cp_name: str,
    coverage_desc: str,
):
    """Add a (cp_name, coverage_desc) column pair to a norm rule row.

    Mutates fieldnames and the matching row in-place. Does NOT write to disk.
    """
    for row in rows:
        if get_norm_name(row) != norm_rule_name:
            continue
        # Find next available pair index
        i = 1
        while f"cp_name_{i}" in row and row[f"cp_name_{i}"].strip():
            # Skip if this exact cp_name already recorded
            if row[f"cp_name_{i}"].strip() == cp_name:
                return  # duplicate
            i += 1
        cp_key = f"cp_name_{i}"
        desc_key = f"coverage_desc_{i}"
        # Ensure columns exist
        for key in (cp_key, desc_key):
            if key not in fieldnames:
                fieldnames.append(key)
        row[cp_key] = cp_name
        row[desc_key] = coverage_desc
        return


def set_coverage_status(
    rows: list[dict],
    fieldnames: list[str],
    norm_rule_name: str,
    status: str,
    explanation: str,
    gaps: list[str],
):
    """Set coverage_status, explanation, gaps columns on a norm rule row (in-place)."""
    for col in ("coverage_status", "explanation", "gaps"):
        if col not in fieldnames:
            fieldnames.append(col)
    for row in rows:
        if get_norm_name(row) != norm_rule_name:
            continue
        row["coverage_status"] = status
        row["explanation"] = explanation
        row["gaps"] = "; ".join(gaps) if gaps else ""
        return


# ---------------------------------------------------------------------------
# Coverpoint CSV helpers
# ---------------------------------------------------------------------------


def add_norm_rules_to_cp_row(
    cp_path: Path,
    fieldnames: list[str],
    rows: list[dict],
    line_number: int,
    norm_rule_names: list[str],
):
    """Append norm rule names to the 'normative rules' column of a coverpoint row.

    Mutates fieldnames and the matching row in-place. Does NOT write to disk.
    """
    col = "normative rules"
    if col not in fieldnames:
        fieldnames.append(col)
    for row in rows:
        if row.get("_line_number") != line_number:
            continue
        existing = (row.get(col) or "").strip()
        existing_set = set(x.strip() for x in existing.split(";") if x.strip())
        for name in norm_rule_names:
            existing_set.add(name)
        row[col] = "; ".join(sorted(existing_set))
        return


def format_coverpoint_row(row: dict) -> str:
    """Format a coverpoint row's data for the Claude prompt."""
    parts = []
    for key, val in row.items():
        if key.startswith("_"):
            continue
        val = (val or "").strip()
        if val:
            parts.append(f"  - {key}: {val}")
    return "\n".join(parts)


def format_active_coverpoints(row: dict) -> str:
    """List column headers marked with 'x' or a variant name (coverpoint columns)."""
    active = []
    for key, val in row.items():
        if key.startswith("_"):
            continue
        val = (val or "").strip().lower()
        if val in ("x", "yes", "1") or (val and val not in ("", "no", "0", "n/a")):
            # Skip metadata columns
            skip = (
                "sr no",
                "goal",
                "feature",
                "expectation",
                "spec",
                "bins",
                "instruction",
                "type",
                "rv32",
                "rv64",
                "description",
                "name",
                "normative",
            )
            if not any(s in key.lower() for s in skip):
                active.append(key)
    return ", ".join(active) if active else "(none detected)"


# ---------------------------------------------------------------------------
# Claude launching
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict | None:
    """Extract the first JSON object from Claude's output."""
    # Try to find JSON block in markdown code fence
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Try to find bare JSON object
    m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    # Try the whole output
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def launch_claude(prompt: str, dry_run: bool = False) -> dict | None:
    """Launch Claude with a prompt, return parsed JSON or None."""
    if dry_run:
        print(f"[DRY RUN] Would send prompt ({len(prompt)} chars):\n{prompt[:300]}...")
        return None

    try:
        result = subprocess.run(
            ["claude", "--dangerously-skip-permissions", prompt],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        output = result.stdout or ""
        if result.returncode != 0:
            print(f"  Claude exited with code {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")

        parsed = extract_json(output)
        if parsed is None:
            print("  WARNING: Could not parse JSON from Claude output")
            print(f"  Raw output (first 500 chars): {output[:500]}")
        return parsed

    except FileNotFoundError:
        print("ERROR: 'claude' command not found. Is Claude Code CLI installed?")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR launching Claude: {e}")
        return None


# ---------------------------------------------------------------------------
# Phase 1: Coverpoint → Normative Rule matching
# ---------------------------------------------------------------------------


def build_phase1_prompt(row: dict, norm_rules: list[dict]) -> str:
    """Build the Phase 1 prompt for a single coverpoint row."""
    instruction = get_field(row, "instruction", "sr no", "name")
    goal = get_field(row, "goal")
    feature_desc = get_field(row, "feature description", "description")
    expectation = get_field(row, "expectation")
    active_cps = format_active_coverpoints(row)

    # Format all normative rules
    rules_text = []
    for nr in norm_rules:
        name = get_norm_name(nr)
        desc = get_norm_description(nr)
        if name:
            rules_text.append(f"- {name}: {desc}")
    rules_block = "\n".join(rules_text)

    return f"""You are a normative rule matcher. Read the coverpoint information below and match it to normative rules.

COVERPOINT ROW:
- Instruction: {instruction}
- Goal: {goal}
- Feature Description: {feature_desc}
- Expectation: {expectation}
- Active coverpoints: {active_cps}

FULL ROW DATA:
{format_coverpoint_row(row)}

NORMATIVE RULES:
{rules_block}

For each normative rule that is AT LEAST PARTIALLY covered by any aspect of this
coverpoint row, output a JSON match. Be inclusive - if any part of the coverpoint
tests any part of the normative rule, include it.

The coverage_description should briefly explain HOW the coverpoint covers the rule.

Output ONLY valid JSON (no markdown, no explanation outside the JSON):
{{"matches": [{{"norm_rule_name": "...", "coverage_description": "..."}}]}}

If no rules match, output: {{"matches": []}}"""


def run_phase1(args):
    """Run Phase 1: match coverpoint rows to normative rules."""
    norm_path, norm_fields, norm_rows = read_norm_csv()
    print(f"Loaded {len(norm_rows)} normative rules from {NORM_CSV}")

    # Process each coverpoint CSV
    for cp_csv_name in COVERPOINT_CSVS:
        cp_path = resolve_csv_path(cp_csv_name)
        if not cp_path.exists():
            print(f"WARNING: Coverpoint CSV not found: {cp_path}, skipping")
            continue

        cp_fields, cp_rows = read_csv(cp_path)
        print(f"\nProcessing coverpoint CSV: {cp_csv_name} ({len(cp_rows)} rows)")

        # Filter rows by line range
        rows_to_process = filter_rows(cp_rows, args)
        print(f"Rows to process: {len(rows_to_process)}")

        success = 0
        fail = 0

        for row in rows_to_process:
            line_num = row["_line_number"]
            row_name = get_field(row, "sr no", "instruction", "name") or f"line {line_num}"
            print(f"\n{'=' * 60}")
            print(f"Phase 1 - {cp_csv_name} line {line_num}: {row_name}")
            print(f"{'=' * 60}")

            prompt = build_phase1_prompt(row, norm_rows)
            result = launch_claude(prompt, dry_run=args.dry_run)

            if args.dry_run:
                success += 1
                continue

            if result is None:
                fail += 1
                continue

            matches = result.get("matches", [])
            print(f"  Found {len(matches)} matches")

            matched_norm_names = []
            for match in matches:
                norm_name = match.get("norm_rule_name", "")
                cov_desc = match.get("coverage_description", "")
                if not norm_name:
                    continue
                print(f"    -> {norm_name}: {cov_desc[:80]}")
                # Update norm CSV in memory
                add_coverpoint_to_norm_row(
                    norm_path,
                    norm_fields,
                    norm_rows,
                    norm_name,
                    row_name,
                    cov_desc,
                )
                matched_norm_names.append(norm_name)

            # Update coverpoint CSV in memory
            if matched_norm_names:
                add_norm_rules_to_cp_row(
                    cp_path,
                    cp_fields,
                    cp_rows,
                    line_num,
                    matched_norm_names,
                )

            success += 1

        if not args.dry_run:
            # Write updated coverpoint CSV
            write_csv(cp_path, cp_fields, cp_rows)
            print(f"\nUpdated {cp_csv_name}")

        print(f"Phase 1 results for {cp_csv_name}: {success} succeeded, {fail} failed")

    if not args.dry_run:
        # Write updated norm CSV
        write_csv(norm_path, norm_fields, norm_rows)
        print(f"\nUpdated {NORM_CSV}")


# ---------------------------------------------------------------------------
# Phase 2: Coverage completeness check
# ---------------------------------------------------------------------------


def build_phase2_prompt(norm_row: dict) -> str:
    """Build the Phase 2 prompt for a single normative rule."""
    name = get_norm_name(norm_row)
    desc = get_norm_description(norm_row)
    pairs = get_existing_coverpoint_pairs(norm_row)

    if not pairs:
        pairs_text = "(No coverpoints paired to this rule)"
    else:
        pairs_text = "\n".join(f"- {cp}: {cdesc}" for cp, cdesc in pairs)

    return f"""You are a coverage completeness checker.

NORMATIVE RULE:
- Name: {name}
- Spec text: {desc}

COVERPOINTS PAIRED TO THIS RULE:
{pairs_text}

Determine if this normative rule is FULLY covered by the listed coverpoints.
- "full": Every aspect of the spec text is tested by at least one coverpoint
- "partial": Some aspects are tested but gaps remain
- "none": No meaningful coverage despite pairings (or no pairings at all)

Output ONLY valid JSON (no markdown, no explanation outside the JSON):
{{"coverage_status": "full|partial|none", "explanation": "...", "gaps": ["gap1", "gap2"]}}

Use an empty list for gaps if coverage is full: {{"coverage_status": "full", "explanation": "...", "gaps": []}}"""


def run_phase2(args):
    """Run Phase 2: assess coverage completeness for each normative rule."""
    norm_path, norm_fields, norm_rows = read_norm_csv()
    print(f"Loaded {len(norm_rows)} normative rules from {NORM_CSV}")

    rows_to_process = filter_rows(norm_rows, args)
    print(f"Rules to process: {len(rows_to_process)}")

    success = 0
    fail = 0

    for row in rows_to_process:
        line_num = row["_line_number"]
        name = get_norm_name(row)
        if not name:
            continue

        print(f"\n{'=' * 60}")
        print(f"Phase 2 - line {line_num}: {name}")
        print(f"{'=' * 60}")

        pairs = get_existing_coverpoint_pairs(row)
        print(f"  Has {len(pairs)} paired coverpoints")

        prompt = build_phase2_prompt(row)
        result = launch_claude(prompt, dry_run=args.dry_run)

        if args.dry_run:
            success += 1
            continue

        if result is None:
            fail += 1
            continue

        status = result.get("coverage_status", "unknown")
        explanation = result.get("explanation", "")
        gaps = result.get("gaps", [])

        print(f"  Status: {status}")
        print(f"  Explanation: {explanation[:120]}")
        if gaps:
            print(f"  Gaps: {gaps}")

        set_coverage_status(norm_rows, norm_fields, name, status, explanation, gaps)
        success += 1

    if not args.dry_run:
        write_csv(norm_path, norm_fields, norm_rows)
        print(f"\nUpdated {NORM_CSV}")

    print(f"\nPhase 2 results: {success} succeeded, {fail} failed")


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------


def filter_rows(rows: list[dict], args) -> list[dict]:
    """Filter rows by --line, --start, --end arguments."""
    if args.line is not None:
        return [r for r in rows if r["_line_number"] == args.line]
    if args.start is not None:
        if args.end is not None:
            return [r for r in rows if args.start <= r["_line_number"] <= args.end]
        return [r for r in rows if r["_line_number"] >= args.start]
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Process normative rule ↔ coverpoint pairings with fresh Claude instances"
    )
    parser.add_argument(
        "--phase",
        type=int,
        required=True,
        choices=[1, 2],
        help="Phase 1: match coverpoints to norm rules. Phase 2: check completeness.",
    )
    parser.add_argument("--start", type=int, help="Start line number")
    parser.add_argument("--end", type=int, help="End line number (inclusive, use with --start)")
    parser.add_argument("--line", type=int, help="Process only this single line")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed")

    args = parser.parse_args()

    # Validate configuration
    if not NORM_CSV:
        print("ERROR: NORM_CSV is not configured. Edit the USER CONFIGURATION section at the top of this script.")
        sys.exit(1)
    if not COVERPOINT_CSVS and args.phase == 1:
        print(
            "ERROR: COVERPOINT_CSVS is not configured. Edit the USER CONFIGURATION section at the top of this script."
        )
        sys.exit(1)

    if args.phase == 1:
        run_phase1(args)
    else:
        run_phase2(args)


if __name__ == "__main__":
    main()
