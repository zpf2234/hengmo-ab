#!/usr/bin/env python3
"""Run isolated positive and negative tests for the question-depth audit."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "audit_question_depth.py"
SPEC = importlib.util.spec_from_file_location("audit_question_depth_under_test", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def component(**fields: str) -> dict:
    return {
        "pass": True,
        **fields,
        "evidence": ["论文/论文.tex#5.1-对应职责"],
    }


def readiness_item(task: str) -> dict:
    return {
        "status": "ready",
        "substantive_task": task,
        "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
    }


def valid_payload(body_pages: int = 23, total_pages: int = 42, digest: str = "a" * 64) -> dict:
    return {
        "schema_version": 1,
        "question_ids": ["q1"],
        "body_page_plan": {
            "official_body_max": 30,
            "shared_sections_page_range": [4, 6],
            "basis": "前置章节、评价、AI 声明和参考文献的合计估计",
        },
        "questions": {
            "q1": {
                "architecture": {
                    "role": "core",
                    "chain_type": "boundary-optimization",
                    "progression_axis": "foundation",
                    "route_summary": "先证明搜索域，再求解边界最优并验证邻域",
                    "planned_page_range": [4, 6],
                    "page_basis": "含几何推导、边界优化和独立复核",
                    "planned_subsections": ["几何边界", "目标函数", "参数搜索"],
                    "inheritance": {"status": "none", "objects": []},
                },
                "argument_plan": {
                    "structure_anchor": "A053-structure-only",
                    "adaptation_basis": "本问属于边界优化，只迁移等价转化、约束搜索和邻域复核功能链",
                    "derivation_path": [
                        {
                            "purpose": "由几何关系压缩候选域并导出容量约束",
                            "relation_or_method": "先证明上界，再写目标函数与可行约束",
                            "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
                        }
                    ],
                    "result_claims": [
                        {
                            "claim_id": "C-Q1-01",
                            "expected_output": "最终方案、目标值和约束余量",
                            "interpretation_task": "解释活跃约束为何决定最优点及其决策影响",
                            "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
                        }
                    ],
                    "validation_plan": {
                        "main_risk": "搜索区间遗漏更优边界点",
                        "independent_check": "用小规模精确枚举复算主搜索结果",
                        "boundary_or_stress_check": "扩大搜索域并比较最优点两侧邻域",
                        "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
                    },
                    "presentation_plan": [
                        {
                            "claim_id": "C-Q1-01",
                            "medium": "table",
                            "purpose": "并列报告方案、目标值与约束余量并供正文解释",
                            "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
                        }
                    ],
                },
                "search_scope_justification": {
                    "applicable": True,
                    "basis": "由几何上界和必要条件压缩候选区间",
                    "resulting_scope": "变量限制在 [0, 20]，且覆盖全部可行边界",
                    "boundary_or_counterexample_check": "将区间扩至 [0, 30] 后最优点不变",
                    "evidence": ["论文/论文.tex#搜索范围说明"],
                },
                "active_constraint_check": {
                    "applicable": True,
                    "active_constraints": "最优点处容量约束取等号",
                    "slack_or_multiplier": "其余约束最小余量为 0.18",
                    "neighborhood_check": "最优点两侧各复算 20 个邻域点",
                    "outside_or_counterexample": "域外点违反容量约束或目标至少劣化 1.2%",
                    "evidence": ["论文/论文.tex#活跃约束与邻域复核"],
                },
                "prewrite_readiness": {
                    "status": "ready",
                    "blocking_gaps": [],
                    "responsibilities": {
                        "requirements": readiness_item("冻结题面输出、约束和 claim_id 对应"),
                        "model_specific_derivation": readiness_item("从几何关系推出本题核心约束"),
                        "parameter_sources": readiness_item("核对题面量、标定量及误差来源"),
                        "solver_contract": readiness_item("冻结精度、停止条件和边界处理"),
                        "result_interpretation": readiness_item("准备关键读数、机理及决策影响证据"),
                        "independent_validation": readiness_item("准备与主搜索异构的小规模精确枚举"),
                        "stress_or_failure_boundary": readiness_item("准备约束边界与参数扰动证据"),
                        "final_answer_mapping": readiness_item("逐项绑定题面要求、结论和 claim_id"),
                    },
                    "conditional_responsibilities": {
                        "search_scope_justification": readiness_item(
                            "用几何上界和扩大区间复算证明搜索域覆盖目标"
                        ),
                        "active_constraint_check": readiness_item(
                            "识别活跃约束并复算最优点邻域与域外反例"
                        ),
                    },
                },
                "requirements": [
                    {
                        "id": "q1-r1",
                        "prompt_item": "给出题面要求的最终方案与指标",
                        "claim_id": "C-Q1-01",
                        "evidence": ["求解/证据矩阵.csv#C-Q1-01"],
                    }
                ],
                "model_specific_derivation": component(summary="由本题几何关系推出核心约束"),
                "parameter_sources": component(summary="题面量与标定量均已给出来源"),
                "solver_contract": component(
                    precision="报告精度 1e-4",
                    stopping_condition="相邻目标相对差小于 1e-6",
                    boundary_handling="投影回可行域并复算约束余量",
                ),
                "result_interpretation": component(
                    key_result="最优指标为 12.34 单位",
                    mechanism="核心约束在边界处起作用",
                    answer_impact="据此确定最终方案",
                ),
                "independent_validation": component(
                    method="小规模精确枚举",
                    independence="与主启发式搜索不共享更新机制",
                    metric="目标相对差",
                    threshold="小于 0.5%",
                    observed="0.12%",
                ),
                "stress_or_failure_boundary": component(
                    type="constraint-boundary",
                    range_or_case="全部边界情形与 ±10% 参数扰动",
                    observed_effect="约束均满足且方案排序不变",
                    decision="在该范围内结论有效，超出后重新优化",
                ),
                "final_answer_mapping": [
                    {
                        "requirement_id": "q1-r1",
                        "claim_id": "C-Q1-01",
                        "final_answer": "采用方案 A，指标为 12.34 单位",
                    "evidence": ["论文/论文.tex#问题一结论"],
                    }
                ],
            }
        },
        "compile_feedback": {
            "iterations": [
                {
                    "iteration": 1,
                    "body_pages": body_pages,
                    "total_pdf_pages": total_pages,
                    "pdf_sha256": digest,
                    "build_status": (
                        "INTERNAL_REVIEW_CANDIDATE"
                        if body_pages <= 30
                        else "INTERNAL_FAILED_BUILD"
                    ),
                    "deliverable": False,
                    "missing_depth_items": [],
                    "actions": [],
                }
            ]
        },
    }


def two_question_payload() -> dict:
    payload = copy.deepcopy(valid_payload())
    q2 = copy.deepcopy(payload["questions"]["q1"])
    q2["architecture"] = {
        "role": "core",
        "chain_type": "sequential-decision",
        "progression_axis": "information-state",
        "route_summary": "继承问题一的可行域，再把单阶段决策扩展为序贯策略",
        "planned_page_range": [3, 5],
        "page_basis": "继承前问约束，重点展开状态扩展和策略验证",
        "planned_subsections": ["状态扩展", "序贯决策"],
        "inheritance": {
            "status": "used",
            "objects": [
                {
                    "source_question": "q1",
                    "object": "可行域与容量约束",
                    "consistency_check": "单位、有效数字和约束方向与问题一一致",
                    "evidence": ["求解/证据矩阵.csv#C-Q1-01"],
                }
            ],
        },
    }
    q2["search_scope_justification"] = {
        "applicable": False,
        "basis": "",
        "resulting_scope": "",
        "boundary_or_counterexample_check": "",
        "evidence": [],
    }
    q2["active_constraint_check"] = {
        "applicable": False,
        "active_constraints": "",
        "slack_or_multiplier": "",
        "neighborhood_check": "",
        "outside_or_counterexample": "",
        "evidence": [],
    }
    q2["prewrite_readiness"]["conditional_responsibilities"] = {
        "search_scope_justification": {
            "status": "not-applicable",
            "reason": "本问继承已验证可行域，不执行新的临界或边界搜索",
            "substantive_task": "",
            "source_evidence": [],
        },
        "active_constraint_check": {
            "status": "not-applicable",
            "reason": "本问是序贯决策而非边界最优化或容量上界问题",
            "substantive_task": "",
            "source_evidence": [],
        },
    }
    q2["requirements"][0]["id"] = "q2-r1"
    q2["requirements"][0]["claim_id"] = "C-Q2-01"
    q2["argument_plan"]["adaptation_basis"] = (
        "本问只迁移基础状态继承和新增信息机制，不复制边界优化模型"
    )
    q2["argument_plan"]["result_claims"][0]["claim_id"] = "C-Q2-01"
    q2["argument_plan"]["presentation_plan"][0]["claim_id"] = "C-Q2-01"
    q2["final_answer_mapping"][0]["requirement_id"] = "q2-r1"
    q2["final_answer_mapping"][0]["claim_id"] = "C-Q2-01"
    payload["question_ids"] = ["q1", "q2"]
    payload["questions"]["q2"] = q2
    return payload


def measurements(body_pages: int = 23, total_pages: int = 42, digest: str = "a" * 64) -> dict:
    return {
        "body_pages": body_pages,
        "total_pdf_pages": total_pages,
        "body_start_page": 2,
        "appendix_start_page": body_pages + 2,
        "references_start_page": body_pages,
        "pdf_sha256": digest,
        "pdf": "论文/论文.pdf",
    }


def run_case(
    root: Path,
    payload: dict,
    expected_pass: bool,
    expected_error: str | None = None,
    phase: str = "final",
    measured: dict | None = None,
    selected: list[str] | None = None,
) -> dict:
    result = AUDIT.validate_payload(
        payload,
        root,
        phase,
        measured if measured is not None else measurements(),
        selected,
    )
    error_match = expected_error is None or any(
        expected_error in item for item in result["errors"]
    )
    return {
        "expected_pass": expected_pass,
        "actual_pass": result["pass"],
        "expected_error": expected_error,
        "errors": result["errors"],
        "pass": result["pass"] is expected_pass and error_match,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/question-depth-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="cumcm-depth-selftest-") as tmp:
        root = Path(tmp)
        (root / "论文").mkdir(parents=True)
        (root / "求解").mkdir(parents=True)
        (root / "论文" / "论文.tex").write_text("模型、结果与验证。", encoding="utf-8")
        (root / "求解" / "证据矩阵.csv").write_text(
            "claim_id,结论\nC-Q1-01,采用方案A\nC-Q2-01,采用序贯策略B\n", encoding="utf-8"
        )

        cases: dict[str, dict] = {}
        cases["prewrite_ready_without_compile"] = run_case(
            root, valid_payload(), True, phase="prewrite", measured=None
        )
        missing_page_plan = valid_payload()
        del missing_page_plan["body_page_plan"]
        cases["prewrite_requires_body_page_plan"] = run_case(
            root,
            missing_page_plan,
            False,
            "body_page_plan must be an object",
            phase="prewrite",
            measured=None,
        )
        overplanned = valid_payload()
        overplanned["body_page_plan"]["shared_sections_page_range"] = [20, 25]
        overplanned["questions"]["q1"]["architecture"]["planned_page_range"] = [8, 10]
        cases["prewrite_plan_must_fit_official_maximum"] = run_case(
            root,
            overplanned,
            False,
            "planned upper bound exceeds",
            phase="prewrite",
            measured=None,
        )
        missing_question_range = valid_payload()
        missing_question_range["questions"]["q1"]["architecture"]["planned_page_range"] = []
        cases["each_question_requires_planned_page_range"] = run_case(
            root,
            missing_question_range,
            False,
            "planned_page_range must be two positive numbers",
            phase="prewrite",
            measured=None,
        )
        cases["content_complete_without_compile"] = run_case(
            root, valid_payload(), True, phase="content", measured=None
        )
        cases["single_question_completion_passes"] = run_case(
            root,
            two_question_payload(),
            True,
            phase="question",
            measured=None,
            selected=["q1"],
        )
        cases["official_range_body_passes"] = run_case(root, valid_payload(), True)
        cases["cross_question_inheritance_passes"] = run_case(
            root, two_question_payload(), True
        )

        long_total = valid_payload(total_pages=80)
        cases["total_pdf_pages_are_not_a_target"] = run_case(
            root, long_total, True, measured=measurements(total_pages=80)
        )

        short_complete = valid_payload(body_pages=12, total_pages=28)
        cases["short_complete_body_passes"] = run_case(
            root,
            short_complete,
            True,
            measured=measurements(body_pages=12, total_pages=28),
        )

        second_pass = valid_payload(body_pages=23, total_pages=39, digest="c" * 64)
        second_pass["compile_feedback"]["iterations"] = [
            {
                "iteration": 1,
                "body_pages": 18,
                "total_pdf_pages": 34,
                "pdf_sha256": "b" * 64,
                "build_status": "INTERNAL_FAILED_BUILD",
                "deliverable": False,
                "missing_depth_items": ["q1: 独立验证强度不足"],
                "actions": ["增加异构复算并解释阈值"],
            },
            {
                "iteration": 2,
                "body_pages": 23,
                "total_pdf_pages": 39,
                "pdf_sha256": "c" * 64,
                "build_status": "INTERNAL_REVIEW_CANDIDATE",
                "deliverable": False,
                "missing_depth_items": [],
                "actions": [],
            },
        ]
        cases["unresolved_first_compile_can_pass_after_recompile"] = run_case(
            root,
            second_pass,
            True,
            measured=measurements(body_pages=23, total_pages=39, digest="c" * 64),
        )

        cases["twenty_one_official_pages_need_no_second_metric"] = run_case(
            root,
            valid_payload(body_pages=21, total_pages=39),
            True,
            measured=measurements(body_pages=21, total_pages=39),
        )

        over = valid_payload(body_pages=31, total_pages=45)
        cases["above_official_max_blocks"] = run_case(
            root,
            over,
            False,
            "body above hard maximum",
            measured=measurements(body_pages=31, total_pages=45),
        )

        missing_derivation = valid_payload()
        missing_derivation["questions"]["q1"]["model_specific_derivation"]["pass"] = False
        cases["missing_derivation_blocks"] = run_case(
            root, missing_derivation, False, "model_specific_derivation: pass must be true"
        )

        weak_validation = valid_payload()
        weak_validation["questions"]["q1"]["independent_validation"]["independence"] = ""
        cases["validation_independence_is_required"] = run_case(
            root, weak_validation, False, "independent_validation: independence is empty"
        )

        missing_search_basis = valid_payload()
        missing_search_basis["questions"]["q1"]["search_scope_justification"]["basis"] = ""
        cases["search_scope_basis_is_required"] = run_case(
            root, missing_search_basis, False, "search_scope_justification: basis is empty"
        )

        missing_progression_axis = valid_payload()
        missing_progression_axis["questions"]["q1"]["architecture"]["progression_axis"] = ""
        cases["progression_axis_is_required"] = run_case(
            root, missing_progression_axis, False, "architecture: progression_axis must be one of"
        )

        compact_question_without_subsections = valid_payload()
        compact_question_without_subsections["questions"]["q1"]["architecture"]["planned_subsections"] = []
        cases["empty_planned_subsections_allowed_for_compact_question"] = run_case(
            root,
            compact_question_without_subsections,
            True,
            None,
            phase="prewrite",
            measured=None,
        )

        incomplete_argument_plan = valid_payload()
        incomplete_argument_plan["questions"]["q1"]["argument_plan"]["validation_plan"][
            "independent_check"
        ] = ""
        cases["complete_argument_plan_is_required_before_writing"] = run_case(
            root,
            incomplete_argument_plan,
            False,
            "validation_plan: independent_check is empty",
            phase="prewrite",
            measured=None,
        )

        figure_is_not_required = valid_payload()
        figure_is_not_required["questions"]["q1"]["argument_plan"]["presentation_plan"] = [
            {
                "claim_id": "C-Q1-01",
                "medium": "formula",
                "purpose": "直接给出边界关系并由正文解释约束作用",
                "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
            }
        ]
        cases["prewrite_does_not_require_a_figure"] = run_case(
            root, figure_is_not_required, True, phase="prewrite", measured=None
        )

        multiple_complementary_figures_are_allowed = valid_payload()
        multiple_complementary_figures_are_allowed["questions"]["q1"]["argument_plan"][
            "presentation_plan"
        ] = [
            {
                "claim_id": "C-Q1-01",
                "medium": "figure",
                "purpose": "展示目标在候选域内的整体变化",
                "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
            },
            {
                "claim_id": "C-Q1-01",
                "medium": "figure",
                "purpose": "放大最优点邻域并展示约束余量",
                "source_evidence": ["求解/证据矩阵.csv#C-Q1-01"],
            },
        ]
        cases["multiple_complementary_figures_are_allowed"] = run_case(
            root,
            multiple_complementary_figures_are_allowed,
            True,
            phase="prewrite",
            measured=None,
        )

        missing_neighborhood = valid_payload()
        missing_neighborhood["questions"]["q1"]["active_constraint_check"][
            "neighborhood_check"
        ] = ""
        cases["active_constraint_neighborhood_is_required"] = run_case(
            root,
            missing_neighborhood,
            False,
            "active_constraint_check: neighborhood_check is empty",
        )

        manuscript_as_source = valid_payload()
        manuscript_as_source["questions"]["q1"]["prewrite_readiness"][
            "responsibilities"
        ]["model_specific_derivation"]["source_evidence"] = [
            "论文/论文.tex#模型特有推导"
        ]
        cases["prewrite_cannot_use_manuscript_as_source"] = run_case(
            root,
            manuscript_as_source,
            False,
            "prewrite source evidence cannot come from the manuscript",
            phase="prewrite",
            measured=None,
        )

        quota_plan = valid_payload()
        quota_plan["questions"]["q1"]["prewrite_readiness"]["responsibilities"][
            "model_specific_derivation"
        ]["substantive_task"] = "把模型推导写满 3 页"
        cases["prewrite_rejects_page_quota"] = run_case(
            root,
            quota_plan,
            False,
            "pagination/content quota marker",
            phase="prewrite",
            measured=None,
        )

        for case_id, task in {
            "prewrite_rejects_expand_three_pages": "扩写 3 页模型说明",
            "prewrite_rejects_add_five_hundred_characters": "补 500 字背景",
            "prewrite_rejects_two_figure_allocation": "安排两张图",
            "prewrite_rejects_ten_formula_allocation": "列 10 个公式",
        }.items():
            quota_variant = valid_payload()
            quota_variant["questions"]["q1"]["prewrite_readiness"]["responsibilities"][
                "model_specific_derivation"
            ]["substantive_task"] = task
            cases[case_id] = run_case(
                root,
                quota_variant,
                False,
                "pagination/content quota",
                phase="prewrite",
                measured=None,
            )

        quota_action = valid_payload(body_pages=19, total_pages=35)
        quota_action["compile_feedback"]["iterations"][0]["missing_depth_items"] = [
            "q1: 参数来源说明不足"
        ]
        quota_action["compile_feedback"]["iterations"][0]["actions"] = ["补 500 字背景"]
        cases["short_compile_rejects_quota_revision_action"] = run_case(
            root,
            quota_action,
            False,
            "numeric pagination/content quota",
            measured=measurements(body_pages=19, total_pages=35),
        )

        source_only_completion = valid_payload()
        source_only_completion["questions"]["q1"]["model_specific_derivation"][
            "evidence"
        ] = ["求解/证据矩阵.csv#C-Q1-01"]
        cases["question_completion_requires_manuscript_anchor"] = run_case(
            root,
            source_only_completion,
            False,
            "completed responsibility needs a 论文/论文.tex#specific-anchor locator",
            phase="question",
            measured=None,
            selected=["q1"],
        )

        unknown_inheritance = two_question_payload()
        unknown_inheritance["questions"]["q2"]["architecture"]["inheritance"]["objects"][0][
            "source_question"
        ] = "q9"
        cases["unknown_inheritance_source_blocks"] = run_case(
            root, unknown_inheritance, False, "unknown source_question q9"
        )

        mapping_gap = valid_payload()
        mapping_gap["questions"]["q1"]["final_answer_mapping"] = []
        cases["final_answer_mapping_is_required"] = run_case(
            root, mapping_gap, False, "final_answer_mapping must be a non-empty list"
        )

        stale = valid_payload(digest="b" * 64)
        cases["stale_pdf_binding_blocks"] = run_case(
            root, stale, False, "latest compile feedback does not match current PDF: pdf_sha256"
        )

    result = {
        "schema_version": 1,
        "pass": all(item["pass"] for item in cases.values()),
        "case_count": len(cases),
        "cases": cases,
    }
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(cases)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
