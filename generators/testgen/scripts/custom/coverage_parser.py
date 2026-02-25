#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Parse coverage uncovered reports to extract coverpoint coverage status."""

from __future__ import annotations

import os
import re
from pathlib import Path


def parse_uncovered(report_dir: str, coverpoint_name: str, effew_list: list[str] | None = None, category: str = "VfCustom") -> dict:
    """Parse uncovered reports for a specific coverpoint.

    Args:
        report_dir: Path to reports directory (e.g. work/sail-rv64-max/reports)
        coverpoint_name: Coverpoint name (e.g. cp_custom_vfp_flags_set)
        effew_list: List of EFFEWs to check (e.g. ["16", "32", "64"])
        category: Category prefix (e.g. "VfCustom")

    Returns:
        Dict: {effew: {instruction: {coverpoint_or_cross: {hit: N, total: M, missing: K, pct: P}}}}
    """
    if effew_list is None:
        effew_list = ["16", "32", "64"]

    results: dict = {}
    for effew in effew_list:
        report_file = Path(report_dir) / f"{category}{effew}_uncovered.txt"
        if not report_file.exists():
            results[effew] = {"_error": f"Report file not found: {report_file}"}
            continue

        results[effew] = _parse_report_file(report_file, coverpoint_name)

    return results


def _parse_report_file(report_file: Path, coverpoint_name: str) -> dict:
    """Parse a single uncovered report file for sections matching coverpoint_name."""
    content = report_file.read_text()
    result: dict = {}

    # Find all covergroup instances (one per instruction)
    # Pattern: "Covergroup instance obj_{Category}{SEW}_{instruction}"
    instance_pattern = re.compile(
        r"Covergroup instance obj_\w+?_(\w+)\s+(\d+\.\d+)%\s+\d+\s+-\s+\w+",
    )

    # Split content by TYPE lines to get per-instruction blocks
    type_blocks = re.split(r"(?=\s*TYPE\s+/RISCV_coverage_pkg)", content)

    for block in type_blocks:
        # Extract instruction name from TYPE line
        type_match = re.search(r"TYPE\s+/RISCV_coverage_pkg/RISCV_coverage__\d+/\w+?_(\w+?)_cg", block)
        if not type_match:
            continue
        instruction = type_match.group(1).replace("_", ".")

        # Look for our coverpoint in this block
        cp_info = _extract_coverpoint_info(block, coverpoint_name)
        if cp_info:
            result[instruction] = cp_info

    return result


def _extract_coverpoint_info(block: str, coverpoint_name: str) -> dict | None:
    """Extract coverage info for a specific coverpoint from a covergroup block."""
    info: dict = {}

    # Match both "Coverpoint {name}" and "Cross {name}" lines
    pattern = re.compile(
        rf"\s+(?:Coverpoint|Cross)\s+{re.escape(coverpoint_name)}\s+(\d+\.\d+)%\s+(\d+)\s+-\s+(\w+)",
    )

    lines = block.split("\n")
    i = 0
    while i < len(lines):
        match = pattern.match(lines[i])
        if match:
            pct = float(match.group(1))
            goal = int(match.group(2))
            status = match.group(3)

            # Read the covered/missing/% lines that follow
            covered = 0
            total = 0
            missing = 0
            for j in range(i + 1, min(i + 8, len(lines))):
                cov_match = re.search(r"covered/total bins:\s+(\d+)\s+(\d+)", lines[j])
                if cov_match:
                    covered = int(cov_match.group(1))
                    total = int(cov_match.group(2))
                miss_match = re.search(r"missing/total bins:\s+(\d+)\s+(\d+)", lines[j])
                if miss_match:
                    missing = int(miss_match.group(1))

            info[coverpoint_name] = {
                "hit": covered,
                "total": total,
                "missing": missing,
                "pct": pct,
                "status": status,
            }
            break
        i += 1

    return info if info else None


def summarize_coverage(report_dir: str, coverpoint_name: str, effew_list: list[str] | None = None, category: str = "VfCustom") -> dict:
    """Return a concise coverage summary for a coverpoint.

    Returns:
        Dict with keys: total_bins, covered_bins, uncovered_bins, uncovered_list, fully_covered
    """
    results = parse_uncovered(report_dir, coverpoint_name, effew_list, category)

    total_bins = 0
    covered_bins = 0
    uncovered_list: list[str] = []

    for effew, instructions in results.items():
        if "_error" in instructions:
            uncovered_list.append(f"EFFEW{effew}: {instructions['_error']}")
            continue
        for inst, cp_info in instructions.items():
            for cp_name, info in cp_info.items():
                total_bins += info["total"]
                covered_bins += info["hit"]
                if info["missing"] > 0:
                    uncovered_list.append(f"EFFEW{effew}/{inst}: {info['missing']}/{info['total']} bins uncovered ({info['pct']}%)")

    return {
        "total_bins": total_bins,
        "covered_bins": covered_bins,
        "uncovered_bins": total_bins - covered_bins,
        "uncovered_list": uncovered_list,
        "fully_covered": total_bins > 0 and covered_bins == total_bins,
    }


def format_coverage_for_prompt(report_dirs: list[str], coverpoint_name: str, effew_list: list[str] | None = None, category: str = "VfCustom") -> str:
    """Format coverage results as a string suitable for including in a prompt."""
    lines = [f"Coverage results for {coverpoint_name}:"]

    for report_dir in report_dirs:
        dir_name = os.path.basename(os.path.dirname(report_dir))
        summary = summarize_coverage(report_dir, coverpoint_name, effew_list, category)
        lines.append(f"\n  {dir_name}:")
        lines.append(f"    Total bins: {summary['total_bins']}, Covered: {summary['covered_bins']}, Uncovered: {summary['uncovered_bins']}")
        if summary["uncovered_list"]:
            for item in summary["uncovered_list"]:
                lines.append(f"    - {item}")
        elif summary["total_bins"] > 0:
            lines.append("    All bins covered!")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: coverage_parser.py <report_dir> <coverpoint_name> [effew_list] [category]")
        sys.exit(1)

    report_dir = sys.argv[1]
    cp_name = sys.argv[2]
    effews = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    cat = sys.argv[4] if len(sys.argv) > 4 else "VfCustom"

    summary = summarize_coverage(report_dir, cp_name, effews, cat)
    print(f"Coverpoint: {cp_name}")
    print(f"  Total bins: {summary['total_bins']}")
    print(f"  Covered:    {summary['covered_bins']}")
    print(f"  Uncovered:  {summary['uncovered_bins']}")
    print(f"  Fully covered: {summary['fully_covered']}")
    if summary["uncovered_list"]:
        print("  Uncovered details:")
        for item in summary["uncovered_list"]:
            print(f"    {item}")
