#!/usr/bin/env python3
"""Verify claim-driven figure authority and reject quota or unauthorised guidance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

STATE = {
    "page_policy": {
        "body_definition": "body:start through the page before appendix:start; includes AI statement and references; excludes abstract and appendix",
        "body_page_max": 30,
    }
}

CLEAN = """---
name: cumcm
---

# CUMCM 优秀论文总控

## 核心原则

1. 官方口径正文不得超过 30 页；不以页数、图数、表数和公式数灌水。
2. 图数不设上下限，由待证明命题、不可替代证据职责和正文解读决定。
3. 复杂候选通常规划 2--3 张特色主视觉图，不适合时记录豁免理由。

## 阶段 0

校准语料。
"""

# Rule 2 keeps the subject word 图数 but replaces the computed authority with a fixed range.
QUOTA = CLEAN.replace(
    "2. 图数不设上下限，由待证明命题、不可替代证据职责和正文解读决定。",
    "2. **图形数量硬性锁定（16 ~ 22 幅）**：正式注册的插图数量硬性限制在 **16 ~ 22 幅**。",
)

# States figure guidance but names no claim/evidence authority.
NO_AUTHORITY = CLEAN.replace(
    "2. 图数不设上下限，由待证明命题、不可替代证据职责和正文解读决定。",
    "2. 图数按经验灵活安排。",
)

DUPLICATE_RULE = CLEAN.replace(
    "3. 复杂候选通常规划 2--3 张特色主视觉图，不适合时记录豁免理由。",
    "2. 复杂候选通常规划 2--3 张特色主视觉图，不适合时记录豁免理由。",
)

NESTED_RULE = CLEAN.replace(
    "3. 复杂候选通常规划 2--3 张特色主视觉图，不适合时记录豁免理由。",
    "    3. 复杂候选通常规划 2--3 张特色主视觉图，不适合时记录豁免理由。",
)

STALE_PAGE_RANGE = CLEAN.replace(
    "官方口径正文不得超过 30 页",
    "官方口径正文必须落在 20--30 页",
)

INVALID_PAGE_MAX = {"page_policy": {**STATE["page_policy"], "body_page_max": 35}}

# Sub-skill and stage bodies: the figure-count invariants must also hold in routed modules
# (round 2 fixed the orchestrator while the same quota survived in cumcm-figures).
SUB_QUOTA = """---
name: cumcm-figures
---

# 数据图形

1. **图形数量硬性约束（16 ~ 22 幅）**：正式注册的图号数量必须硬性限制在 16 ~ 22 幅之间。
"""

SUB_CLEAN = """---
name: cumcm-figures
---

# 数据图形

1. 图形数量不设上下限，由待证明命题、不可替代证据职责和正文解读决定。
"""

REFERENCE_QUOTA = """# 图形路由

1. 图形数量硬性规定（16 ~ 22 幅）：正式插图数量严格限制为 16 ~ 22 幅。
"""

REFERENCE_CLEAN = """# 图形路由

图形数量不设上下限，由待证明命题、不可替代证据职责和正文解读决定。
"""

CASES: dict[
    str,
    tuple[str, bool, str | None, dict[str, str] | None, dict[str, str] | None],
] = {
    "clean_defers_to_gate": (CLEAN, True, None, None, None),
    "absolute_figure_quota": (QUOTA, False, "absolute_figure_quota", None, None),
    "figure_count_authority": (NO_AUTHORITY, False, "figure_count_authority", None, None),
    "duplicate_rule_number": (DUPLICATE_RULE, False, "rule_numbering", None, None),
    "nested_rule_number": (NESTED_RULE, False, "rule_numbering", None, None),
    "stale_page_range": (STALE_PAGE_RANGE, False, "page_policy_mismatch", None, None),
    "sub_skill_quota": (
        CLEAN,
        False,
        "absolute_figure_quota",
        {"cumcm-figures": SUB_QUOTA},
        None,
    ),
    "sub_skill_clean_authority": (CLEAN, True, None, {"cumcm-figures": SUB_CLEAN}, None),
    "stage_module_quota": (
        CLEAN,
        False,
        "absolute_figure_quota",
        {"stage:cumcm-model-writing": SUB_QUOTA.replace("cumcm-figures", "cumcm-model-writing")},
        None,
    ),
    "stage_module_clean_authority": (
        CLEAN,
        True,
        None,
        {"stage:cumcm-model-writing": SUB_CLEAN.replace("cumcm-figures", "cumcm-model-writing")},
        None,
    ),
    "reference_quota": (
        CLEAN,
        False,
        "absolute_figure_quota",
        None,
        {"cumcm/references/figure-routing.md": REFERENCE_QUOTA},
    ),
    "reference_clean": (
        CLEAN,
        True,
        None,
        None,
        {"cumcm/references/figure-routing.md": REFERENCE_CLEAN},
    ),
}


def run_case(
    script: Path,
    root: Path,
    body: str | None,
    expected_pass: bool,
    expected_pattern: str | None,
    sub_skills: dict[str, str] | None = None,
    references: dict[str, str] | None = None,
    state_payload: dict | None = None,
) -> dict:
    # Modules live in root/<name>/{SKILL,STAGE}.md so the audit's sibling scan sees
    # exactly this case's fixtures and nothing else. A ``stage:`` prefix selects STAGE.md.
    skill = root / "cumcm" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    if body is not None:
        skill.write_text(body, encoding="utf-8")
    for name, sub_body in (sub_skills or {}).items():
        is_stage = name.startswith("stage:")
        folder = name.removeprefix("stage:")
        sub_path = root / folder / ("STAGE.md" if is_stage else "SKILL.md")
        sub_path.parent.mkdir(parents=True, exist_ok=True)
        sub_path.write_text(sub_body, encoding="utf-8")
    for relative, reference_body in (references or {}).items():
        reference_path = root / relative
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_text(reference_body, encoding="utf-8")
    state = root / ".cumcm_state.json"
    state.write_text(json.dumps(state_payload or STATE, ensure_ascii=False), encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--root",
            str(root),
            "--skill",
            str(skill),
            "--state",
            str(state),
            "--no-write",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    try:
        payload = json.loads(completed.stdout.strip() or "{}")
    except json.JSONDecodeError:
        payload = {}
    actual_pass = completed.returncode == 0 and payload.get("pass") is True
    patterns = payload.get("patterns") or []
    pattern_pass = expected_pattern is None or expected_pattern in patterns
    return {
        "expected_pass": expected_pass,
        "actual_pass": actual_pass,
        "expected_pattern": expected_pattern,
        "patterns": patterns,
        "pass": actual_pass == expected_pass and pattern_pass,
        "returncode": completed.returncode,
        "finding_count": payload.get("finding_count"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/orchestrator-consistency-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    script = Path(__file__).resolve().parent / "audit_orchestrator_consistency.py"
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-orchestrator-selftest-") as tmp:
        base = Path(tmp)
        for name, (body, expected_pass, expected_pattern, sub_skills, references) in CASES.items():
            results[name] = run_case(
                script,
                base / name,
                body,
                expected_pass,
                expected_pattern,
                sub_skills,
                references,
            )
        results["invalid_page_max"] = run_case(
            script,
            base / "invalid_page_max",
            CLEAN,
            False,
            "page_policy_mismatch",
            state_payload=INVALID_PAGE_MAX,
        )
        # Fail closed when the orchestrator itself is absent.
        results["skill_missing"] = run_case(script, base / "missing", None, False, "skill_missing")

    result = {
        "schema_version": 2,
        "pass": all(item["pass"] for item in results.values()),
        "case_count": len(results),
        "cases": results,
    }
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(results)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
