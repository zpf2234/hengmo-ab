#!/usr/bin/env python3
"""Pin the MCP figure router and the deterministic fallback to identical decisions.

The skill promises: the flat contract documented in SKILL.md is canonical, the nested
geometry/data/relations form stays accepted, and "MCP preferred, fallback when absent"
must never change the routing decision. Historically the MCP server consumed only the
nested form, so every spec written per SKILL.md was rejected as "not needing a figure"
-- but only when the MCP was available, which is exactly the preferred path. These cases
pin both implementations to the same (should_insert, renderer, figure_type) triple so
the two code paths cannot drift apart silently again.

The MCP server imports the `mcp` package at module level; a stub is injected when the
package is absent so this selftest only depends on the decision logic.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import types
from pathlib import Path

SCHEMA_VERSION = 1

SCRIPTS = Path(__file__).resolve().parent

# name -> (spec, expected {should_insert, renderer, figure_type})
CASES: dict[str, tuple[dict, dict]] = {
    # SKILL.md flat contract routed through the historically broken MCP path.
    "flat_time_series_validation": (
        {
            "figure_id": "F01",
            "section": "结果验证",
            "claim_id": "Q1-C1",
            "claim": "残差随迭代单调收敛到阈值以下",
            "data_shape": "time_series",
            "step_count": 1,
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "time_response"},
    ),
    # The nested form earlier callers used must keep working.
    "nested_time_series_validation": (
        {
            "section": "结果验证",
            "claim_id": "Q1-C1",
            "claim": "残差随迭代单调收敛到阈值以下",
            "data": {"time_series": True},
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "time_response"},
    ),
    # Section title variant (missing 的) used to fall out of the exact alias table.
    "section_variant_geometry": (
        {
            "section": "模型建立与求解",
            "claim_id": "Q2-C3",
            "claim": "首次接触发生在切点，最小间隙连续跨零",
            "has_geometry": True,
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "geometry_mechanism"},
    ),
    "nested_geometry": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q2-C3",
            "claim": "首次接触发生在切点，最小间隙连续跨零",
            "geometry": {"tangency": True},
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "geometry_mechanism"},
    ),
    # Three linear stages alone do not justify a flow diagram. The information-gain
    # gate deliberately prefers short prose or a compact formula in this case.
    "linear_three_steps_rejected": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q3-C1",
            "claim": "粗搜—细化—复核三阶段给出全局最优带误差界",
            "step_count": 3,
            "object_count": 2,
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    # A decision alone justifies a flow diagram even with fewer than three steps.
    "decision_two_steps_flow": (
        {
            "section": "建模求解",
            "claim_id": "Q3-C2",
            "claim": "步长自适应依赖误差阈值判断",
            "step_count": 2,
            "has_decision": True,
            "prose_formula_table_insufficient": True,
            "information_gain_reason": "分支条件与回退方向难以由短文同时表达",
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "decision_flow"},
    ),
    "nested_branches_flow": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q3-C3",
            "claim": "候选生成—筛选—复核含双分支回退",
            "relations": {
                "steps": 4,
                "branches": 2,
                "prose_formula_table_insufficient": True,
                "information_gain_reason": "双分支回退与汇合关系需要在同一阅读链中呈现",
            },
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "decision_flow"},
    ),
    "nested_feedback_flow": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q3-C4",
            "claim": "迭代含反馈回路直至收敛",
            "relations": {
                "steps": 2,
                "feedback": True,
                "prose_formula_table_insufficient": True,
                "information_gain_reason": "反馈位置和判停回路仅用线性文字容易误读",
            },
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "algorithm_flow"},
    ),
    # Module structure: three-plus linear stages across three-plus objects, no branches.
    "module_structure": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q1-C2",
            "claim": "三个子模型共享几何输入并递进传递结果",
            "step_count": 3,
            "object_count": 3,
            "has_nontrivial_relations": True,
            "prose_formula_table_insufficient": True,
            "information_gain_reason": "共享输入和多模块递进关系需要同时对照",
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "module_structure"},
    ),
    # Analysis-chapter shared relations.
    "analysis_problem_relation": (
        {
            "section": "问题分析",
            "claim_id": "Q0-C1",
            "claim": "三问共享螺线几何模型并逐问递进",
            "shared_outputs": 2,
            "object_count": 3,
            "prose_formula_table_insufficient": True,
            "information_gain_reason": "跨问共享量和递进输出难以由一段短文完整复原",
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "problem_relation"},
    ),
    "nested_analysis_problem_relation": (
        {
            "section": "问题分析",
            "claim_id": "Q0-C1",
            "claim": "三问共享螺线几何模型并逐问递进",
            "relations": {
                "shared_outputs": 2,
                "object_count": 3,
                "prose_formula_table_insufficient": True,
                "information_gain_reason": "跨问共享量和递进输出难以由一段短文完整复原",
            },
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "problem_relation"},
    ),
    # Python data-shape mapping parity for the nested booleans.
    "nested_surface_results": (
        {
            "section": "结果",
            "claim_id": "Q4-C1",
            "claim": "响应曲面在参数区间内存在唯一峰",
            "data": {"surface": True},
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "surface"},
    ),
    "flat_spatial_path": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q4-C2",
            "claim": "路径覆盖满足最小转弯半径约束",
            "data_shape": "spatial_path",
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "trajectory"},
    ),
    "spatial_coordinates_default": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q4-C3",
            "claim": "把手轨迹为等距螺线且无碰撞",
            "has_spatial_coordinates": True,
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "trajectory"},
    ),
    "role_quantitative_over_geometry": (
        {
            "section": "结果验证",
            "claim_id": "2025B-Q2-C2",
            "claim": "双角度光谱反演厚度在容差内一致",
            "figure_role": "quantitative_evidence",
            "has_geometry": True,
            "data_shape": "xy_relation",
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "scatter_fit"},
    ),
    "role_quantitative_over_decision": (
        {
            "section": "结果验证",
            "claim_id": "2024B-Q4-C3",
            "claim": "次品率不确定性改变最优策略切换边界",
            "figure_role": "quantitative_evidence",
            "has_decision": True,
            "data_shape": "parameter_scan_2d",
        },
        {"should_insert": True, "renderer": "python-matplotlib", "figure_type": "contour"},
    ),
    "role_quantitative_without_data_rejected": (
        {
            "section": "结果",
            "claim_id": "NEG-NODATA",
            "claim": "装饰性三维强调结论",
            "figure_role": "quantitative_evidence",
            "has_geometry": True,
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    # Outside the analysis chapter the same relation is expressed as a module structure.
    "object_module_structure": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q5-C1",
            "claim": "三个对象共享输入并存在递进依赖",
            "object_count": 3,
            "has_nontrivial_relations": True,
            "prose_formula_table_insufficient": True,
            "information_gain_reason": "对象间并行共享与递进依赖需要统一表达",
        },
        {"should_insert": True, "renderer": "paper-tikz", "figure_type": "module_structure"},
    ),
    "manual_layout_visio_fallback": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q5-C2",
            "claim": "多层业务状态需要团队继续在图形界面中调整布局",
            "has_decision": True,
            "prose_formula_table_insufficient": True,
            "information_gain_reason": "多层状态分支无法由短文和表格清楚复原",
            "requires_manual_layout": True,
            "visio_fallback_reason": "对象层级很多且比赛现场需由多人继续在图形界面中协同调整",
        },
        {"should_insert": True, "renderer": "paper-visio", "figure_type": "decision_flow"},
    ),
    # Rejections.
    "abstract_rejected": (
        {
            "section": "摘要",
            "claim_id": "Q1-C1",
            "claim": "残差收敛",
            "data_shape": "time_series",
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "evaluation_rejected": (
        {
            "section": "模型评价",
            "claim_id": "Q9-C1",
            "claim": "模型在扰动下保持稳定",
            "data_shape": "uncertainty",
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "appendix_rejected_even_with_data": (
        {
            "section": "附录",
            "claim_id": "Q9-C2",
            "claim": "补充参数扫描",
            "data_shape": "parameter_scan_1d",
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "missing_claim_id_rejected": (
        {
            "section": "模型的建立与求解",
            "claim": "缺证据来源的图",
            "data_shape": "time_series",
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "missing_claim_rejected": (
        {
            "section": "模型的建立与求解",
            "claim_id": "QX-C0",
            "data_shape": "time_series",
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "flat_duplicate_rejected": (
        {
            "section": "结果验证",
            "claim_id": "Q1-C1",
            "claim": "残差收敛",
            "data_shape": "time_series",
            "existing_figure_overlap": True,
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "nested_duplicate_rejected": (
        {
            "section": "结果验证",
            "claim_id": "Q1-C1",
            "claim": "残差收敛",
            "data": {"time_series": True},
            "duplicates_existing_figure": True,
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
    "simple_step_rejected": (
        {
            "section": "模型的建立与求解",
            "claim_id": "Q6-C1",
            "claim": "闭式代入即可完成",
            "step_count": 1,
            "object_count": 1,
        },
        {"should_insert": False, "renderer": None, "figure_type": None},
    ),
}


def _stub_mcp_package() -> None:
    """Provide a minimal mcp.server.fastmcp so the server module imports without the SDK."""
    if "mcp.server.fastmcp" in sys.modules:
        return
    try:
        import mcp.server.fastmcp  # noqa: F401

        return
    except ImportError:
        pass

    class _FastMCP:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def tool(self, *args, **kwargs):
            def wrap(fn):
                return fn

            return wrap

        def run(self) -> None:
            pass

    fastmcp = types.ModuleType("mcp.server.fastmcp")
    fastmcp.FastMCP = _FastMCP
    server = types.ModuleType("mcp.server")
    server.fastmcp = fastmcp
    package = types.ModuleType("mcp")
    package.server = server
    sys.modules.setdefault("mcp", package)
    sys.modules.setdefault("mcp.server", server)
    sys.modules["mcp.server.fastmcp"] = fastmcp


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalize_triple(payload: dict) -> dict:
    renderer = payload.get("renderer")
    figure_type = payload.get("figure_type")
    return {
        "should_insert": bool(payload.get("should_insert")),
        "renderer": None if renderer in (None, "none") else renderer,
        "figure_type": None if figure_type in (None, "none") else figure_type,
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--server",
        default=None,
        help="figure_router_server.py; defaults to <root>/figure_mcp/figure_router_server.py",
    )
    parser.add_argument("--output", default="审查/router-parity-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    server_path = (
        Path(args.server).resolve() if args.server else root / "figure_mcp" / "figure_router_server.py"
    )
    fallback_path = SCRIPTS / "route_figures.py"

    if not server_path.is_file():
        print(
            json.dumps(
                {"pass": False, "error": f"figure router MCP server not found: {server_path}"},
                ensure_ascii=False,
            )
        )
        return 1

    _stub_mcp_package()
    server = load_module(server_path, "figure_router_server_under_test")
    fallback = load_module(fallback_path, "route_figures_under_test")

    results: dict[str, dict] = {}
    for name, (spec, expected) in CASES.items():
        mcp_triple = normalize_triple(server.decide(dict(spec)))
        fallback_triple = normalize_triple(fallback.route(dict(spec)))
        ok = mcp_triple == fallback_triple == expected
        results[name] = {
            "pass": ok,
            "expected": expected,
            "mcp": mcp_triple,
            "fallback": fallback_triple,
        }

    result = {
        "schema_version": SCHEMA_VERSION,
        "pass": all(item["pass"] for item in results.values()),
        "case_count": len(results),
        "server": str(server_path),
        "fallback": str(fallback_path),
        "cases": results,
    }
    if not args.no_write:
        output = root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = sorted(name for name, item in results.items() if not item["pass"])
    print(
        json.dumps(
            {"pass": result["pass"], "case_count": len(results), "failed": failed},
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
