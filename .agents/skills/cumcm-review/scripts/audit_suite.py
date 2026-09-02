#!/usr/bin/env python3
"""Unified, fail-closed CUMCM audit entry point.

It may refresh objective metadata first, then runs independent audits.  Expected
failures are recorded rather than hidden.  A REVIEW_REQUIRED scorecard can
never become PASS through this command.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def run(name: str, command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"name": name, "command": command, "returncode": completed.returncode,
            "pass": completed.returncode == 0, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--skills-root", default=None)
    parser.add_argument("--track", choices=("standard", "national-first"), default="national-first")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    skills = Path(args.skills_root).resolve() if args.skills_root else Path(__file__).resolve().parents[2]
    python = sys.executable
    steps: list[dict[str, Any]] = []
    if not args.skip_sync:
        steps.append(run("sync_review_artifacts", [python, str(skills / "cumcm-review/scripts/sync_review_artifacts.py"), "--root", str(root)], root))
    steps.extend([
        run("evidence", [python, str(skills / "cumcm-solve/scripts/audit_evidence.py"), "--root", str(root)], root),
        run(
            "first_draft_gate",
            [python, str(skills / "cumcm-paper/scripts/check_first_draft_gate.py"), "--root", str(root)]
            + (["--no-write"] if args.no_write else []),
            root,
        ),
        run(
            "question_depth",
            [
                python,
                str(skills / "cumcm-paper/scripts/audit_question_depth.py"),
                "--root",
                str(root),
                "--phase",
                "final",
            ]
            + (["--no-write"] if args.no_write else []),
            root,
        ),
        run(
            "single_tex_delivery",
            [
                python,
                str(
                    skills
                    / "cumcm-paper/scripts/audit_single_tex_delivery.py"
                ),
                "--root",
                str(root),
                "--phase",
                "final",
            ],
            root,
        ),
        run(
            "skill_execution_plan",
            [
                python,
                str(skills / "cumcm/scripts/audit_skill_execution_plan.py"),
                "--root",
                str(root),
            ]
            + (["--no-write"] if args.no_write else []),
            root,
        ),
        run("figure_style", [python, str(skills / "cumcm-figures/scripts/audit_figure_style.py"), "--root", str(root)] + (["--track", "national-first"] if args.track == "national-first" else []), root),
        run("diagram_style", [python, str(skills / "cumcm-diagrams/scripts/audit_diagram_style.py"), "--root", str(root)], root),
        run("artifacts", [python, str(skills / "cumcm-review/scripts/audit_artifacts.py"), "--root", str(root), "--track", args.track] + (["--no-write"] if args.no_write else []), root),
    ])
    card = read_json(root / "审查/评分卡.json")
    card_state = card.get("verdict") if isinstance(card, dict) else "MISSING"
    scorecard_ready = isinstance(card, dict) and card_state in {"PASS_EXCELLENT_CANDIDATE", "PASS_NATIONAL_FIRST_CANDIDATE"}
    if isinstance(card, dict) and card.get("review_required"):
        scorecard_ready = False
    issues = [f"{step['name']} returned {step['returncode']}" for step in steps if not step["pass"]]
    if not scorecard_ready:
        issues.append(f"scorecard is not an accountable PASS: {card_state}")
    result = {"schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "root": str(root), "track": args.track, "pass": not issues,
              "scorecard_verdict": card_state, "steps": steps, "issues": issues}
    review = root / "审查"
    review.mkdir(parents=True, exist_ok=True)
    if not args.no_write:
        (review / "统一审计.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines = ["# 统一审计", "", f"结论：{'PASS' if result['pass'] else 'FAIL'}", f"评分卡：{card_state}", "", "## 步骤"]
        lines += [f"- {step['name']}: {'PASS' if step['pass'] else 'FAIL'} (rc={step['returncode']})" for step in steps]
        lines += ["", "## 阻断项"] + ([f"- {issue}" for issue in issues] or ["- 无"])
        (review / "统一审计.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "scorecard_verdict": card_state, "issues": issues}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
