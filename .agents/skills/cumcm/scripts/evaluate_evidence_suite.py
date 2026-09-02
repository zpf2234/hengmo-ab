#!/usr/bin/env python
"""Run the latest solve-stage audit across independent evidence-package projects."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SKILLS_DIR = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = SKILLS_DIR / "cumcm-solve" / "scripts" / "audit_evidence.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_project(root: Path) -> dict:
    root = root.resolve()
    process = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    issues = []
    report_path = root / "求解" / "证据审计.json"
    report = None
    if not report_path.exists():
        issues.append("evidence audit report missing")
    else:
        try:
            report = load_json(report_path)
        except Exception as exc:  # noqa: BLE001
            issues.append(f"evidence audit report invalid: {exc}")
    if process.returncode != 0:
        issues.append(f"audit command failed with exit {process.returncode}")
    if report and not report.get("pass"):
        issues.extend(report.get("global_issues", []))
        for problem in report.get("problems", []):
            issues.extend(f"{problem['problem']}: {item}" for item in problem.get("hard_errors", []))

    contract_path = root / "求解" / "任务契约.json"
    archetypes = set()
    title = None
    if contract_path.exists():
        try:
            contract = load_json(contract_path)
            title = contract.get("赛题标题")
            for question in contract.get("问题", []):
                archetypes.update(question.get("原型", []))
        except Exception as exc:  # noqa: BLE001
            issues.append(f"task contract invalid: {exc}")
    else:
        issues.append("task contract missing")
    return {
        "root": str(root),
        "title": title,
        "pass": not issues,
        "archetypes": sorted(archetypes),
        "issues": issues,
    }


def write_report(output_dir: Path, result: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "证据包回归.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# CUMCM Skills 证据包回归",
        "",
        f"结论：{'PASS' if result['pass'] else 'FAIL'}",
        f"通过项目：{result['passed_projects']}/{result['project_count']}",
        f"覆盖原型：{'、'.join(result['covered_archetypes'])}",
        "",
    ]
    for item in result["projects"]:
        lines.extend(
            [
                f"## {item['title'] or item['root']}",
                f"- 结论：{'PASS' if item['pass'] else 'FAIL'}",
                f"- 原型：{'、'.join(item['archetypes'])}",
            ]
        )
        lines.extend(f"- 问题：{issue}" for issue in item["issues"])
        lines.append("")
    (output_dir / "证据包回归.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", nargs="+", required=True)
    parser.add_argument("--min-projects", type=int, default=3)
    parser.add_argument("--required-archetypes", nargs="*", default=["机理", "统计", "优化"])
    parser.add_argument("--output", default="审查/skills回归/证据包")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    projects = [evaluate_project(Path(path)) for path in args.projects]
    covered = set().union(*(set(item["archetypes"]) for item in projects)) if projects else set()
    passed_projects = sum(1 for item in projects if item["pass"])
    issues = []
    if len(projects) < args.min_projects:
        issues.append(f"projects below minimum: {len(projects)} < {args.min_projects}")
    if passed_projects != len(projects):
        issues.append("one or more evidence packages failed")
    missing = sorted(set(args.required_archetypes) - covered)
    if missing:
        issues.append(f"archetypes not covered: {', '.join(missing)}")
    result = {
        "pass": not issues,
        "project_count": len(projects),
        "passed_projects": passed_projects,
        "covered_archetypes": sorted(covered),
        "required_archetypes": sorted(set(args.required_archetypes)),
        "issues": issues,
        "projects": projects,
    }
    if args.no_write:
        print(json.dumps(result, ensure_ascii=False))
    else:
        write_report(Path(args.output).resolve(), result)
        print(f"Wrote {Path(args.output).resolve() / '证据包回归.md'}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
