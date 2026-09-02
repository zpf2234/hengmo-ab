#!/usr/bin/env python3
"""Self-test for validate_answer_benchmarks.py.

Covers both directions:
1. the real answer-benchmark library must validate clean;
2. corrupted benchmarks must each be rejected (fail-closed), so the validator
   cannot silently degrade into a rubber stamp.
"""

from __future__ import annotations

import copy
import argparse
import json
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import validate_answer_benchmarks as vab  # noqa: E402

ROOT = SCRIPTS.parent.parent.parent.parent  # repository root
BENCH_DIR = SCRIPTS.parent / "assets" / "answer-benchmarks"

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"name": name, "pass": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f" | {detail}" if detail and not ok else ""))


def good_benchmark() -> dict:
    return json.loads((BENCH_DIR / "2020B.json").read_text(encoding="utf-8"))


def errors_for(data: dict, filename: str = "2020B.json") -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / filename
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return vab.validate_file(path, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default="审查/答案基准库自测.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    # 1. Real library validates clean. The public release intentionally omits the
    # source PDF corpus; local development remains strict when that corpus exists.
    real_errors: list[str] = []
    files = sorted(BENCH_DIR.glob("*.json"))
    private_corpus_present = (ROOT / "最终效果" / "高教杯优秀论文").exists()
    for path in files:
        real_errors.extend(
            vab.validate_file(path, ROOT, require_source_files=private_corpus_present)
        )
    record("real_library_clean", len(files) == 16 and not real_errors, "; ".join(real_errors[:3]) or f"files={len(files)}")

    # 2. Coverage: every contest year 2018-2025 x {A,B} present.
    expected = {f"{year}{problem}" for year in range(2018, 2026) for problem in "AB"}
    record("coverage_2018_2025_AB", {p.stem for p in files} == expected)

    # 3. Corruptions must each fail.
    base = good_benchmark()

    broken = copy.deepcopy(base)
    broken["questions"][0]["checks"][0].pop("tolerance")
    record("rejects_missing_tolerance", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    broken["questions"][0]["checks"][0]["values"] = {"B078": 10470}
    record("rejects_high_confidence_single_source", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    broken["questions"][0]["checks"][0]["values"]["B078"] = 99999
    record("rejects_high_confidence_wide_spread", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    broken["sources"][0]["file"] = "最终效果/不存在的论文.pdf"
    record("rejects_missing_source_file", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    record("rejects_filename_year_mismatch", bool(errors_for(broken, filename="2019B.json")))

    broken = copy.deepcopy(base)
    broken["provenance"] = "these are the true answers"
    record("rejects_provenance_without_official_disclaimer", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    broken["questions"][2] = {"question": 3, "task": "多人博弈情形（第五、六关）的策略设计", "evaluation_mode": "strategy"}
    record("rejects_question_without_checks_or_criteria", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    broken["questions"][0]["checks"][0]["values"]["ZZZZ"] = 10470
    record("rejects_unknown_source_id_in_values", bool(errors_for(broken)))

    broken = copy.deepcopy(base)
    broken["questions"][1]["evaluation_mode"] = "vibes"
    record("rejects_unknown_evaluation_mode", bool(errors_for(broken)))

    band_owner = json.loads((BENCH_DIR / "2021B.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(band_owner)
    for question in broken["questions"]:
        for check in question.get("checks", []):
            check.pop("better_direction", None)
    record("rejects_band_without_direction", bool(errors_for(broken, filename="2021B.json")))

    passed = sum(1 for r in RESULTS if r["pass"])
    report = {"pass": passed == len(RESULTS), "passed": passed, "total": len(RESULTS), "results": RESULTS}
    if not args.no_write:
        out = Path(args.root).resolve() / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n{passed}/{len(RESULTS)} passed -> {out}")
    else:
        print(f"\n{passed}/{len(RESULTS)} passed")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
