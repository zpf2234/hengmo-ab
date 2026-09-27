#!/usr/bin/env python3
"""Audit CUMCM prose for factual preservation and expression-review signals.

The tool never estimates whether text was written by AI.  With ``--baseline``
it flags changed/lost numbers, math expressions, citations, references and
claim identifiers. Fewer copies of a retained prose number require review.
Lexical source/strength/condition signals are not semantic verification.
Exit code 0 indicates completion without a mechanical integrity failure only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SUPPORTED_SUFFIXES = {".tex", ".md", ".txt"}

INTERNAL_META_TERMS = (
    "全链路",
    "工作流",
    "门禁",
    "冻结口径",
    "口径锁定",
    "交付闭环",
    "证据矩阵",
    "验收标准",
    "部署",
    "流水线",
)

METHOD_TERMS = (
    "AHP",
    "TOPSIS",
    "VIKOR",
    "CRITIC",
    "熵权法",
    "主成分分析",
    "聚类",
    "随机森林",
    "支持向量机",
    "神经网络",
    "遗传算法",
    "粒子群",
    "模拟退火",
    "差分进化",
    "蒙特卡洛",
    "线性规划",
    "整数规划",
    "动态规划",
    "CP-SAT",
    "Spearman",
    "Kendall",
)

PROCESS_PATTERNS = (
    ("trial", re.compile(r"(?:最初|开始时|起初)[^。！？\n]{0,50}(?:尝试|采用|考虑)")),
    ("time_limit", re.compile(r"(?:由于|考虑到)[^。！？\n]{0,20}时间(?:限制|有限|不足)")),
    ("abandoned_route", re.compile(r"(?:发现|结果表明)[^。！？\n]{0,50}(?:不适用|不可行|效果较差).{0,20}(?:改为|转而)")),
)

QUESTION_HEADING = re.compile(
    r"(?m)^(?:"
    r"\\(?:sub)*section\{[^{}\n]*问题[一二三四五六七八九十0-9]+[^{}\n]*\}"
    r"|#{1,6}\s*[^\n]*问题[一二三四五六七八九十0-9]+[^\n]*"
    r"|\s*问题[一二三四五六七八九十0-9]+[^\n]*"
    r")"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"unsupported input format: {path.suffix or '<none>'}; use .tex, .md, or .txt")
    return path.read_text(encoding="utf-8")


def strip_tex_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%.*$", "", text)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", "", text)


def extract_math(text: str) -> list[str]:
    source = strip_tex_comments(text)
    expressions: list[str] = []
    patterns = (
        re.compile(r"\$\$(.+?)\$\$", re.S),
        re.compile(r"\\\[(.+?)\\\]", re.S),
        re.compile(
            r"\\begin\{(equation\*?|align\*?|gather\*?|multline\*?)\}(.+?)\\end\{\1\}",
            re.S,
        ),
        re.compile(r"(?<!\\)\$(?!\$)(.+?)(?<!\\)\$", re.S),
    )
    for index, pattern in enumerate(patterns):
        for match in pattern.finditer(source):
            body = match.group(2) if index == 2 else match.group(1)
            body = re.sub(r"\\label\{[^{}]+\}", "", body)
            expressions.append(normalize_space(body))
    return [item for item in expressions if item]


def extract_protected(text: str) -> dict[str, Counter[str]]:
    source = strip_tex_comments(text)
    number_pattern = re.compile(
        r"(?<![A-Za-z\\])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?:\s*[%‰])?(?![A-Za-z])"
    )
    citation_pattern = re.compile(r"\\cite[a-zA-Z]*\{[^{}]+\}|(?<!\w)\[(?:\d+)(?:\s*[-,，]\s*\d+)*\]")
    reference_pattern = re.compile(r"\\(?:ref|eqref|autoref)\{[^{}]+\}")
    label_pattern = re.compile(r"\\label\{[^{}]+\}|\bclaim[_-][A-Za-z0-9_.:-]+\b", re.I)
    return {
        "numbers": Counter(normalize_space(item) for item in number_pattern.findall(source)),
        "math": Counter(extract_math(source)),
        "citations": Counter(normalize_space(item) for item in citation_pattern.findall(source)),
        "references": Counter(normalize_space(item) for item in reference_pattern.findall(source)),
        "labels_and_claims": Counter(normalize_space(item) for item in label_pattern.findall(source)),
    }


def counter_delta(before: Counter[str], after: Counter[str]) -> dict[str, list[dict[str, Any]]]:
    def rows(delta: Counter[str]) -> list[dict[str, Any]]:
        return [{"token": token, "count": count} for token, count in sorted(delta.items()) if count > 0]

    return {"removed": rows(before - after), "added": rows(after - before)}


def compare_protected(baseline: str, revised: str) -> dict[str, Any]:
    before = extract_protected(baseline)
    after = extract_protected(revised)
    categories: dict[str, Any] = {}
    changed = False
    review = False
    for name in before:
        delta = counter_delta(before[name], after[name])
        category_changed = bool(delta["removed"] or delta["added"])
        # Fewer copies of a retained prose number can be legitimate deduplication.
        # It is never auto-approved: the surrounding claims must still be checked.
        dedup = bool(category_changed and name == "numbers" and not delta["added"]
                     and all(after[name][row["token"]] > 0 for row in delta["removed"]))
        review = review or dedup
        changed = changed or (category_changed and not dedup)
        categories[name] = {
            "pass": None if dedup else not category_changed,
            "review_required": dedup,
            "baseline_count": sum(before[name].values()),
            "revised_count": sum(after[name].values()),
            **delta,
        }
    status = "FAIL" if changed else "REVIEW" if review else "PASS"
    return {"status": status, "pass": False if changed else None if review else True,
            "categories": categories}


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def visible_text(text: str) -> str:
    text = strip_tex_comments(text)
    text = re.sub(r"\\(?:sub)*section\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"[{}$#*_`]", "", text)
    return re.sub(r"\s+", "", text)


def question_sections(text: str) -> list[tuple[str, str, int]]:
    matches = list(QUESTION_HEADING.finditer(text))
    if not matches:
        return [("全文", text, 0)]
    sections: list[tuple[str, str, int]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = visible_text(match.group(0))[:80]
        sections.append((heading, text[match.start():end], match.start()))
    return sections


def find_occurrences(text: str, terms: Iterable[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for term in terms:
        for match in re.finditer(re.escape(term), text, re.I):
            rows.append({"term": term, "line": line_number(text, match.start())})
    return sorted(rows, key=lambda item: (item["line"], item["term"]))


def paragraph_opening_findings(text: str) -> list[dict[str, Any]]:
    groups: dict[str, list[int]] = defaultdict(list)
    offset = 0
    for paragraph in re.split(r"\n\s*\n", text):
        start = text.find(paragraph, offset)
        offset = max(offset, start + len(paragraph))
        clean = visible_text(paragraph)
        if len(clean) < 40:
            continue
        opening = re.sub(r"^[0-9一二三四五六七八九十、.（）()]+", "", clean)[:10]
        if len(opening) >= 6:
            groups[opening].append(line_number(text, max(0, start)))
    return [
        {"opening": opening, "lines": lines, "count": len(lines)}
        for opening, lines in sorted(groups.items())
        if len(lines) >= 3
    ]


def audit_style(text: str) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    claim_terms = ("无偏", "正交", "全局最优", "全局参数空间", "精确求解", "唯一",
                   "充要条件", "证伪", "证明", "理论检出", "仪器检出", "仪器噪声阈值",
                   "全参数回收", "物理定论", "严密", "严苛", "三位一体")
    claim_hits = find_occurrences(text, claim_terms)
    if claim_hits:
        findings.append({
            "id": "claim_strength_and_source", "severity": "review",
            "message": "核对声明的对象、条件、来源及证据；术语命中不等于错误，不得仅换词消除信号。",
            "occurrences": claim_hits,
        })

    meta_hits = find_occurrences(text, INTERNAL_META_TERMS)
    if meta_hits:
        findings.append({
            "id": "internal_meta_language",
            "severity": "review",
            "message": "正文出现内部工程或审查用语；确认是否可改为具体对象、关系和结果。",
            "occurrences": meta_hits,
        })

    process_hits: list[dict[str, Any]] = []
    for kind, pattern in PROCESS_PATTERNS:
        for match in pattern.finditer(text):
            process_hits.append({"kind": kind, "text": match.group(0), "line": line_number(text, match.start())})
    if process_hits:
        findings.append({
            "id": "process_claims_need_evidence",
            "severity": "review",
            "message": "正文包含试错或时间限制叙述；仅在真实、有记录且影响最终决策时保留。",
            "occurrences": process_hits,
        })

    repeated = paragraph_opening_findings(text)
    if repeated:
        findings.append({
            "id": "repeated_paragraph_openings",
            "severity": "review",
            "message": "三个以上段落共享相同开头；检查是否存在复制式段落骨架。",
            "groups": repeated,
        })

    sections = question_sections(text)
    section_lengths: list[dict[str, Any]] = []
    for heading, body, start in sections:
        length = len(visible_text(body))
        section_lengths.append({"section": heading, "characters": length})
        methods = sorted({term for term in METHOD_TERMS if re.search(re.escape(term), body, re.I)})
        if len(methods) >= 3:
            findings.append({
                "id": "dense_method_mentions",
                "severity": "review",
                "section": heading,
                "line": line_number(text, start),
                "methods": methods,
                "message": "同一问出现至少三种方法；核对每种方法是否具有独立职责和运行证据。",
            })
        if re.search(r"Spearman", body, re.I) and re.search(r"Kendall", body, re.I):
            findings.append({
                "id": "parallel_rank_tests",
                "severity": "review",
                "section": heading,
                "line": line_number(text, start),
                "message": "同一问同时使用 Spearman 与 Kendall；若二者提供不同证据可保留，否则精简。",
            })

    real_question_lengths = [row["characters"] for row in section_lengths if row["section"] != "全文" and row["characters"] >= 80]
    if len(real_question_lengths) >= 3:
        mean = statistics.fmean(real_question_lengths)
        cv = statistics.pstdev(real_question_lengths) / mean if mean else 0.0
        if cv < 0.12:
            findings.append({
                "id": "uniform_question_lengths",
                "severity": "review",
                "coefficient_of_variation": round(cv, 4),
                "message": "至少三问的文本长度异常接近；检查是否由真实论证负担决定，禁止人为拉开篇幅。",
            })

    return {
        "status": "REVIEW" if findings else "PASS",
        "finding_count": len(findings),
        "findings": findings,
        "question_lengths": section_lengths,
        "interpretation": "Signals locate passages for human review; they do not estimate AI authorship.",
    }


def build_report(paper_path: Path, text: str, baseline_path: Path | None, baseline: str | None) -> dict[str, Any]:
    integrity: dict[str, Any]
    if baseline is None:
        integrity = {
            "status": "NOT_RUN",
            "pass": None,
            "message": "Provide --baseline for fact-preservation verification after rewriting.",
        }
    else:
        integrity = compare_protected(baseline, text)
        integrity["baseline"] = str(baseline_path)
        integrity["baseline_sha256"] = sha256_text(baseline)

    style = audit_style(text)
    semantic_changes = []
    if baseline is not None:
        # Lexical triage only; unchanged numbers do not imply unchanged meaning.
        groups = {
            "source": ("经验", "本文取", "设定", "假设", "题面给定", "仪器", "理论", "标定", "实测"),
            "strength": ("支持", "提示", "证明", "证伪", "无偏", "正交", "全局", "唯一"),
            "conditions": ("若", "假设", "条件下", "本算例", "本次", "在本文", "可能", "近似"),
        }
        for group, terms in groups.items():
            delta = {term: {"before": baseline.count(term), "after": text.count(term)}
                     for term in terms if baseline.count(term) != text.count(term)}
            if delta:
                semantic_changes.append({"group": group, "changes": delta})
    if integrity["status"] == "FAIL":
        overall = "FAIL_INTEGRITY"
    elif integrity["status"] == "NOT_RUN":
        overall = "BASELINE_REQUIRED"
    elif integrity["status"] == "REVIEW" or style["finding_count"] or semantic_changes:
        overall = "REVIEW_REQUIRED"
    else:
        overall = "PASS"

    return {
        "schema_version": 2,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "paper": str(paper_path),
        "paper_sha256": sha256_text(text),
        "scope": "factual preservation plus expression-review triage; not AI detection",
        "integrity": integrity,
        "expression_review": style,
        "semantic_review": {
            "status": "NOT_PERFORMED",
            "required": True,
            "changes": semantic_changes,
            "message": "逐项核对数值归属、来源、适用条件及结论强度；词项变化仅定位风险，未命中不证明语义一致。",
        },
        "automated_scope_pass": overall == "PASS",
        "manual_review_required": True,
        "overall_status": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit factual preservation and natural-expression review signals in CUMCM prose."
    )
    parser.add_argument("paper", help="Revised .tex, .md, or .txt paper")
    parser.add_argument("--baseline", help="Pre-rewrite file used to verify protected facts")
    parser.add_argument("--output", help="JSON report path; defaults beside the paper")
    parser.add_argument("--no-write", action="store_true", help="Print the summary without writing JSON")
    args = parser.parse_args()

    paper_path = Path(args.paper).resolve()
    try:
        text = load_text(paper_path)
        if not visible_text(text):
            raise ValueError("paper contains no readable content")
        baseline_path = Path(args.baseline).resolve() if args.baseline else None
        baseline = load_text(baseline_path) if baseline_path else None
        report = build_report(paper_path, text, baseline_path, baseline)
    except (OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"overall_status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2

    if not args.no_write:
        output = Path(args.output).resolve() if args.output else paper_path.with_name("authentic-expression-audit.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "overall_status": report["overall_status"],
        "integrity": report["integrity"]["status"],
        "review_findings": report["expression_review"]["finding_count"],
        "manual_review_required": report["manual_review_required"],
        "semantic_review": report["semantic_review"]["status"],
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 1 if report["overall_status"] == "FAIL_INTEGRITY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
