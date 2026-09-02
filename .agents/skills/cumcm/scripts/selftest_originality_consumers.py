#!/usr/bin/env python3
"""Pin how the two downstream gates consume the originality verdict.

`benchmark_corpus.py` owns the originality release rule and records it as
``originality_gate.verdict``. Two gates consume it: `evaluate_skill_suite.py` (cross-problem
regression) and `cumcm-national-first-gate/scripts/check_gate.py` (final submission gate).

Both used to re-derive the rule from `similarity.status` plus a `manual_review` key, and their
copy was weaker than the owner's in two ways: it accepted a bare ``{"pass": true}`` carrying no
accountable reviewer or scope, and nothing in the suite ever wrote `manual_review` at all, so the
release channel it guarded was dead. Re-derived rules drift; these cases pin that both consumers
now read the recorded verdict, and that a report predating the verdict is only accepted in the one
state where the old and new rules provably agree.

Fixtures are a bare 审查/优秀论文对标.json in a temp project. Every other input is absent, so both
gates report many unrelated `missing:` issues -- that is expected. Each case asserts only on the
presence or absence of the originality issue, matched by substring.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1

# Consumers print Chinese JSON; on Windows a child Python defaults stdout to the ANSI code
# page (cp936), which the UTF-8 reader here cannot decode. Force UTF-8 in the children and
# keep errors="replace" so an unexpected byte degrades one issue string, not the whole run.
CHILD_ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

SCRIPTS = Path(__file__).resolve().parent
EVALUATE = SCRIPTS / "evaluate_skill_suite.py"
CHECK_GATE = (
    SCRIPTS.parent.parent / "cumcm-national-first-gate" / "scripts" / "check_gate.py"
)

# Both consumers word the issue differently; this substring is what they share.
ORIGINALITY_MARKER = "原创"
# The backward-compatibility issue names the missing field instead.
LEGACY_MARKER = "originality_gate"

VALID_REVIEW = {
    "pass": True,
    "reviewer": "independent-reviewer-1",
    "scope": "抽查 12 处连续句段",
}

# name -> (报告内容, 是否应报原创性问题)
CASES: dict[str, tuple[dict, bool]] = {
    "verdict_pass_clears": (
        {
            "similarity": {"status": "PASS"},
            "originality_gate": {"verdict": "PASS", "status": "PASS", "reasons": []},
        },
        False,
    ),
    "verdict_manual_review_clears": (
        {
            "similarity": {"status": "WARN_REVIEW"},
            "manual_review": VALID_REVIEW,
            "originality_gate": {
                "verdict": "PASS_WITH_MANUAL_REVIEW",
                "status": "WARN_REVIEW",
                "reasons": ["摘要 containment 0.200 落在人工检查区间"],
            },
        },
        False,
    ),
    "verdict_unproven_blocks": (
        {
            "similarity": {"status": "NOT_RUN"},
            "originality_gate": {
                "verdict": "BLOCK_ORIGINALITY_UNPROVEN",
                "status": "NOT_RUN",
                "reasons": ["相似度从未执行，不得视为原创门槛通过"],
            },
        },
        True,
    ),
    "verdict_high_similarity_blocks": (
        {
            "similarity": {"status": "FAIL_HIGH_SIMILARITY"},
            "originality_gate": {
                "verdict": "FAIL_HIGH_SIMILARITY",
                "status": "FAIL_HIGH_SIMILARITY",
                "reasons": [],
            },
        },
        True,
    ),
    # A verdict of PASS_WITH_MANUAL_REVIEW is the owner's decision; a consumer must not
    # second-guess it just because the band status is non-PASS.
    "verdict_wins_over_status": (
        {
            "similarity": {"status": "WARN_REVIEW"},
            "originality_gate": {
                "verdict": "PASS_WITH_MANUAL_REVIEW",
                "status": "WARN_REVIEW",
                "reasons": [],
            },
        },
        False,
    ),
    # Reports written before the verdict existed: only a measured PASS is still accepted.
    "legacy_pass_still_accepted": ({"similarity": {"status": "PASS"}}, False),
    "legacy_not_run_blocks": ({"similarity": {"status": "NOT_RUN"}}, True),
    # The closed hole: a bare manual note used to release the human-review band here even
    # though no producer ever wrote the key and no reviewer was named.
    "legacy_bare_manual_review_blocks": (
        {"similarity": {"status": "WARN_REVIEW"}, "manual_review": {"pass": True}},
        True,
    ),
    "legacy_full_manual_review_blocks": (
        {"similarity": {"status": "WARN_REVIEW"}, "manual_review": VALID_REVIEW},
        True,
    ),
    "legacy_missing_similarity_blocks": ({}, True),
}


def issues_from_evaluate(root: Path) -> list[str]:
    completed = subprocess.run(
        [
            sys.executable,
            str(EVALUATE),
            "--projects",
            str(root),
            "--min-projects",
            "1",
            "--no-write",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=CHILD_ENV,
        check=False,
    )
    for line in reversed((completed.stdout or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        payload = json.loads(line)
        projects = payload.get("projects") or []
        return list(projects[0].get("issues") or []) if projects else []
    raise AssertionError(f"evaluate_skill_suite emitted no JSON: {completed.stderr[-300:]}")


def issues_from_check_gate(root: Path) -> list[str]:
    completed = subprocess.run(
        [sys.executable, str(CHECK_GATE), "--root", str(root), "--no-write"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=CHILD_ENV,
        check=False,
    )
    for line in reversed((completed.stdout or "").splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        return list(json.loads(line).get("issues") or [])
    raise AssertionError(f"check_gate emitted no JSON: {completed.stderr[-300:]}")


CONSUMERS = {
    "evaluate_skill_suite": issues_from_evaluate,
    "check_gate": issues_from_check_gate,
}


def run_case(base: Path, name: str) -> dict:
    report, should_block = CASES[name]
    outcome: dict = {"pass": True, "consumers": {}}
    for consumer, collect in CONSUMERS.items():
        root = base / f"{name}--{consumer}"
        (root / "审查").mkdir(parents=True, exist_ok=True)
        (root / "审查" / "优秀论文对标.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )
        issues = collect(root)
        hits = [
            issue
            for issue in issues
            if ORIGINALITY_MARKER in issue or LEGACY_MARKER in issue
        ]
        ok = bool(hits) == should_block
        outcome["consumers"][consumer] = {
            "expected_block": should_block,
            "blocked": bool(hits),
            "issue": hits[0] if hits else None,
            "pass": ok,
        }
        outcome["pass"] = outcome["pass"] and ok
    return outcome


def main() -> int:
    # Both consumers print their verdict as UTF-8 JSON regardless of console encoding, but
    # keep this side symmetrical so a failure report is readable when piped on Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - older interpreters or a replaced stdout
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/originality-consumers-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    if not EVALUATE.is_file() or not CHECK_GATE.is_file():
        print(
            json.dumps(
                {
                    "pass": False,
                    "error": "consumer script missing",
                    "evaluate": str(EVALUATE),
                    "check_gate": str(CHECK_GATE),
                },
                ensure_ascii=False,
            )
        )
        return 1

    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-originality-consumers-") as tmp:
        base = Path(tmp)
        for name in CASES:
            results[name] = run_case(base, name)

    result = {
        "schema_version": SCHEMA_VERSION,
        "pass": all(item["pass"] for item in results.values()),
        "case_count": len(results),
        "consumer_count": len(CONSUMERS),
        "cases": results,
    }
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = sorted(name for name, item in results.items() if not item["pass"])
    print(
        json.dumps(
            {"pass": result["pass"], "case_count": len(results), "failed": failed},
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
