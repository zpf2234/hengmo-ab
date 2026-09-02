#!/usr/bin/env python3
"""Self-test for audit_corpus_voice.py.

Verifies both directions of the gate: natural corpus-like prose passes, and each
statistical AI-slop signal (isomorphic paragraph openings, uniform sentence
rhythm, connector flooding) hard-fails on its own. Also verifies fail-closed
behaviour on empty projects, soft-only findings not blocking, and baseline
source reporting for both corpus-present and corpus-missing roots. Problem-
analysis cases additionally verify content-led openings and deterministic
rejection of repeated four-step/purpose-method scaffolds.
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

SCRIPT = Path(__file__).resolve().parent / "audit_corpus_voice.py"

CLEAN_TEX = r"""
\section{模型的建立与求解}

浮子在入射波作用下同时受到重力、静水恢复力与兴波阻尼力，取平衡位置为原点建立坐标系。
对浮子与振子分别应用牛顿第二定律，得二元二阶常系数微分方程组：式。将其改写为四元一阶
形式后代入初值，解得前 40 个周期内以 0.2 s 为间隔的位移与速度序列。

数值结果显示位移始终落在 -1 m 到 2 m 之间，说明只有部分圆柱浸没的假设成立。取 10 s、
20 s、40 s、60 s、100 s 五个时刻的状态列于表中，浮子位移最大为 0.435 m，振子相对速度
峰值 0.647 m/s。

第二问在稳态区间上推导平均输出功率的表达式，遍历阻尼系数取值后得到最大平均输出功率
229.334 W，对应阻尼系数 37193.8。若阻尼系数与相对速度的 0.5 次幂成正比，梯形数值积分
给出最大功率 230.127 W。两条路线结果相差 0.35%，交叉验证通过。

灵敏度分析将波浪频率扰动 5%，最优阻尼系数移动不超过 2.1%，功率峰值变化 0.8%，
说明优化解在工程公差内稳定。
"""

ISO_TEX = r"""
\section{求解}

基于上述分析，本文首先针对该问题建立了相应的数学模型，通过对相关参数进行分析，得到了模型的基本结构与主要变量之间的关系。

基于上述分析，本文首先针对该问题设计了相应的求解算法，通过对相关变量进行处理，得到了算法的基本流程与主要步骤之间的关系。

基于上述分析，本文首先针对该问题给出了相应的数值结果，通过对相关结果进行整理，得到了结果的基本特征与主要指标之间的关系。

基于上述分析，本文首先针对该问题完成了相应的验证工作，通过对相关误差进行比较，得到了误差的基本范围与主要来源之间的关系。

基于上述分析，本文首先针对该问题开展了相应的推广讨论，通过对相关场景进行梳理，得到了场景的基本类型与主要差异之间的关系。
"""

UNIFORM_TEX = r"""
\section{分析}

本文对第一个子问题进行了系统的分析和处理并给出了结果。本文对第二个子问题进行了完整的建模和求解并得到了答案。本文对第三个子问题进行了详细的推导和计算并形成了结论。本文对第四个子问题进行了全面的验证和检验并确认了精度。本文对第五个子问题进行了深入的比较和讨论并明确了边界。本文对第六个子问题进行了充分的扩展和延伸并总结了规律。本文对第七个子问题进行了严格的复核和校对并锁定了口径。本文对第八个子问题进行了必要的整理和归纳并输出了清单。
"""

CONNECTOR_TEX = r"""
\section{求解}

