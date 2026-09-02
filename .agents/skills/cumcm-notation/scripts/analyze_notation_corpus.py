#!/usr/bin/env python3
"""Audit notation-section patterns in the top-level 50-paper CUMCM corpus."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pdfplumber


HEADING_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"符\s*号\s*说\s*明",
        r"符\s*号\s*表",
        r"主\s*要\s*符\s*号",
        r"符\s*号\s*及\s*其?\s*说\s*明",
        r"符\s*号\s*约\s*定",
        r"变\s*量\s*说\s*明",
    )
]

HEADER_WORDS = {"符号", "变量", "记号", "含义", "说明", "单位", "量纲"}
GREEK_RE = re.compile(
    r"[α-ωΑ-Ωλμσθρτφψωηξζβγδεκνπχ]|"
    r"\b(alpha|beta|gamma|delta|theta|lambda|mu|sigma|rho|tau|phi|psi|omega)\b",
    re.IGNORECASE,
)
NUMERIC_INDEX_RE = re.compile(r"[_\s]?\d|[₀₁₂₃₄₅₆₇₈₉]")
LATIN_RE = re.compile(r"[A-Za-z]")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def has_notation_heading(text: str) -> bool:
    compact = compact_text(text)
    return any(pattern.search(compact) for pattern in HEADING_PATTERNS)


def plausible_symbol(value: str) -> bool:
    compact = compact_text(value)
    if not compact or len(compact) > 36:
        return False
    if compact in HEADER_WORDS or all(word in compact for word in ("符号", "说明")):
        return False
    if CHINESE_RE.search(compact) and not LATIN_RE.search(compact) and not GREEK_RE.search(compact):
        return False
    return bool(LATIN_RE.search(compact) or GREEK_RE.search(compact))


def extract_symbol_rows(page: pdfplumber.page.Page) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    table_count = 0
    try:
        tables = page.extract_tables() or []
    except Exception:  # noqa: BLE001
        tables = []
    for table in tables:
        if not table:
            continue
        table_count += 1
        for raw_row in table:
            cells = [clean_cell(cell) for cell in (raw_row or [])]
            cells = [cell for cell in cells if cell]
            if len(cells) < 2 or not plausible_symbol(cells[0]):
                continue
            rows.append(
                {
                    "symbol": cells[0][:80],
                    "meaning": cells[1][:180],
                    "unit": cells[2][:80] if len(cells) >= 3 else "",
                }
            )
    unique: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row["symbol"], row["meaning"], row["unit"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique, table_count


def classify_symbol(symbol: str) -> list[str]:
    classes: list[str] = []
    compact = compact_text(symbol)
    if LATIN_RE.search(compact):
        classes.append("latin")
    if GREEK_RE.search(compact):
        classes.append("greek")
    if NUMERIC_INDEX_RE.search(compact):
        classes.append("numeric_index")
    if any(token in compact for token in ("max", "min", "avg", "in", "out", "up", "down")):
        classes.append("semantic_roman_fragment")
    if any(token in compact for token in ("*", "^", "ˆ", "̂", "¯", "̄", "·", "˙")):
        classes.append("decorated")
    if not classes:
        classes.append("other")
    return classes


def paper_code(path: Path) -> str:
    match = re.search(r"[（(]([AB]\d{3})[）)]", path.name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match = re.search(r"20\d{2}.*?([AB])题", path.name, re.IGNORECASE)
    if match:
        return f"2025{match.group(1).upper()}"
    return path.stem[:24]


def inspect_pdf(path: Path, scan_pages: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "paper_id": paper_code(path),
        "filename": path.name,
        "page_count": 0,
        "scanned_pages": 0,
        "notation_pages": [],
        "table_count": 0,
        "symbol_rows": [],
        "status": "ok",
        "error": None,
    }
    try:
        with pdfplumber.open(path) as pdf:
            result["page_count"] = len(pdf.pages)
            limit = min(len(pdf.pages), scan_pages)
            result["scanned_pages"] = limit
            candidate_indices: list[int] = []
            page_texts: dict[int, str] = {}
            for index in range(limit):
                text = pdf.pages[index].extract_text() or ""
                page_texts[index] = text
                if has_notation_heading(text):
                    candidate_indices.append(index)
            expanded = sorted(
                {
                    index
                    for candidate in candidate_indices
                    for index in (candidate, candidate + 1)
                    if index < limit
                }
            )
            rows: list[dict[str, str]] = []
            excerpts: list[dict[str, Any]] = []
            for index in expanded:
                page_rows, table_count = extract_symbol_rows(pdf.pages[index])
                rows.extend(page_rows)
                result["table_count"] += table_count
                excerpts.append(
                    {
                        "page": index + 1,
                        "text_excerpt": re.sub(
                            r"\s+", " ", page_texts.get(index, "")
                        )[:700],
                    }
                )
            result["notation_pages"] = [index + 1 for index in candidate_indices]
            result["symbol_rows"] = rows
            result["excerpts"] = excerpts
    except Exception as exc:  # noqa: BLE001
        result["status"] = "error"
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    detected = [record for record in records if record["notation_pages"]]
    with_rows = [record for record in records if record["symbol_rows"]]
    classes: Counter[str] = Counter()
    unit_rows = 0
    meaning_rows = 0
    total_rows = 0
    for record in records:
        for row in record["symbol_rows"]:
            total_rows += 1
            if row["meaning"]:
                meaning_rows += 1
            if row["unit"]:
                unit_rows += 1
            classes.update(classify_symbol(row["symbol"]))
    return {
        "paper_count": len(records),
        "notation_heading_detected_count": len(detected),
        "extractable_symbol_table_count": len(with_rows),
        "symbol_row_count": total_rows,
        "rows_with_meaning_count": meaning_rows,
        "rows_with_unit_count": unit_rows,
        "symbol_class_counts": dict(classes),
        "detection_rate": len(detected) / len(records) if records else 0.0,
        "paper_ids_without_detected_heading": [
            record["paper_id"] for record in records if not record["notation_pages"]
        ],
        "paper_ids_with_extraction_error": [
            record["paper_id"] for record in records if record["status"] != "ok"
        ],
    }


def write_markdown(path: Path, summary: dict[str, Any], records: list[dict[str, Any]]) -> None:
    lines = [
        "# 50 篇优秀论文符号普查",
        "",
        "本报告只用于统计符号组织方式，不复制论文模型、答案或完整符号表。",
        "",
        "## 汇总",
        "",
        f"- 论文数：{summary['paper_count']}",
        f"- 前置页检测到符号标题：{summary['notation_heading_detected_count']}",
        f"- 可抽取表格行的论文：{summary['extractable_symbol_table_count']}",
        f"- 抽取符号行：{summary['symbol_row_count']}",
        f"- 含单位列的符号行：{summary['rows_with_unit_count']}",
        f"- 符号形态计数：{json.dumps(summary['symbol_class_counts'], ensure_ascii=False)}",
        "",
        "## 逐篇定位",
        "",
        "| 编号 | 总页数 | 扫描页数 | 符号标题页 | 抽取行数 |",
        "|---|---:|---:|---|---:|",
    ]
    for record in records:
        pages = ",".join(str(page) for page in record["notation_pages"]) or "--"
        lines.append(
            f"| {record['paper_id']} | {record['page_count']} | "
            f"{record['scanned_pages']} | {pages} | {len(record['symbol_rows'])} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scan-pages", type=int, default=12)
    args = parser.parse_args()

    pdfs = sorted(args.corpus.glob("*.pdf"))
    records = [inspect_pdf(path, args.scan_pages) for path in pdfs]
    summary = summarize(records)
    report = {
        "schema_version": 1,
        "scope": "top_level_pdfs_only",
        "corpus": str(args.corpus.resolve()),
        "scan_pages_per_pdf": args.scan_pages,
        "summary": summary,
        "papers": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(args.output.with_suffix(".md"), summary, records)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["paper_ids_with_extraction_error"] else 1


if __name__ == "__main__":
    sys.exit(main())
