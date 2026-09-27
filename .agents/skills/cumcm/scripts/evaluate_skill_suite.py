#!/usr/bin/env python
"""Aggregate completed CUMCM projects into an excellent-paper skill regression gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from benchmark_corpus import originality_report_issues

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


DIMENSIONS = (
    "题意与口径",
    "数据理解",
    "模型适配",
    "数学严谨",
    "求解实现",
    "验证强度",
    "结果价值",
    "证据追溯",
    "可复现性",
    "写作原创",
    "可视表达",
    "提交就绪",
)


def read_json(path: Path) -> tuple[dict | None, str | None]:
    if not path.exists():
        return None, f"missing: {path}"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"invalid json {path}: {exc}"
    if not isinstance(value, dict):
        return None, f"json root is not object: {path}"
    return value, None


def evaluate_scorecard(root: Path, scorecard: dict, track: str = "excellent") -> tuple[dict, list[str]]:
    issues: list[str] = []
    national = track == "national-first"
    dimensions = scorecard.get("dimensions")
    if not isinstance(dimensions, dict):
        return {"total": 0, "minimum": 0}, ["评分卡 dimensions missing"]
    missing = [name for name in DIMENSIONS if name not in dimensions]
    extra = [name for name in dimensions if name not in DIMENSIONS]
    if missing:
        issues.append(f"评分卡缺维度: {', '.join(missing)}")
    if extra:
        issues.append(f"评分卡未知维度: {', '.join(extra)}")

    scores = []
    for name in DIMENSIONS:
        item = dimensions.get(name, {})
        if isinstance(item, dict) and item.get("status") == "REVIEW_REQUIRED":
            issues.append(f"{name} 仍为 REVIEW_REQUIRED")
            continue
        score = item.get("score") if isinstance(item, dict) else None
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 5:
            issues.append(f"{name} 分数无效")
            continue
        scores.append(float(score))
        evidence = item.get("evidence", [])
        if not isinstance(evidence, list) or not evidence:
            issues.append(f"{name} 缺证据路径")
            continue
        for relative in evidence:
            if not isinstance(relative, str) or not (root / relative).exists():
                issues.append(f"{name} 证据不存在: {relative}")

    computed_total = sum(scores)
    stated_total = scorecard.get("total")
    if stated_total != computed_total:
        issues.append(f"评分卡总分不一致: stated={stated_total}, computed={computed_total}")
    if scorecard.get("p0_findings"):
        issues.append("评分卡仍有 P0 findings")
    if scorecard.get("p1_findings"):
        issues.append("评分卡仍有 P1 findings")
    if not scorecard.get("hard_gates_pass"):
        issues.append("评分卡 hard_gates_pass 不是 true")
    expected_verdict = "PASS_NATIONAL_FIRST_CANDIDATE" if national else "PASS_EXCELLENT_CANDIDATE"
    if scorecard.get("verdict") != expected_verdict:
        issues.append(f"评分卡 verdict 不是 {expected_verdict}")
    if scorecard.get("review_required"):
        issues.append("评分卡仍含 REVIEW_REQUIRED 项")
    return {
        "total": computed_total,
        "minimum": min(scores) if scores else 0,
    }, issues


def evaluate_project(root: Path, track: str = "excellent") -> dict:
    root = root.resolve()
    issues: list[str] = []
    evidence, error = read_json(root / "求解" / "证据审计.json")
    if error:
        issues.append(error)
    elif not evidence.get("pass"):
        issues.append("求解证据审计未通过")

    artifacts, error = read_json(root / "审查" / "自动审查.json")
    if error:
        issues.append(error)
    elif not artifacts.get("pass"):
        issues.append("自动审查未通过")
    else:
        counts = artifacts.get("counts", {})
        if not isinstance(counts, dict):
            counts = {}
        body_pages = counts.get("body_pages")
        if not isinstance(body_pages, int) or isinstance(body_pages, bool):
            issues.append("自动审查缺少按 appendix:start - body:start 计算的官方正文页数")
        elif body_pages > 30:
            issues.append(f"官方正文页数超过 30 页上限: {body_pages}")
        if counts.get("body_start_page") is None or counts.get("appendix_start_page") is None:
            issues.append("自动审查缺少 body:start 或 appendix:start 页码")
        if counts.get("question_depth_audit_pass") is not True:
            issues.append("自动审查未绑定通过的逐问正文深度审计")

    depth, error = read_json(root / "审查" / "正文深度审计.json")
    if error:
        issues.append(error)
    elif depth.get("pass") is not True or depth.get("phase") != "final":
        issues.append("逐问正文深度最终审计未通过")

    first_draft, error = read_json(root / "审查" / "首份可交付初稿门禁.json")
    if error:
        issues.append(error)
    elif (
        first_draft.get("pass") is not True
        or first_draft.get("status") != "PASS_FIRST_DELIVERABLE_DRAFT"
        or first_draft.get("build_status") != "FIRST_DRAFT_CANDIDATE"
        or first_draft.get("deliverable") is not True
    ):
        issues.append("首份可交付初稿门禁未通过，内部失败构建不得冒充初稿")

    execution, error = read_json(root / "审查" / "skill-execution-audit.json")
    if error:
        issues.append(error)
    elif execution.get("pass") is not True or execution.get("all_applicable_completed") is not True:
        issues.append("适用 Skills/STAGE 执行覆盖未闭环")

    benchmark, error = read_json(root / "审查" / "优秀论文对标.json")
    if error:
        issues.append(error)
    else:
        # Share the producer's binding/coverage contract; old abstract-only PASS is stale.
        issues.extend(originality_report_issues(benchmark, root / "论文" / "论文.pdf"))

    visual, error = read_json(root / "审查" / "视觉审查.json")
    if error:
        issues.append(error)
    elif not visual.get("pass"):
        issues.append("视觉审查未通过")
    elif visual.get("chart_type_appropriateness_pass") is not True:
        issues.append("视觉审查未明确图型适配通过")

    deai, error = read_json(root / "审查" / "去AI化审查.json")
    if error:
        issues.append(error)
    elif not deai.get("pass"):
        issues.append("去 AI 化审查未通过")

    language, error = read_json(root / "审查" / "section-chain" / "language-audit.json")
    if error:
        issues.append(error)
    else:
        if language.get("pass") is not True:
            issues.append("正文语言自动门禁未通过")
        if language.get("hard_count") != 0:
            issues.append(f"正文仍有硬禁表达: {language.get('hard_count')}")

    chain, error = read_json(root / "审查" / "section-chain" / "chain-audit.json")
    if error:
        issues.append(error)
    elif chain.get("pass") is not True:
        issues.append("章节子技能链审计未通过")

    manifest, error = read_json(root / "审查" / "section-chain" / "manifest.json")
    if error:
        issues.append(error)
    else:
        cross = manifest.get("cross_cutting", {})
        if not isinstance(cross, dict):
            issues.append("章节清单 cross_cutting 无效")
            cross = {}
        for flag, filename, label in (
            ("figures_used", "figure-style-audit.json", "数据图形风格审计"),
            ("diagrams_used", "diagram-style-audit.json", "TikZ/Visio 图形风格审计"),
        ):
            if cross.get(flag):
                report, report_error = read_json(root / "审查" / filename)
                if report_error:
                    issues.append(report_error)
                elif report.get("pass") is not True:
                    issues.append(f"{label}未通过")

    reproduction, error = read_json(root / "审查" / "复现抽查.json")
    if error:
        issues.append(error)
    elif not reproduction.get("pass"):
        issues.append("复现抽查未通过")

    blind, error = read_json(root / "审查" / "盲测答案评估.json")
    if error:
        issues.append(error)
    else:
        if blind.get("pass") is not True:
            issues.append("盲测答案评估未通过")
        if blind.get("reference_visible_during_solve") is not False:
            issues.append("盲测答案在求解期并非隐藏")
        if blind.get("answer_frozen_before_reference") is not True:
            issues.append("盲测未证明答案先于参考冻结")
        if blind.get("constraints_pass") is not True:
            issues.append("盲测约束检查未通过")
        questions = blind.get("questions")
        if not isinstance(questions, dict) or not questions:
            issues.append("盲测答案评估缺逐问记录")
        else:
            for name, item in questions.items():
                if not isinstance(item, dict) or item.get("通过") is not True:
                    issues.append(f"盲测答案评估未通过: {name}")

    independent, error = read_json(root / "审查" / "独立评审.json")
    if error:
        issues.append(error)
    else:
        if not independent.get("pass"):
            issues.append("独立评审未通过")
        if independent.get("p0_findings"):
            issues.append("独立评审仍有 P0 findings")
        if independent.get("p1_findings"):
            issues.append("独立评审仍有 P1 findings")
        total = independent.get("total")
        minimum = independent.get("minimum_dimension")
        required_total = 57 if track == "national-first" else 54
        if not isinstance(total, (int, float)) or isinstance(total, bool) or total < required_total:
            issues.append(f"独立评审总分低于 {required_total}: {total}")
        if not isinstance(minimum, (int, float)) or isinstance(minimum, bool) or minimum < 4:
            issues.append(f"独立评审最低维度低于 4: {minimum}")

    scorecard, error = read_json(root / "审查" / "评分卡.json")
    score_summary = {"total": 0, "minimum": 0}
    if error:
        issues.append(error)
    else:
        score_summary, score_issues = evaluate_scorecard(root, scorecard, track)
        issues.extend(score_issues)

    required_total = 57 if track == "national-first" else 54
    if score_summary["total"] < required_total:
        issues.append(f"总分低于 {required_total}: {score_summary['total']}")
    if score_summary["minimum"] < 4:
        issues.append(f"最低维度低于 4: {score_summary['minimum']}")

    if track == "national-first":
        dimensions = scorecard.get("dimensions", {}) if isinstance(scorecard, dict) else {}
        visual_item = dimensions.get("可视表达", {}) if isinstance(dimensions, dict) else {}
        if not isinstance(visual_item, dict) or visual_item.get("score") != 5:
            issues.append("国一模式可视表达必须为 5")
        national_gate, gate_error = read_json(root / "审查" / "NATIONAL_FIRST_SCORECARD.json")
        if gate_error:
            issues.append(gate_error)
        elif national_gate.get("pass") is not True or national_gate.get("verdict") != "PASS_NATIONAL_FIRST_CANDIDATE":
            issues.append("国一总门禁未通过")

    return {
        "root": str(root),
        "pass": not issues,
        "score": score_summary,
        "body_pages": (
            artifacts.get("counts", {}).get("body_pages")
            if isinstance(artifacts, dict) and isinstance(artifacts.get("counts"), dict)
            else None
        ),
        "issues": issues,
    }


def write_report(output_dir: Path, result: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "skills回归评测.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# CUMCM Skills 回归评测",
        "",
        f"结论：{'PASS' if result['pass'] else 'FAIL'}",
        f"通过项目：{result['passed_projects']}/{result['project_count']}",
        "",
    ]
    for item in result["projects"]:
        lines.extend(
            [
                f"## {item['root']}",
                f"- 结论：{'PASS' if item['pass'] else 'FAIL'}",
                f"- 总分：{item['score']['total']}",
                f"- 最低维度：{item['score']['minimum']}",
                f"- 官方正文页数：{item['body_pages']}",
            ]
        )
        lines.extend(f"- 问题：{issue}" for issue in item["issues"])
        lines.append("")
    (output_dir / "skills回归评测.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projects", nargs="+", required=True)
    parser.add_argument("--min-projects", type=int, default=3)
    parser.add_argument("--output", default="审查")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--track", choices=("excellent", "national-first"), default="excellent")
    args = parser.parse_args()

    projects = [evaluate_project(Path(path), args.track) for path in args.projects]
    passed = sum(1 for item in projects if item["pass"])
    result = {
        "pass": len(projects) >= args.min_projects and passed == len(projects),
        "project_count": len(projects),
        "passed_projects": passed,
        "minimum_projects": args.min_projects,
        "projects": projects,
    }
    if args.no_write:
        print(json.dumps(result, ensure_ascii=False))
    else:
        write_report(Path(args.output).resolve(), result)
        print(f"Wrote {Path(args.output).resolve() / 'skills回归评测.md'}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
