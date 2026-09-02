from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import fitz
import pytest

import figure_router_server
import common
import matlab_server
import python_figure
import signature_benchmarks
import tikz_server
import visio_server


class _Cell:
    def __init__(self, value: float):
        self.ResultIU = value


class _Shape:
    def __init__(self, x: float, y: float, width: float, height: float, text: str = ""):
        self._cells = {
            "PinX": _Cell(x), "PinY": _Cell(y),
            "Width": _Cell(width), "Height": _Cell(height),
        }
        self.Text = text

    def CellsU(self, name: str):
        return self._cells[name]


class _FormulaCell:
    def __init__(self):
        self.FormulaU = ""


class _TextShape:
    def __init__(self):
        self.Text = ""
        self.cells: dict[str, _FormulaCell] = {}

    def CellsU(self, name: str):
        return self.cells.setdefault(name, _FormulaCell())


def test_decision_default_size_is_not_overwritten_by_process_defaults():
    nodes, _, _ = visio_server.normalize_spec({
        "nodes": [{"id": "d", "type": "decision", "text": "误差小于阈值？"}],
        "edges": [],
    })
    assert nodes[0]["width"] >= 1.75
    assert nodes[0]["height"] >= 0.92


def test_auto_layout_never_shrinks_nodes_below_text_minimum():
    nodes = [
        {"id": f"n{i}", "text": "很长的论文流程节点文字内容", "width": 2.1}
        for i in range(4)
    ]
    spec = {
        "page_width_in": 6.1,
        "nodes": nodes + [{"id": "end", "text": "结束"}],
        "edges": [{"from": f"n{i}", "to": "end"} for i in range(4)],
    }
    resolved, _, meta = visio_server.normalize_spec(spec)
    first_layer = [n for n in resolved if n["id"].startswith("n")]
    assert min(n["width"] for n in first_layer) >= 1.75
    assert meta["page_width_in"] >= 6.1
    for a in first_layer:
        for b in first_layer:
            if a is b:
                continue
            assert abs(a["x"] - b["x"]) >= (a["width"] + b["width"]) / 2


def test_feedback_route_is_orthogonal_and_inside_safe_margin():
    nodes, edges, meta = visio_server.normalize_spec({
        "page_width_in": 6.1,
        "nodes": [
            {"id": "a", "text": "搜索"},
            {"id": "b", "text": "判断", "type": "decision"},
            {"id": "u", "text": "更新"},
        ],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "u", "label": "否", "branch": "left"},
            {"from": "u", "to": "a", "feedback": True, "dashed": True},
        ],
    })
    feedback = edges[-1]
    assert all(visio_server.STYLE["safe_margin_in"] <= p[0] <= meta["page_width_in"] - visio_server.STYLE["safe_margin_in"] for p in feedback["waypoints"])
    by_id = {n["id"]: _Shape(n["x"], n["y"], n["width"], n["height"]) for n in nodes}
    pts = visio_server.edge_points(by_id["u"], by_id["a"], feedback)
    assert all(math.isclose(a[0], b[0], abs_tol=1e-9) or math.isclose(a[1], b[1], abs_tol=1e-9) for a, b in zip(pts, pts[1:]))


def test_decision_branch_uses_declared_source_port():
    source = _Shape(3.0, 3.0, 2.0, 1.0)
    target = _Shape(1.0, 3.0, 1.5, 0.7)
    pts = visio_server.edge_points(source, target, {"branch": "left", "route": "orthogonal"})
    assert pts[0] == pytest.approx((2.0, 3.0))
    target2 = _Shape(3.0, 1.0, 1.5, 0.7)
    pts2 = visio_server.edge_points(source, target2, {"branch": "bottom", "route": "orthogonal"})
    assert pts2[0] == pytest.approx((3.0, 2.5))


def test_layout_audit_detects_connector_crossing_and_node_overlap():
    shapes = {
        "a": _Shape(1, 3, 1, 0.5, "a"),
        "b": _Shape(5, 3, 1, 0.5, "b"),
        "c": _Shape(3, 5, 1, 0.5, "c"),
        "d": _Shape(3, 1, 1, 0.5, "d"),
        "middle": _Shape(3, 3, 0.8, 0.8, "middle"),
    }
    edges = [{"id": "h", "from": "a", "to": "b", "meaning": "h"}, {"id": "v", "from": "c", "to": "d", "meaning": "v"}]
    paths = [(edges[0], [(1.5, 3), (4.5, 3)]), (edges[1], [(3, 4.75), (3, 1.25)])]
    report = visio_server.build_layout_report({"strict_audit": True}, shapes, edges, paths, 6.1, 6.0)
    assert not report["pass"]
    assert report["checks"]["non_target_crossings_zero"] is False
    assert report["checks"]["connector_crossings_zero"] is False
    assert all(item["connector_crossings"] == 1 for item in report["connection_audit"]["items"])
    assert report["connection_audit"]["failed"] >= 2


