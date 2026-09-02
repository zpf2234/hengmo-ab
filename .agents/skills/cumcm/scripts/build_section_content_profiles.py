#!/usr/bin/env python3
"""Build aggregate CUMCM section-content profiles without exporting source prose."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import median

import fitz


ROLE_LABELS = {
    "restatement": "问题重述",
    "analysis": "问题分析",
    "assumptions": "模型假设",
    "notation": "符号说明",
    "modeling": "模型建立与求解",
    "validation": "结果与验证",
    "evaluation": "评价、改进与推广",
    "references": "参考文献",
    "appendix": "附录",
}

SIGNALS = {
    "restatement": {
        "task_split": r"问题[一二三四五六七八九十\d]|任务[一二三四五六七八九十\d]",
        "given_input": r"给定|已知|数据|参数|条件|观测|材料",
        "required_output": r"求得|求解|确定|计算|设计|制定|给出|判断|预测|评价",
        "background": r"背景|近年来|随着|意义|应用",
    },
    "analysis": {
        "question_split": r"问题[一二三四五六七八九十\d]",
        "dependency": r"在.+基础上|承接|递进|前问|上一问|共享|耦合",
        "route_reason": r"因此|故|考虑到|由于|转化为|归结为|建立|采用",
        "difficulty": r"难点|关键|非线性|高维|约束|不确定|未知|可识别|冲突",
        "validation_plan": r"检验|验证|灵敏度|敏感性|稳健|误差|复算",
    },
    "assumptions": {
        "simplification": r"忽略|不考虑|视为|认为|假定|假设|理想",
        "scope": r"范围内|时段内|条件下|小量|常数|均匀|稳定|静态",
        "independence": r"相互独立|独立同分布|互不影响",
        "impact_or_check": r"影响|检验|验证|敏感|误差|边界",
    },
    "notation": {
        "meaning": r"含义|意义|表示|定义",
        "unit": r"单位|量纲|无量纲|kg|mm|cm|km|m/s|s\b|%",
        "index_or_set": r"下标|上标|集合|矩阵|向量|序号|索引",
    },
    "modeling": {
        "definition": r"令|设|记|定义|其中|分别表示",
        "mechanism": r"根据|由此可得|满足|守恒|受力|几何|概率|状态转移",
        "objective_constraint": r"目标函数|约束条件|最大化|最小化|可行域|边界条件",
        "solver": r"求解|迭代|算法|遍历|搜索|优化|递推|离散化",
        "parameter_source": r"参数|取值|估计|标定|拟合|初值|阈值",
    },
    "validation": {
        "error_precision": r"误差|精度|相对误差|绝对误差",
        "sensitivity": r"灵敏度|敏感性",
        "robustness": r"稳健|鲁棒|扰动",
        "convergence": r"收敛|迭代次数|步长|网格",
        "residual_fit": r"残差|拟合|决定系数|R\^?2",
        "constraint_boundary": r"边界|约束|可行|余量|极限|守恒",
        "comparison_recalc": r"对比|比较|复算|重算|解析解|特例|基准",
    },
    "evaluation": {
        "strength": r"优点|优势|长处",
        "limitation": r"缺点|局限|不足|缺陷|失效",
        "improvement": r"改进|修正|进一步|引入",
        "extension": r"推广|适用|应用于|迁移",
        "evidence": r"误差|精度|稳定|复杂度|结果|时间|成本|范围",
    },
    "references": {
        "numbered_entry": r"\[\d+\]|^\s*\d+[.、]",
        "doi_url": r"doi|https?://|www\.",
        "year": r"(?:19|20)\d{2}",
    },
    "appendix": {
        "code": r"MATLAB|Python|C\+\+|代码|程序|function|import|def\s+",
        "environment": r"版本|环境|依赖|运行|命令",
        "supplement": r"补充|中间结果|附表|推导|证明",
        "material_index": r"文件列表|支撑材料|文件名|用途",
    },
}


def quantiles(values: list[float]) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    ordered = sorted(values)

    def q(p: float) -> float:
        position = (len(ordered) - 1) * p
        lo = int(position)
        hi = min(lo + 1, len(ordered) - 1)
        frac = position - lo
        return ordered[lo] * (1 - frac) + ordered[hi] * frac

    return q(0.25), q(0.5), q(0.75)


def normalize_role(category: str, heading: str) -> str | None:
    if category == "问题重述":
        return "restatement"
    if category == "问题分析":
        return "analysis"
    if category == "模型假设":
        return "assumptions"
    if category == "符号说明":
        return "notation"
    if category == "模型建立与求解":
        return "modeling"
    if category == "灵敏度与稳定性":
        return "validation"
    if category == "模型检验与评价":
        if re.search(r"优点|缺点|评价|推广|改进|局限", heading):
            return "evaluation"
        return "validation"
    if category == "结论":
        return "evaluation"
    if category == "参考文献":
        return "references"
    if category == "附录":
        return "appendix"
    if category == "其他":
        if re.search(r"优点|缺点|模型评价|推广|改进|局限|不足", heading):
            return "evaluation"
        if re.search(r"结果|检验|验证|误差|精度|可靠性|灵敏|敏感|稳健|鲁棒|收敛|残差|拟合|边界检查|约束检查", heading):
            return "validation"
    return None


def page_lines(page: fitz.Page) -> list[tuple[float, str]]:
    records: list[tuple[float, str]] = []
    data = page.get_text("dict")
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(span.get("text", "") for span in spans).strip()
            if text:
                y0 = min(span.get("bbox", [0, 0, 0, 0])[1] for span in spans)
                records.append((float(y0), text))
    return sorted(records)


def extract_segment(doc: fitz.Document, start: dict, end: dict | None) -> str:
    start_page = max(0, int(start["page"]) - 1)
    end_page = max(start_page, int(end["page"]) - 1) if end else len(doc) - 1
    chunks: list[str] = []
    for page_no in range(start_page, min(end_page, len(doc) - 1) + 1):
        page = doc[page_no]
        height = page.rect.height
        lower = float(start.get("y_ratio", 0)) * height if page_no == start_page else -1
        upper = float(end.get("y_ratio", 1)) * height if end and page_no == end_page else height + 1
        chunks.extend(text for y, text in page_lines(page) if y >= lower and y < upper)
    text = "\n".join(chunks)
    heading = re.sub(r"\s+", "", start.get("heading", ""))
    lines = text.splitlines()
    if lines and heading and heading in re.sub(r"\s+", "", lines[0]):
        lines = lines[1:]
    return "\n".join(lines).strip()


def select_sections(rows: list[dict]) -> list[tuple[str, dict, dict | None]]:
    candidates: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, row in enumerate(rows):
        role = normalize_role(row["category"], row["heading"])
        if role:
            candidates[role].append((index, row))
    selected: list[tuple[str, dict, dict | None]] = []
    for role, entries in candidates.items():
        min_level = min(int(row["level"]) for _, row in entries)
        for index, row in entries:
            if int(row["level"]) != min_level:
                continue
            end = None
            for later in rows[index + 1 :]:
                if int(later["level"]) <= int(row["level"]):
                    end = later
                    break
            selected.append((role, row, end))
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", default="内容职责普查")
    args = parser.parse_args()

    corpus = Path(args.corpus).resolve()
    manifest_path = corpus / "全文脉络普查" / "corpus_manifest.csv"
    title_path = corpus / "标题结构普查" / "title_inventory.csv"
    manifest = list(csv.DictReader(manifest_path.open(encoding="utf-8-sig", newline="")))
    titles = list(csv.DictReader(title_path.open(encoding="utf-8-sig", newline="")))

    by_paper: dict[str, list[dict]] = defaultdict(list)
    for row in titles:
        by_paper[row["paper"]].append(row)
    for rows in by_paper.values():
        rows.sort(key=lambda row: int(row["order"]))

    pdf_candidates: dict[str, list[Path]] = defaultdict(list)
    for path in corpus.rglob("*.pdf"):
        pdf_candidates[path.name].append(path)
    pdf_map = {
        name: sorted(paths, key=lambda path: (len(path.relative_to(corpus).parts), str(path)))[0]
        for name, paths in pdf_candidates.items()
    }

    per_role: dict[str, dict[str, str]] = defaultdict(dict)
    missing_pdfs: list[str] = []
    for item in manifest:
        paper = item["paper"]
        path = pdf_map.get(paper)
        if not path:
            missing_pdfs.append(paper)
            continue
        rows = by_paper.get(paper, [])
        if not rows:
            continue
        doc = fitz.open(path)
        try:
            for role, start, end in select_sections(rows):
                text = extract_segment(doc, start, end)
                if text:
                    per_role[role][paper] = (per_role[role].get(paper, "") + "\n" + text).strip()
        finally:
            doc.close()

    profiles = {}
    for role, label in ROLE_LABELS.items():
        papers = per_role.get(role, {})
        char_counts = [len(re.sub(r"\s+", "", text)) for text in papers.values()]
        q1, med, q3 = quantiles(char_counts)
        signal_counts = {}
        for name, pattern in SIGNALS[role].items():
            signal_counts[name] = sum(bool(re.search(pattern, text, flags=re.I | re.M)) for text in papers.values())
        numeric_density = []
        crossref_density = []
        for text in papers.values():
            chars = max(1, len(re.sub(r"\s+", "", text)))
            numeric_density.append(len(re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text)) * 1000 / chars)
            crossref_density.append(len(re.findall(r"图\s*\d+|表\s*\d+|式[（(]?\d+", text)) * 1000 / chars)
        profiles[role] = {
            "label": label,
            "paper_count": len(papers),
            "char_count_q1_median_q3": [round(q1, 1), round(med, 1), round(q3, 1)],
            "numeric_tokens_per_1000_chars_median": round(median(numeric_density), 2) if numeric_density else 0,
            "figure_table_equation_refs_per_1000_chars_median": round(median(crossref_density), 2) if crossref_density else 0,
            "signals": {
                name: {"papers": count, "share": round(count / len(papers), 3) if papers else 0}
                for name, count in signal_counts.items()
            },
        }

    result = {
        "schema_version": 1,
        "corpus_papers": len(manifest),
        "missing_pdfs": missing_pdfs,
        "method": "coordinate-bounded section extraction; aggregate signals only; no source prose exported",
        "profiles": profiles,
    }
    out_dir = corpus / args.output
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "section_content_profiles.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# A/B 50 篇优秀论文章节内容职责画像",
        "",
        "本报告按标题坐标切分正文，只输出聚合统计与内容信号，不输出或复刻来源段落。",
        "字符量受公式抽取和扫描质量影响，只用于密度校准，不构成写作配额。",
        "",
    ]
    for role, profile in profiles.items():
        q1, med, q3 = profile["char_count_q1_median_q3"]
        lines.extend([
            f"## {profile['label']}",
            "",
            f"- 覆盖论文：{profile['paper_count']}/50",
            f"- 近似字符量 Q1 / 中位数 / Q3：{q1} / {med} / {q3}",
            f"- 每千字数值词中位数：{profile['numeric_tokens_per_1000_chars_median']}",
            f"- 每千字图表公式交叉引用中位数：{profile['figure_table_equation_refs_per_1000_chars_median']}",
            "- 内容信号：",
        ])
        for name, item in profile["signals"].items():
            lines.append(f"  - `{name}`：{item['papers']}/{profile['paper_count']}（{item['share']:.1%}）")
        lines.append("")
    if missing_pdfs:
        lines.extend(["## 缺失 PDF", "", *[f"- {name}" for name in missing_pdfs], ""])
    (out_dir / "AB优秀论文章节内容职责画像.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"papers": len(manifest), "roles": len(profiles), "missing_pdfs": len(missing_pdfs)}, ensure_ascii=False))
    return 0 if not missing_pdfs else 1


if __name__ == "__main__":
    raise SystemExit(main())
