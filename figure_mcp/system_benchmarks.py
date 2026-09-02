from __future__ import annotations

import json
from pathlib import Path

import tikz_server
import visio_server

OUT = Path(__file__).resolve().parent / "system_benchmark_outputs"
OUT.mkdir(parents=True, exist_ok=True)


def tikz_cases() -> dict[str, dict]:
    return {
        "a_geometry_inset": {
            "width_cm": 15.5,
            "canvas": {"width": 15.5, "height": 7.2},
            "elements": [
                {"type": "bezier", "from": [0.8, 1.5], "control1": [3.0, 5.7], "control2": [6.0, 0.8], "to": [8.6, 4.8], "style": "paperline"},
                {"type": "circle", "center": [4.5, 3.0], "radius": 0.07, "style": "paperline,fill=paperblue"},
                {"type": "arrow", "from": [4.5, 3.0], "to": [5.8, 3.65], "style": "accentline", "label": "$\\boldsymbol\\tau$", "label_options": "above,fill=none"},
                {"type": "detail_inset", "source_center": [4.5, 3.0], "source_width": 0.8, "source_height": 0.8,
                 "inset_center": [11.7, 3.4], "inset_width": 5.0, "inset_height": 4.2, "scale": 1.25,
                 "title": "切点解析放大",
                 "elements": [
                     {"type": "bezier", "from": [-1.6, -0.3], "control1": [-0.6, 0.4], "control2": [0.6, 0.4], "to": [1.6, 1.1], "style": "paperline"},
                     {"type": "circle", "center": [0, 0.35], "radius": 0.055, "style": "paperline,fill=paperblue"},
                     {"type": "arrow", "from": [0, 0.35], "to": [1.1, 0.8], "style": "accentline", "label": "$\\boldsymbol\\tau$", "label_options": "above,fill=none"},
                     {"type": "arrow", "from": [0, 0.35], "to": [-0.45, 1.45], "style": "draw=black!55,line width=.65pt", "label": "$\\boldsymbol n$", "label_options": "left,fill=none"},
                     {"type": "node", "at": [0.5, -0.65], "text": "$\\boldsymbol\\tau^{T}\\boldsymbol n=0$", "options": "mathlabel"},
                 ]},
            ],
        },
        "b_decision_boundary_inset": {
            "width_cm": 15.5,
            "canvas": {"width": 15.5, "height": 7.2},
            "elements": [
                {"type": "line", "from": [0.8, 1.0], "to": [8.0, 6.0], "style": "paperline"},
                {"type": "line", "from": [0.8, 5.8], "to": [8.0, 1.3], "style": "accentline,dashed"},
                {"type": "detail_inset", "source_center": [4.5, 3.55], "source_width": 0.85, "source_height": 0.85,
                 "inset_center": [11.8, 3.5], "inset_width": 5.2, "inset_height": 4.3, "scale": 1.2,
                 "title": "策略切换边界",
                 "elements": [
                     {"type": "line", "from": [-1.7, -1.0], "to": [1.7, 1.2], "style": "paperline"},
                     {"type": "line", "from": [-1.7, 1.0], "to": [1.7, -1.1], "style": "accentline,dashed"},
                     {"type": "circle", "center": [0, 0], "radius": 0.06, "style": "accentline,fill=paperorange"},
                     {"type": "node", "at": [0.5, 0.4], "text": "$\\Delta J=0$", "options": "mathlabel"},
                 ]},
            ],
        },
    }


def visio_cases() -> dict[str, dict]:
    return {
        "a_numeric_iteration": {
            "page_name": "数值迭代证据链", "page_width_in": 6.4,
            "visual_preset": "cumcm-classic-orthogonal", "layout_variant": "horizontal-feedback",
            "strict_audit": True, "nodes": [
                {"id": "input", "type": "start", "text": "物理参数与边界"},
                {"id": "solve", "text": "离散求解与校正"},
                {"id": "judge", "type": "decision", "text": "误差收敛？"},
                {"id": "refine", "text": "加密网格"},
                {"id": "verify", "text": "守恒与独立复算"},
                {"id": "out", "type": "end", "text": "冻结数值答案"},
            ], "edges": [
                {"id": "e1", "from": "input", "to": "solve", "meaning": "参数进入离散求解"},
                {"id": "e2", "from": "solve", "to": "judge", "meaning": "候选数值进入收敛判定"},
                {"id": "e3", "kind": "decision_branch", "from": "judge", "to": "verify", "label": "是", "meaning": "收敛后独立验证"},
                {"id": "e4", "kind": "decision_branch", "from": "judge", "to": "refine", "label": "否", "branch": "left", "meaning": "不收敛时加密网格"},
                {"id": "e5", "kind": "feedback_loop", "from": "refine", "to": "solve", "label": "更新", "feedback": True, "meaning": "加密后重新求解"},
                {"id": "e6", "from": "verify", "to": "out", "meaning": "验证通过后冻结答案"},
            ]},
        "b_strategy_optimization": {
            "page_name": "策略优化证据链", "page_width_in": 6.4,
            "visual_preset": "cumcm-classic-orthogonal", "layout_variant": "horizontal-feedback",
            "strict_audit": True, "nodes": [
                {"id": "input", "type": "start", "text": "场景与成本参数"},
                {"id": "search", "text": "枚举候选策略"},
                {"id": "judge", "type": "decision", "text": "约束满足？"},
                {"id": "repair", "text": "修复不可行策略"},
                {"id": "robust", "text": "稳健性与挑战路线"},
                {"id": "out", "type": "end", "text": "冻结近优方案"},
            ], "edges": [
                {"id": "e1", "from": "input", "to": "search", "meaning": "参数定义策略空间"},
                {"id": "e2", "from": "search", "to": "judge", "meaning": "候选策略进入约束判定"},
                {"id": "e3", "kind": "decision_branch", "from": "judge", "to": "robust", "label": "是", "meaning": "可行策略进入稳健验证"},
                {"id": "e4", "kind": "decision_branch", "from": "judge", "to": "repair", "label": "否", "branch": "left", "meaning": "不可行策略进入修复"},
                {"id": "e5", "kind": "feedback_loop", "from": "repair", "to": "search", "label": "回填", "feedback": True, "meaning": "修复后重新比较"},
                {"id": "e6", "from": "robust", "to": "out", "meaning": "验证后冻结近优方案"},
            ]},
    }


def main() -> int:
    results = {"tikz": {}, "visio": {}}
    for name, spec in tikz_cases().items():
        results["tikz"][name] = json.loads(tikz_server.render_geometry(spec, str(OUT), name))
    for name, spec in visio_cases().items():
        results["visio"][name] = json.loads(visio_server.render_diagram(spec, str(OUT), name))
    (OUT / "system_benchmark_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = all(v.get("ok") for group in results.values() for v in group.values())
    print(json.dumps({"ok": ok, "cases": {k: list(v) for k, v in results.items()}}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
