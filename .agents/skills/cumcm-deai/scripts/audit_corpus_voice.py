#!/usr/bin/env python3
"""Corpus-anchored voice audit for CUMCM manuscripts.

Detects statistical AI-slop signals that rule-based scanning (audit_language.py)
cannot see: uniform sentence rhythm, template-connector flooding, isomorphic
paragraph openings, numberless abstracts and runaway comma chains. The problem-
analysis section also receives a deterministic structural audit for repeated
four-step scaffolds, purpose-before-method openings and cross-question sameness.

Thresholds are frozen from the measured distribution of the 50 excellent-paper
abstracts (2026-08-13 snapshot, see references/corpus-voice-profile.md). When the
local corpus is present the baseline is recomputed and reported for reference,
but pass/fail always uses the frozen thresholds so the gate cannot drift when
corpus files change.

Fail-closed: no auditable body text means fail.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = 3

CONNECTORS = re.compile(
    r"首先|其次|最后|此外|然后|接着|在此基础上|进一步地|与此同时|总的来说|由此可见|值得注意的是|综上所述"
)

# Frozen snapshot of the 50-abstract corpus distribution (see corpus-voice-profile.md).
BUILTIN_BASELINE = {
    "sentence_cv": {"min": 0.302, "p10": 0.401, "median": 0.517, "p90": 0.704, "max": 1.171},
    "conn_density": {"min": 0.0, "p10": 0.87, "median": 3.67, "p90": 11.44, "max": 17.98},
    "num_density": {"min": 0.0, "p10": 5.25, "median": 20.24, "p90": 36.03, "max": 56.79},
    "comma_p90": {"min": 2, "p10": 3, "median": 4, "p90": 8, "max": 20},
    "iso_pairs": {"min": 0, "p10": 0, "median": 0, "p90": 0, "max": 3},
}

THRESHOLDS = {
    "hard_iso_pairs": 4,          # corpus max is 3
    "hard_sentence_cv": 0.25,     # corpus min is 0.302
    "hard_conn_density": 18.0,    # corpus max is 17.98
    "soft_iso_pairs": 1,
    "soft_sentence_cv": 0.30,
    "soft_conn_density": 11.5,    # corpus P90
    "soft_abstract_num_density": 5.5,  # corpus P10 is 5.25
    "soft_comma_p90": 12,
    "min_sentences_for_cv": 8,
}

EXCLUDED_STAGES = {"references", "appendix"}

ANALYSIS_SECTION = re.compile(r"\\section\*?\s*\{[^{}]*问题分析[^{}]*\}")
SECTION_HEADING = re.compile(r"\\section\*?\s*\{[^{}]*\}")
SUBSECTION_HEADING = re.compile(r"\\subsection\*?\s*\{([^{}]*)\}")
QUESTION_TOKEN = re.compile(r"问题(?:第)?[一二三四五六七八九十百0-9]+|第[一二三四五六七八九十百0-9]+问")
PURPOSE_METHOD = re.compile(
    r"(?:为了|为求|为解决|为确定|为获得|为得到|为完成)[^。！？；]{0,48}"
    r"(?:采用|使用|选用|建立|构建|引入|利用)"
)
TRIPLE_SEQUENCE = re.compile(
    r"首先[\s\S]*?(?:然后|接着|其次)[\s\S]*?(?:最后|最终)"
)
FOUR_STEP_LABELS = ("特征判断", "分析思路", "求解过程")
FOUR_STEP_END_LABELS = ("输出衔接", "衔接关系")
FORMULAIC_OPENING = re.compile(
    r"^(?:(?:针对|对于)?问题(?:第)?[一二三四五六七八九十百0-9]+[，,:：]?)?"
    r"(?:首先|第一步|先对|为了|为求|为解决|为确定|为获得|为得到|为完成)"
)

ANALYSIS_THRESHOLDS = {
    # Cross-question findings are counted by distinct question subsections,
    # never by the number of phrase hits inside one subsection.
    "hard_repeated_purpose_method_questions": 2,
    "hard_repeated_triple_sequence": 2,
    "hard_opening_template_pairs": 2,
    "soft_uniform_question_length_cv": 0.12,
    "min_questions_for_length_check": 3,
}

MATH_ENV = re.compile(
    r"\\begin\{(equation|align|gather|multline|eqnarray|cases|array|split|aligned)\*?\}.*?"
    r"\\end\{\1\*?\}",
    flags=re.S,
)
DISPLAY_MATH = re.compile(r"\$\$.*?\$\$|\\\[.*?\\\]", flags=re.S)
INLINE_MATH = re.compile(r"\$[^$]*\$|\\\(.*?\\\)", flags=re.S)
FLOAT_ENV = re.compile(
    r"\\begin\{(figure|table|tabular|tikzpicture|thebibliography|lstlisting|verbatim)\*?\}.*?"
    r"\\end\{\1\*?\}",
    flags=re.S,
)
COMMAND_WITH_ARG = re.compile(
    r"\\(?:label|ref|eqref|cite|includegraphics|input|include|bibliography|caption)\s*(?:\[[^\]]*\])?\{[^{}]*\}"
)
GENERIC_COMMAND = re.compile(r"\\[A-Za-z@]+\s*(?:\[[^\]]*\])?")


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def latex_to_prose(text: str) -> str:
    """Reduce LaTeX source to auditable Chinese prose."""
    text = strip_comments(text)
    text = re.split(
        r"\\label\{ai-statement:start\}|\\section\*?\{AI\s*工具使用声明\}|"
        r"\\begin\{thebibliography\}|\\bibliography\{|\\appendix\b",
        text,
        maxsplit=1,
    )[0]
    text = FLOAT_ENV.sub(" ", text)
    text = MATH_ENV.sub(" 式 ", text)
    text = DISPLAY_MATH.sub(" 式 ", text)
    text = INLINE_MATH.sub("式", text)
    text = re.sub(r"\\begin\{abstractquestion\}\{[^{}]*\}", " ", text)
    text = re.sub(r"\\end\{abstractquestion\}", " ", text)
    text = COMMAND_WITH_ARG.sub(" ", text)
    # keep argument text of sectioning/formatting commands, drop the command itself
    text = re.sub(r"\\(?:section|subsection|subsubsection|paragraph|textbf|textit|emph|keymethod|keyresult)\*?\{([^{}]*)\}", r"\1", text)
    text = GENERIC_COMMAND.sub(" ", text)
    text = text.replace("{", " ").replace("}", " ").replace("~", " ")
    return text


def extract_abstract(text: str) -> str | None:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, flags=re.S)
    return match.group(1) if match else None


def extract_analysis_questions(text: str) -> list[tuple[str, str]]:
    """Return subsection title/body pairs from the problem-analysis section."""
    clean = strip_comments(text)
    section = ANALYSIS_SECTION.search(clean)
    if not section:
        return []
    following = SECTION_HEADING.search(clean, section.end())
    block = clean[section.end():following.start() if following else len(clean)]
    headings = list(SUBSECTION_HEADING.finditer(block))
    if not headings:
        return [("问题分析", block)] if block.strip() else []
    questions: list[tuple[str, str]] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(block)
        questions.append((heading.group(1).strip(), block[heading.end():end]))
    return questions


def opening_prefix(opening: str, width: int = 12) -> str:
    """Normalize question numbers so numbering cannot mask the same opening shape."""
    normalized = QUESTION_TOKEN.sub("问题#", opening)
    normalized = re.sub(r"^(?:针对|对于)", "", normalized)
    normalized = re.sub(r"\d+(?:\.\d+)?", "N", normalized)
    normalized = re.sub(r"[\s，,。；;：:！？!（）()、]", "", normalized)
    return normalized[:width]


def analysis_narrative_metrics(text: str) -> tuple[dict[str, object], list[str], list[str]] | None:
    """Audit problem-analysis prose without imposing a fixed paragraph recipe."""
    chunks = extract_analysis_questions(text)
    if not chunks:
        return None

    questions: list[dict[str, object]] = []
    purpose_hits = 0
    purpose_question_count = 0
    triple_count = 0
    fixed_four_count = 0
    formulaic_count = 0
    for title, body in chunks:
        prose = latex_to_prose(body).strip()
        compact = re.sub(r"\s", "", prose)
        opening_parts = [part.strip() for part in re.split(r"[。！？；]", prose) if part.strip()]
        opening = opening_parts[0] if opening_parts else ""
        purpose = len(PURPOSE_METHOD.findall(prose))
        triple = bool(TRIPLE_SEQUENCE.search(prose))
        fixed_four = all(label in prose for label in FOUR_STEP_LABELS) and any(
            label in prose for label in FOUR_STEP_END_LABELS
        )
        formulaic = bool(FORMULAIC_OPENING.search(opening))
        purpose_hits += purpose
        purpose_question_count += int(purpose > 0)
        triple_count += int(triple)
        fixed_four_count += int(fixed_four)
        formulaic_count += int(formulaic)
        questions.append({
            "title": title,
            "chars": len(compact),
            "opening": opening[:80],
            "opening_prefix": opening_prefix(opening),
            "formulaic_opening": formulaic,
            "purpose_method_hits": purpose,
            "triple_sequence": triple,
            "fixed_four_labels": fixed_four,
        })

    prefixes = [str(q["opening_prefix"]) for q in questions if q["opening_prefix"]]
    prefix_pairs = sum(
        1
        for i in range(len(prefixes))
        for j in range(i + 1, len(prefixes))
        if prefixes[i] == prefixes[j]
    )
    lengths = [int(q["chars"]) for q in questions if int(q["chars"]) > 0]
    length_cv = None
    if len(lengths) >= 2 and statistics.mean(lengths):
        length_cv = round(statistics.pstdev(lengths) / statistics.mean(lengths), 3)

    hard: list[str] = []
    soft: list[str] = []
    if fixed_four_count:
        hard.append(
            f"fixed_four_step_questions={fixed_four_count}（把职责池写成固定四步/四段）"
        )
    if purpose_question_count >= ANALYSIS_THRESHOLDS["hard_repeated_purpose_method_questions"]:
        hard.append(
            f"purpose_method_questions={purpose_question_count}, purpose_method_hits={purpose_hits}"
            "（命中不同问题，判为跨问重复‘为了……采用……’）"
        )
    elif purpose_question_count == 1:
        if purpose_hits > 1:
            soft.append(
                f"purpose_method_questions=1, purpose_method_hits={purpose_hits}"
                "（仅同一问内重复，不判跨问；人工复核该问的局部因果顺序）"
            )
        else:
            soft.append(
                "purpose_method_questions=1, purpose_method_hits=1"
                "（单问单次命中，不判跨问；检查是否可从对象、约束或异常直接起句）"
            )
    if triple_count >= ANALYSIS_THRESHOLDS["hard_repeated_triple_sequence"]:
        hard.append(
            f"triple_sequence_questions={triple_count}（跨问复制‘首先—然后/其次—最后’骨架）"
        )
    elif triple_count:
        soft.append("triple_sequence_questions=1（确认顺序词承担真实计算时序）")
    if prefix_pairs >= ANALYSIS_THRESHOLDS["hard_opening_template_pairs"]:
        hard.append(
            f"opening_template_pairs={prefix_pairs}（问题编号归一化后，跨问开头同构）"
        )
    elif prefix_pairs:
        soft.append(f"opening_template_pairs={prefix_pairs}（人工复核跨问开头）")
    if formulaic_count >= 2:
        hard.append(
            f"formulaic_openings={formulaic_count}（多问从顺序/目的套话起句，未由本题内容驱动）"
        )
    elif formulaic_count:
        soft.append("formulaic_openings=1（人工复核该问是否应从具体对象或条件起句）")
    if (
        len(lengths) >= ANALYSIS_THRESHOLDS["min_questions_for_length_check"]
        and length_cv is not None
        and length_cv < ANALYSIS_THRESHOLDS["soft_uniform_question_length_cv"]
    ):
        soft.append(
            f"question_length_cv={length_cv}（各问近乎等长；核对是否按真实难度分配篇幅）"
        )

    metrics = {
        "question_count": len(questions),
        "question_length_cv": length_cv,
        "purpose_method_hits": purpose_hits,
        "purpose_method_questions": purpose_question_count,
        "triple_sequence_questions": triple_count,
        "fixed_four_step_questions": fixed_four_count,
        "formulaic_openings": formulaic_count,
        "opening_template_pairs": prefix_pairs,
        "questions": questions,
    }
    return metrics, hard, soft


def voice_metrics(prose: str) -> dict[str, object] | None:
    """Compute the frozen metric set over plain prose."""
    sentences = [s.strip() for s in re.split(r"[。！？；]", prose) if len(s.strip()) >= 4]
    if len(sentences) < 3:
        return None
    lengths = [len(s) for s in sentences]
    mean_len = statistics.mean(lengths)
    cv = statistics.pstdev(lengths) / mean_len if mean_len else 0.0
    chars = len(re.sub(r"\s", "", prose))
    if chars < 200:
        return None
    conn_density = len(CONNECTORS.findall(prose)) / chars * 1000
    num_density = len(re.findall(r"\d+(?:\.\d+)?", prose)) / chars * 1000
    commas = sorted(s.count("，") for s in sentences)
    comma_p90 = commas[min(len(commas) - 1, int(len(commas) * 0.9))]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if len(p.strip()) > 30]
    prefixes = [p[:6] for p in paragraphs]
    iso_pairs = sum(
        1
        for i in range(len(prefixes))
        for j in range(i + 1, len(prefixes))
        if prefixes[i] == prefixes[j]
    )
    return {
        "n_sentences": len(sentences),
        "n_paragraphs": len(paragraphs),
        "chars": chars,
        "sentence_cv": round(cv, 3),
        "conn_density": round(conn_density, 2),
        "num_density": round(num_density, 2),
        "comma_p90": comma_p90,
        "iso_pairs": iso_pairs,
    }


def judge(metrics: dict[str, object], is_abstract: bool) -> tuple[list[str], list[str]]:
    hard: list[str] = []
    soft: list[str] = []
    t = THRESHOLDS
    if metrics["iso_pairs"] >= t["hard_iso_pairs"]:
        hard.append(f"iso_pairs={metrics['iso_pairs']} >= {t['hard_iso_pairs']}（段首同构，语料上限 3）")
    elif metrics["iso_pairs"] >= t["soft_iso_pairs"]:
        soft.append(f"iso_pairs={metrics['iso_pairs']}（语料 47/50 为 0，人工复核）")
    if metrics["n_sentences"] >= t["min_sentences_for_cv"]:
        if metrics["sentence_cv"] < t["hard_sentence_cv"]:
            hard.append(f"sentence_cv={metrics['sentence_cv']} < {t['hard_sentence_cv']}（机械均匀句长，语料最低 0.302）")
        elif metrics["sentence_cv"] < t["soft_sentence_cv"]:
            soft.append(f"sentence_cv={metrics['sentence_cv']}（低于语料最低值附近，人工复核）")
    if metrics["conn_density"] > t["hard_conn_density"]:
        hard.append(f"conn_density={metrics['conn_density']}/千字 > {t['hard_conn_density']}（模板连接词失控，语料最高 17.98）")
    elif metrics["conn_density"] > t["soft_conn_density"]:
        soft.append(f"conn_density={metrics['conn_density']}/千字（超语料 P90=11.44，人工复核）")
    if is_abstract and metrics["num_density"] < t["soft_abstract_num_density"]:
        soft.append(f"num_density={metrics['num_density']}/千字（摘要低于语料 P10=5.25，疑似零数字摘要雷点）")
    if metrics["comma_p90"] > t["soft_comma_p90"]:
        soft.append(f"comma_p90={metrics['comma_p90']}（一逗到底风险，人工复核）")
    return hard, soft


def load_files(root: Path, manifest_path: Path, explicit: list[str]) -> list[Path]:
    if explicit:
        return [root / item for item in explicit]
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        files: list[Path] = []
        for stage, spec in data.get("stages", {}).items():
            if stage in EXCLUDED_STAGES:
                continue
            for item in spec.get("source_files", []):
                path = root / item
                if path.suffix.lower() == ".tex" and path not in files:
                    files.append(path)
        if files:
            return files
    paper_dir = root / "论文"
    return sorted(
        p
        for p in paper_dir.rglob("*.tex")
        if "appendix" not in p.name.lower() and "附录" not in p.stem and "参考文献" not in p.stem
    )


def corpus_baseline(corpus_md: Path) -> dict[str, dict[str, float]] | None:
    """Recompute abstract baseline for the report; judgement never uses it."""
    if not corpus_md.exists():
        return None
    text = corpus_md.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```text\n(.*?)```", text, flags=re.S)
    rows = []
    for block in blocks:
        clean = re.sub(r"[\$\\{}_^&%]|\*\*", "", block)
        m = voice_metrics(clean)
        if m:
            rows.append(m)
    if len(rows) < 10:
        return None
    result: dict[str, dict[str, float]] = {}
    for key in ("sentence_cv", "conn_density", "num_density", "comma_p90", "iso_pairs"):
        values = sorted(float(r[key]) for r in rows)
        pick = lambda q: values[min(len(values) - 1, int(len(values) * q))]
        result[key] = {
            "min": round(values[0], 3),
            "p10": round(pick(0.10), 3),
            "median": round(pick(0.5), 3),
            "p90": round(pick(0.90), 3),
            "max": round(values[-1], 3),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="审查/section-chain/manifest.json")
    parser.add_argument("--corpus", default="最终效果/高教杯优秀论文/摘要普查/all_paper_abstracts.md")
    parser.add_argument("--files", nargs="*", default=[])
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = load_files(root, root / args.manifest, args.files)

    recomputed = corpus_baseline(root / args.corpus)
    baseline_source = "corpus" if recomputed else "builtin"

    records = []
    missing = []
    hard_total = 0
    soft_total = 0
    for path in files:
        if not path.exists():
            missing.append(str(path.relative_to(root)))
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        abstract_block = extract_abstract(raw)
        is_abstract = "摘要" in path.stem or "abstract" in path.stem.lower() or abstract_block is not None
        prose = latex_to_prose(abstract_block if abstract_block is not None else raw)
        metrics = voice_metrics(prose)
        analysis_audit = analysis_narrative_metrics(raw)
        if metrics is None and analysis_audit is None:
            records.append({
                "file": str(path.relative_to(root)),
                "skipped": "text too short for voice metrics",
            })
            continue
        hard, soft = judge(metrics, is_abstract) if metrics is not None else ([], [])
        analysis_metrics = None
        if analysis_audit is not None:
            analysis_metrics, analysis_hard, analysis_soft = analysis_audit
            hard.extend(f"[问题分析] {item}" for item in analysis_hard)
            soft.extend(f"[问题分析] {item}" for item in analysis_soft)
        hard_total += len(hard)
        soft_total += len(soft)
        record = {
            "file": str(path.relative_to(root)),
            "is_abstract": is_abstract,
            "hard": hard,
            "soft": soft,
        }
        if metrics is not None:
            record["metrics"] = metrics
        if analysis_metrics is not None:
            record["analysis_narrative"] = analysis_metrics
        records.append(record)

    audited = [r for r in records if "metrics" in r or "analysis_narrative" in r]
    result = {
        "schema_version": SCHEMA_VERSION,
        "pass": bool(audited) and not missing and hard_total == 0,
        "files_scanned": len(audited),
        "missing_files": missing,
        "hard_count": hard_total,
        "soft_count": soft_total,
        "baseline_source": baseline_source,
        "thresholds": THRESHOLDS,
        "analysis_thresholds": ANALYSIS_THRESHOLDS,
        "builtin_baseline": BUILTIN_BASELINE,
        "recomputed_baseline": recomputed,
        "manual_review_required": True,
        "records": records,
    }

    out_dir = root / "审查" / "section-chain"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "corpus-voice-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 语料声纹审计",
        "",
        f"- 自动门禁：{'PASS' if result['pass'] else 'FAIL'}",
        f"- 扫描文件：{len(audited)}；硬失败：{hard_total}；人工复核项：{soft_total}",
        f"- 判定阈值：固化基线快照；基线来源（报告参考）：{baseline_source}",
        "- 说明：软项必须逐条人工复核；自动 PASS 不代替逐部分语料对照。",
        "",
    ]
    for item in records:
        if item.get("skipped"):
            lines.append(f"## {item['file']}\n\n- SKIPPED：{item['skipped']}\n")
            continue
        if not item["hard"] and not item["soft"]:
            continue
        lines.append(f"## {item['file']}")
        lines.append("")
        for finding in item["hard"]:
            lines.append(f"- HARD {finding}")
        for finding in item["soft"]:
            lines.append(f"- SOFT {finding}")
        lines.append("")
    if missing:
        lines.extend(["## 缺失文件", "", *[f"- {item}" for item in missing], ""])
    (out_dir / "corpus-voice-audit.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(
        {k: result[k] for k in ("pass", "files_scanned", "hard_count", "soft_count", "baseline_source")},
        ensure_ascii=False,
    ))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