def test_valid_mechanical_layout_can_be_publication_ready_before_optional_visual_review():
    shapes = {"a": _Shape(2, 3, 1, 0.5, "a"), "b": _Shape(2, 1, 1, 0.5, "b")}
    edge = {"id": "e", "from": "a", "to": "b", "meaning": "flow"}
    report = visio_server.build_layout_report(
        {"strict_audit": True}, shapes, [edge], [(edge, [(2, 2.75), (2, 1.25)])], 4, 4
    )
    assert report["pass"] is True
    assert report["requires_visual_review"] is True
    assert report["connection_audit"]["failed"] == 0


def test_visio_branch_labels_are_transparent_native_text():
    class _Page:
        def __init__(self):
            self.tag = None
        def DrawRectangle(self, *_args):
            self.tag = _TextShape()
            return self.tag
    page = _Page()
    edge = {}
    visio_server.add_label(page, [(0, 0), (2, 0)], "否", edge)
    assert page.tag is not None
    assert page.tag.cells["FillPattern"].FormulaU == "0"
    assert page.tag.cells["LinePattern"].FormulaU == "0"
    assert edge["_label_path_overlap"] is False


def test_visio_long_vertical_label_is_offset_beyond_its_width():
    class _Page:
        def __init__(self):
            self.tag = None
        def DrawRectangle(self, *_args):
            self.tag = _TextShape()
            return self.tag
    page = _Page()
    edge = {}
    visio_server.add_label(page, [(0, 0), (0, 2)], "达到停止精度要求", edge)
    left, _, _, _ = edge["_label_box"]
    assert left > 0
    assert edge["_label_path_overlap"] is False


def test_python_figure_saves_exact_physical_output_size(tmp_path: Path):
    result = python_figure.render_line2d(
        {"kind": "line2d", "width_cm": 15.5, "height_cm": 8.8, "series": [{"x": [0, 1], "y": [0, 1]}]},
        tmp_path,
        "probe_size",
    )
    assert result["ok"] is True
    doc = fitz.open(tmp_path / "probe_size.pdf")
    page = doc[0]
    expected_w, expected_h = 15.5 / 2.54 * 72, 8.8 / 2.54 * 72
    assert abs(page.rect.width / expected_w - 1.0) <= 0.002
    assert abs(page.rect.height / expected_h - 1.0) <= 0.002
    assert len(doc.get_page_images(0, full=True)) == 0
    doc.close()


def test_tikz_document_honors_requested_width_without_scaling_fonts():
    tex = tikz_server.document(r"\draw (0,0)--(2,0);", width_cm=15.5, border_pt=0)
    assert r"rectangle (15.5cm,0 |- paper-bbox-north)" in tex
    assert r"\pgfresetboundingbox" in tex
    assert tex.index(r"\draw (0,0)--(2,0);") < tex.index(r"use as bounding box")
    assert r"\resizebox" not in tex


def test_compile_tikz_preserves_complete_picture_options_and_injects_fixed_width_box():
    picture = r"""\begin{tikzpicture}[x=2cm,y=3cm,scale=.75]
\draw (0,0)--(2,1);
\end{tikzpicture}"""
    tex = tikz_server.document(picture, width_cm=12.3, border_pt=0)
    assert r"\begin{tikzpicture}[x=2cm,y=3cm,scale=.75]" in tex
    assert tex.count(r"\begin{tikzpicture}") == 1
    assert r"rectangle (12.3cm,0 |- paper-bbox-north)" in tex


def test_compile_tikz_trusts_explicit_canvas_without_second_bbox_reset():
    picture = r"""\begin{tikzpicture}
\path[use as bounding box] (0,0) rectangle (15.5,8.8);
\draw (0,0)--(2,1);
\end{tikzpicture}"""
    tex = tikz_server.document(picture, width_cm=15.5, border_pt=0)
    assert tex.count("use as bounding box") == 1
    assert r"\pgfresetboundingbox" not in tex


