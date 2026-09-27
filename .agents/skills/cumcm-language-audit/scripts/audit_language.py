#!/usr/bin/env python3
"""Scan CUMCM abstract/body sources for production traces and meta-writing."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


HARD_PATTERNS = {
    "calculation_scope": r"计算口径",
    "process_scope_trace": r"口径(?:不一|不一致|差异|冲突|校准|核对)|统一口径",
    "answer_label": r"本文的回答|本问回答",
    "rubric_meta": r"满足问题.{0,12}(要求|可计算性)|可计算性的要求|验证了本文写法",
    "reader_explanation": r"前者回答.{0,40}后者回答|不因.{0,40}预设结论",
    "definition_navigation": r"首次出现处定义|见下文定义|未在表中列出的.{0,20}定义",
    "appendix_navigation": r"完整程序见附录|详见附件|代码实现如下|见支撑材料",
    "ai_trace": r"人工智能|生成式人工智能|大语言模型|提示词|\bprompt\b|(?<![A-Za-z])AI(?![A-Za-z])|(?:Chat)?GPT|Claude",
    "similarity_process_trace": r"去\s*AI(?:化|味)|AIGC|查重",
    "internal_process_trace": r"审计|门禁|冒烟实验|工作流|证据包|证据矩阵|claim_id|生产痕迹|提示词泄露|落盘|交付物|全链路|端到端(?:流程|工作流)|(?:冻结|锁定)(?:模型|路线|口径|方案|标题树|版本)",
    "delivery_trace": r"(?:工作表名|sheet\s*名|必填单元格|模板错位)|(?:重新打开|重新读取).{0,24}(?:工作表|工作簿|必填单元格|模板)|(?:官方|原始)(?:\s*Excel|模板).{0,20}(?:写入|检查|复核)|交付(?:层|检查|验证)",
    "file_trace": r"(?:附件|文件)(?:名|路径)|见附件|附件(?:中|所给|数据|表格)|运行命令|支撑材料清单|\b(?:CSV|JSON)\b|\.(?:csv|json|py)\b",
    "code_trace": r"代码|脚本",
}

SOFT_PATTERNS = {
    "empty_transition": r"值得注意的是|综上所述|不难发现|毋庸置疑",
    "reader_meta": r"便于读者理解|使(?:本文|论文)结构更加清晰|为后续.{0,12}奠定基础",
    "empty_praise": r"效果良好|性能优越|具有重要意义|应用前景广阔|具有较强的鲁棒性",
    "announcing_sentence": r"(?:本节|本问|下文|下面|接下来)(?:中)?(?:，|我们)?(?:将|主要|首先|对)|我们将(?:从|通过|采用|围绕|基于)",
    "engineering_register": r"搭建.{0,8}(?:框架|体系|管线)|构建.{0,8}(?:工作流|管线|闭环)|形成.{0,6}闭环|模块化|(?:部署|集成|封装|调度).{0,10}(?:模型|流程|模块)|版本(?:管理|控制|迭代)|验收(?:模型|结果|文本)",
    "machine_grandiosity": r"多维度|全方位|全面深入|系统性地|体系化|层层递进|环环相扣|赋能",
    "empty_handoff": r"为(?:后续|下一问|接下来).{0,18}(?:奠定基础|提供依据|提供支撑)|提供了?(?:有益)?参考",
    "question_template_opener": r"针对问题[一二三四五六七八九十\d]+",
    "audit_architecture": r"验证矩阵|(?:共享|统一)(?:机理|物理)?内核|(?:求解与验证|总体反演|全流程解算)(?:技术)?路线|(?:三位一体|立体交叉|多维).{0,10}(?:体系|检验|检证|解算)",
    "inflated_certainty": r"科学界定|严苛检验|严密无偏|数学闭合|严格闭合|高度自洽|强证据|物理定论|结论自验|共同证伪|精准确定|明确证明",
    "workflow_heading": r"问题[一二三四五六七八九十\d].{0,16}(?:解算结论|定论汇总|结果报告|结论自验)|(?:模型的)?综合验证.{0,12}(?:误差|稳健性|敏感性)",
}

EXCLUDED_STAGES = {"references", "appendix"}


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


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
        p for p in paper_dir.rglob("*.tex")
        if "appendix" not in p.name.lower()
        and "附录" not in p.stem
        and "参考文献" not in p.stem
    )


def auditable_text(path: Path, source_text: str | None = None) -> str:
    """Return abstract/main-body text while excluding the AI declaration and later matter."""
    text = strip_comments(source_text if source_text is not None else path.read_text(encoding="utf-8", errors="replace"))
    return re.split(
        r"\\label\{ai-statement:start\}|\\section\*?\{AI\s*工具使用声明\}|"
        r"\\begin\{thebibliography\}|\\bibliography\{|\\appendix\b",
        text,
        maxsplit=1,
    )[0]


def scan(path: Path, patterns: dict[str, str], source_text: str | None = None) -> list[dict[str, object]]:
    text = auditable_text(path, source_text)
    findings: list[dict[str, object]] = []
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            line = text.count("\n", 0, match.start()) + 1
            snippet = re.sub(r"\s+", " ", text[max(0, match.start() - 28): match.end() + 28]).strip()
            findings.append({"pattern": name, "line": line, "match": match.group(0), "context": snippet})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="审查/section-chain/manifest.json")
    parser.add_argument("--files", nargs="*", default=[])
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest = root / args.manifest
    files = load_files(root, manifest, args.files)
    records = []
    missing = []
    paper_source = None
    for path in files:
        if not path.exists():
            missing.append(str(path.relative_to(root)))
            continue
        source_bytes = path.read_bytes()
        source_text = source_bytes.decode("utf-8", errors="replace")
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        if path.resolve() == root / "论文" / "论文.tex":
            paper_source = {"path": "论文/论文.tex", "sha256": source_sha256}
        records.append({
            "file": str(path.relative_to(root)),
            "source_sha256": source_sha256,
            "hard": scan(path, HARD_PATTERNS, source_text),
            "soft": scan(path, SOFT_PATTERNS, source_text),
        })

    hard_count = sum(len(item["hard"]) for item in records)
    soft_count = sum(len(item["soft"]) for item in records)
    result = {
        "schema_version": 1,
        "pass": bool(files) and not missing and hard_count == 0,
        "files_scanned": len(records),
        "missing_files": missing,
        "hard_count": hard_count,
        "soft_count": soft_count,
        "manual_review_required": True,
        "paper_source": paper_source,
        "records": records,
    }

    out_dir = root / "审查" / "section-chain"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "language-audit.json"
    md_path = out_dir / "language-audit.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# 正文语言自动审计", "", f"- 自动门禁：{'PASS' if result['pass'] else 'FAIL'}",
             f"- 扫描文件：{len(records)}", f"- 硬错误：{hard_count}", f"- 软提示：{soft_count}",
             "- 说明：软提示需人工判断；自动 PASS 后仍须逐章人工复核。", ""]
    for item in records:
        if not item["hard"] and not item["soft"]:
            continue
        lines.append(f"## {item['file']}")
        lines.append("")
        for level in ("hard", "soft"):
            for finding in item[level]:
                lines.append(f"- {level.upper()} L{finding['line']} `{finding['pattern']}`：{finding['context']}")
        lines.append("")
    if missing:
        lines.extend(["## 缺失文件", "", *[f"- {item}" for item in missing], ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("pass", "files_scanned", "hard_count", "soft_count")}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