首先，此外，需要对整个装置的受力情况进行系统的分析，然后，接着，在此基础上，首先建立描述垂荡运动的基本模型。其次，进一步地，与此同时，总的来说，需要对模型中的各项参数进行整理，由此可见，然后进行数值求解并记录各时刻状态。最后，值得注意的是，综上所述，首先，其次，最后，此外，需要将求解得到的位移与速度序列整理成表，然后再对整体精度进行验证。接着，在此基础上，进一步地，与此同时，总的来说，由此可见，综上所述，值得注意的是，通过对结果的比较可以得到最终的结论。首先，其次，最后，此外，然后，接着，在此基础上，进一步地，与此同时，对全部子问题的答案进行汇总并完成分析。
"""

SOFT_ABSTRACT_TEX = r"""
\begin{abstract}
本文研究波浪能装置的能量转换问题，建立了浮子与振子的耦合运动模型并完成求解。
针对问题一，依据牛顿第二定律建立垂荡方向的动力学方程，采用数值迭代方法求出各时刻的位移与速度序列，结果与解析路线互相印证。
针对问题二，以平均输出功率最大为目标建立优化模型，通过遍历搜索确定最优阻尼系数，并对搜索步长做了收敛性检查。
针对问题三，将纵摇自由度引入原模型，讨论了小角度近似的适用范围，并说明该近似在波高较大时会引入可见偏差。
模型的主要局限是未考虑非线性波浪激励，推广时可将激励项替换为实测谱。
\end{abstract}
"""

NATURAL_ANALYSIS_TEX = r"""
\section{问题分析}
\label{sec:analysis}

\subsection{问题一的分析}
相邻观测时刻的间隔并不一致，直接作普通差分会把采样间隔误当成状态变化。将时间差保留在变化率
定义中，可先得到各区段可比的演化速度，再由边界时刻确定本问所需状态。

\subsection{问题二的分析}
车辆容量与站点等待量共同限制调度次序：提前服务远端站点会增加空驶，延后服务又可能越过最大
等待时间。两类代价因此不能分别最小化，需要把发车时刻、访问次序和装载量置于同一可行域。
容量约束先排除不可行组合，剩余方案按总等待时间比较；若多个方案的目标差落在计算误差内，
再用最大单站等待量区分。这里传递的是每个可行方案的时刻表，而不是一个脱离路径的目标值。

\subsection{问题三的分析}
上问得到的时刻表已经固定车辆到站状态。本问只需把新增需求映射到对应站点，并检查原有容量余量；
发生越界时局部调整相邻两站的服务次序，未越界则沿用原方案。
"""

TEMPLATE_ANALYSIS_TEX = r"""
\section{问题分析}
\label{sec:analysis}

\subsection{问题一的分析}
为了求解问题一，我们采用统一模型完成计算。首先进行特征判断，然后给出分析思路，接着说明求解过程，
最后完成输出衔接。相关数据经过处理后进入模型，并为后续步骤提供基础。

\subsection{问题二的分析}
为了求解问题二，我们采用统一模型完成计算。首先进行特征判断，然后给出分析思路，接着说明求解过程，
最后完成输出衔接。相关数据经过处理后进入模型，并为后续步骤提供基础。

\subsection{问题三的分析}
为了求解问题三，我们采用统一模型完成计算。首先进行特征判断，然后给出分析思路，接着说明求解过程，
最后完成输出衔接。相关数据经过处理后进入模型，并为后续步骤提供基础。
"""

SAME_QUESTION_PURPOSE_REPEAT_TEX = r"""
\section{问题分析}

\subsection{问题一的分析}
相邻观测时刻的间隔并不一致，普通差分会把采样间隔混入状态变化。为了保留真实时间尺度，采用
带时间差的变化率；为了核对端点误差，使用边界时刻的原始观测作复算。
"""

CROSS_QUESTION_PURPOSE_REPEAT_TEX = r"""
\section{问题分析}

\subsection{问题一的分析}
相邻观测时刻的间隔并不一致。为了保留真实时间尺度，采用带时间差的变化率。

