#!/usr/bin/env python3
"""Self-test for audit_figure_table_narration.py.

Covers both directions: a corpus-conformant manuscript passes; each hard rule
(missing caption, filler caption, sentence-style caption, unreferenced label)
fails on its own; weak interaction, naked pointer sentences and positional references
surface as soft findings without blocking; conceptual
diagram explanations and multiple complementary figures pass; empty projects fail closed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPT = Path(__file__).resolve().parent / "audit_figure_table_narration.py"

GOOD_TEX = r"""
\section{结果}

为确定最优阻尼系数，在 1000 到 100000 范围内扫描目标函数，响应曲线如图~\ref{fig:power}
所示。由图~\ref{fig:power} 可知，平均输出功率在 37639 处达到峰值 327.45 W，
两侧单调下降，说明解位于共振带内。

\begin{figure}[htbp]
  \centering
  \caption{阻尼系数与平均输出功率的关系}
  \label{fig:power}
\end{figure}

各关键时刻状态如表~\ref{tab:state} 所示，其中 10 s 时浮子位移 0.1845 m，
振子相对速度 0.0921 m/s，与解析路线偏差不超过 0.35\%。

\begin{table}[htbp]
  \centering
  \caption{关键时刻浮子与振子状态（位移单位 m，速度单位 m/s）}
  \label{tab:state}
\end{table}
"""

MISSING_CAPTION_TEX = r"""
\section{结果}

响应曲线如图~\ref{fig:a} 所示，峰值为 327.45 W。

\begin{figure}[htbp]
  \centering
  \label{fig:a}
\end{figure}
"""

FILLER_CAPTION_TEX = r"""
\section{结果}

响应曲线如图~\ref{fig:b} 所示，峰值为 327.45 W。

\begin{figure}[htbp]
  \caption{结果图}
  \label{fig:b}
\end{figure}
"""

SENTENCE_CAPTION_TEX = r"""
\section{结果}

响应曲线如图~\ref{fig:c} 所示，峰值为 327.45 W。

\begin{figure}[htbp]
  \caption{该图展示了阻尼系数变化时输出功率的变化情况}
  \label{fig:c}
\end{figure}
"""

UNREFERENCED_TEX = r"""
\section{结果}

扫描阻尼系数得到功率峰值 327.45 W，对应最优系数 37639。

\begin{figure}[htbp]
  \caption{阻尼系数与平均输出功率的关系}
  \label{fig:d}
\end{figure}
"""

NAKED_POINTER_TEX = r"""
\section{结果}

各时刻的求解输出已经整理完毕，结果见表~1。

\begin{table}[htbp]
  \caption{关键时刻浮子与振子状态（位移单位 m，速度单位 m/s）}
  \label{tab:naked}
\end{table}

由表~\ref{tab:naked} 可知，10 s 时浮子位移 0.1845 m，各时刻偏差均小于 0.4\%。
"""

POSITIONAL_TEX = r"""
\section{结果}

如上图所示，输出功率随阻尼系数先增后减，峰值 327.45 W 出现在 37639 处。
功率细节如图~\ref{fig:e} 所示，峰值区间宽度约 8000。

\begin{figure}[htbp]
  \caption{阻尼系数与平均输出功率的关系}
  \label{fig:e}
\end{figure}
"""

UNINTERPRETED_REFERENCE_TEX = r"""
\section{结果}

计算结果汇总见图~\ref{fig:bare}。

\begin{figure}[htbp]
  \caption{阻尼系数与平均输出功率的关系}
  \label{fig:bare}
\end{figure}
"""

CONCEPTUAL_DIAGRAM_TEX = r"""
\section{机理}

对象之间的传递关系如图~\ref{fig:mechanism} 所示。状态量由观测层传递到判定层，
约束分支决定不可行方案回到参数更新步骤，因此该连接关系对应后续递推式的计算顺序。

\begin{figure}[htbp]
  \caption{状态传递与约束判定关系}
  \label{fig:mechanism}
\end{figure}
"""

MULTIPLE_FIGURES_TEX = r"""
\section{结果}

