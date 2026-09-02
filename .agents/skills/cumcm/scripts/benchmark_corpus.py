#!/usr/bin/env python
"""Profile local excellent-paper PDFs and audit first-page similarity."""

from __future__ import annotations

import argparse
import fnmatch
import json
import logging
import re
import statistics
import sys
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)

# Originality-gate exit codes. 2 is the historical FAIL_HIGH_SIMILARITY code and is kept so
# existing callers keep working; 3 marks "originality is unproven", which used to exit 0.
EXIT_HIGH_SIMILARITY = 2
EXIT_UNPROVEN = 3

DEFAULT_MANUAL_REVIEW = "审查/原创性人工复核.json"


def load_reader():
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore
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
    reader = PdfReader(str(path))
    first_page = reader.pages[0].extract_text() or "" if reader.pages else ""
    result = {
        "path": str(path),
        "name": path.name,
        "pages": len(reader.pages),
        "title": first_nonempty_line(first_page),
        "first_page": first_page,
    }
    if full_text:
        pages = [(page.extract_text() or "") for page in reader.pages]
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
    missing = [
        key for key in ("reviewer", "scope") if not str(record.get(key) or "").strip()
    ]
    if missing:
        return record, (
            f"人工复核记录缺少 {'、'.join(missing)}，不足以支撑解释性放行：{path}"
        )
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
) -> dict:
    """Decide the originality verdict, failing closed when nothing was measured.

    The release rule already exists in evaluate_skill_suite.py: PASS, or WARN_REVIEW with an
    independent manual review that passed. This mirrors it so the gate that runs on every
    阶段 3 invocation agrees with the one that runs during cross-problem regression, instead
    of exiting 0 for every state in which the comparison never happened.
    """
    status = similarity["status"]
    manual_pass = isinstance(manual_review, dict) and manual_review.get("pass") is True
    reasons: list[str] = []

    if status != "PASS":
        if not paper_path.exists():
            reasons.append(f"候选论文缺失：{paper_path}")
        elif not similarity["available"]:
            reasons.append("候选论文首页无可提取文本层，无法计算 containment")
        elif not candidate_abstract:
            reasons.append("候选论文首页无“摘要—关键词”正文，无法计算 containment")
        if not corpus_count:
            reasons.append(f"对标语料为空：{corpus_dir}")
        if similarity["corpus_extraction_limited"]:
            reasons.append("无任何可比同题摘要（语料文本层不可用或未选出同题样本）")
        if status == "WARN_REVIEW" and not reasons:
            reasons.append(
                f"摘要 containment {similarity['max_containment']:.3f} 落在人工检查区间"
            )

    if status == "FAIL_HIGH_SIMILARITY":
        # High similarity is never releasable by manual note.
        verdict, code = "FAIL_HIGH_SIMILARITY", EXIT_HIGH_SIMILARITY
    elif status == "PASS":
        verdict, code = "PASS", 0
    elif status == "WARN_REVIEW" and manual_pass and manual_error is None:
        verdict, code = "PASS_WITH_MANUAL_REVIEW", 0
    else:
        verdict, code = "BLOCK_ORIGINALITY_UNPROVEN", EXIT_UNPROVEN
        if manual_error:
            reasons.append(manual_error)
        elif status == "WARN_REVIEW" and not manual_pass:
            reasons.append(
                "无独立人工复核 PASS 记录，人工检查区间不得自动放行"
                f"（可在 {DEFAULT_MANUAL_REVIEW} 记录 reviewer/scope 后重跑）"
            )
        elif status == "NOT_RUN":
            reasons.append("相似度从未执行，不得视为原创门槛通过")

    return {
        "verdict": verdict,
        "status": status,
        "enforced": bool(enforced),
        "manual_review_pass": manual_pass and manual_error is None,
        "reasons": reasons,
        # Without --fail-on-similarity the verdict is reported but never blocks, so 阶段 0
        # calibration can still run before any paper exists.
        "exit_code": code if enforced else 0,
    }


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
    lines.extend(["", "## 原创性预警"])
    similarity = result["similarity"]
    if similarity["available"]:
        if similarity.get("corpus_extraction_limited"):
            lines.append("- 同题样本文本层不可提取，未获得可解释的摘要或全文 containment；需 OCR/人工复核。")
        else:
            lines.append(
                f"- 最高摘要 containment：{similarity['max_containment']:.3f}"
                f"（{similarity['closest_paper']}）"
            )
        if similarity["full_text_containment"] is not None:
            lines.append(
                f"- 对最高风险论文的全文 containment："
                f"{similarity['full_text_containment']:.3f}"
            )
        lines.append(f"- 结论：{similarity['status']}")
        manual_review = result.get("manual_review")
        if isinstance(manual_review, dict):
            lines.append(f"- 独立人工复核：{'PASS' if manual_review.get('pass') else 'FAIL'}")
    else:
        lines.append("- 候选论文尚未生成，未执行相似度审计。")
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
    parser.add_argument("--top-k", type=int, default=5)
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
    if not corpus_dir.exists():
        raise SystemExit(f"benchmark corpus missing: {corpus_dir}")

    problem_path, problem_title = discover_problem(root, args.problem)
    track = track_from_problem(problem_path) or infer_track(root)
    metadata: list[dict] = []
    for path in sorted(corpus_dir.glob("*.pdf")):
        try:
            item = extract_pdf(path)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: skipped {path.name}: {exc}")
            continue
        match = re.search(r"[\(（]([AB])\d+", path.name.upper())
        if match is None:
            match = re.search(r"([AB])\s*题", path.name.upper())
        item["track"] = match.group(1) if match else None
        metadata.append(item)

    eligible = [item for item in metadata if not track or item["track"] in {track, None}]
    candidate_title = ""
    candidate_first_page = ""
    candidate_abstract = ""
    if paper_path.exists():
        candidate = extract_pdf(paper_path)
        candidate_title = candidate["title"]
        candidate_first_page = candidate["first_page"]
        candidate_abstract = extract_abstract(candidate_first_page)

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
    peers = []
    for item in selected_metadata:
        try:
            peer = extract_pdf(Path(item["path"]), full_text=True)
            peer.pop("first_page", None)
            peer.pop("_full_text", None)
            peers.append(peer)
        except Exception as exc:  # noqa: BLE001
            print(f"WARN: peer profiling failed for {item['name']}: {exc}")

    similarity = {
        "available": bool(candidate_first_page),
        "max_containment": 0.0,
        "closest_paper": None,
        "full_text_containment": None,
        "scope": "selected same/near-problem peers",
        "corpus_extraction_limited": False,
        "status": "NOT_RUN",
    }
    if candidate_abstract:
        scored = [
            (
                containment(candidate_abstract, extract_abstract(item["first_page"])),
                item["name"],
                item["path"],
            )
            for item in selected_metadata
            if extract_abstract(item["first_page"])
        ]
        best_score, best_name, best_path = max(scored, default=(0.0, None, None))
        full_score = None
        if best_path and best_score >= 0.15:
            candidate_full = extract_pdf(paper_path, full_text=True)["_full_text"]
            reference_full = extract_pdf(Path(best_path), full_text=True)["_full_text"]
            full_score = containment(candidate_full, reference_full, width=12)
        failed = best_score >= 0.30 or (full_score is not None and full_score >= 0.20)
        warned = best_score >= 0.15 or (full_score is not None and full_score >= 0.10)
        extraction_limited = bool(peers) and all(
            item.get("extraction_quality") == "low" for item in peers
        )
        status = "FAIL_HIGH_SIMILARITY" if failed else "WARN_REVIEW" if warned else "PASS"
        if extraction_limited or not scored:
            status = "WARN_REVIEW" if not failed else status
        similarity.update(
            {
                "max_containment": best_score,
                "closest_paper": best_name,
                "full_text_containment": full_score,
                "corpus_extraction_limited": extraction_limited or not scored,
                "status": status,
            }
        )

    result = {
        "track": track,
        "problem_path": str(problem_path) if problem_path else None,
        "problem_title": problem_title,
        "corpus_map": str(map_path),
        "candidate_title": candidate_title,
        "corpus_stats": corpus_stats(eligible),
        "peers": peers,
        "similarity": similarity,
    }

    manual_path = (
        Path(args.manual_review).resolve()
        if args.manual_review
        else root / DEFAULT_MANUAL_REVIEW
    )
    manual_review, manual_error = load_manual_review(manual_path)
    if manual_review is not None:
        # Carried into the report so evaluate_skill_suite.py and the national-first gate can
        # see the record instead of reading a key this script never wrote.
        result["manual_review"] = manual_review
        result["manual_review_path"] = str(manual_path)
    gate = originality_gate(
        similarity,
        result["corpus_stats"]["count"],
        paper_path,
        corpus_dir,
        candidate_abstract,
        manual_review,
        manual_error,
        args.fail_on_similarity,
    )
    result["originality_gate"] = gate
    if args.no_write:
        print(
            json.dumps(
                {
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
