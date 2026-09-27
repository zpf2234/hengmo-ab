#!/usr/bin/env python
"""Profile quality peers and independently audit the complete local PDF corpus.

These are text-layer screening measures, not a commercial plagiarism or AIGC score.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import logging
import re
import statistics
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

# Originality-gate exit codes. 2 is the historical FAIL_HIGH_SIMILARITY code and is kept so
# existing callers keep working; 3 marks "originality is unproven", which used to exit 0.
EXIT_HIGH_SIMILARITY = 2
EXIT_UNPROVEN = 3

DEFAULT_MANUAL_REVIEW = "审查/原创性人工复核.json"
SCHEMA_VERSION = 2
MAX_OVERLAPS = 5
EXCERPT_CHARS = 160
LOCAL_REVIEW_CHARS = 80
AUDIT_ALGORITHM_VERSION = 2
RISK_THRESHOLDS = {"abstract_warn": 0.15, "abstract_high": 0.30,
                   "body_full_warn": 0.10, "body_full_high": 0.20,
                   "local_span_warn_chars": LOCAL_REVIEW_CHARS}


def file_sha256(path: Path) -> str | None:
    try:
        with path.open("rb") as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest()
    except OSError:
        return None


def discover_corpus_paths(corpus_dir: Path, paper_path: Path) -> list[Path]:
    """One discovery rule shared by producer and freshness consumers."""
    return sorted(path for path in corpus_dir.glob("*")
                  if path.is_file() and path.suffix.lower() == ".pdf"
                  and path.resolve() != paper_path.resolve())


def capture_corpus_source(corpus_dir: Path, paper_path: Path) -> dict:
    """Read-only source snapshot; callable by isolated regression fixtures too."""
    corpus_dir = corpus_dir.resolve()
    return {"path": str(corpus_dir), "discovery": "top_level_pdf_files_all_tracks",
            "members": [{"path": str(path), "sha256": file_sha256(path)}
                        for path in discover_corpus_paths(corpus_dir, paper_path)]}


def load_reader():
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            # PyMuPDF is already an explicit project dependency. This adapter avoids an
            # undeclared pypdf-only requirement while preserving page-level error checks.
            try:
                import pymupdf
            except ImportError:
                import fitz as pymupdf  # type: ignore

            class MuPage:
                def __init__(self, page):
                    self.page = page

                def extract_text(self):
                    return self.page.get_text("text")

            class MuReader:
                extraction_engine = "pymupdf"

                def __init__(self, stream):
                    self.document = pymupdf.open(stream=stream.getvalue(), filetype="pdf")
                    self.pages = [MuPage(page) for page in self.document]

            return MuReader
    return PdfReader


def normalize(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text.lower())


def ngrams(text: str, width: int) -> set[str]:
    if len(text) < width:
        return {text} if text else set()
    return {text[i : i + width] for i in range(len(text) - width + 1)}


def containment(candidate: str, reference: str, width: int = 8) -> float:
    candidate_grams = ngrams(normalize(candidate), width)
    if not candidate_grams:
        return 0.0
    return len(candidate_grams & ngrams(normalize(reference), width)) / len(candidate_grams)


def extract_abstract(first_page: str) -> str:
    start = re.search(r"摘\s*要", first_page)
    if not start:
        return ""
    body = first_page[start.end() :]
    end = re.search(r"关\s*键\s*词", body)
    return body[: end.start()] if end else body


def quantile(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return float(ordered[index])


def infer_track(root: Path) -> str | None:
    problem_dir = root / "题目"
    names = " ".join(path.name.upper() for path in problem_dir.glob("*"))
    has_a = bool(re.search(r"(^|[^A-Z])A\s*题", names))
    has_b = bool(re.search(r"(^|[^A-Z])B\s*题", names))
    if has_a and not has_b:
        return "A"
    if has_b and not has_a:
        return "B"
    return None


def title_tokens(text: str) -> set[str]:
    compact = normalize(text)
    for phrase in (
        "基于",
        "模型",
        "优化",
        "设计",
        "研究",
        "问题",
        "目标",
        "动态",
        "方法",
        "分析",
        "形态",
        "形状",
        "调节",
    ):
        compact = compact.replace(phrase, "")
    return ngrams(compact, 2)


def title_similarity(left: str, right: str) -> float:
    left_tokens = title_tokens(left)
    right_tokens = title_tokens(right)
    union = left_tokens | right_tokens
    return len(left_tokens & right_tokens) / len(union) if union else 0.0


def title_from_filename(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"^[\(（][AB]\d+[\)）]", "", stem, flags=re.IGNORECASE)


def load_corpus_map(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"invalid corpus map {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"corpus map root must be an object: {path}")
    return {
        str(title): [str(pattern) for pattern in patterns]
        for title, patterns in value.items()
        if isinstance(patterns, list)
    }


def mapped_priority(problem_title: str, filename: str, corpus_map: dict[str, list[str]]) -> int:
    normalized_problem = normalize(problem_title)
    for mapped_title, patterns in corpus_map.items():
        normalized_mapped = normalize(mapped_title)
        if normalized_problem not in normalized_mapped and normalized_mapped not in normalized_problem:
            continue
        if any(fnmatch.fnmatch(filename, pattern) for pattern in patterns):
            return 1
    return 0


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line and not re.fullmatch(r"\d+", line):
            return line
    return ""


def problem_title_from_text(text: str) -> str:
    match = re.search(r"(?:^|\n)\s*[AB]\s*题\s+([^\n]{2,80})", text, flags=re.IGNORECASE)
    if not match:
        return ""
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return re.split(r"(?:请建立|问题\s*1|现计划)", title, maxsplit=1)[0].strip()


def discover_problem(root: Path, explicit: str | None) -> tuple[Path | None, str]:
    candidates = [Path(explicit)] if explicit else sorted((root / "题目").glob("*.pdf"))
    for candidate in candidates:
        path = candidate if candidate.is_absolute() else (root / candidate)
        if not path.exists():
            continue
        try:
            item = extract_pdf(path)
        except Exception:  # noqa: BLE001
            continue
        title = problem_title_from_text(item["first_page"])
        if title:
            return path.resolve(), title
        return path.resolve(), path.stem
    return None, ""


def track_from_problem(path: Path | None) -> str | None:
    if path is None:
        return None
    match = re.search(r"([AB])\s*题", path.name.upper())
    if match:
        return match.group(1)
    try:
        text = extract_pdf(path)["first_page"]
    except Exception:  # noqa: BLE001
        return None
    match = re.search(r"(?:^|\n)\s*([AB])\s*题", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def extract_pdf(path: Path, full_text: bool = False) -> dict:
    PdfReader = load_reader()
    pdf_bytes = path.read_bytes()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[str] = []
    errors: list[dict] = []
    for index, page in enumerate(reader.pages if full_text else reader.pages[:1], start=1):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001 - keep failed pages in coverage, not silently skip
            pages.append("")
            errors.append({"page": index, "error": str(exc)[:240]})
    first_page = pages[0] if pages else ""
    result = {
        "path": str(path),
        "name": path.name,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "extraction_engine": getattr(reader, "extraction_engine", reader.__class__.__module__.split(".")[0]),
        "pages": len(reader.pages),
        "title": first_nonempty_line(first_page),
        "first_page": first_page,
    }
    if full_text:
        text = "\n".join(pages)
        figure_ids = set(re.findall(r"图\s*\d+(?:[.\-]\d+)?", text))
        table_ids = set(re.findall(r"表\s*\d+(?:[.\-]\d+)?", text))
        extraction_quality = (
            "low"
            if len(normalize(text)) < 1000
            or (len(reader.pages) > 10 and not figure_ids and not table_ids)
            else "ok"
        )
        appendix_page = None
        for index, page_text in enumerate(pages, start=1):
            if index > len(pages) // 2 and re.search(r"(^|\n)\s*附\s*录\s*($|\n)", page_text):
                appendix_page = index
                break
        result.update(
            {
                "_full_text": text,
                "_page_texts": pages,
                "_page_errors": errors,
                "figures_approx": len(figure_ids),
                "tables_approx": len(table_ids),
                "extraction_quality": extraction_quality,
                "appendix_start_approx": appendix_page,
                "validation_signals": {
                    key: key in text
                    for key in ["误差分析", "灵敏度", "稳健性", "残差", "收敛", "约束满足"]
                },
            }
        )
    return result


def text_blocks(pages: list[str]) -> list[dict]:
    """Bounded extraction blocks, not an assertion about original author paragraphs."""
    blocks = []
    for page_number, page in enumerate(pages, start=1):
        current = ""
        start = 0
        block_number = 0
        for match in re.finditer(r"[^\n]*(?:\n|$)", page):
            line = match.group(0)
            if not line:
                continue
            if current and (not line.strip() or len(normalize(current + line)) > 700):
                block_number += 1
                blocks.append({"page": page_number, "block": block_number,
                               "char_start": start, "text": current,
                               "normalized": normalize(current)})
                current = ""
            if not current:
                start = match.start()
            if line.strip():
                current += line
        if current:
            blocks.append({"page": page_number, "block": block_number + 1,
                           "char_start": start, "text": current,
                           "normalized": normalize(current)})
    return blocks


def body_pages(pages: list[str]) -> tuple[list[str], dict]:
    """Trim only identifiable abstract/backmatter boundaries; full text is always audited too."""
    scoped = pages.copy()
    boundary = {"start": "full_text_fallback", "end": "document_end", "end_page": None}
    if not pages:
        return scoped, boundary
    abstract = re.search(r"摘\s*要", pages[0])
    keywords = re.search(r"关\s*键\s*词[^\n]*(?:\n|$)", pages[0])
    if abstract and keywords and keywords.start() > abstract.end():
        # Spaces preserve original page offsets for actionable evidence.
        scoped[0] = " " * keywords.end() + pages[0][keywords.end():]
        boundary["start"] = "after_first_page_keywords"
    # Reject TOC lines and require substantial preceding body text. Unrecognized headings
    # keep all remaining text; they never silently remove possible reuse from full-text scan.
    heading = re.compile(
        r"^\s*(?:[0-9一二三四五六七八九十]+[.、．]?\s*)?"
        r"(?:参\s*考\s*文\s*献|references|bibliography|附\s*录(?:\s*[A-Z0-9一二三四五六七八九十])?)\s*$",
        re.IGNORECASE,
    )
    preceding = 0
    for index, page in enumerate(scoped):
        if index >= 1 and not re.search(r"目\s*录|table\s+of\s+contents", page, re.I):
            for line in re.finditer(r"[^\n]+", page):
                if heading.fullmatch(line.group(0)) and preceding + len(normalize(page[:line.start()])) >= 500:
                    scoped[index] = page[:line.start()]
                    scoped[index + 1:] = [""] * (len(scoped) - index - 1)
                    boundary.update({"end": "standalone_backmatter_heading", "end_page": index + 1,
                                     "end_heading": line.group(0).strip()})
                    return scoped, boundary
        preceding += len(normalize(page))
    return scoped, boundary


def extraction_coverage(item: dict, require_abstract: bool = False) -> dict:
    pages = item.get("_page_texts", [])
    page_chars = [len(normalize(page)) for page in pages]
    sparse = [index + 1 for index, count in enumerate(page_chars) if count < 80]
    damaged = [index + 1 for index, page in enumerate(pages) if "\ufffd" in page]
    abstract = extract_abstract(item.get("first_page", ""))
    scoped, boundary = body_pages(pages)
    issues = []
    if item.get("error"):
        issues.append("PDF 无法读取")
    if len(pages) != item.get("pages", 0) or not pages:
        issues.append("页数未完整提取")
    if item.get("_page_errors"):
        issues.append("存在页面提取错误")
    if sparse:
        issues.append("存在空白或稀疏文本页；须检查扫描图/公式是否遗漏")
    if damaged:
        issues.append("存在替换字符，文本层可能损坏")
    abstract_available = len(normalize(abstract)) >= 8
    if require_abstract and not abstract_available:
        issues.append("候选摘要正文缺失或不足 8 字符，摘要指标未执行")
    if sum(page_chars) < 1000 or len(normalize("\n".join(scoped))) < 500:
        issues.append("正文文本过少，不能宣称完整文字覆盖")
    return {"complete": not issues, "basis": "page_level_text_layer_heuristics_not_OCR",
            "engine": item.get("extraction_engine"),
            "abstract_available": abstract_available,
            "abstract_scope": "first_page_abstract_marker" if abstract_available else "not_identified_body_full_still_compared",
            "page_count": item.get("pages", 0), "extracted_pages": len(pages),
            "page_normalized_chars": page_chars, "sparse_pages": sparse,
            "damaged_pages": damaged, "page_errors": item.get("_page_errors", []),
            "body_boundary": boundary, "issues": issues}


def overlap_evidence(candidate_blocks: list[dict], reference_blocks: list[dict]) -> tuple[list[dict], int]:
    """Locate long exact spans via n-gram shortlist; bounded examples, no copyable full corpus."""
    inverted: dict[str, set[int]] = defaultdict(set)
    for index, block in enumerate(reference_blocks):
        for gram in ngrams(block["normalized"], 12):
            inverted[gram].add(index)
    hits = []
    for candidate in candidate_blocks:
        counts: Counter[int] = Counter()
        for gram in ngrams(candidate["normalized"], 12):
            counts.update(inverted.get(gram, ()))
        for ref_index, _ in counts.most_common(3):
            reference = reference_blocks[ref_index]
            match = SequenceMatcher(None, candidate["normalized"], reference["normalized"], autojunk=False).find_longest_match()
            if match.size < 12:
                continue
            def location(block: dict, offset: int) -> dict:
                return {"page": block["page"], "extraction_block": block["block"],
                        "block_page_char_start": block["char_start"],
                        "normalized_span": [offset, offset + match.size],
                        "excerpt": block["normalized"][offset:offset + min(match.size, EXCERPT_CHARS)]}
            hits.append({"matched_normalized_chars": match.size,
                         "candidate": location(candidate, match.a),
                         "reference": location(reference, match.b)})
    hits.sort(key=lambda hit: hit["matched_normalized_chars"], reverse=True)
    return hits[:MAX_OVERLAPS], max((hit["matched_normalized_chars"] for hit in hits), default=0)


def audit_similarity(candidate: dict | None, references: list[dict], excluded_self: list[str]) -> dict:
    """Compare every readable reference independently of peer ranking and abstract risk."""
    coverage = {"scope": "all_local_corpus_pdfs", "discovery": "top_level_pdf_files_all_tracks",
                "eligible_count": len(references),
                "compared_count": 0, "abstract_compared_count": 0,
                "complete": False, "candidate_complete": False,
                "excluded_self": excluded_self, "incomplete_references": []}
    similarity = {"available": bool(candidate and candidate.get("_full_text")),
                  "max_containment": None, "closest_paper": None, "full_text_containment": None,
                  "closest_full_text_paper": None, "body_containment": None, "closest_body_paper": None,
                  "scope": coverage["scope"], "coverage": coverage, "per_reference": [],
                  "corpus_extraction_limited": False, "status": "NOT_RUN"}
    if candidate is not None:
        coverage["candidate"] = extraction_coverage(candidate, require_abstract=True)
        coverage["candidate_complete"] = coverage["candidate"]["complete"]
    candidate_abstract = extract_abstract(candidate.get("first_page", "")) if candidate else ""
    candidate_full = candidate.get("_full_text", "") if candidate else ""
    candidate_body = "\n".join(body_pages(candidate.get("_page_texts", []))[0]) if candidate else ""
    candidate_blocks = text_blocks(candidate.get("_page_texts", [])) if candidate else []
    for reference in references:
        reference_coverage = extraction_coverage(reference)
        record = {"name": reference["name"], "path": reference["path"], "sha256": reference.get("sha256"),
                  "coverage": reference_coverage, "abstract_containment": None,
                  "full_text_containment": None, "body_containment": None,
                  "overlaps": [], "longest_located_span_chars": 0, "compared": False}
        if not reference_coverage["complete"]:
            coverage["incomplete_references"].append(reference["path"])
        reference_full = reference.get("_full_text", "")
        if candidate_full and reference_full:
            record["compared"] = True
            coverage["compared_count"] += 1
            abstract = extract_abstract(reference.get("first_page", ""))
            if len(normalize(candidate_abstract)) >= 8 and len(normalize(abstract)) >= 8:
                record["abstract_containment"] = containment(candidate_abstract, abstract)
                coverage["abstract_compared_count"] += 1
            record["full_text_containment"] = containment(candidate_full, reference_full, width=12)
            reference_body = "\n".join(body_pages(reference.get("_page_texts", []))[0])
            if normalize(candidate_body) and normalize(reference_body):
                record["body_containment"] = containment(candidate_body, reference_body, width=12)
            record["overlaps"], record["longest_located_span_chars"] = overlap_evidence(
                candidate_blocks, text_blocks(reference.get("_page_texts", [])))
        similarity["per_reference"].append(record)
    for source, target, closest in (("abstract_containment", "max_containment", "closest_paper"),
                                    ("body_containment", "body_containment", "closest_body_paper"),
                                    ("full_text_containment", "full_text_containment", "closest_full_text_paper")):
        rows = [row for row in similarity["per_reference"] if row[source] is not None]
        if rows:
            best = max(rows, key=lambda row: row[source])
            similarity[target], similarity[closest] = best[source], best["name"]
    coverage["complete"] = bool(coverage["candidate_complete"] and references
                                and coverage["compared_count"] == len(references)
                                and not coverage["incomplete_references"])
    similarity["corpus_extraction_limited"] = bool(not references or coverage["incomplete_references"])
    abstract_score = similarity["max_containment"] or 0.0
    body_score = similarity["body_containment"] or 0.0
    full_score = similarity["full_text_containment"] or 0.0
    similarity["local_overlap_review"] = any(row["longest_located_span_chars"] >= LOCAL_REVIEW_CHARS
                                               for row in similarity["per_reference"])
    if abstract_score >= RISK_THRESHOLDS["abstract_high"] or max(body_score, full_score) >= RISK_THRESHOLDS["body_full_high"]:
        similarity["status"] = "FAIL_HIGH_SIMILARITY"
    elif coverage["compared_count"] or candidate_full:
        similarity["status"] = "WARN_REVIEW" if (not coverage["complete"] or abstract_score >= RISK_THRESHOLDS["abstract_warn"]
                                  or max(body_score, full_score) >= RISK_THRESHOLDS["body_full_warn"] or similarity["local_overlap_review"]) else "PASS"
    return similarity


def compute_audit_basis(candidate_pdf_sha256: str | None, similarity: dict) -> str:
    """Bind reviewed evidence, not just candidate bytes; stable under project relocation."""
    coverage = similarity.get("coverage") or {}
    basis = {"schema_version": SCHEMA_VERSION, "algorithm_version": AUDIT_ALGORITHM_VERSION,
             "risk_thresholds": RISK_THRESHOLDS, "candidate_pdf_sha256": candidate_pdf_sha256,
             "coverage": {key: value for key, value in coverage.items()
                          if key not in {"excluded_self", "incomplete_references"}},
             "references": []}
    for row in similarity.get("per_reference", []):
        basis["references"].append({key: value for key, value in row.items() if key != "path"})
    basis["references"].sort(key=lambda row: (str(row.get("sha256") or ""), str(row.get("name") or "")))
    encoded = json.dumps(basis, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def corpus_stats(items: list[dict]) -> dict:
    pages = [int(item["pages"]) for item in items]
    return {
        "count": len(pages),
        "pages": {
            "min": min(pages) if pages else None,
            "q25": quantile(pages, 0.25),
            "median": statistics.median(pages) if pages else None,
            "q75": quantile(pages, 0.75),
            "max": max(pages) if pages else None,
        },
    }


def load_manual_review(path: Path) -> tuple[dict | None, str | None]:
    """Read the independent originality review record, if a reviewer filed one.

    references/benchmarking.md allows a WARN_REVIEW result to be released only after an
    independent reviewer checks the overlapping sentences. The record lives in its own file
    because 优秀论文对标.json is rewritten on every run, so anything a reviewer typed there
    was erased the next time this script executed -- which left the downstream
    manual_review checks in evaluate_skill_suite.py and cumcm-national-first-gate
    permanently unsatisfiable.
    """
    if not path.exists():
        return None, None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, f"人工复核记录无法解析：{path}（{exc}）"
    if not isinstance(record, dict):
        return None, f"人工复核记录必须是 JSON 对象：{path}"
    if record.get("pass") is not True:
        # A filed-but-failed review is a real signal; keep it and let the gate block.
        return record, None
    missing = [key for key in ("reviewer", "reviewer_type", "scope", "date", "candidate_pdf_sha256", "audit_basis_sha256")
               if not str(record.get(key) or "").strip()]
    if missing:
        return record, (
            f"人工复核记录缺少 {'、'.join(missing)}，不足以支撑解释性放行：{path}"
        )
    if record.get("reviewer_type") not in {"ai", "participant"}:
        return record, "人工复核 reviewer_type 必须如实标记 ai 或 participant，不能将 AI 自审冒充队员核验"
    return record, None


def originality_gate(
    similarity: dict,
    corpus_count: int,
    paper_path: Path,
    corpus_dir: Path,
    candidate_abstract: str,
    manual_review: dict | None,
    manual_error: str | None,
    enforced: bool,
    candidate_pdf_sha256: str | None = None,
    audit_basis_sha256: str | None = None,
) -> dict:
    """Own the release verdict: measured coverage first, then risk and bound review."""
    status = similarity["status"]
    coverage = similarity.get("coverage", {})
    coverage_complete = coverage.get("complete") is True
    manual_pass = bool(isinstance(manual_review, dict) and manual_review.get("pass") is True
                       and candidate_pdf_sha256
                       and manual_review.get("candidate_pdf_sha256") == candidate_pdf_sha256
                       and audit_basis_sha256
                       and manual_review.get("audit_basis_sha256") == audit_basis_sha256)
    reasons: list[str] = []

    if status != "PASS":
        if not paper_path.exists():
            reasons.append(f"候选论文缺失：{paper_path}")
        elif not similarity["available"]:
            reasons.append("候选论文无可提取文本层，无法计算 containment")
        elif not candidate_abstract:
            reasons.append("候选论文首页无“摘要—关键词”正文，无法计算 containment")
        if not corpus_count:
            reasons.append(f"对标语料为空：{corpus_dir}")
        if not coverage_complete:
            reasons.append("全库文本层覆盖未完成；人工复核不能替代未测范围")
            reasons.extend((coverage.get("candidate") or {}).get("issues", []))
            if coverage.get("incomplete_references"):
                reasons.append(f"存在 {len(coverage['incomplete_references'])} 篇提取不完整语料，见逐篇 coverage")
        if status == "WARN_REVIEW" and not reasons:
            reasons.append("摘要/正文/全文 containment 或连续句段命中人工检查区间，见逐篇重合定位")

    if status == "FAIL_HIGH_SIMILARITY":
        # High similarity is never releasable by manual note.
        verdict, code = "FAIL_HIGH_SIMILARITY", EXIT_HIGH_SIMILARITY
    elif status == "PASS" and coverage_complete:
        verdict, code = "PASS", 0
    elif status == "WARN_REVIEW" and coverage_complete and manual_pass and manual_error is None:
        verdict, code = "PASS_WITH_MANUAL_REVIEW", 0
    else:
        verdict, code = "BLOCK_ORIGINALITY_UNPROVEN", EXIT_UNPROVEN
        if manual_error:
            reasons.append(manual_error)
        elif status == "WARN_REVIEW" and not manual_pass:
            reasons.append(
                "无独立人工复核 PASS 记录，人工检查区间不得自动放行"
                f"（需在 {DEFAULT_MANUAL_REVIEW} 记录具名复核、当前 PDF 与审计依据 SHA-256）"
            )
        elif status == "NOT_RUN":
            reasons.append("相似度从未执行，不得视为原创门槛通过")

    return {
        "verdict": verdict,
        "status": status,
        "enforced": bool(enforced),
        "manual_review_pass": manual_pass and manual_error is None,
        "coverage_complete": coverage_complete,
        "candidate_pdf_sha256": candidate_pdf_sha256,
        "audit_basis_sha256": audit_basis_sha256,
        "reasons": reasons,
        # Without --fail-on-similarity the verdict is reported but never blocks, so 阶段 0
        # calibration can still run before any paper exists.
        "exit_code": code if enforced else 0,
    }


def originality_report_issues(report: dict, paper_path: Path) -> list[str]:
    """Consumer contract: a previous abstract-only PASS cannot certify this PDF."""
    issues = []
    gate = report.get("originality_gate")
    gate = gate if isinstance(gate, dict) else {}
    if gate.get("verdict") not in {"PASS", "PASS_WITH_MANUAL_REVIEW"}:
        issues.append(f"原创性裁定未放行：{gate.get('verdict') or 'missing originality_gate'}")
    if report.get("schema_version") != SCHEMA_VERSION:
        issues.append("原创性报告不是全库覆盖 schema v2，须重新运行审计")
    candidate = report.get("candidate_pdf")
    candidate = candidate if isinstance(candidate, dict) else {}
    current_sha = file_sha256(paper_path)
    if not current_sha or candidate.get("sha256") != current_sha or gate.get("candidate_pdf_sha256") != current_sha:
        issues.append("原创性报告未绑定当前候选 PDF SHA-256")
    similarity = report.get("similarity")
    similarity = similarity if isinstance(similarity, dict) else {}
    try:
        basis = compute_audit_basis(current_sha, similarity)
    except (TypeError, AttributeError, ValueError):
        basis = None
        issues.append("原创性审计依据结构无效，须重新运行审计")
    if report.get("audit_basis_sha256") != basis or gate.get("audit_basis_sha256") != basis:
        issues.append("原创性审计依据哈希缺失或与当前报告覆盖/语料/重合证据不一致")
    coverage = similarity.get("coverage", {}) if isinstance(similarity, dict) else {}
    coverage = coverage if isinstance(coverage, dict) else {}
    count = coverage.get("eligible_count")
    if (coverage.get("scope") != "all_local_corpus_pdfs" or coverage.get("complete") is not True
            or coverage.get("candidate_complete") is not True or gate.get("coverage_complete") is not True
            or not isinstance(count, int) or isinstance(count, bool) or count < 1
            or coverage.get("compared_count") != count or coverage.get("incomplete_references")):
        issues.append("原创性全库正文/全文覆盖未完成，不接受部分比较或未知提取范围")
    source = report.get("corpus_source")
    if (not isinstance(source, dict) or source.get("discovery") != "top_level_pdf_files_all_tracks"
            or not isinstance(source.get("path"), str) or not source["path"]):
        issues.append("原创性语料源快照缺失或发现范围无效，须重新运行审计")
    else:
        source_dir = Path(source["path"])
        try:
            current_source = capture_corpus_source(source_dir, paper_path)
            def member_map(rows: object) -> dict[str, str]:
                if not isinstance(rows, list):
                    raise ValueError("missing members")
                mapping = {}
                for row in rows:
                    if (not isinstance(row, dict) or not isinstance(row.get("path"), str)
                            or not row["path"] or not isinstance(row.get("sha256"), str)
                            or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None):
                        raise ValueError("invalid source member")
                    key = str(Path(row["path"]).resolve())
                    if key in mapping:
                        raise ValueError("duplicate source member")
                    mapping[key] = row["sha256"]
                return mapping
            saved_members = member_map(source.get("members"))
            current_members = member_map(current_source["members"])
            measured_members = member_map(similarity.get("per_reference"))
            if (not source_dir.is_dir() or not saved_members or len(saved_members) != count
                    or saved_members != current_members or saved_members != measured_members):
                issues.append("原创性语料源已新增/删除/修改，或源快照与实际比较记录不一致，须重新审计")
        except (OSError, ValueError, TypeError):
            issues.append("原创性语料源快照无法复核，不能沿用旧 PASS")
    if gate.get("verdict") == "PASS_WITH_MANUAL_REVIEW":
        review_file = report.get("manual_review_file")
        if (not isinstance(review_file, dict) or not isinstance(review_file.get("path"), str)
                or not review_file["path"]):
            issues.append("原创性人工复核缺真实来源文件绑定，旧嵌入 PASS 不足以放行")
        else:
            review_path = Path(review_file["path"])
            live_review, review_error = load_manual_review(review_path)
            if (not review_file.get("sha256") or file_sha256(review_path) != review_file["sha256"]
                    or review_error is not None or not isinstance(live_review, dict)
                    or live_review != report.get("manual_review") or live_review.get("pass") is not True
                    or live_review.get("candidate_pdf_sha256") != current_sha
                    or live_review.get("audit_basis_sha256") != basis):
                issues.append("原创性人工复核文件已撤回/删除/修改或依据失效，须以当前真实记录重新审计")
    return issues


def write_report(output_dir: Path, result: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "优秀论文对标.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    stats = result["corpus_stats"]["pages"]
    lines = [
        "# 优秀论文语料对标",
        "",
        f"- 语料数量：{result['corpus_stats']['count']}",
        f"- 赛道：{result['track'] or '未判定'}",
        f"- 赛题：{result['problem_title'] or '未提取'}",
        f"- 页数分布：{stats['min']} / {stats['q25']} / {stats['median']} / "
        f"{stats['q75']} / {stats['max']}（最小/Q1/中位数/Q3/最大）",
        "",
        "## 邻近样本",
        "",
    ]
    if not result["peers"]:
        lines.append("- 未找到可靠的同题或近题语料；本轮只使用赛道级页数统计。")
    for item in result["peers"]:
        signals = "、".join(key for key, value in item["validation_signals"].items() if value) or "未检出"
        if item["extraction_quality"] == "low":
            lines.append(
                f"- {item['name']}：{item['pages']} 页，PDF 文本层异常，"
                "图表与验证统计需 OCR/人工复核"
            )
        else:
            lines.append(
                f"- {item['name']}：{item['pages']} 页，图约 {item['figures_approx']}，"
                f"表约 {item['tables_approx']}，验证信号：{signals}"
            )
    lines.extend(["", "## 原创性预警", ""])
    similarity = result["similarity"]
    coverage = similarity["coverage"]
    lines.append(f"- 当前候选 PDF SHA-256：`{result['candidate_pdf']['sha256'] or '缺失'}`")
    lines.append(f"- 本次审计依据 SHA-256：`{result['audit_basis_sha256']}`")
    lines.append(f"- 全库覆盖：{coverage['compared_count']}/{coverage['eligible_count']} 篇已比较；"
                 f"文本层完整性检查：{'通过' if coverage['complete'] else '未通过'}。"
                 "范围为语料目录顶层全部 PDF、跨 A/B 赛道；不受 `--top-k` 或摘要得分限制。")
    for key, closest, label in (("max_containment", "closest_paper", "摘要"),
                                ("body_containment", "closest_body_paper", "正文"),
                                ("full_text_containment", "closest_full_text_paper", "全文")):
        score = similarity[key]
        lines.append(f"- 最高{label} containment：" + (f"{score:.3f}（{similarity[closest]}）" if score is not None else "未测"))
    lines.append(f"- 结论：{similarity['status']}")
    if coverage["excluded_self"]:
        lines.append("- 排除当前候选自身路径：" + "、".join(coverage["excluded_self"]))
    lines.extend(["", "### 逐篇覆盖与重合定位", "",
                  "下列页码为 PDF 物理页，从 1 开始；块号是文本提取块，不等同于原稿自然段。"
                  "示例仅保留规范化片段，最多每篇 5 处、每侧 160 字符，须打开原页判断术语、规范引用或实质复用。", ""])
    def shown(value: float | None) -> str:
        return f"{value:.3f}" if value is not None else "未测"
    for row in similarity["per_reference"]:
        lines.append(f"- {row['name']}：摘要 {shown(row['abstract_containment'])}；正文 {shown(row['body_containment'])}；"
                     f"全文 {shown(row['full_text_containment'])}；覆盖 {'通过' if row['coverage']['complete'] else '不完整'}。")
        for issue in row["coverage"]["issues"]:
            lines.append(f"  - {issue}")
        for hit in row["overlaps"]:
            candidate, reference = hit["candidate"], hit["reference"]
            lines.append(f"  - 候选第 {candidate['page']} 页块 {candidate['extraction_block']} ↔ "
                         f"参考第 {reference['page']} 页块 {reference['extraction_block']}："
                         f"连续规范化 {hit['matched_normalized_chars']} 字符；`{candidate['excerpt']}`")
    gate = result.get("originality_gate")
    if isinstance(gate, dict):
        lines.append(f"- 门禁裁定：{gate.get('verdict')}")
        for reason in gate.get("reasons") or []:
            lines.append(f"  - {reason}")
        if not gate.get("enforced"):
            lines.append("  - 本次未启用 `--fail-on-similarity`，裁定仅记录，不阻断。")
    lines.extend(
        [
            "",
            "> 页数与图表数仅用于校准，不是写作配额；官方格式、题目需要和证据完整性优先。",
            "> 这是本地文字重合预警，不是知网重复率、AI 率、原创证明或方法独占保证。"
            "完整仅指页面级文本层启发式检查未发现缺口，不证明扫描图、公式、代码与所有字词均被抽取。"
            "不检测语义改写、图形/代码复用、全网论文或其他队伍方案；未上传任何稿件。",
        ]
    )
    (output_dir / "优秀论文对标.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="CUMCM project root")
    parser.add_argument("--corpus", default="最终效果/高教杯优秀论文")
    parser.add_argument("--paper", default="论文/论文.pdf")
    parser.add_argument("--problem", help="problem PDF; defaults to 题目/*.pdf")
    parser.add_argument("--corpus-map", help="JSON mapping problem titles to corpus filename globs")
    parser.add_argument("--top-k", type=int, default=5, help="quality peers only; originality always scans every corpus PDF")
    parser.add_argument("--fail-on-similarity", action="store_true")
    parser.add_argument(
        "--manual-review",
        default=None,
        help=f"independent originality review record; defaults to <root>/{DEFAULT_MANUAL_REVIEW}",
    )
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    # The gate verdict has to be machine-readable on Windows too, where the default console
    # encoding is GBK and any caller decoding as UTF-8 would corrupt the reasons.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - older interpreters or a replaced stdout
        pass

    root = Path(args.root).resolve()
    corpus_dir = (root / args.corpus).resolve()
    paper_path = (root / args.paper).resolve()
    map_path = (
        Path(args.corpus_map).resolve()
        if args.corpus_map
        else Path(__file__).resolve().parent.parent / "references" / "corpus-map.json"
    )
    corpus_map = load_corpus_map(map_path)
    problem_path, problem_title = discover_problem(root, args.problem)
    track = track_from_problem(problem_path) or infer_track(root)
    metadata: list[dict] = []
    excluded_self: list[str] = []
    # The curated corpus lives at the directory's top level. Nested work-in-progress
    # drafts are deliberately not quality references; every selected PDF is listed.
    corpus_paths = sorted(path for path in corpus_dir.glob("*") if path.is_file() and path.suffix.lower() == ".pdf")
    for path in corpus_paths:
        if path.resolve() == paper_path:
            excluded_self.append(str(path.resolve()))
            continue
        try:
            item = extract_pdf(path, full_text=True)
        except Exception as exc:  # noqa: BLE001
            # Keep broken PDFs in the denominator; a skipped unreadable reference is a
            # coverage failure, not successful audit of a smaller convenient corpus.
            item = {"path": str(path), "name": path.name, "pages": 0, "title": "",
                    "first_page": "", "sha256": file_sha256(path), "error": str(exc)[:240],
                    "extraction_quality": "low", "validation_signals": {}}
        match = re.search(r"[\(（]([AB])\d+", path.name.upper())
        if match is None:
            match = re.search(r"([AB])\s*题", path.name.upper())
        item["track"] = match.group(1) if match else None
        metadata.append(item)

    eligible = [item for item in metadata if not track or item["track"] in {track, None}]
    candidate: dict | None = None
    if paper_path.exists():
        try:
            candidate = extract_pdf(paper_path, full_text=True)
        except Exception as exc:  # noqa: BLE001
            candidate = {"path": str(paper_path), "name": paper_path.name, "title": "",
                         "pages": 0, "first_page": "", "sha256": file_sha256(paper_path),
                         "error": str(exc)[:240]}
    candidate_title = candidate.get("title", "") if candidate else ""
    candidate_abstract = extract_abstract(candidate.get("first_page", "")) if candidate else ""

    ranking_title = problem_title or candidate_title
    scored = [
        (
            mapped_priority(problem_title, item["name"], corpus_map),
            title_similarity(ranking_title, title_from_filename(item["name"])),
            item,
        )
        for item in eligible
    ]
    ranked = [
        item
        for mapped, similarity_score, item in sorted(scored, key=lambda row: (row[0], row[1]), reverse=True)
        if mapped or similarity_score > 0
    ]
    selected_metadata = ranked[: max(1, args.top_k)]
    peers = [{key: value for key, value in item.items() if not key.startswith("_") and key != "first_page"}
             for item in selected_metadata]
    similarity = audit_similarity(candidate, metadata, excluded_self)

    result = {
        "schema_version": SCHEMA_VERSION,
        "candidate_pdf": {"path": str(paper_path), "sha256": candidate.get("sha256") if candidate else None},
        "track": track,
        "problem_path": str(problem_path) if problem_path else None,
        "problem_title": problem_title,
        "corpus_map": str(map_path),
        "candidate_title": candidate_title,
        "corpus_stats": corpus_stats(eligible),
        "peers": peers,
        "similarity": similarity,
        "corpus_source": {"path": str(corpus_dir), "discovery": "top_level_pdf_files_all_tracks",
                          "members": [{"path": item["path"], "sha256": item.get("sha256")}
                                      for item in metadata]},
    }
    result["audit_basis_sha256"] = compute_audit_basis(result["candidate_pdf"]["sha256"], similarity)

    manual_path = (
        Path(args.manual_review).resolve()
        if args.manual_review
        else root / DEFAULT_MANUAL_REVIEW
    )
    manual_review, manual_error = load_manual_review(manual_path)
    result["manual_review_file"] = {"path": str(manual_path), "sha256": file_sha256(manual_path)}
    if manual_review is not None:
        # Carried into the report so evaluate_skill_suite.py and the national-first gate can
        # see the record instead of reading a key this script never wrote.
        result["manual_review"] = manual_review
        result["manual_review_path"] = str(manual_path)
    gate = originality_gate(
        similarity,
        len(metadata),
        paper_path,
        corpus_dir,
        candidate_abstract,
        manual_review,
        manual_error,
        args.fail_on_similarity,
        result["candidate_pdf"]["sha256"],
        result["audit_basis_sha256"],
    )
    result["originality_gate"] = gate
    if args.no_write:
        print(
            json.dumps(
                {
                    "schema_version": result["schema_version"],
                    "candidate_pdf": result["candidate_pdf"],
                    "audit_basis_sha256": result["audit_basis_sha256"],
                    "corpus_source": result["corpus_source"],
                    "manual_review_file": result["manual_review_file"],
                    "manual_review": result.get("manual_review"),
                    "track": track,
                    "problem_title": problem_title,
                    "corpus_stats": result["corpus_stats"],
                    "peers": [item["name"] for item in peers],
                    "similarity": similarity,
                    "originality_gate": gate,
                },
                ensure_ascii=False,
            )
        )
    else:
        write_report(root / "审查", result)
        print(f"Wrote {root / '审查' / '优秀论文对标.md'}")
    if gate["verdict"] not in {"PASS", "PASS_WITH_MANUAL_REVIEW"}:
        # Reported even without --fail-on-similarity so 阶段 0 sees what would block later.
        suffix = "" if gate["enforced"] else "（未启用 --fail-on-similarity，本次不阻断）"
        print(
            "{} status={}: {}{}".format(
                gate["verdict"],
                gate["status"],
                "；".join(gate["reasons"]) or "相似度未执行",
                suffix,
            )
        )
    return gate["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
