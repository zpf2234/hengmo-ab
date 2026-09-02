#!/usr/bin/env python3
"""Self-test for the formula readability and notation-simplicity audit."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "audit_formula_readability.py"

GOOD_TEX = r"""
\section{模型的建立与求解}
为描述构件在时刻 $t$ 的位移，设位移为 $x(t)$（单位：m），质量为 $m$（单位：kg），
恢复系数为 $k$（单位：N/m），根据受力平衡建立运动关系：
\begin{equation}\label{eq:motion}
m\ddot{x}(t)+kx(t)=0
\end{equation}
其中，$m\ddot{x}(t)$ 表示惯性力，$kx(t)$ 表示恢复力；该式给出后续积分所需的状态关系。
"""

GENERIC_AND_NEW_TEX = r"""
\section{符号说明}
\begin{table}\begin{tabular}{ccc}$x$&位移&m\\$m$&质量&kg\end{tabular}\end{table}
\section{模型的建立与求解}
建立如下模型：
\begin{equation}\label{eq:opaque}
m\ddot{x}(t)=F(t)
\end{equation}
其中各项满足平衡关系。
"""

MISSING_FOLLOW_TEX = r"""
\section{模型的建立与求解}
为描述质量为 $m$ 的构件在时刻 $t$ 的位移，设其位移为 $x(t)$，根据受力平衡有：
\begin{equation}\label{eq:no-follow}
m\ddot{x}(t)=0
\end{equation}
\section{模型评价}
"""

COMPOUND_TEX = r"""
\section{模型的建立与求解}
为分别计算两个派生量，设输入为 $a,b$，输出为 $u,v$，并引入参数 $c,d$，代入定义得：
\begin{align}\label{eq:compound}
u&=a+c\\
v&=b+d
\end{align}
其中，$u$ 与 $v$ 分别进入后续两条相互独立的计算链。
"""

NESTED_TEX = r"""
\section{模型的建立与求解}
为表示对象 $i$ 在时段 $t$ 的状态，设该状态为 $x_{i,t}$，由状态定义写成：
\begin{equation}\label{eq:nested}
x_{i_{t}}=x_{i,t}
\end{equation}
其中，$i$ 表示对象，$t$ 表示时段；等式两侧本应采用同一层索引。
"""

SEMANTIC_INTERMEDIATE_TEX = r"""
\section{模型的建立与求解}
为选择使总损失最小的方案，设决策为 $x$、样本损失为 $l_i(x)$、样本数为 $n$，定义最优决策为 $x^*$：
\begin{equation}\label{eq:objective}
x^*:=\argmin_x\sum_{i=1}^{n}l_i(x)
\end{equation}
其中，求和项表示全部样本的累计损失，$x^*$ 对应累计损失最小的方案。
"""

FRONT_SECTION_TEX = r"""
\label{body:start}
\section{问题分析}
为刻画时刻 $t$ 的剩余需求，设需求为 $d(t)$，根据守恒关系可得：
\begin{equation}\label{eq:front}
d(t)=d(0)-t
\end{equation}
\section{模型假设}
"""

TABLE_ONLY_FOLLOW_TEX = r"""
\section{模型的建立与求解}
为描述时刻 $t$ 的位移，设位移为 $x(t)$、速度为 $v(t)$，根据运动关系可得：
\begin{equation}\label{eq:table-only}
v(t)=\dot{x}(t)
\end{equation}
式中符号见符号说明表。
"""

TABLE_BEFORE_FORMULA_TEX = r"""
\section{模型的建立与求解}
\begin{table}\centering\begin{tabular}{cc}情形&状态\\A&稳定\end{tabular}\end{table}
为描述时刻 $t$ 的位移，设位移为 $x(t)$、速度为 $v(t)$，根据运动关系可得：
\begin{equation}\label{eq:after-table}
v(t)=\dot{x}(t)
\end{equation}
其中，$v(t)$ 表示位移的瞬时变化率，该关系用于下一步积分更新状态。
"""


def write_project(root: Path, tex: str) -> None:
    paper = root / "论文"
    paper.mkdir(parents=True, exist_ok=True)
    (paper / "论文.tex").write_text(tex, encoding="utf-8")


def run_audit(root: Path) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    report_path = root / "审查" / "公式可读性审计.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return completed.returncode, report


def kinds(report: dict) -> set[str]:
    return {str(item.get("kind")) for item in report.get("unresolved", [])}


CASES: list[tuple[str, object]] = []


def case(name: str):
    def wrap(fn):
        CASES.append((name, fn))
        return fn
    return wrap


@case("reader_ready_formula_passes")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "good"
    write_project(root, GOOD_TEX)
    code, report = run_audit(root)
    digest = str(report.get("tex_sha256", ""))
    ok = (
        code == 0
        and report.get("pass") is True
        and report.get("risk_count") == 0
        and len(digest) == 64
    )
    return ok, f"exit={code} risks={report.get('risk_count')} sha={len(digest)}"


@case("notation_table_does_not_replace_local_introduction")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "global-only"
    write_project(root, GENERIC_AND_NEW_TEX)
    code, report = run_audit(root)
    found = kinds(report)
    ok = code == 1 and "symbols_not_locally_introduced" in found and "generic_formula_lead" in found
    return ok, f"exit={code} kinds={sorted(found)}"


@case("missing_formula_followup_is_found")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "missing-follow"
    write_project(root, MISSING_FOLLOW_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "missing_followup_explanation" in kinds(report)
    return ok, f"exit={code} kinds={sorted(kinds(report))}"


@case("multiple_primary_relations_require_split_or_system_cue")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "compound"
    write_project(root, COMPOUND_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "compound_primary_relations" in kinds(report)
    return ok, f"exit={code} kinds={sorted(kinds(report))}"


@case("nested_scripts_are_found")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "nested"
    write_project(root, NESTED_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "nested_scripts" in kinds(report)
    return ok, f"exit={code} kinds={sorted(kinds(report))}"


@case("definition_aggregate_optimization_requests_intermediate")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "semantic"
    write_project(root, SEMANTIC_INTERMEDIATE_TEX)
    code, report = run_audit(root)
    ok = code == 1 and "semantic_intermediate_candidate" in kinds(report)
    return ok, f"exit={code} kinds={sorted(kinds(report))}"


@case("formulas_before_model_section_are_also_audited")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "front-section"
    write_project(root, FRONT_SECTION_TEX)
    code, report = run_audit(root)
    found = kinds(report)
    ok = code == 1 and "missing_followup_explanation" in found
    return ok, f"exit={code} kinds={sorted(found)}"


@case("symbol_table_only_followup_does_not_pass")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "table-only-follow"
    write_project(root, TABLE_ONLY_FOLLOW_TEX)
    code, report = run_audit(root)
    found = kinds(report)
    ok = code == 1 and "symbol_table_only_followup" in found
    return ok, f"exit={code} kinds={sorted(found)}"


@case("completed_table_does_not_hide_later_formula_lead")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "table-before-formula"
    write_project(root, TABLE_BEFORE_FORMULA_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("risk_count") == 0
    return ok, f"exit={code} kinds={sorted(kinds(report))}"


@case("specific_retention_reason_closes_remaining_risk")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "retained"
    write_project(root, COMPOUND_TEX)
    _, first = run_audit(root)
    unresolved = first.get("unresolved", [])
    if len(unresolved) != 1:
        return False, f"expected one risk, got {len(unresolved)}"
    ledger = {
        "schema_version": 1,
        "resolutions": [{
            "risk_id": unresolved[0]["risk_id"],
            "disposition": "retain",
            "reason": "两式共享同一组输入且正文明确说明分别进入两条计算链，合并便于核对共同来源。",
            "evidence": "式 eq:compound 前后的对象说明",
        }],
    }
    review = root / "审查"
    review.mkdir(parents=True, exist_ok=True)
    (review / "公式可读性处置.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    code, report = run_audit(root)
    ok = code == 0 and report.get("unresolved_count") == 0 and report.get("retained_count") == 1
    return ok, f"exit={code} retained={report.get('retained_count')}"


@case("vague_retention_reason_does_not_close_risk")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "bad-retention"
    write_project(root, COMPOUND_TEX)
    _, first = run_audit(root)
    risk_id = first["unresolved"][0]["risk_id"]
    review = root / "审查"
    review.mkdir(parents=True, exist_ok=True)
    (review / "公式可读性处置.json").write_text(
        json.dumps({
            "schema_version": 1,
            "resolutions": [{
                "risk_id": risk_id,
                "disposition": "retain",
                "reason": "有必要",
                "evidence": "式",
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    code, report = run_audit(root)
    ok = code == 1 and report.get("unresolved_count") == 1
    return ok, f"exit={code} unresolved={report.get('unresolved_count')}"


def main() -> int:
    failed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cumcm-formula-readability-") as tmpdir:
        tmp = Path(tmpdir)
        for name, fn in CASES:
            ok, detail = fn(tmp)
            print(f"{'PASS' if ok else 'FAIL'} {name} ({detail})")
            if not ok:
                failed.append(name)
    summary = {"pass": not failed, "case_count": len(CASES), "failed": failed}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
