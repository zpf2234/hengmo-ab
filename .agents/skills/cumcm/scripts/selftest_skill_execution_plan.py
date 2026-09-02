#!/usr/bin/env python3
"""Isolated positive and negative tests for CUMCM module execution plans."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "audit_skill_execution_plan.py"
SPEC = importlib.util.spec_from_file_location("skill_execution_plan_under_test", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def make_skill(root: Path, name: str, kind: str) -> None:
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    filename = "SKILL.md" if kind == "public-skill" else "STAGE.md"
    (folder / filename).write_text(
        f"---\nname: {name}\ndescription: {'x' * 30}\n---\n", encoding="utf-8"
    )


def prepare() -> tuple[Path, Path, tempfile.TemporaryDirectory]:
    holder = tempfile.TemporaryDirectory(prefix="cumcm-skill-plan-")
    base = Path(holder.name)
    skills = base / "skills"
    project = base / "project"
    project.mkdir()
    for name in sorted(AUDIT.CORE_PUBLIC_SKILLS):
        make_skill(skills, name, "public-skill")
    for name in sorted(AUDIT.CONDITIONAL_PUBLIC_SKILLS):
        make_skill(skills, name, "public-skill")
    for name in sorted(AUDIT.REQUIRED_STAGES):
        make_skill(skills, name, "internal-stage")
    return skills, project, holder


def result_case(mutate=None) -> dict:
    skills, project, holder = prepare()
    try:
        plan = AUDIT.initial_plan(skills)
        if mutate:
            mutate(plan, project)
        result = AUDIT.validate(plan, skills, project)
        return result
    finally:
        holder.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/skill-execution-plan-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    cases: dict[str, dict] = {}
    baseline = result_case()
    cases["all_modules_are_planned"] = {"pass": baseline["pass"], "errors": baseline["errors"]}

    missing = result_case(lambda plan, _project: plan["modules"].pop())
    cases["missing_module_is_rejected"] = {
        "pass": not missing["pass"] and any("does not cover modules" in item for item in missing["errors"]),
        "errors": missing["errors"],
    }

    def skip_required(plan, _project):
        item = next(entry for entry in plan["modules"] if entry["module"] == "cumcm-paper")
        item.update({"applicability": "not-applicable", "status": "skipped-not-applicable"})

    skipped = result_case(skip_required)
    cases["required_skill_cannot_be_skipped"] = {
        "pass": not skipped["pass"] and any("national-first core module must be required" in item for item in skipped["errors"]),
        "errors": skipped["errors"],
    }

    def complete_without_evidence(plan, _project):
        item = next(entry for entry in plan["modules"] if entry["module"] == "cumcm-solve")
        item["status"] = "completed"

    no_evidence = result_case(complete_without_evidence)
    cases["completed_skill_requires_evidence"] = {
        "pass": not no_evidence["pass"] and any("completed status requires evidence" in item for item in no_evidence["errors"]),
        "errors": no_evidence["errors"],
    }

    def skip_conditional(plan, _project):
        for name in AUDIT.CONDITIONAL_PUBLIC_SKILLS:
            item = next(entry for entry in plan["modules"] if entry["module"] == name)
            item.update({"applicability": "not-applicable", "status": "skipped-not-applicable", "reason": "accepted figure plan contains no such visual family"})

    conditional = result_case(skip_conditional)
    cases["conditional_visual_skills_may_be_skipped_with_reason"] = {
        "pass": conditional["pass"],
        "errors": conditional["errors"],
    }

    def complete_all_applicable(plan, project):
        evidence = project / "审查" / "proof.txt"
        evidence.parent.mkdir(parents=True)
        evidence.write_text("verified", encoding="utf-8")
        for item in plan["modules"]:
            if item["module"] in AUDIT.CONDITIONAL_PUBLIC_SKILLS:
                item.update({"applicability": "not-applicable", "status": "skipped-not-applicable", "reason": "not applicable"})
            else:
                item.update({"status": "completed", "evidence": ["审查/proof.txt"]})

    finished = result_case(complete_all_applicable)
    cases["all_applicable_modules_can_close"] = {
        "pass": finished["pass"] and finished["all_applicable_completed"],
        "errors": finished["errors"],
    }

    result = {"schema_version": 1, "pass": all(item["pass"] for item in cases.values()), "case_count": len(cases), "cases": cases}
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(cases)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
