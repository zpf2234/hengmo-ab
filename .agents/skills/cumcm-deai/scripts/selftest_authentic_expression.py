#!/usr/bin/env python3
"""Deterministic self-test for audit_authentic_expression.py."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT = Path(__file__).resolve().parent / "audit_authentic_expression.py"
SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"
REFERENCE = Path(__file__).resolve().parents[1] / "references" / "authentic-expression-standard.md"

BASELINE = r"""
\section{问题一的求解}\label{sec:q1}
车辆容量为 $Q=30\,\mathrm{kg}$，最大等待时间为 15 min。我们建立整数规划模型，并用
Spearman 系数检验排序稳定性。计算得到总等待时间 42.75 min，见式 \eqref{eq:obj} 和文献 \cite{wang2024}。
\begin{equation}\label{eq:obj}
  \min Z=\sum_{i=1}^{n} w_i t_i
\end{equation}
"""

SAFE_REWRITE = r"""
\section{问题一的求解}\label{sec:q1}
容量 $Q=30\,\mathrm{kg}$ 先排除超载路线，15 min 的等待上限进一步限制访问次序。剩余路线
通过整数规划比较，总等待时间为 42.75 min。目标函数见式 \eqref{eq:obj}：
\begin{equation}\label{eq:obj}
  \min Z=\sum_{i=1}^{n} w_i t_i