def test_tikz_formula_and_dimension_labels_are_transparent_by_default():
    body = tikz_server.build_from_spec({"elements": [
        {"type": "line", "from": [0, 0], "to": [2, 0], "label": "$g_{ij}>0$"},
        {"type": "dimension", "from": [0, -1], "to": [2, -1], "label": "$L$"},
    ]})
    assert "fill=white" not in body
    assert "$g_{ij}>0$" in body and "$L$" in body
    assert "-- node[" not in body
    assert body.count("fill=none") >= 2
    assert "anchor=south" in body


def test_tikz_vertical_formula_label_is_placed_beside_uninterrupted_line():
    body = tikz_server.build_from_spec({"elements": [
        {"type": "line", "from": [0, 0], "to": [0, 3], "label": "$v(t)$"},
    ]})
    assert r"\draw[paperline] (0,0) -- (0,3);" in body
    assert "anchor=west" in body
    assert "-- node[" not in body


def test_structured_tikz_canvas_is_not_collapsed_by_second_bbox_reset():
    body = tikz_server.build_from_spec({"canvas": {"width": 15.5, "height": 7.2}, "elements": [
        {"type": "line", "from": [0, 0], "to": [2, 1]},
    ]})
    tex = tikz_server.document(body, width_cm=15.5, border_pt=0)
    assert tex.count("use as bounding box") == 1
    assert r"\pgfresetboundingbox" not in tex


def test_tikz_detail_inset_is_native_geometry_not_raster():
    body = tikz_server.build_from_spec({"elements": [{
        "type": "detail_inset", "source_center": [1, 1], "inset_center": [6, 3],
        "elements": [{"type": "line", "from": [-1, 0], "to": [1, 0]}],
    }]})
    assert "includegraphics" not in body
    assert "fill=white" not in body
    assert "densely dashed" in body and "begin{scope}" in body


def test_classic_flow_preset_freezes_plain_academic_style_and_horizontal_axis():
    nodes, edges, meta = visio_server.normalize_spec({
        "visual_preset": "cumcm-classic-orthogonal",
        "layout_variant": "horizontal-feedback",
        "nodes": [
            {"id": "a", "type": "start", "text": "开始"},
            {"id": "b", "text": "更新状态"},
            {"id": "d", "type": "decision", "text": "满足精度？"},
            {"id": "z", "type": "end", "text": "结束"},
        ],
        "edges": [
            {"from": "a", "to": "b"},
            {"from": "b", "to": "d"},
            {"from": "d", "to": "z", "label": "是"},
            {"kind": "feedback_loop", "from": "d", "to": "b", "label": "否", "feedback": True},
        ],
    })
    by_id = {node["id"]: node for node in nodes}
    assert meta["visual_preset"] == "cumcm-classic-orthogonal"
    assert meta["layout_variant"] == "horizontal-feedback"
    assert meta["style_confirmation_required"] is False
    assert by_id["a"]["x"] < by_id["b"]["x"] < by_id["d"]["x"] < by_id["z"]["x"]
    assert {node["fill"] for node in nodes} == {"none"}
    assert {node["line"] for node in nodes} == {visio_server.STYLE["line_color"]}
    assert by_id["d"].get("bold", False) is False
    assert edges[-1]["dashed"] is False
    assert edges[-1]["waypoints"][0][1] == pytest.approx(meta["page_height_in"] - visio_server.STYLE["safe_margin_in"])


def test_legacy_editorial_preset_is_a_visual_compatibility_alias_without_focus_cards():
    nodes, _, meta = visio_server.normalize_spec({
        "visual_preset": "editorial-spine", "focus_node": "b",
        "nodes": [{"id": "a", "text": "输入"}, {"id": "b", "text": "核心"}],
        "edges": [{"from": "a", "to": "b"}],
    })
    by_id = {node["id"]: node for node in nodes}
    assert meta["visual_preset"] == "cumcm-classic-orthogonal"
    assert by_id["a"]["line_weight_pt"] == by_id["b"]["line_weight_pt"]
    assert by_id["b"].get("bold", False) is False