\subsection{问题二的分析}
车辆容量与站点等待量同时限制调度次序。为了比较可行方案，采用总等待时间作为目标量。
"""


def write_project(root: Path, tex_name: str, tex_content: str) -> None:
    paper = root / "论文"
    paper.mkdir(parents=True, exist_ok=True)
    (paper / tex_name).write_text(tex_content, encoding="utf-8")


def run_audit(root: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    report_path = root / "审查" / "section-chain" / "corpus-voice-audit.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return proc.returncode, report


CASES = []


def case(name):
    def wrap(fn):
        CASES.append((name, fn))
        return fn
    return wrap


@case("clean_prose_passes")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "clean"
    write_project(root, "model.tex", CLEAN_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("pass") is True and report.get("hard_count") == 0
    return ok, f"exit={code} pass={report.get('pass')} hard={report.get('hard_count')} soft={report.get('soft_count')}"


@case("isomorphic_paragraphs_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "iso"
    write_project(root, "model.tex", ISO_TEX)
    code, report = run_audit(root)
    findings = "".join(str(r.get("hard")) for r in report.get("records", []))
    ok = code == 1 and report.get("pass") is False and "iso_pairs" in findings
    return ok, f"exit={code} hard={report.get('hard_count')}"


@case("uniform_sentences_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "uniform"
    write_project(root, "model.tex", UNIFORM_TEX)
    code, report = run_audit(root)
    findings = "".join(str(r.get("hard")) for r in report.get("records", []))
    ok = code == 1 and "sentence_cv" in findings
    return ok, f"exit={code} findings={findings[:80]}"


@case("connector_flood_hard_fail")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "conn"
    write_project(root, "model.tex", CONNECTOR_TEX)
    code, report = run_audit(root)
    findings = "".join(str(r.get("hard")) for r in report.get("records", []))
    ok = code == 1 and "conn_density" in findings
    return ok, f"exit={code} findings={findings[:80]}"


@case("content_led_analysis_passes")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "analysis_clean"
    write_project(root, "论文.tex", NATURAL_ANALYSIS_TEX)
    code, report = run_audit(root)
    record = next((r for r in report.get("records", []) if r.get("analysis_narrative")), {})
    analysis = record.get("analysis_narrative", {})
    ok = (
        code == 0
        and report.get("hard_count") == 0
        and analysis.get("question_count") == 3
        and analysis.get("formulaic_openings") == 0
    )
    return ok, (
        f"exit={code} hard={report.get('hard_count')} "
        f"questions={analysis.get('question_count')} formulaic={analysis.get('formulaic_openings')}"
    )


@case("templated_analysis_hard_fails")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "analysis_template"
    write_project(root, "论文.tex", TEMPLATE_ANALYSIS_TEX)
    code, report = run_audit(root)
    record = next((r for r in report.get("records", []) if r.get("analysis_narrative")), {})
    findings = "".join(str(item) for item in record.get("hard", []))
    expected = ("purpose_method_questions", "triple_sequence_questions", "fixed_four_step_questions")
    ok = code == 1 and all(item in findings for item in expected)
    return ok, f"exit={code} findings={findings[:160]}"


@case("same_question_purpose_repeat_is_soft_only")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "analysis_same_question_purpose"
    write_project(root, "论文.tex", SAME_QUESTION_PURPOSE_REPEAT_TEX)
    code, report = run_audit(root)
    record = next((r for r in report.get("records", []) if r.get("analysis_narrative")), {})
    analysis = record.get("analysis_narrative", {})
    hard = "".join(str(item) for item in record.get("hard", []))
    soft = "".join(str(item) for item in record.get("soft", []))
    ok = (
        code == 0
        and report.get("hard_count") == 0
        and analysis.get("purpose_method_hits") == 2
        and analysis.get("purpose_method_questions") == 1
        and "跨问" not in hard
        and "仅同一问内重复，不判跨问" in soft
    )
    return ok, (
        f"exit={code} hard={report.get('hard_count')} "
        f"hits={analysis.get('purpose_method_hits')} "
        f"questions={analysis.get('purpose_method_questions')}"
    )


@case("cross_question_purpose_repeat_hard_fails")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "analysis_cross_question_purpose"
    write_project(root, "论文.tex", CROSS_QUESTION_PURPOSE_REPEAT_TEX)
    code, report = run_audit(root)
    record = next((r for r in report.get("records", []) if r.get("analysis_narrative")), {})
    analysis = record.get("analysis_narrative", {})
    hard = "".join(str(item) for item in record.get("hard", []))
    ok = (
        code == 1
        and analysis.get("purpose_method_hits") == 2
        and analysis.get("purpose_method_questions") == 2
        and "purpose_method_questions=2" in hard
        and "判为跨问重复" in hard
    )
    return ok, (
        f"exit={code} hard={report.get('hard_count')} "
        f"hits={analysis.get('purpose_method_hits')} "
        f"questions={analysis.get('purpose_method_questions')}"
    )


@case("empty_project_fails_closed")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "empty"
    (root / "论文").mkdir(parents=True, exist_ok=True)
    code, report = run_audit(root)
    ok = code == 1 and report.get("pass") is False and report.get("files_scanned") == 0
    return ok, f"exit={code} scanned={report.get('files_scanned')}"


@case("soft_findings_do_not_block")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "soft"
    write_project(root, "摘要.tex", SOFT_ABSTRACT_TEX)
    code, report = run_audit(root)
    ok = code == 0 and report.get("pass") is True and report.get("hard_count") == 0
    return ok, f"exit={code} pass={report.get('pass')} soft={report.get('soft_count')}"


@case("builtin_baseline_without_corpus")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "nocorpus"
    write_project(root, "model.tex", CLEAN_TEX)
    code, report = run_audit(root)
    ok = report.get("baseline_source") == "builtin"
    return ok, f"baseline={report.get('baseline_source')}"


@case("corpus_baseline_reported_when_present")
def _(tmp: Path) -> tuple[bool, str]:
    root = tmp / "withcorpus"
    write_project(root, "model.tex", CLEAN_TEX)
    corpus = root / "最终效果" / "高教杯优秀论文" / "摘要普查"
    corpus.mkdir(parents=True, exist_ok=True)
    sample = CLEAN_TEX.replace("\\section{模型的建立与求解}", "")
    blocks = "\n".join(f"```text\n{sample}\n```" for _ in range(12))
    (corpus / "all_paper_abstracts.md").write_text(blocks, encoding="utf-8")
    code, report = run_audit(root)
    ok = report.get("baseline_source") == "corpus" and report.get("recomputed_baseline") is not None
    return ok, f"baseline={report.get('baseline_source')}"


@case("analysis_guidance_has_no_length_or_flowchart_quota")
def _(tmp: Path) -> tuple[bool, str]:
    skills = Path(__file__).resolve().parents[2]
    paths = {
        "analysis": skills / "cumcm-analysis" / "STAGE.md",
        "deai": skills / "cumcm-deai" / "SKILL.md",
        "front": skills / "cumcm-paper" / "references" / "front-section-content-standard.md",
        "template": skills / "cumcm-paper" / "assets" / "latex-template" / "论文.tex",
        "national": skills / "cumcm" / "references" / "national-first-precision-and-visual-gates.md",
        "orchestrator": skills / "cumcm" / "SKILL.md",
        "solve": skills / "cumcm-solve" / "SKILL.md",
        "model_writing": skills / "cumcm-model-writing" / "STAGE.md",
        "model_result": skills / "cumcm-paper" / "references" / "model-result-content-standard.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    required = {
        "analysis": ("150 字不是目标，也不是硬上限", "图示按信息增益触发"),
        "deai": ("问题分析专项复核", "不设 150 字上限"),
        "front": ("组成职责池", "不是 150 字上限"),
        "template": ("按需组合的职责", "不设固定字数"),
        "national": ("图示信息增益门禁", "三个以上阶段本身不足以要求流程图"),
        "orchestrator": ("不设 1--2 句或固定段长", "图能带来明确的信息增益"),
        "solve": ("不把模型选择压成固定", "图能带来信息增益"),
        "model_writing": ("图能带来信息增益", "不设 1--2 句的硬上限"),
        "model_result": ("图能带来信息增益", "必须同公式和脚本一致"),
    }
    missing = [
        f"{name}:{needle}"
        for name, needles in required.items()
        for needle in needles
        if needle not in texts[name]
    ]
    forbidden = (
        "一段话（150 字以内）",
        "复杂思路强制流程图",
        "强制流程图门禁",
        "复杂求解过程必须引用对应的分问题流程图",
        "复杂求解链必须有与公式和脚本一致的流程图",
        "大部分转化为模型选择流程图",
        "实现“一图胜千言”",
    )
    joined = "\n".join(texts.values())
    found = [needle for needle in forbidden if needle in joined]
    ok = not missing and not found
    return ok, f"missing={missing} forbidden={found}"


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
    out = Path(__file__).resolve().parents[4] / "审查" / "corpus-voice-selftest.json"
    if out.parent.exists():
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