\end{equation}
排序稳定性用 Spearman 系数检验，具体定义参见文献 \cite{wang2024}。
"""

STYLE_REVIEW = SAFE_REWRITE + "\n由于时间限制，我们最初尝试了 TOPSIS、VIKOR 和 AHP，随后改为当前方法。\n"


def run(paper: Path, baseline: Path | None = None, no_write: bool = True) -> tuple[int, dict]:
    command = [sys.executable, "-X", "utf8", str(SCRIPT), str(paper)]
    if baseline:
        command.extend(["--baseline", str(baseline)])
    if no_write:
        command.append("--no-write")
    proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    summary = json.loads(lines[-1]) if lines else {}
    return proc.returncode, summary


CASES = []


def case(name):
    def wrap(function):
        CASES.append((name, function))
        return function
    return wrap


@case("safe_rewrite_preserves_facts")
def _(root: Path) -> tuple[bool, str]:
    baseline = root / "baseline.tex"
    revised = root / "revised.tex"
    baseline.write_text(BASELINE, encoding="utf-8")
    revised.write_text(SAFE_REWRITE, encoding="utf-8")
    code, summary = run(revised, baseline)
    ok = code == 0 and summary.get("integrity") == "PASS"
    return ok, f"exit={code} summary={summary}"


@case("changed_number_fails_integrity")
def _(root: Path) -> tuple[bool, str]:
    baseline = root / "number-baseline.tex"
    revised = root / "number-revised.tex"
    baseline.write_text(BASELINE, encoding="utf-8")
    revised.write_text(SAFE_REWRITE.replace("42.75", "41.75"), encoding="utf-8")
    code, summary = run(revised, baseline)
    ok = code == 1 and summary.get("overall_status") == "FAIL_INTEGRITY"
    return ok, f"exit={code} summary={summary}"


@case("changed_formula_fails_integrity")
def _(root: Path) -> tuple[bool, str]:
    baseline = root / "formula-baseline.tex"
    revised = root / "formula-revised.tex"
    baseline.write_text(BASELINE, encoding="utf-8")
    revised.write_text(SAFE_REWRITE.replace("w_i t_i", "w_i t_i^2"), encoding="utf-8")
    code, summary = run(revised, baseline)
    ok = code == 1 and summary.get("integrity") == "FAIL"
    return ok, f"exit={code} summary={summary}"


@case("process_and_method_signals_only_require_review")
def _(root: Path) -> tuple[bool, str]:
    baseline = root / "style-baseline.tex"
    revised = root / "style-revised.tex"
    baseline.write_text(BASELINE, encoding="utf-8")
    revised.write_text(STYLE_REVIEW, encoding="utf-8")
    code, summary = run(revised, baseline)
    ok = (
        code == 0
        and summary.get("integrity") == "PASS"
        and summary.get("overall_status") == "REVIEW_REQUIRED"
        and summary.get("review_findings", 0) >= 1
    )
    return ok, f"exit={code} summary={summary}"


@case("no_baseline_is_explicit_not_run")
def _(root: Path) -> tuple[bool, str]:
    revised = root / "no-baseline.tex"
    revised.write_text(SAFE_REWRITE, encoding="utf-8")
    code, summary = run(revised)
    ok = (
        code == 0
        and summary.get("integrity") == "NOT_RUN"
        and summary.get("overall_status") == "BASELINE_REQUIRED"
    )
    return ok, f"exit={code} summary={summary}"


@case("no_write_creates_no_report")
def _(root: Path) -> tuple[bool, str]:
    revised = root / "no-write.tex"
    revised.write_text(SAFE_REWRITE, encoding="utf-8")
    code, summary = run(revised)
    report = root / "authentic-expression-audit.json"
    ok = code == 0 and not report.exists()
    return ok, f"exit={code} report_exists={report.exists()}"


@case("skill_routes_safe_standard_and_audit")
def _(root: Path) -> tuple[bool, str]:
    skill = SKILL.read_text(encoding="utf-8")
    reference = REFERENCE.read_text(encoding="utf-8")
    required = (
        "authentic-expression-standard.md",
        "audit_authentic_expression.py",
        "不为显得像学生而编造试错",
    )
    forbidden = ("结果必须\"不够圆\"", "必须有\"赶工痕迹\"", "允许存在排版小瑕疵")
    joined = skill + "\n" + reference
    missing = [item for item in required if item not in joined]
    found = [item for item in forbidden if item in joined]
    ok = not missing and not found
    return ok, f"missing={missing} forbidden={found}"


def main() -> int:
    failed: list[str] = []
    spec = importlib.util.spec_from_file_location("authentic_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    probes = [
        ("source_changed", "本文取0.08作为经验判别阈值。", "仪器检出阈值为0.08。", "REVIEW_REQUIRED"),
        ("claim_upgraded", "本次估计值为7.5005，真值为7.5000。", "理论无偏估计值为7.5005，真值为7.5000，证明估计无偏。", "REVIEW_REQUIRED"),
        ("number_dedup", "厚度为7.46。综上，厚度为7.46。", "厚度为7.46。", "REVIEW_REQUIRED"),
        ("number_lost", "厚度为7.46。", "厚度已求出。", "FAIL_INTEGRITY"),
        ("condition_removed", "在本文假设条件下，厚度为7.46。", "厚度为7.46。", "REVIEW_REQUIRED"),
        ("valid_strong_term_reviewed", "估计量无偏，证明如下。", "估计量无偏，证明如下。", "REVIEW_REQUIRED"),
    ]
    for name, before, after, expected in probes:
        report = module.build_report(Path("revised.txt"), after, Path("baseline.txt"), before)
        ok = (report["overall_status"] == expected
              and report["manual_review_required"] is True
              and report["semantic_review"]["status"] == "NOT_PERFORMED")
        print(f"{'PASS' if ok else 'FAIL'} {name}: {report['overall_status']}")
        if not ok:
            failed.append(name)
    # Same counters cannot establish semantic equivalence: keep review mandatory.
    semantic_limits = [
        ("word_unit_change_not_certified", "厚度为7.46微米。", "厚度为7.46毫米。"),
        ("source_reassignment_not_certified", "甲为经验阈值0.08，乙为仪器阈值0.09。", "甲为仪器阈值0.08，乙为经验阈值0.09。"),
    ]
    for name, before, after in semantic_limits:
        report = module.build_report(Path("revised.txt"), after, Path("baseline.txt"), before)
        ok = (report["manual_review_required"] is True
              and report["semantic_review"]["status"] == "NOT_PERFORMED")
        print(f"{'PASS' if ok else 'FAIL'} {name}: manual semantic review remains required")
        if not ok:
            failed.append(name)
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        for name, function in CASES:
            ok, detail = function(root)
            print(f"{'PASS' if ok else 'FAIL'} {name} ({detail})")
            if not ok:
                failed.append(name)
    summary = {"pass": not failed, "case_count": len(CASES) + len(probes) + len(semantic_limits), "failed": failed}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
