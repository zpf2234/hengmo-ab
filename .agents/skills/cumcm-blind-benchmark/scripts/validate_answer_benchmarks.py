#!/usr/bin/env python3
"""Fail-closed validator for the hidden answer-benchmark library.

The library lives in assets/answer-benchmarks/<year><problem>.json and is an
evaluator-only asset: solvers must never read it before freezing (see SKILL.md).
This validator checks structure only; it never judges whether a candidate
answer passes.
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

EVALUATION_MODES = {"numeric", "optimization", "strategy", "design_open", "estimation"}
CONFIDENCE = {"high", "medium", "low"}
TOLERANCE_TYPES = {"relative", "absolute"}
EXTRACTION_MODES = {"text_layer", "visual_read", "manual"}


def validate_check(check: dict, sources: set[str], errors: list[str], where: str) -> None:
    if not isinstance(check.get("quantity"), str) or len(check["quantity"].strip()) < 2:
        errors.append(f"{where}: quantity must be a named measurable")
    if "unit" not in check:
        errors.append(f"{where}: unit is required (use \"1\" for dimensionless)")
    values = check.get("values")
    if not isinstance(values, dict) or not values:
        errors.append(f"{where}: values must map source id -> number|null")
        values = {}
    unknown = set(values) - sources
    if unknown:
        errors.append(f"{where}: values reference unknown sources {sorted(unknown)}")
    numeric_values = [v for v in values.values() if isinstance(v, (int, float))]
    if any(not isinstance(v, (int, float)) and v is not None for v in values.values()):
        errors.append(f"{where}: values must be numbers or null")

    confidence = check.get("confidence")
    if confidence not in CONFIDENCE:
        errors.append(f"{where}: confidence must be one of {sorted(CONFIDENCE)}")

    reference = check.get("reference_value")
    band = check.get("reference_band")
    tolerance = check.get("tolerance")

    if reference is None and band is None:
        errors.append(f"{where}: needs reference_value or reference_band")
    if reference is not None:
        if not isinstance(reference, (int, float)):
            errors.append(f"{where}: reference_value must be numeric")
        if not isinstance(tolerance, dict):
            errors.append(f"{where}: reference_value requires a tolerance object")
        else:
            if tolerance.get("type") not in TOLERANCE_TYPES:
                errors.append(f"{where}: tolerance.type must be relative or absolute")
            if not isinstance(tolerance.get("value"), (int, float)) or tolerance.get("value", 0) <= 0:
                errors.append(f"{where}: tolerance.value must be a positive number")
        # Confidence discipline: "high" requires >=2 agreeing extracted values.
        if confidence == "high":
            if len(numeric_values) < 2:
                errors.append(f"{where}: high confidence requires >=2 extracted source values")
            elif isinstance(reference, (int, float)) and reference != 0:
                spread = (max(numeric_values) - min(numeric_values)) / abs(reference)
                tol = tolerance.get("value", 0) if isinstance(tolerance, dict) else 0
                tol_rel = tol if isinstance(tolerance, dict) and tolerance.get("type") == "relative" else (
                    tol / abs(reference) if isinstance(tol, (int, float)) else 0
                )
                if spread > 2 * max(tol_rel, 1e-12):
                    errors.append(
                        f"{where}: source spread {spread:.4f} exceeds twice the tolerance; lower confidence or widen tolerance"
                    )
    if band is not None:
        if (
            not isinstance(band, dict)
            or not isinstance(band.get("low"), (int, float))
            or not isinstance(band.get("high"), (int, float))
            or band["low"] > band["high"]
        ):
            errors.append(f"{where}: reference_band must be {{low <= high}} numbers")
        if check.get("better_direction") not in {"higher", "lower"}:
            errors.append(f"{where}: reference_band requires better_direction higher|lower")
    if not isinstance(check.get("source_note"), str) or len(check["source_note"].strip()) < 4:
        errors.append(f"{where}: source_note must state where the numbers were read from")


def validate_file(path: Path, root: Path, *, require_source_files: bool = True) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [f"{path.name}: unreadable JSON ({exc})"]

    where = path.name
    if data.get("schema_version") != 1:
        errors.append(f"{where}: schema_version must be 1")
    year = data.get("year")
    problem = data.get("problem")
    if not isinstance(year, int) or not 2000 <= year <= 2100:
        errors.append(f"{where}: year must be a contest year")
    if problem not in {"A", "B"}:
        errors.append(f"{where}: problem must be A or B")
    if isinstance(year, int) and problem in {"A", "B"} and path.stem != f"{year}{problem}":
        errors.append(f"{where}: filename must be <year><problem>.json")
    if not isinstance(data.get("title"), str) or len(data["title"].strip()) < 4:
        errors.append(f"{where}: title missing")

    extraction = data.get("extraction")
    if not isinstance(extraction, dict) or extraction.get("mode") not in EXTRACTION_MODES:
        errors.append(f"{where}: extraction.mode must be one of {sorted(EXTRACTION_MODES)}")

    sources = data.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append(f"{where}: sources must be a non-empty list")
    else:
        for index, source in enumerate(sources):
            sid = source.get("id") if isinstance(source, dict) else None
            file_rel = source.get("file") if isinstance(source, dict) else None
            if not isinstance(sid, str) or not sid:
                errors.append(f"{where}: sources[{index}] lacks id")
                continue
            if sid in source_ids:
                errors.append(f"{where}: duplicate source id {sid}")
            source_ids.add(sid)
            if not isinstance(file_rel, str) or not file_rel.strip():
                errors.append(f"{where}: sources[{index}] lacks source file metadata")
            elif require_source_files and not (root / file_rel).exists():
                errors.append(f"{where}: source file missing on disk: {file_rel}")

    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        errors.append(f"{where}: questions must be a non-empty list")
        questions = []
    seen_questions: set[int] = set()
    for question in questions:
        qnum = question.get("question") if isinstance(question, dict) else None
        qwhere = f"{where} Q{qnum}"
        if not isinstance(qnum, int) or qnum < 1:
            errors.append(f"{where}: question number must be a positive integer")
            continue
        if qnum in seen_questions:
            errors.append(f"{qwhere}: duplicate question number")
        seen_questions.add(qnum)
        if not isinstance(question.get("task"), str) or len(question["task"].strip()) < 6:
            errors.append(f"{qwhere}: task summary missing")
        mode = question.get("evaluation_mode")
        if mode not in EVALUATION_MODES:
            errors.append(f"{qwhere}: evaluation_mode must be one of {sorted(EVALUATION_MODES)}")
        checks = question.get("checks", [])
        if not checks and not question.get("qualitative_criteria"):
            errors.append(f"{qwhere}: requires checks or qualitative_criteria")
        for cindex, check in enumerate(checks):
            if not isinstance(check, dict):
                errors.append(f"{qwhere}: checks[{cindex}] must be an object")
                continue
            validate_check(check, source_ids, errors, f"{qwhere} check[{cindex}] {check.get('quantity', '?')}")

    if not isinstance(data.get("provenance"), str) or "官方" not in data.get("provenance", ""):
        errors.append(f"{where}: provenance must state these are excellent-paper values, not official answers")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="repository root containing the corpus")
    parser.add_argument("--benchmarks-dir", default=None, help="answer-benchmarks directory override")
    parser.add_argument(
        "--allow-missing-source-files",
        action="store_true",
        help="validate metadata and values without requiring the private local PDF corpus",
    )
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    bench_dir = Path(args.benchmarks_dir).resolve() if args.benchmarks_dir else (
        Path(__file__).resolve().parent.parent / "assets" / "answer-benchmarks"
    )
    files = sorted(bench_dir.glob("*.json"))
    all_errors: list[str] = []
    per_file: dict[str, int] = {}
    total_checks = 0
    if not files:
        all_errors.append(f"no benchmark files found in {bench_dir}")
    for path in files:
        errors = validate_file(path, root, require_source_files=not args.allow_missing_source_files)
        all_errors.extend(errors)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            count = sum(len(q.get("checks", [])) for q in data.get("questions", []))
        except Exception:  # noqa: BLE001
            count = 0
        per_file[path.stem] = count
        total_checks += count

    report = {
        "pass": not all_errors,
        "benchmark_count": len(files),
        "total_checks": total_checks,
        "checks_per_problem": per_file,
        "source_file_check": "skipped" if args.allow_missing_source_files else "required",
        "errors": all_errors,
    }
    if not args.no_write:
        out = root / "审查" / "答案基准库校验.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "benchmark_count": len(files), "total_checks": total_checks, "errors": all_errors[:20]}, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
