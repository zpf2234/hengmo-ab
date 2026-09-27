#!/usr/bin/env python3
"""Verify that the language gate accepts clean prose and rejects known production traces."""

from __future__ import annotations

import argparse
import json
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


CASES = {
    "calculation_scope": "模型假设与计算口径如下。",
    "process_scope_trace": "两套结果口径不一致，需要先完成口径校准。",
    "answer_label": "本文的回答可概括为三个方面。",
    "rubric_meta": "该处理满足问题一对模型建立和可计算性的要求。",
    "reader_explanation": "前者回答能否形成，后者回答是否需要修正。",
    "preset_conclusion": "不因材料名称或条纹振幅大小预设结论。",
    "definition_navigation": "在表中列出的局部多项式系数在首次出现处定义。",
    "appendix_navigation": "完整程序见附录。",
    "file_trace": "具体结果见附件中的 CSV 文件。",
    "ai_trace": "本文使用 AI 提示词辅助生成。",
    "similarity_process_trace": "定稿后再进行去AI化与查重。",
    "ai_model_trace": "这段文字由 Claude 与 GPT 协助生成。",
    "internal_engineering_trace": "结果通过门禁后落盘为交付物。",
    "delivery_trace": "结果写入官方 Excel 后重新打开并检查工作表名和必填单元格。",
}

EXPECTED_PATTERNS = {
    "preset_conclusion": "reader_explanation",
    "ai_model_trace": "ai_trace",
    "internal_engineering_trace": "internal_process_trace",
}

SOFT_CASES = {
    "announcing_sentence": "接下来我们将从三个方面讨论该模型。",
    "engineering_register": "我们搭建了完整框架，并形成闭环。",
    "machine_grandiosity": "下面从多维度进行全面深入分析。",
    "empty_handoff": "该结果为下一问的求解奠定基础。",
    "question_template_opener": "针对问题三，建立联合优化模型。",
    "audit_architecture": "全文采用统一机理内核，并设置验证矩阵。",
    "inflated_certainty": "严苛检验证明模型达到数学闭合。",
    "workflow_heading": "问题三解算结论与物理定论汇总",
}


def write_fixture(root: Path, body: str) -> None:
    paper = root / "论文/论文.tex"
    paper.parent.mkdir(parents=True, exist_ok=True)
    paper.write_text(body, encoding="utf-8")


def run_case(script: Path, root: Path, expected_pass: bool, expected_pattern: str | None = None) -> dict:
    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(root), "--files", "论文/论文.tex"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    report_path = root / "审查/section-chain/language-audit.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    patterns = {
        finding.get("pattern")
        for record in report.get("records", [])
        for finding in record.get("hard", [])
        if isinstance(finding, dict)
    }
    soft_patterns = {
        finding.get("pattern")
        for record in report.get("records", [])
        for finding in record.get("soft", [])
        if isinstance(finding, dict)
    }
    actual_pass = completed.returncode == 0 and report.get("pass") is True
    pattern_pass = expected_pattern is None or expected_pattern in patterns
    source_hash = hashlib.sha256((root / "论文/论文.tex").read_bytes()).hexdigest()
    source_bound = report.get("paper_source") == {"path": "论文/论文.tex", "sha256": source_hash}
    return {
        "expected_pass": expected_pass,
        "actual_pass": actual_pass,
        "expected_pattern": expected_pattern,
        "patterns": sorted(value for value in patterns if isinstance(value, str)),
        "soft_patterns": sorted(value for value in soft_patterns if isinstance(value, str)),
        "pass": actual_pass == expected_pass and pattern_pass and source_bound,
        "source_bound": source_bound,
        "returncode": completed.returncode,
        "hard_count": report.get("hard_count"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/language-audit-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    skills_root = Path(__file__).resolve().parents[2]
    script = skills_root / "cumcm-language-audit/scripts/audit_language.py"
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-language-selftest-") as tmp:
        base = Path(tmp)
        clean_root = base / "clean"
        write_fixture(clean_root, "由边界条件可得厚度估计为 7.46 微米，窗口扰动下变化不超过 0.09 微米。")
        results["clean"] = run_case(script, clean_root, True)
        physical_root = base / "physical_caliber"
        write_fixture(physical_root, "主管内径取 50 mm，支管口径随流量上限确定。")
        results["physical_caliber_allowed"] = run_case(script, physical_root, True)
        for name, body in CASES.items():
            case_root = base / name
            write_fixture(case_root, body)
            results[name] = run_case(script, case_root, False, EXPECTED_PATTERNS.get(name, name))
        for name, body in SOFT_CASES.items():
            case_root = base / name
            write_fixture(case_root, body)
            result = run_case(script, case_root, True)
            result["expected_soft_pattern"] = name
            result["pass"] = result["pass"] and name in result["soft_patterns"]
            results[name] = result

    result = {
        "schema_version": 1,
        "pass": all(item["pass"] for item in results.values()),
        "case_count": len(results),
        "cases": results,
    }
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(results)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
