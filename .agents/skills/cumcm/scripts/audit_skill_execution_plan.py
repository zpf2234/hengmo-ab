#!/usr/bin/env python3
"""Validate the CUMCM competition-time skill/stage execution plan.

The suite intentionally contains public skills, internal stages, conditional visual
skills, and release-only regressions.  This audit makes that distinction executable:
"use all skills" means every applicable module has an explicit route and evidence,
not that every module is invoked unconditionally on every problem.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_PLAN = "审查/skill-execution-plan.json"
DEFAULT_REPORT = "审查/skill-execution-audit.json"
VALID_KINDS = {"public-skill", "internal-stage"}
VALID_APPLICABILITY = {"required", "conditional", "not-applicable"}
VALID_STATUSES = {"planned", "running", "completed", "skipped-not-applicable"}
CORE_PUBLIC_SKILLS = {
    "cumcm",
    "cumcm-contest-operations",
    "cumcm-problem-selection",
    "cumcm-model-tournament",
    "cumcm-solve",
    "cumcm-paper",
    "cumcm-notation",
    "cumcm-results-validation",
    "cumcm-deai",
    "cumcm-review",
}
CONDITIONAL_PUBLIC_SKILLS = {"cumcm-figures", "cumcm-diagrams"}
REQUIRED_STAGES = {
    "cumcm-outline",
    "cumcm-restatement",
    "cumcm-analysis",
    "cumcm-assumptions",
    "cumcm-model-writing",
    "cumcm-evaluation",
    "cumcm-references",
    "cumcm-appendix",
    "cumcm-abstract",
    "cumcm-language-audit",
    "cumcm-figure-router",
    "cumcm-blind-benchmark",
    "cumcm-adversarial-review",
    "cumcm-national-first-gate",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inventory(skills_root: Path) -> dict[str, str]:
    modules: dict[str, str] = {}
    for folder in sorted(skills_root.glob("cumcm*")):
        if (folder / "SKILL.md").is_file():
            modules[folder.name] = "public-skill"
        elif (folder / "STAGE.md").is_file():
            modules[folder.name] = "internal-stage"
    return modules


def frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\s*\n.*?^name:\s*([^\n]+).*?^---\s*$", text, re.S | re.M)
    return match.group(1).strip().strip('"\'') if match else None


def default_entry(name: str, kind: str) -> dict[str, Any]:
    if name in CORE_PUBLIC_SKILLS or name in REQUIRED_STAGES:
        applicability = "required"
        reason = "national-first competition workflow"
    elif name in CONDITIONAL_PUBLIC_SKILLS:
        applicability = "conditional"
        reason = "used only when the accepted figure plan contains this visual family"
    else:
        applicability = "conditional"
        reason = "project evidence and declared track decide applicability"
    return {
        "module": name,
        "kind": kind,
        "applicability": applicability,
        "status": "planned",
        "reason": reason,
        "evidence": [],
    }


def initial_plan(skills_root: Path) -> dict[str, Any]:
    modules = inventory(skills_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "track": "national-first",
        "rule": "Every applicable public skill and internal stage must be explicitly planned and evidenced; conditional modules are not forced when scientifically inapplicable.",
        "modules": [default_entry(name, kind) for name, kind in sorted(modules.items())],
    }


def validate(plan: Any, skills_root: Path, project_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    modules = inventory(skills_root)
    entries = plan.get("modules") if isinstance(plan, dict) else None
    if not isinstance(plan, dict) or plan.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(entries, list):
        entries = []
        errors.append("modules must be a list")

    by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(entries, start=1):
        label = f"modules[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        name = item.get("module")
        if not isinstance(name, str) or not name:
            errors.append(f"{label}: module is empty")
            continue
        if name in by_name:
            errors.append(f"{label}: duplicate module {name}")
            continue
        by_name[name] = item
        if name not in modules:
            errors.append(f"{label}: unknown module {name}")
            continue
        if item.get("kind") != modules[name] or item.get("kind") not in VALID_KINDS:
            errors.append(f"{name}: kind must be {modules[name]}")
        applicability = item.get("applicability")
        status = item.get("status")
        if applicability not in VALID_APPLICABILITY:
            errors.append(f"{name}: invalid applicability")
        if status not in VALID_STATUSES:
            errors.append(f"{name}: invalid status")
        if not isinstance(item.get("reason"), str) or not item.get("reason", "").strip():
            errors.append(f"{name}: reason is required")
        evidence = item.get("evidence")
        if status == "completed":
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{name}: completed status requires evidence")
            else:
                for relative in evidence:
                    if not isinstance(relative, str) or not (project_root / relative).exists():
                        errors.append(f"{name}: evidence does not exist: {relative}")
        if status == "skipped-not-applicable" and applicability != "not-applicable":
            errors.append(f"{name}: skipped status requires not-applicable")
        if applicability == "not-applicable" and status != "skipped-not-applicable":
            errors.append(f"{name}: not-applicable module must be explicitly skipped")
        if applicability == "required" and status == "skipped-not-applicable":
            errors.append(f"{name}: required module cannot be skipped")

    missing = sorted(set(modules) - set(by_name))
    if missing:
        errors.append(f"plan does not cover modules: {', '.join(missing)}")
    for name in sorted((CORE_PUBLIC_SKILLS | REQUIRED_STAGES) & set(modules)):
        item = by_name.get(name)
        if item and item.get("applicability") != "required":
            errors.append(f"{name}: national-first core module must be required")
    for name in sorted(CONDITIONAL_PUBLIC_SKILLS & set(modules)):
        item = by_name.get(name)
        if item and item.get("applicability") == "required":
            warnings.append(f"{name}: unconditional use may force scientifically unnecessary visuals")

    completed = sum(1 for item in by_name.values() if item.get("status") == "completed")
    applicable_entries = [
        item for item in by_name.values() if item.get("applicability") != "not-applicable"
    ]
    unfinished = sorted(
        str(item.get("module"))
        for item in applicable_entries
        if item.get("status") != "completed"
    )
    if unfinished:
        warnings.append(f"applicable modules not completed yet: {', '.join(unfinished)}")
    applicable = len(applicable_entries)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pass": not errors,
        "inventory_count": len(modules),
        "public_skill_count": sum(kind == "public-skill" for kind in modules.values()),
        "stage_count": sum(kind == "internal-stage" for kind in modules.values()),
        "covered_count": len(set(modules) & set(by_name)),
        "applicable_count": applicable,
        "completed_count": completed,
        "all_applicable_completed": not errors and applicable == completed,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--skills-root", default=None)
    parser.add_argument("--plan", default=DEFAULT_PLAN)
    parser.add_argument("--output", default=DEFAULT_REPORT)
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(args.root).resolve()
    skills_root = Path(args.skills_root).resolve() if args.skills_root else Path(__file__).resolve().parents[2]
    plan_path = root / args.plan

    if args.init:
        plan = initial_plan(skills_root)
        if not args.no_write:
            write_json(plan_path, plan)
        print(json.dumps({"created": not args.no_write, "module_count": len(plan["modules"])}, ensure_ascii=False))
        return 0

    try:
        plan = read_json(plan_path)
    except Exception as exc:  # noqa: BLE001
        result = {
            "schema_version": SCHEMA_VERSION,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "pass": False,
            "inventory_count": len(inventory(skills_root)),
            "errors": [f"execution plan missing or unreadable: {exc}"],
            "warnings": [],
        }
    else:
        result = validate(plan, skills_root, root)

    if not args.no_write:
        write_json(root / args.output, result)
    print(json.dumps({"pass": result["pass"], "inventory_count": result.get("inventory_count"), "error_count": len(result["errors"])}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