def test_classic_flow_auto_selects_objective_constraint_fusion_from_semantics():
    _, _, meta = visio_server.normalize_spec({
        "visual_preset": "cumcm-classic-orthogonal",
        "nodes": [
            {"id": "x", "text": "状态变量"},
            {"id": "obj", "role": "objective", "text": "目标函数"},
            {"id": "con", "role": "constraint", "text": "碰撞约束"},
            {"id": "solve", "text": "优化求解"},
        ],
        "edges": [
            {"from": "x", "to": "obj"},
            {"from": "x", "to": "con"},
            {"from": "obj", "to": "solve"},
            {"from": "con", "to": "solve"},
        ],
    })
    assert meta["layout_variant"] == "objective-constraint-fusion"


def test_visio_default_sets_latin_and_east_asian_fonts_to_microsoft_yahei():
    shape = _TextShape()
    visio_server.shape_text(shape, "中文 ABC")
    assert visio_server.STYLE["font"] == "Microsoft YaHei"
    assert shape.cells["Char.Font"].FormulaU == 'FONT("微软雅黑")'
    assert shape.cells["Char.AsianFont"].FormulaU == 'FONT("微软雅黑")'
    assert shape.cells["Char.ComplexScriptFont"].FormulaU == 'FONT("微软雅黑")'


def test_visio_explicit_simsun_override_remains_backward_compatible():
    shape = _TextShape()
    visio_server.shape_text(shape, "中文 ABC", font="SimSun")
    assert shape.cells["Char.Font"].FormulaU == 'FONT("宋体")'
    assert shape.cells["Char.AsianFont"].FormulaU == 'FONT("宋体")'


def test_python_figure_save_never_refits_canvas(tmp_path: Path):
    # The physical canvas is the contract: save_figure must not pass bbox_inches="tight",
    # otherwise long labels would silently change the page size.
    fig = python_figure.new_figure(12.0, 6.0)
    ax = fig.add_axes((0.1, 0.1, 0.85, 0.85))
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel("一个足够长的横轴标签用来诱发画布重排" * 2)
    python_figure.save_figure(fig, tmp_path, "probe_fixed")
    doc = fitz.open(tmp_path / "probe_fixed.pdf")
    page = doc[0]
    assert abs(page.rect.width / (12.0 / 2.54 * 72) - 1.0) <= 0.002
    assert abs(page.rect.height / (6.0 / 2.54 * 72) - 1.0) <= 0.002
    doc.close()


def test_quantitative_data_route_uses_python_as_primary_renderer():
    result = figure_router_server.decide({
        "section": "结果验证",
        "claim_id": "Q2-C4",
        "claim": "参数扫描显示临界区间内存在稳定策略切换边界",
        "data_shape": "parameter_scan_2d",
    })
    assert result["should_insert"] is True
    assert result["renderer"] == "python-matplotlib"
    assert result["style_family"] == "python"


def test_legacy_matlab_tools_are_not_selected_by_the_active_router():
    # The compatibility server may remain for old artifacts, but active CUMCM routing
    # must keep quantitative figures on the Python/matplotlib path.
    assert callable(matlab_server.health_check)
    assert callable(matlab_server.render_figure)
    assert callable(matlab_server.render_scene3d)
    assert "MATLAB" in matlab_server.mcp.name
    routed = figure_router_server.decide({
        "section": "结果",
        "claim_id": "QX-C1",
        "claim": "参数扫描给出稳定边界",
        "data_shape": "parameter_scan_2d",
    })
    assert routed["renderer"] == "python-matplotlib"


def test_process_runner_returns_structured_timeout_instead_of_raising(tmp_path: Path):
    """A stalled renderer must return before the MCP transport's 300 s deadline."""
    started = time.monotonic()
    result = common.run_process(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        tmp_path,
        timeout=0.15,
    )
    elapsed = time.monotonic() - started
    assert result["returncode"] == 124
    assert result["timed_out"] is True
    assert elapsed < 5.0


def test_process_runner_marks_normal_completion_as_not_timed_out(tmp_path: Path):
    result = common.run_process(
        [sys.executable, "-c", "print('renderer-ready')"],
        tmp_path,
        timeout=5,
    )
    assert result["returncode"] == 0
    assert result["timed_out"] is False
    assert "renderer-ready" in result["stdout"]


def test_matlab_deadlines_leave_transport_response_margin():
    assert matlab_server.MATLAB_HEALTH_TIMEOUT_SECONDS < 300
    assert matlab_server.MATLAB_RENDER_TIMEOUT_SECONDS < 300


