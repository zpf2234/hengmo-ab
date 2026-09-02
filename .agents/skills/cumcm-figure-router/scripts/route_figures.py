#!/usr/bin/env python
"""Deterministic CUMCM figure necessity, type, and MCP backend router.

This is the fallback used when the paper-figure-router MCP is unavailable. It
implements the same input normalization and decision table as
figure_mcp/figure_router_server.py: the flat SKILL.md contract is canonical and
the nested geometry/data/relations form stays accepted. selftest_router_parity.py
pins both implementations to identical decisions -- change them together.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORBIDDEN_SECTIONS = {
    "abstract",
    "restatement",
    "assumptions",
    "notation",
    "references",
    "appendix",
    "evaluation",
}
ROUTABLE_SECTIONS = {"analysis", "model", "results", "validation"}

SECTION_ALIASES = {
    "摘要": "abstract",
    "问题重述": "restatement",
    "问题分析": "analysis",
    "模型假设": "assumptions",
    "符号说明": "notation",
    "模型的建立与求解": "model",
    "模型建立与求解": "model",
    "建模求解": "model",
    "结果": "results",
    "结果验证": "validation",
    "验证": "validation",
    "模型评价": "evaluation",
    "参考文献": "references",
    "附录": "appendix",
}

# Ordered substring fallback: 评价 wins inside 模型评价, 验证 wins inside 结果验证.
SECTION_SUBSTRING_RULES = (
    ("重述", "restatement"),
    ("假设", "assumptions"),
    ("符号", "notation"),
    ("摘要", "abstract"),
    ("参考文献", "references"),
    ("附录", "appendix"),
    ("评价", "evaluation"),
    ("验证", "validation"),
    ("分析", "analysis"),
    ("结果", "results"),
    ("模型", "model"),
    ("建模", "model"),
    ("求解", "model"),
)

GEOMETRY_KEYS = ("coordinates", "angles", "tangency", "projection", "collision_boundary", "dimensions")

DATA_KEY_TO_SHAPE = (
    ("time_series", "time_series"),
    ("trajectory", "spatial_path"),
    ("surface", "field_3d"),
    ("matrix", "matrix"),
    ("sensitivity", "parameter_scan_1d"),
    ("uncertainty", "uncertainty"),
    ("distribution", "distribution"),
    ("comparison", "groups"),
)

DATA_TYPES = {
    "time_series": "time_response",
    "iteration": "convergence",
    "xy_relation": "scatter_fit",
    "distribution": "distribution_comparison",
    "groups": "ranked_comparison",
    "parameter_scan_1d": "sensitivity_curve",
    "parameter_scan_2d": "contour",
    "matrix": "heatmap",
    "spatial_path": "trajectory",
    "spatial_state": "configuration",
    "field_2d": "contour",
    "field_3d": "surface",
    "uncertainty": "uncertainty_band",
}

INSERTION_POINTS = {
    "problem_relation": "问题分析章末，在各问依赖与共享量说明之后",
    "geometry_mechanism": "对应模型小节中，坐标系和对象定义之后、首个控制方程之前",
    "decision_flow": "对应求解小节中，算法状态与判停条件定义之后、参数设置或结果之前",
    "algorithm_flow": "对应求解小节中，算法状态与判停条件定义之后、参数设置或结果之前",
    "module_structure": "共享模型或模块定义之后、各模块公式展开之前",
    "__data__": "提出待检验命题的引导句之后、关键数值与机理解释之前",
}

REJECT_NO_CLAIM = "缺少唯一 claim 或 claim_id，没有可检验命题的图不得进入正式路由"
REJECT_FORBIDDEN_SECTION = "该章节只承担文字、假设、符号、评价或文献职责，正式论证图移至分析、模型、结果或验证部分"
REJECT_DUPLICATE = "与现有图形承担相同证据职责，应合并或删除重复图"
REJECT_INSUFFICIENT = "正文或表格能够更短地完成该职责，现有关系复杂度不足以支持新增图形"
REJECT_FLOW_INFO_GAIN = (
    "未明确证明短文、公式与表格不足以清楚表达该流程；步骤数或单个判断本身不构成流程图理由"
)
REJECT_FLOW_STRUCTURE = (
    "虽声明非图表达不足，但未提供非平凡关系、分支、反馈、回退或状态转移，线性步骤不路由流程图"
)

CLASSIC_FLOW_PRESET = "cumcm-classic-orthogonal"
CLASSIC_FLOW_VARIANTS = {
    "horizontal-mainline", "horizontal-feedback", "vertical-branching",
    "layered-dependency", "objective-constraint-fusion", "phased-groups",
    "hybrid-evolution", "mechanism-assisted",
}


def flowchart_render_contract(spec: dict[str, Any], norm: dict[str, Any], figure_type: str) -> dict[str, Any]:
    requested = str(spec.get("layout_variant", "")).strip().lower()
    if requested in CLASSIC_FLOW_VARIANTS:
        variant = requested
    elif spec.get("groups") or spec.get("has_phases"):
        variant = "phased-groups"
    elif spec.get("has_objective_constraint_fusion"):
        variant = "objective-constraint-fusion"
    elif spec.get("mechanism_assisted"):
        variant = "mechanism-assisted"
    elif figure_type in {"problem_relation", "module_structure"}:
        variant = "layered-dependency"
    elif norm["has_decision"] and norm["step_count"] >= 7:
        variant = "vertical-branching"
    elif norm["has_loop"]:
        variant = "horizontal-feedback"
    else:
        variant = "horizontal-mainline"
    return {
        "visual_preset": CLASSIC_FLOW_PRESET,
        "layout_variant": variant,
        "style_confirmation_required": False,
        "innovation_contract": "创新本题特有的信息结构、阶段、约束汇合与反馈，不改变固定视觉风格",
    }

ROUTE_REASONS = {
    "problem_relation": "多问题/对象存在共享输入、输出或递进关系",
    "geometry_mechanism": "精确几何、角度、尺寸或公式标注",
    "decision_flow": "存在判断分支，需要可检验的决策流程",
    "algorithm_flow": "存在循环/反馈或三个以上不可合并阶段",
    "module_structure": "三个以上模块共享输入输出，结构需要显式表达",
    "__data__": "真实数值、轨迹、状态或统计证据",
}


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalize_section(value: Any) -> str:
    text = str(value or "").strip()
    if text in SECTION_ALIASES:
        return SECTION_ALIASES[text]
    lowered = text.lower()
    if lowered in FORBIDDEN_SECTIONS or lowered in ROUTABLE_SECTIONS:
        return lowered
    for token, kind in SECTION_SUBSTRING_RULES:
        if token in text:
            return kind
    return lowered


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Accept both the flat SKILL.md contract and the nested geometry/data/relations form."""
    geometry = spec.get("geometry") if isinstance(spec.get("geometry"), dict) else {}
    data = spec.get("data") if isinstance(spec.get("data"), dict) else {}
    relations = spec.get("relations") if isinstance(spec.get("relations"), dict) else {}

    data_shape = str(spec.get("data_shape") or "").strip()
    if not data_shape:
        for key, shape in DATA_KEY_TO_SHAPE:
            if data.get(key):
                data_shape = shape
                break

    step_count = max(_int(spec.get("step_count")), _int(relations.get("steps")))
    object_count = max(_int(spec.get("object_count")), _int(relations.get("object_count")))
    shared_outputs = max(_int(spec.get("shared_outputs")), _int(relations.get("shared_outputs")))
    has_decision = (
        bool(spec.get("has_decision"))
        or bool(spec.get("has_nested_decisions"))
        or bool(spec.get("has_state_transition"))
        or _int(relations.get("branches")) >= 1
        or bool(relations.get("nested_decisions"))
        or bool(relations.get("state_transition"))
    )
    has_loop = (
        bool(spec.get("has_loop"))
        or bool(spec.get("has_feedback"))
        or bool(spec.get("has_backtrack"))
        or bool(relations.get("feedback"))
        or bool(relations.get("backtrack"))
    )
    prose_formula_table_insufficient = (
        bool(spec.get("prose_formula_table_insufficient"))
        or bool(spec.get("text_formula_table_insufficient"))
        or bool(spec.get("nonvisual_explanation_insufficient"))
        or bool(relations.get("prose_formula_table_insufficient"))
        or bool(relations.get("text_formula_table_insufficient"))
        or bool(relations.get("nonvisual_explanation_insufficient"))
    )
    has_nontrivial_relations = (
        bool(spec.get("has_nontrivial_relations"))
        or bool(spec.get("has_branch_rejoin"))
        or bool(relations.get("nontrivial_relations"))
        or bool(relations.get("complex_dependencies"))
        or bool(relations.get("branch_rejoin"))
        or (shared_outputs >= 1 and object_count >= 3)
    )

    return {
        "section": normalize_section(spec.get("section")),
        "claim": str(spec.get("claim", "")).strip(),
        "claim_id": str(spec.get("claim_id", "")).strip(),
        "figure_role": str(spec.get("figure_role", "")).strip().lower(),
        "duplicates": bool(spec.get("existing_figure_overlap")) or bool(spec.get("duplicates_existing_figure")),
        "has_geometry": (
            bool(spec.get("has_geometry"))
            or bool(spec.get("needs_exact_labels"))
            or any(bool(geometry.get(key)) for key in GEOMETRY_KEYS)
        ),
        "has_decision": has_decision,
        "has_loop": has_loop,
        "has_nontrivial_relations": has_nontrivial_relations,
        "has_nontrivial_flow_structure": has_decision or has_loop or has_nontrivial_relations,
        "prose_formula_table_insufficient": prose_formula_table_insufficient,
        "information_gain_reason": str(
            spec.get("information_gain_reason")
            or relations.get("information_gain_reason")
            or ""
        ).strip(),
        "has_spatial_coordinates": bool(spec.get("has_spatial_coordinates")),
        "step_count": step_count,
        "object_count": object_count,
        "shared_outputs": shared_outputs,
        "data_shape": data_shape,
        "requires_manual_layout": bool(spec.get("requires_manual_layout")),
        "visio_fallback_reason": str(spec.get("visio_fallback_reason", "")).strip(),
    }


