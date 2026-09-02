#!/usr/bin/env python3
"""Fail-closed validator for the grading-standards library.

The library lives in assets/grading-standards/<year><problem>.md and mirrors the
answer-benchmark isolation discipline: files contain official grading points with
answer-revealing numbers, so solvers must never read same-problem files before
freezing. This validator checks structural completeness only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

EXPECTED_IDS = [
    f"{year}{problem}" for year in range(2018, 2026) for problem in ("A", "B")
]
REQUIRED_SECTIONS = [
    "来源清单",
    "置信度评估",
]
JUDGEMENT_SECTION_PATTERN = re.compile(r"加分|扣分|评阅要点|评阅导向|评阅中发现")
CONFIDENCE_LEVELS = (
    "official_text",
    "official_image_transcribed",
    "authored_analysis",
    "third_party",
)


def validate_file(path: Path, errors: list[str], warnings: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    name = path.stem

    title_line = text.splitlines()[0] if text.splitlines() else ""
    if not title_line.startswith("# ") or name[:4] not in title_line:
        errors.append(f"{name}: first line must be a title containing the year")

    for section in REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"{name}: missing required section 「{section}」")

    if not JUDGEMENT_SECTION_PATTERN.search(text):
        errors.append(f"{name}: no grading-point content (加分/扣分/评阅要点) found")

    if not any(level in text for level in CONFIDENCE_LEVELS):
        errors.append(
            f"{name}: confidence level must be one of {CONFIDENCE_LEVELS}"
        )

    if "http" not in text:
        errors.append(f"{name}: source list must contain at least one URL")

    if len(text) < 1500:
        warnings.append(f"{name}: unusually short ({len(text)} chars), verify content")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dir",
        default=None,
        help="grading-standards directory (defaults to sibling assets dir)",
    )
    parser.add_argument("--json-out", default=None, help="write report JSON here")
    args = parser.parse_args()

    base = (
        Path(args.dir)
        if args.dir
        else Path(__file__).resolve().parent.parent / "assets" / "grading-standards"
    )
    errors: list[str] = []
    warnings: list[str] = []

    if not base.is_dir():
        errors.append(f"directory not found: {base}")
        present: list[str] = []
        missing = list(EXPECTED_IDS)
    else:
        present = sorted(p.stem for p in base.glob("*.md") if p.stem != "README")
        missing = [pid for pid in EXPECTED_IDS if pid not in present]
        unexpected = [pid for pid in present if pid not in EXPECTED_IDS]
        for pid in unexpected:
            errors.append(f"unexpected file {pid}.md (naming must be <year><A|B>)")
        if not (base / "README.md").is_file():
            errors.append("README.md with isolation discipline is required")
        for pid in present:
            if pid in EXPECTED_IDS:
                validate_file(base / f"{pid}.md", errors, warnings)

    # Missing problems are warnings, not errors: coverage grows incrementally,
    # but consumers must treat absent files as "no grading standard" (fail-closed).
    for pid in missing:
        warnings.append(f"{pid}: not collected yet (consumers must fail closed)")

    report = {
        "pass": not errors,
        "present": present,
        "missing": missing,
        "errors": errors,
        "warnings": warnings,
    }
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"grading-standards: {len(present)} present, {len(missing)} missing")
    for line in errors:
        print(f"ERROR: {line}")
    for line in warnings:
        print(f"WARN: {line}")
    print("PASS" if report["pass"] else "FAIL")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