def test_runtime_docs_do_not_call_python_a_fallback():
    """Nearby renderer docs must agree that Python is the production data backend."""
    texts = {
        "signature_benchmarks": Path(signature_benchmarks.__file__).read_text(encoding="utf-8"),
        "python_figure": Path(python_figure.__file__).read_text(encoding="utf-8"),
        "regression_suite": (
            Path(__file__).resolve().parents[1]
            / ".agents/skills/cumcm/references/regression-suite.md"
        ).read_text(encoding="utf-8"),
    }
    forbidden = ("matplotlib fallback", "Python fallback only", "Python 仅为明确登记的后备路线")
    for name, text in texts.items():
        assert not any(token.lower() in text.lower() for token in forbidden), name
    assert "PDF/SVG/PNG/M/JSON" not in texts["regression_suite"]


@pytest.mark.parametrize(
    ("case", "spec", "renderer", "figure_type"),
    [
        (
            "2024A时空轨迹结果",
            {
                "section": "结果",
                "claim_id": "2024A-Q4-C1",
                "claim": "调头前后各把手的时空轨迹连续且满足速度约束",
                "figure_role": "quantitative_evidence",
                "has_geometry": True,
                "has_spatial_coordinates": True,
                "data_shape": "spatial_path",
            },
            "python-matplotlib",
            "trajectory",
        ),
        (
            "2024A临界构型机理",
            {
                "section": "模型建立与求解",
                "claim_id": "2024A-Q2-C2",
                "claim": "板凳矩形边界首次相交定义盘入终止事件",
                "figure_role": "mechanism",
                "has_geometry": True,
                "data_shape": "spatial_state",
            },
            "paper-tikz",
            "geometry_mechanism",
        ),
        (
            "2024B策略景观结果",
            {
                "section": "结果验证",
                "claim_id": "2024B-Q4-C3",
                "claim": "次品率不确定性改变最优检测拆解策略的切换边界",
                "figure_role": "quantitative_evidence",
                "has_decision": True,
                "data_shape": "parameter_scan_2d",
            },
            "python-matplotlib",
            "contour",
        ),
        (
            "2024B递归决策流程",
            {
                "section": "模型建立与求解",
                "claim_id": "2024B-Q3-C1",
                "claim": "拆解回收后的零件返回检测装配状态形成再生决策",
                "figure_role": "algorithm",
                "has_decision": True,
                "has_loop": True,
                "step_count": 6,
                "prose_formula_table_insufficient": True,
                "information_gain_reason": "拆解回流形成跨周期状态更新与反馈，公式无法直接表达分支返回路径",
            },
            "paper-tikz",
            "decision_flow",
        ),
        (
            "2025B双角度光谱证据",
            {
                "section": "结果验证",
                "claim_id": "2025B-Q2-C2",
                "claim": "双入射角谱峰间距反演的外延层厚度在容差内一致",
                "figure_role": "quantitative_evidence",
                "has_geometry": True,
                "data_shape": "xy_relation",
            },
            "python-matplotlib",
            "scatter_fit",
        ),
        (
            "2025B多光束干涉机理",
            {
                "section": "模型建立与求解",
                "claim_id": "2025B-Q3-C1",
                "claim": "界面多次反射的光程差与反射率共同决定多光束干涉条件",
                "figure_role": "mechanism",
                "has_geometry": True,
                "object_count": 4,
            },
            "paper-tikz",
            "geometry_mechanism",
        ),
    ],
)
def test_2024a_2024b_2025b_cross_problem_role_aware_routing(case, spec, renderer, figure_type):
    result = figure_router_server.decide(spec)
    assert result["should_insert"] is True, case
    assert result["renderer"] == renderer, case
    assert result["figure_type"] == figure_type, case
    if renderer == "paper-visio":
        assert result["visual_preset"] == "cumcm-classic-orthogonal", case
        assert result["style_confirmation_required"] is False, case
        assert result["layout_variant"] in visio_server.CLASSIC_FLOW_VARIANTS, case


def test_quantitative_role_without_structured_data_is_fail_closed():
    result = figure_router_server.decide({
        "section": "结果",
        "claim_id": "NEG-NODATA",
        "claim": "仅用装饰性三维强调结论",
        "figure_role": "quantitative_evidence",
        "has_geometry": True,
    })
    assert result["should_insert"] is False
    assert "结构化数据" in result["reason"]