def flow_renderer(norm: dict[str, Any]) -> tuple[str | None, str | None]:
    """Use TikZ by default; allow Visio only for a justified manual-layout need."""
    if not norm["requires_manual_layout"]:
        return "paper-tikz", None
    if len(norm["visio_fallback_reason"]) < 12:
        return None, "选择 Visio 必须说明 TikZ 无法妥善处理的人工编排需求"
    return "paper-visio", None


def route_normalized(norm: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """Shared decision table; returns (renderer, figure_type, reject_reason).

    A flow/relationship diagram needs both explicit information gain and a
    non-trivial relation, branch, feedback, backtrack, or state transition. Step
    count alone never triggers a flowchart. Exact geometry outranks flow;
    analysis-chapter shared relations outrank geometry only after passing this gate.
    """
    if not norm["claim"] or not norm["claim_id"]:
        return None, None, REJECT_NO_CLAIM
    if norm["section"] in FORBIDDEN_SECTIONS:
        return None, None, REJECT_FORBIDDEN_SECTION
    if norm["duplicates"]:
        return None, None, REJECT_DUPLICATE

    if norm["figure_role"] in {"quantitative_evidence", "result", "validation"}:
        if norm["has_spatial_coordinates"] or norm["data_shape"] in DATA_TYPES:
            return "python-matplotlib", DATA_TYPES.get(norm["data_shape"], "trajectory"), None
        return None, None, "定量证据图缺少受支持的结构化数据形态，禁止用几何或装饰性三维替代"

    flow_information_gain = (
        norm["prose_formula_table_insufficient"]
        and norm["has_nontrivial_flow_structure"]
    )
    analysis_relation = (
        norm["section"] == "analysis"
        and norm["has_nontrivial_relations"]
    )

    if norm["has_geometry"] and not (analysis_relation and flow_information_gain):
        return "paper-tikz", "geometry_mechanism", None
    if analysis_relation and flow_information_gain:
        renderer, flow_error = flow_renderer(norm)
        if flow_error:
            return None, None, flow_error
        return renderer, "problem_relation", None
    if flow_information_gain:
        renderer, flow_error = flow_renderer(norm)
        if flow_error:
            return None, None, flow_error
        if norm["has_decision"]:
            return renderer, "decision_flow", None
        if norm["has_loop"]:
            return renderer, "algorithm_flow", None
        if norm["has_nontrivial_relations"]:
            return renderer, "module_structure", None
        return None, None, REJECT_FLOW_STRUCTURE
    if norm["has_spatial_coordinates"] or norm["data_shape"] in DATA_TYPES:
        return "python-matplotlib", DATA_TYPES.get(norm["data_shape"], "trajectory"), None
    if norm["has_nontrivial_flow_structure"] and not norm["prose_formula_table_insufficient"]:
        return None, None, REJECT_FLOW_INFO_GAIN
    if norm["prose_formula_table_insufficient"] and not norm["has_nontrivial_flow_structure"]:
        return None, None, REJECT_FLOW_STRUCTURE
    return None, None, REJECT_INSUFFICIENT


def route(item: dict) -> dict:
    norm = normalize_spec(item)
    renderer, ftype, reject_reason = route_normalized(norm)
    if renderer is None or ftype is None:
        return {
            "should_insert": False,
            "renderer": None,
            "figure_type": None,
            "reasons": [str(reject_reason)],
            "status": "REJECT",
        }
    insertion_key = ftype if ftype in INSERTION_POINTS else "__data__"
    reason_key = ftype if ftype in ROUTE_REASONS else "__data__"
    result = {
        "should_insert": True,
        "renderer": renderer,
        "figure_type": ftype,
        "reasons": [ROUTE_REASONS[reason_key]],
        "status": "ROUTED",
        "insertion_point": INSERTION_POINTS[insertion_key],
        "before_sentence_contract": "图前提出对象、条件和待读数，不提前宣布结论",
        "after_paragraph_contract": "图后依次写观察、关键数值、机制解释和对当前答案的影响",
        "required_artifacts": ["spec_json", "editable_source", "pdf", "svg", "png_preview", "provenance", "final_page_review"],
    }
    if ftype in {"problem_relation", "decision_flow", "algorithm_flow", "module_structure"}:
        result.update(flowchart_render_contract(item, norm, ftype))
        result["information_gain_gate"] = {
            "prose_formula_table_insufficient": norm["prose_formula_table_insufficient"],
            "has_nontrivial_flow_structure": norm["has_nontrivial_flow_structure"],
            "reason": norm["information_gain_reason"],
        }
        result["renderer_choice"] = {
            "tikz_considered": True,
            "selected": "visio" if renderer == "paper-visio" else "tikz",
            "fallback_reason": norm["visio_fallback_reason"] if renderer == "paper-visio" else "not-applicable",
        }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    src = Path(a.input)
    data = json.loads(src.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("figures", [])
    out = []
    for item in items:
        r = route(item)
        r.update({"figure_id": item.get("figure_id"), "claim_id": item.get("claim_id"), "claim": item.get("claim"), "section": item.get("section")})
        out.append(r)
    result = {"schema_version": 2, "router_mode": "deterministic_fallback", "pass": all(x["status"] in {"ROUTED", "REJECT"} for x in out), "figures": out}
    p = Path(a.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "routed": sum(x["should_insert"] for x in out), "rejected": sum(not x["should_insert"] for x in out), "output": str(p)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
