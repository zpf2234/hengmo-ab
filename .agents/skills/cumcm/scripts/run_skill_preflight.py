#!/usr/bin/env python3
"""Run the deterministic local preflight for the compressed CUMCM skill suite.

This is not a substitute for the six-case and held-out-problem evaluations.  It
closes the cheaper engineering layer: skill metadata, links, fail-closed gates,
router parity, delivery contracts, visual audits, benchmark validators, and the
figure runtime regressions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def inspect_skill_structure(root: Path) -> dict[str, Any]:
    skills_root = root / ".agents/skills"
    errors: list[str] = []
    public_skills = sorted(path for path in skills_root.glob("cumcm*") if (path / "SKILL.md").exists())
    stage_files = sorted(skills_root.glob("cumcm*/STAGE.md"))
    markdown_files = [path / "SKILL.md" for path in public_skills] + stage_files

    for folder in public_skills:
        skill_path = folder / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        front = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
        if not front:
            errors.append(f"invalid frontmatter: {skill_path.relative_to(root)}")
            continue
        keys = re.findall(r"^([A-Za-z0-9_-]+):", front.group(1), re.M)
        if set(keys) != {"name", "description"}:
            errors.append(f"frontmatter keys must be name/description only: {skill_path.relative_to(root)}")
        name_match = re.search(r"^name:\s*([^\n]+)$", front.group(1), re.M)
        desc_match = re.search(r"^description:\s*(.+)$", front.group(1), re.M)
        name = name_match.group(1).strip().strip('"\'') if name_match else ""
        if name != folder.name:
            errors.append(f"skill name/folder mismatch: {folder.name} != {name}")
        if not desc_match or len(desc_match.group(1).strip()) < 20:
            errors.append(f"missing or weak description: {skill_path.relative_to(root)}")

        agent_path = folder / "agents/openai.yaml"
        if not agent_path.exists():
            errors.append(f"missing agents/openai.yaml: {folder.name}")
            continue
        agent_text = agent_path.read_text(encoding="utf-8")
        short = re.search(r'^\s*short_description:\s*"([^"]+)"', agent_text, re.M)
        prompt = re.search(r'^\s*default_prompt:\s*"([^"]+)"', agent_text, re.M)
        if not short or not 25 <= len(short.group(1)) <= 64:
            errors.append(f"short_description must be 25..64 chars: {folder.name}")
        if not prompt or f"${folder.name}" not in prompt.group(1):
            errors.append(f"default_prompt must mention ${folder.name}: {folder.name}")

    link_pattern = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")
    for path in markdown_files:
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"broken link: {path.relative_to(root)} -> {target}")

    return {
        "id": "skill_structure",
        "pass": not errors,
        "public_skill_count": len(public_skills),
        "stage_count": len(stage_files),
        "errors": errors,
    }


def command_specs(root: Path, no_write: bool, include_figure_pytest: bool) -> list[dict[str, Any]]:
    py = sys.executable
    checks: list[dict[str, Any]] = []

    def add(check_id: str, script: str, *args: str, cwd: Path | None = None) -> None:
        checks.append({
            "id": check_id,
            "cmd": [py, str(root / script), *args],
            "cwd": str(cwd or root),
        })

    no_write_args = ("--no-write",) if no_write else ()
    add("orchestrator_audit", ".agents/skills/cumcm/scripts/audit_orchestrator_consistency.py", "--root", str(root), *no_write_args)
    add("orchestrator_selftest", ".agents/skills/cumcm/scripts/selftest_orchestrator_consistency.py", "--root", str(root), *no_write_args)
    add("skill_execution_plan", ".agents/skills/cumcm/scripts/selftest_skill_execution_plan.py", "--root", str(root), *no_write_args)
    add("user_confirmations", ".agents/skills/cumcm/scripts/selftest_user_confirmations.py", "--root", str(root), *no_write_args)
    add("similarity_selftest", ".agents/skills/cumcm/scripts/selftest_similarity_gate.py", "--root", str(root), *no_write_args)
    add("originality_consumers", ".agents/skills/cumcm/scripts/selftest_originality_consumers.py", "--root", str(root), *no_write_args)
    add("router_parity", ".agents/skills/cumcm-figure-router/scripts/selftest_router_parity.py", "--root", str(root), *no_write_args)
    add("visual_audits", ".agents/skills/cumcm/scripts/selftest_visual_audits.py", "--root", str(root), *no_write_args)
    add("language_audit", ".agents/skills/cumcm/scripts/selftest_language_audit.py", "--root", str(root), *no_write_args)
    add("provenance_registry", ".agents/skills/cumcm/scripts/selftest_provenance_registry.py")
    add("national_artifact_gates", ".agents/skills/cumcm/scripts/selftest_artifact_national_gates.py")
    add("corpus_voice", ".agents/skills/cumcm-deai/scripts/selftest_corpus_voice.py")
    add("authentic_expression", ".agents/skills/cumcm-deai/scripts/selftest_authentic_expression.py")
    add("formula_readability", ".agents/skills/cumcm-notation/scripts/selftest_formula_readability.py")
    add("figure_table_narration", ".agents/skills/cumcm-paper/scripts/selftest_figure_table_narration.py")
    add("question_depth", ".agents/skills/cumcm-paper/scripts/selftest_question_depth.py", "--root", str(root), *no_write_args)
    add("compile_binding", ".agents/skills/cumcm-paper/scripts/selftest_compile_binding.py", "--no-write")
    add("first_draft_gate", ".agents/skills/cumcm-paper/scripts/selftest_first_draft_gate.py", "--root", str(root), *no_write_args)
    add("section_chain_bindings", ".agents/skills/cumcm-paper/scripts/selftest_section_chain_bindings.py")
    add("single_tex_delivery", ".agents/skills/cumcm-paper/scripts/selftest_single_tex_delivery.py")
    add("ab_model_catalog_validation", ".agents/skills/cumcm-model-tournament/scripts/validate_ab_model_catalog.py")
    add("ab_model_catalog_selftest", ".agents/skills/cumcm-model-tournament/scripts/selftest_ab_model_catalog.py")
    answer_benchmark_args = ["--root", str(root)]
    if not (root / "最终效果" / "高教杯优秀论文").exists():
        answer_benchmark_args.append("--allow-missing-source-files")
    add("answer_benchmark_validation", ".agents/skills/cumcm-blind-benchmark/scripts/validate_answer_benchmarks.py", *answer_benchmark_args)
    add("answer_benchmark_selftest", ".agents/skills/cumcm-blind-benchmark/scripts/selftest_answer_benchmarks.py", "--root", str(root), *no_write_args)
    add("grading_standard_validation", ".agents/skills/cumcm-blind-benchmark/scripts/validate_grading_standards.py")

    checks.append({
        "id": "review_compatibility_pytest",
        "cmd": [py, "-m", "pytest", ".agents/skills/cumcm-review/tests/test_audit_compatibility.py", "-q"],
        "cwd": str(root),
    })
    if include_figure_pytest:
        checks.append({
            "id": "figure_runtime_pytest",
            "cmd": [py, "-m", "pytest", "-q"],
            "cwd": str(root / "figure_mcp"),
        })
    return checks


def run_command(spec: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    started = time.perf_counter()
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    try:
        completed = subprocess.run(
            spec["cmd"],
            cwd=spec["cwd"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
        return {
            "id": spec["id"],
            "pass": completed.returncode == 0,
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "command": spec["cmd"],
            "stdout_tail": completed.stdout[-4000:].strip(),
            "stderr_tail": completed.stderr[-4000:].strip(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": spec["id"],
            "pass": False,
            "returncode": None,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "command": spec["cmd"],
            "stdout_tail": str(exc.stdout or "")[-4000:],
            "stderr_tail": f"timeout after {timeout_seconds}s",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/skill-preflight.json")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--skip-figure-pytest", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    results: list[dict[str, Any]] = [inspect_skill_structure(root)]
    print(f"{'PASS' if results[0]['pass'] else 'FAIL'} skill_structure")
    for error in results[0].get("errors", []):
        print(f"  - {error}")
    for spec in command_specs(root, args.no_write, not args.skip_figure_pytest):
        result = run_command(spec, args.timeout_seconds)
        results.append(result)
        print(f"{'PASS' if result['pass'] else 'FAIL'} {result['id']} ({result['elapsed_seconds']:.1f}s)")

    report = {
        "schema_version": 1,
        "pass": all(item["pass"] for item in results),
        "root": str(root),
        "check_count": len(results),
        "failed": [item["id"] for item in results if not item["pass"]],
        "checks": results,
        "scope_note": "Deterministic local preflight only; held-out full-paper and blind-answer evaluations remain separate release gates.",
    }
    if not args.no_write:
        output = root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("pass", "check_count", "failed")}, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
