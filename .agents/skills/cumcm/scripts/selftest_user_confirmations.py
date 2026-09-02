#!/usr/bin/env python3
"""Regression test for the two semi-automatic user confirmation gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "audit_user_confirmations.py"


def run(root: Path, *args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    try:
        payload = json.loads(completed.stdout.strip() or "{}")
    except json.JSONDecodeError:
        payload = {}
    return completed.returncode, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/user-confirmations-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    cases: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-confirmations-") as tmp:
        root = Path(tmp)
        (root / "求解").mkdir(parents=True)
        (root / "审查/section-chain").mkdir(parents=True)
        (root / "求解/证据审计.json").write_text('{"pass": true}\n', encoding="utf-8")
        (root / "求解/证据矩阵.csv").write_text("claim_id,result\nq1,1\n", encoding="utf-8")
        (root / "审查/section-chain/manifest.json").write_text('{"question_ids":["q1"]}\n', encoding="utf-8")
        (root / "审查/逐问深度清单.json").write_text('{"body_page_plan":{"official_body_max":30}}\n', encoding="utf-8")

        code, _ = run(root, "--init")
        cases["init"] = code == 0
        code, _ = run(root, "--phase", "paper-plan")
        cases["paper_plan_blocks_without_confirmation"] = code == 1
        code, _ = run(
            root,
            "--record", "method-result",
            "--confirmation-note", "用户确认方法与结果",
            "--evidence", "求解/证据审计.json",
            "--evidence", "求解/证据矩阵.csv",
        )
        cases["record_method_result"] = code == 0
        code, _ = run(root, "--phase", "paper-plan")
        cases["paper_plan_passes_after_confirmation"] = code == 0
        code, _ = run(root, "--phase", "draft")
        cases["draft_blocks_before_outline_confirmation"] = code == 1
        code, _ = run(
            root,
            "--record", "outline-page",
            "--confirmation-note", "用户确认目录大纲和页数",
            "--evidence", "审查/section-chain/manifest.json",
            "--evidence", "审查/逐问深度清单.json",
        )
        cases["record_outline_page"] = code == 0
        code, _ = run(root, "--phase", "draft")
        cases["draft_passes_after_both_confirmations"] = code == 0
        (root / "审查/逐问深度清单.json").write_text('{"body_page_plan":{"official_body_max":29}}\n', encoding="utf-8")
        code, payload = run(root, "--phase", "draft")
        cases["changed_plan_invalidates_confirmation"] = code == 1 and any(
            "changed" in item for item in payload.get("errors", [])
        )

    result = {"schema_version": 1, "pass": all(cases.values()), "case_count": len(cases), "cases": cases}
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(cases)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