整体响应见图~\ref{fig:global}，目标随参数先上升后下降，峰值位于可行区内部；
局部边界见图~\ref{fig:local}，活跃约束在最优点处取等号并决定邻域的单侧变化。

\begin{figure}[htbp]
  \caption{全参数域目标响应}
  \label{fig:global}
\end{figure}
\begin{figure}[htbp]
  \caption{最优点邻域与约束边界}
  \label{fig:local}
\end{figure}
"""


def write_project(root: Path, tex: str) -> None:
    paper = root / "论文"
    paper.mkdir(parents=True, exist_ok=True)
    (paper / "results.tex").write_text(tex, encoding="utf-8")


def run_audit(root: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report_path = root / "审查" / "section-chain" / "figure-table-narration.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return proc.returncode, report


def all_findings(report: dict, level: str) -> str:
    return " | ".join(f for r in report.get("records", []) for f in r.get(level, []))


CASES = []


def case(name):
    def wrap(fn):
        CASES.append((name, fn))
        return fn
    return wrap


@case("good_manuscript_passes")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "good"
    write_project(root, GOOD_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("pass") is True and report.get("hard_count") == 0
    return ok, f"exit={code} hard={report.get('hard_count')} soft={report.get('soft_count')}"


@case("missing_caption_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "nocap"
    write_project(root, MISSING_CAPTION_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "缺少" in all_findings(report, "hard")
    return ok, f"exit={code} hard={all_findings(report, 'hard')[:60]}"


@case("filler_caption_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "filler"
    write_project(root, FILLER_CAPTION_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "空泛题注" in all_findings(report, "hard")
    return ok, f"exit={code}"


@case("sentence_caption_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "sentence"
    write_project(root, SENTENCE_CAPTION_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "句子式题注" in all_findings(report, "hard")
    return ok, f"exit={code}"


@case("unreferenced_label_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "unref"
    write_project(root, UNREFERENCED_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "未被正文编号引用" in all_findings(report, "hard")
    return ok, f"exit={code}"


@case("naked_pointer_soft_only")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "naked"
    write_project(root, NAKED_POINTER_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("pass") is True and report.get("soft_count", 0) >= 1
    return ok, f"exit={code} soft={report.get('soft_count')}"


@case("positional_reference_soft")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "positional"
    write_project(root, POSITIONAL_TEX)
    code, report = run_audit(root)
    ok = code == 0 and "位置指代" in all_findings(report, "soft")
    return ok, f"exit={code} soft={all_findings(report, 'soft')[:60]}"


@case("referenced_but_weak_interaction_is_soft")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "uninterpreted"
    write_project(root, UNINTERPRETED_REFERENCE_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("hard_count") == 0 and "交互" in all_findings(report, "soft")
    return ok, f"exit={code} soft={all_findings(report, 'soft')[:80]}"


@case("conceptual_diagram_explanation_passes")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "conceptual"
    write_project(root, CONCEPTUAL_DIAGRAM_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("pass") is True
    return ok, f"exit={code} hard={report.get('hard_count')}"


@case("multiple_complementary_figures_pass")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "multiple"
    write_project(root, MULTIPLE_FIGURES_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("pass") is True and report.get("float_count") == 2
    return ok, f"exit={code} floats={report.get('float_count')}"


@case("empty_project_fails_closed")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "empty"
    (root / "论文").mkdir(parents=True, exist_ok=True)
    code, report = run_audit(root)
    ok = code == 1 and report.get("pass") is False and report.get("files_scanned") == 0
    return ok, f"exit={code} scanned={report.get('files_scanned')}"


def main() -> int:
    failed = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for name, fn in CASES:
            ok, detail = fn(tmp)
            print(f"{'PASS' if ok else 'FAIL'} {name} ({detail})")
            if not ok:
                failed.append(name)
    summary = {"pass": not failed, "case_count": len(CASES), "failed": failed}
    out = Path(__file__).resolve().parents[4] / "审查" / "figure-table-narration-selftest.json"
    if out.parent.exists():
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
