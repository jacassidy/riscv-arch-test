#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Isolate a single coverpoint column in a testplan CSV for coverage testing.

Copies the canonical backup from working-testplans/duplicates/, then strips
the CSV down to only the rows and columns relevant to the target coverpoint.
Rows without an 'x' in the target column are deleted. All other cp_custom_*
columns are removed entirely.

Usage:
    python3 isolate_coverpoint.py VfCustom cp_custom_vfp_state
    python3 isolate_coverpoint.py VlsCustom cp_custom_maskLS
    python3 isolate_coverpoint.py --restore VfCustom   # restore from backup
"""

import argparse
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTPLANS = ROOT / "testplans"
DUPLICATES = ROOT / "working-testplans" / "duplicates"


def get_backup_path(csv_name: str) -> Path:
    """Find the canonical backup in duplicates/."""
    name = csv_name if csv_name.endswith(".csv") else f"{csv_name}.csv"
    # Backups are named like VfCustom-save.csv
    backup = DUPLICATES / name.replace(".csv", "-save.csv")
    if not backup.exists():
        # Try exact name
        backup = DUPLICATES / name
    return backup


def restore(csv_name: str) -> None:
    """Restore a CSV from its canonical backup."""
    name = csv_name if csv_name.endswith(".csv") else f"{csv_name}.csv"
    live = TESTPLANS / name
    backup = get_backup_path(csv_name)

    if not backup.exists():
        print(f"ERROR: No backup found at {backup}")
        sys.exit(1)

    shutil.copy2(backup, live)
    print(f"Restored {live.name} from {backup}")


def isolate(csv_name: str, coverpoint: str) -> None:
    """Isolate a single coverpoint column, removing unrelated rows and columns."""
    name = csv_name if csv_name.endswith(".csv") else f"{csv_name}.csv"
    live = TESTPLANS / name
    backup = get_backup_path(csv_name)

    if not backup.exists():
        print(f"ERROR: No backup found at {backup}")
        sys.exit(1)

    # Start from the canonical backup
    shutil.copy2(backup, live)

    with live.open(newline="") as f:
        rows = list(csv.reader(f))

    headers = rows[0]

    if coverpoint not in headers:
        print(f"ERROR: Column '{coverpoint}' not found in {name}")
        print(f"Available cp_custom columns: {[h for h in headers if h.startswith('cp_custom')]}")
        sys.exit(1)

    target_idx = headers.index(coverpoint)

    # Identify columns to keep: all non-cp_custom columns + the target column
    keep_indices = []
    for i, h in enumerate(headers):
        if not h.startswith("cp_custom") or h == coverpoint:
            keep_indices.append(i)

    # Filter columns
    new_headers = [headers[i] for i in keep_indices]

    # Filter rows: keep header + rows where target column has a value
    new_rows = [new_headers]
    kept = 0
    removed = 0
    for row in rows[1:]:
        # Extend row if needed
        while len(row) <= target_idx:
            row.append("")

        if row[target_idx].strip():
            new_rows.append([row[i] if i < len(row) else "" for i in keep_indices])
            kept += 1
        else:
            removed += 1

    with live.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

    removed_cols = len(headers) - len(new_headers)
    print(f"Isolated '{coverpoint}' in {name}:")
    print(f"  Columns: {len(headers)} -> {len(new_headers)} ({removed_cols} cp_custom columns removed)")
    print(f"  Rows: {kept} kept, {removed} removed (no '{coverpoint}' marking)")


def main():
    parser = argparse.ArgumentParser(description="Isolate a coverpoint column for coverage testing")
    parser.add_argument("csv_name", help="CSV name (e.g. 'VfCustom' or 'VfCustom.csv')")
    parser.add_argument("coverpoint", nargs="?", help="Coverpoint column to isolate (e.g. 'cp_custom_vfp_state')")
    parser.add_argument("--restore", action="store_true", help="Restore CSV from canonical backup instead of isolating")

    args = parser.parse_args()

    if args.restore:
        restore(args.csv_name)
    elif args.coverpoint:
        isolate(args.csv_name, args.coverpoint)
    else:
        parser.error("coverpoint is required unless --restore is used")


if __name__ == "__main__":
    main()
