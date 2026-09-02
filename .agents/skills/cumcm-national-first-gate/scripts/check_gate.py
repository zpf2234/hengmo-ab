#!/usr/bin/env python
"""Fail-closed national-first gate for a completed CUMCM project."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

DIMENSIONS = (
    "题意与口径", "数据理解", "模型适配", "数学严谨", "求解实现", "验证强度",
    "结果价值", "证据追溯", "可复现性", "写作原创", "可视表达", "提交就绪",
)


def load(root: Path, relative: str, issues: list[str]) -> dict | None:
    path = root / relative
    if not path.is_file():
        issues.append(f"missing: {relative}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(f"invalid json: {relative}: {exc}")
        return None
    if not isinstance(value, dict):
        issues.append(f"json root is not object: {relative}")
        return None
    return value


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def pass_field(data: dict | None, label: str, issues: list[str]) -> None:
    if data is not None and data.get("pass") is not True:
        issues.append(f"{label}未通过")


def scorecard_gate(root: Path, data: dict | None, issues: list[str]) -> dict:
    result = {"total": 0.0, "minimum": 0.0, "visual": None}
    if data is None:
        return result
    dims = data.get("dimensions")
    if not isinstance(dims, dict) or set(dims) != set(DIMENSIONS):
        issues.append("评分卡必须恰含 12 个标准维度")
        return result
    scores = []
    for name in DIMENSIONS:
        item = dims[name]
        if not isinstance(item, dict) or item.get("status") == "REVIEW_REQUIRED":
            issues.append(f"评分卡未完成主观复核: {name}")
            continue
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 5:
            issues.append(f"评分无效: {name}")
            continue
        scores.append(float(score))
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            issues.append(f"评分缺证据: {name}")
        else:
            for rel in evidence:
                if not isinstance(rel, str) or not (root / rel).exists():
                    issues.append(f"评分证据不存在: {name}: {rel}")
    result = {"total": sum(scores), "minimum": min(scores) if scores else 0.0,
              "visual": (dims.get("可视表达") or {}).get("score")}
    if data.get("total") != result["total"]:
        issues.append("评分卡声明总分与逐维合计不一致")
    if result["total"] < 57:
        issues.append(f"总分低于 57: {result['total']}")
    if result["minimum"] < 4:
        issues.append(f"最低维度低于 4: {result['minimum']}")
    if result["visual"] != 5:
        issues.append(f"可视表达必须为 5: {result['visual']}")
    if data.get("p0_findings") or data.get("p1_findings"):
        issues.append("评分卡仍有 P0/P1")
    if data.get("hard_gates_pass") is not True:
        issues.append("评分卡硬门禁未通过")
    if data.get("review_required"):
        issues.append("评分卡仍有 REVIEW_REQUIRED")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    issues: list[str] = []

    evidence = load(root, "求解/证据审计.json", issues)
    artifacts = load(root, "审查/自动审查.json", issues)
    benchmark = load(root, "审查/优秀论文对标.json", issues)
    visual = load(root, "审查/视觉审查.json", issues)
    deai = load(root, "审查/去AI化审查.json", issues)
    language = load(root, "审查/section-chain/language-audit.json", issues)
    voice = load(root, "审查/section-chain/corpus-voice-audit.json", issues)
    narration = load(root, "审查/section-chain/figure-table-narration.json", issues)
    chain = load(root, "审查/section-chain/chain-audit.json", issues)
    reproduction = load(root, "审查/复现抽查.json", issues)
    freeze = load(root, "审查/盲测冻结清单.json", issues)
    blind = load(root, "审查/盲测答案评估.json", issues)
    independent = load(root, "审查/独立评审.json", issues)
    scorecard = load(root, "审查/评分卡.json", issues)

    for data, label in ((evidence,"证据审计"),(artifacts,"自动审查"),(visual,"视觉审查"),
                        (deai,"去AI化审查"),(language,"语言审计"),(voice,"语料声纹审计"),
                        (narration,"图表叙述审计"),(chain,"章节链审计"),
                        (reproduction,"复现抽查"),(blind,"盲测"),(independent,"独立评审")):
        pass_field(data, label, issues)

    if benchmark is not None:
        # Consume the owner's recorded verdict (benchmark_corpus.py validates manual review
        # and blocks manual release of high similarity); do not re-derive a weaker rule here.
        gate = benchmark.get("originality_gate")
        verdict = gate.get("verdict") if isinstance(gate, dict) else None
        if verdict is not None:
            if verdict not in ("PASS", "PASS_WITH_MANUAL_REVIEW"):
                issues.append(f"优秀论文对标/原创性裁定未放行：{verdict}")
        else:
            similarity = benchmark.get("similarity", {})
            status = similarity.get("status") if isinstance(similarity, dict) else None
            if status != "PASS":
                issues.append("优秀论文对标缺 originality_gate 裁定且相似度实测非 PASS，原创未证明")
    actions = root / "审查" / "REVISION_ACTIONS.md"
    if not actions.is_file():
        issues.append("missing: 审查/REVISION_ACTIONS.md")

    if blind is not None:
        if blind.get("reference_visible_during_solve") is not False or blind.get("answer_frozen_before_reference") is not True:
            issues.append("盲测隔离或先冻结条件未满足")
        if blind.get("constraints_pass") is not True:
            issues.append("盲测约束未通过")
        questions = blind.get("questions")
        if not isinstance(questions, dict) or not questions or any(not isinstance(v, dict) or v.get("通过") is not True for v in questions.values()):
            issues.append("盲测逐问未全部通过")
        if freeze is not None and blind.get("freeze_manifest_sha256") != freeze.get("manifest_sha256"):
            issues.append("盲测评估未绑定当前冻结清单")

    if independent is not None:
        if independent.get("p0_findings") or independent.get("p1_findings"):
            issues.append("独立评审仍有 P0/P1")
        if not isinstance(independent.get("total"), (int, float)) or independent.get("total") < 57:
            issues.append("独立评审总分低于 57")
        if not isinstance(independent.get("minimum_dimension"), (int, float)) or independent.get("minimum_dimension") < 4:
            issues.append("独立评审最低维度低于 4")

    adversarial = []
    for role in ("题意", "数学", "表达"):
        item = load(root, f"审查/对抗评审_{role}.json", issues)
        adversarial.append(item)
        if item is not None:
            pass_field(item, f"对抗评审_{role}", issues)
            if item.get("open_p0") or item.get("open_p1") or item.get("p0_findings") or item.get("p1_findings"):
                issues.append(f"对抗评审_{role}仍有 P0/P1")

    summary = scorecard_gate(root, scorecard, issues)
    pdf = root / "论文" / "论文.pdf"
    pdf_hash = digest(pdf) if pdf.is_file() else None
    if pdf_hash is None:
        issues.append("missing: 论文/论文.pdf")
    if scorecard is not None and scorecard.get("pdf_sha256") != pdf_hash:
        issues.append("评分卡未绑定当前 PDF SHA-256")
    if independent is not None and independent.get("pdf_sha256") not in (None, pdf_hash):
        issues.append("独立评审绑定的 PDF 与当前版本不一致")

    blocked_markers = [x for x in issues if x.startswith("missing: 求解/证据审计") or "盲测隔离" in x]
    verdict = "PASS_NATIONAL_FIRST_CANDIDATE" if not issues else ("BLOCKED" if blocked_markers else "REVISE_NATIONAL_FIRST_CANDIDATE")
    result = {"pass": not issues, "verdict": verdict, "generated_at": datetime.now(timezone.utc).isoformat(),
              "pdf_sha256": pdf_hash, "score": summary, "issues": issues}

    if not args.no_write:
        audit = root / "审查"
        audit.mkdir(parents=True, exist_ok=True)
        (audit / "NATIONAL_FIRST_SCORECARD.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (audit / "PDF_HASH.json").write_text(json.dumps({"path":"论文/论文.pdf","sha256":pdf_hash}, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = ["# 国一候选最终门禁", "", f"结论：`{verdict}`", f"总分：{summary['total']}",
                 f"最低维度：{summary['minimum']}", f"PDF SHA-256：`{pdf_hash}`", "", "## 阻断项"]
        lines += ([f"- {x}" for x in issues] or ["- 无"])
        (audit / "FINAL_GATE_REPORT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
