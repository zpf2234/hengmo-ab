#!/usr/bin/env python3
"""Audit figure/table captions, numbered references and body interaction.

Enforces cumcm/references/figure-table-narration.md, which is calibrated on the
50-paper corpus (631 figure captions, 153 table captions, 672 reference
sentences): captions are concise and never bare filler words, and every labelled
float is cited by number somewhere in the body.

The audit does not require a fixed before/after explanation template. A weak
citation neighbourhood is a manual-review finding rather than a hard failure.
Fail-closed: no auditable .tex files means fail.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_VERSION = 1

EXCLUDED_STAGES = {"references", "appendix"}

FLOAT_ENV_RE = re.compile(r"\\begin\{(figure|table)\*?\}(.*?)\\end\{\1\*?\}", flags=re.S)
LABEL_RE = re.compile(r"\\label\{([^{}]+)\}")
REF_RE = re.compile(r"\\(?:auto|c|C|page)?ref\{([^{}]+)\}")

# Caption quality: noun-phrase captions; filler words and sentence-style captions fail.
FILLER_CAPTIONS = {
    "结果图", "结果表", "数据表", "数据图", "示意图", "流程图", "仿真结果",
    "计算结果", "求解结果", "结果", "图", "表",
}
SENTENCE_MARKERS = re.compile(r"展示了|给出了|可以看出|说明了|反映了|描述了")

# Positional references are unsafe with floating environments.
POSITIONAL_REF = re.compile(r"如?(?:上|下)[图表](?:所示)?|前面的[图表]|上述[图表]中")

# Signals used only to flag a weak citation neighbourhood for manual review.
INTERP_SIGNAL = re.compile(
    r"\d|可知|可见|可以看出|看出|表明|说明|对比|峰值|极值|最大|最小|最优|稳定|收敛"
    r"|偏差|误差|趋势|下降|上升|增大|减小|集中|分布|拐点|一致|吻合"
    r"|表示|对应|刻画|反映|形成|决定|约束|连接|指向|传递|相交|位于|沿|分支|回到"
)
# Figure/table numbers themselves must not count as interpretation numbers.
FLOAT_NUMBER = re.compile(r"[图表][\s~]*\d+(?:[-.]\d+)?")
NAKED_POINTER = re.compile(r"(?:结果|数据|详情)?(?:详|均|已)?见[图表][\s~]*\d+|结果如[图表][\s~]*\d+[\s~]*所示")


def has_interpretation(text: str) -> bool:
    cleaned = re.sub(r"\\[A-Za-z@]+\s*(?:\[[^\]]*\])?|[{}$]", " ", text)
    cleaned = FLOAT_NUMBER.sub("图", cleaned)
    return bool(INTERP_SIGNAL.search(cleaned))


def paragraph_neighbourhood(text: str, start: int, end: int) -> str:
    """Return the reference paragraph plus one adjacent paragraph on each side."""

    current_start = text.rfind("\n\n", 0, start)
    current_start = 0 if current_start == -1 else current_start + 2
    current_end = text.find("\n\n", end)
    current_end = len(text) if current_end == -1 else current_end
    previous_start = text.rfind("\n\n", 0, max(0, current_start - 2))
    previous_start = 0 if previous_start == -1 else previous_start + 2
    next_end = text.find("\n\n", min(len(text), current_end + 2))
    next_end = len(text) if next_end == -1 else next_end
    return text[previous_start:next_end]

SOFT_CAPTION_LEN = 40  # corpus P90 is 36


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def balanced_arg(text: str, start: int) -> tuple[str, int] | None:
    """Extract a {...} group starting at text[start] == '{' with brace balancing."""
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1: idx], idx + 1
    return None


def extract_captions(env_body: str) -> list[str]:
    captions = []
    for match in re.finditer(r"\\caption(?:\[[^\]]*\])?\s*", env_body):
        arg = balanced_arg(env_body, match.end())
        if arg:
            captions.append(arg[0])
    return captions


def clean_caption(caption: str) -> str:
    text = re.sub(r"\\[A-Za-z@]+\s*(?:\[[^\]]*\])?", " ", caption)
    text = text.replace("{", "").replace("}", "").replace("$", "")
    return re.sub(r"\s+", "", text)


def audit_file(path: Path, root: Path) -> dict:
    raw = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
    body = re.split(r"\\begin\{thebibliography\}|\\bibliography\{|\\appendix\b", raw, maxsplit=1)[0]

    hard: list[str] = []
    soft: list[str] = []
    floats = []

    for env_match in FLOAT_ENV_RE.finditer(body):
        env_kind = env_match.group(1)
        env_body = env_match.group(2)
        line = body.count("\n", 0, env_match.start()) + 1
        captions = extract_captions(env_body)
        labels = LABEL_RE.findall(env_body)
        where = f"L{line} {env_kind}"
        if not captions:
            hard.append(f"{where}: 缺少 \\caption")
        if not labels:
            hard.append(f"{where}: 缺少 \\label，无法执行编号引用与逐项解读审计")
        for caption in captions:
            cleaned = clean_caption(caption)
            if len(cleaned) < 4 or cleaned in FILLER_CAPTIONS:
                hard.append(f"{where}: 空泛题注「{cleaned}」")
                continue
            if cleaned.endswith("。") or SENTENCE_MARKERS.search(cleaned):
                hard.append(f"{where}: 句子式题注「{cleaned[:24]}…」（题注应为名词短语）")
            elif len(cleaned) > SOFT_CAPTION_LEN:
                soft.append(f"{where}: 题注 {len(cleaned)} 字超语料 P90≈36，考虑压缩限定语")
        floats.append({"kind": env_kind, "line": line, "labels": labels, "captions": len(captions)})

    body_without_floats = FLOAT_ENV_RE.sub(" ", body)
    ref_matches = list(REF_RE.finditer(body_without_floats))
    refs = {match.group(1) for match in ref_matches}

    for item in floats:
        for label in item["labels"]:
            if label not in refs:
                hard.append(
                    f"L{item['line']} {item['kind']}: label「{label}」未被正文编号引用（语料 49/50 图号引用）"
                )
                continue
            matching_refs = [match for match in ref_matches if match.group(1) == label]
            interpreted = False
            for match in matching_refs:
                context = paragraph_neighbourhood(
                    body_without_floats, match.start(), match.end()
                ).replace(match.group(0), " ")
                if has_interpretation(context):
                    interpreted = True
                    break
            if not interpreted:
                soft.append(
                    f"L{item['line']} {item['kind']}: label「{label}」已被编号引用，但邻域中的对象、关系或结论联系较弱，请人工确认正文交互是否自然"
                )

    for match in POSITIONAL_REF.finditer(body_without_floats):
        line = body_without_floats.count("\n", 0, match.start()) + 1
        soft.append(f"L{line}: 位置指代「{match.group(0)}」，浮动环境下改为编号引用（[H] 固定时可人工豁免）")

    for match in NAKED_POINTER.finditer(body_without_floats):
        paragraph_start = body_without_floats.rfind("\n\n", 0, match.start()) + 1
        paragraph_end = body_without_floats.find("\n\n", match.end())
        paragraph = body_without_floats[paragraph_start: paragraph_end if paragraph_end != -1 else len(body_without_floats)]
        offset = match.start() - paragraph_start
        sentence_start = paragraph.rfind("。", 0, offset) + 1
        sentence_end = paragraph.find("。", offset)
        if sentence_end == -1:
            sentence_end = len(paragraph)
        rest = paragraph[:sentence_start] + paragraph[sentence_end + 1:]
        if not has_interpretation(rest):
            line = body_without_floats.count("\n", 0, match.start()) + 1
            soft.append(f"L{line}: 「{match.group(0)}」所在段落联系较弱，请人工确认相邻上下文已交代对象或结论")

    return {
        "file": str(path.relative_to(root)),
        "float_count": len(floats),
        "hard": hard,
        "soft": soft,
    }


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="审查/section-chain/manifest.json")
    parser.add_argument("--files", nargs="*", default=[])
    args = parser.parse_args()

    root = Path(args.root).resolve()
    files = load_files(root, root / args.manifest, args.files)

    records = []
    missing = []
    for path in files:
        if not path.exists():
            missing.append(str(path.relative_to(root)))
            continue
        records.append(audit_file(path, root))

    hard_count = sum(len(r["hard"]) for r in records)
    soft_count = sum(len(r["soft"]) for r in records)
    result = {
        "schema_version": SCHEMA_VERSION,
        "pass": bool(records) and not missing and hard_count == 0,
        "files_scanned": len(records),
        "float_count": sum(r["float_count"] for r in records),
        "missing_files": missing,
        "hard_count": hard_count,
        "soft_count": soft_count,
        "manual_review_required": True,
        "records": records,
    }

    out_dir = root / "审查" / "section-chain"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "figure-table-narration.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 图表题注与正文交互审计",
        "",
        f"- 自动门禁：{'PASS' if result['pass'] else 'FAIL'}",
        f"- 扫描文件：{result['files_scanned']}；浮动环境：{result['float_count']}；硬失败：{hard_count}；人工复核：{soft_count}",
        "- 标准：cumcm/references/figure-table-narration.md；软项逐条人工复核。",
        "",
    ]
    for item in records:
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
    (out_dir / "figure-table-narration.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(
        {k: result[k] for k in ("pass", "files_scanned", "float_count", "hard_count", "soft_count")},
        ensure_ascii=False,
    ))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
