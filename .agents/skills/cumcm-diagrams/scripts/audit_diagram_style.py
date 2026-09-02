#!/usr/bin/env python3
"""Audit TikZ/Visio-style diagram sources, vectors and layout reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_ROLES = {"flowchart", "relationship", "mechanism", "geometry", "state_decision", "system_block"}
FIXED_FLOW_ROLES = {"flowchart", "relationship", "state_decision", "system_block"}
FIXED_FLOW_PRESET = "cumcm-classic-orthogonal"
ALLOWED_FLOW_VARIANTS = {
    "horizontal-mainline",
    "horizontal-feedback",
    "vertical-branching",
    "layered-dependency",
    "objective-constraint-fusion",
    "phased-groups",
    "hybrid-evolution",
    "mechanism-assisted",
}
REQUIRED_FIXED_STYLE_TRUE = {
    "white_background",
    "transparent_node_fill",
    "math_labels_transparent",
    "line_continuity_unmasked",
    "labels_outside_line_paths",
    "orthogonal_connectors",
    "classic_shape_semantics",
    "no_grid_background",
    "group_frames_dashed_only",
    "feedback_lines_solid",
}
REQUIRED_FIXED_STYLE_FALSE = {
    "style_confirmation_required",
    "white_node_fill",
    "stage_badges",
    "focus_cards",
    "colored_decision_nodes",
    "title_inside",
}
REQUIRED_LAYOUT_CHECKS = {
    "objects_inside_canvas",
    "node_text_embedded",
    "text_inside_parent",
    "node_lines_max_2",
    "uniform_node_text_style",
    "uniform_arrow_style",
    "annotation_anchors",
    "arrow_endpoints_on_node_boundary",
    "arrowheads_outside_node_interior",
    "connection_inventory_complete",
    "non_target_crossings_zero",
    "final_render_connections_checked",
    "line_direction_semantics_complete",
    "arrow_direction_matches_meaning",
    "line_style_matches_meaning",
    "line_continuity_unmasked",
    "labels_outside_line_paths",
    "final_font_size_readable",
    "composition_balance",
    "branch_labels_near_first_segment",
}


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def require_file(root: Path, value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value or not (root / value).exists():
        errors.append(f"missing {label}: {value}")


def audit_items(container: dict, name: str, errors: list[str]) -> None:
    audit = container.get(name)
    if not isinstance(audit, dict):
        errors.append(f"missing {name}")
        return
    items = audit.get("items")
    total = audit.get("total")
    checked = audit.get("checked")
    failed = audit.get("failed")
    if not isinstance(items, list) or not items or total != len(items) or checked != len(items) or failed != 0:
        errors.append(f"{name} counts incomplete or failed")
        return
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{name} contains invalid item: {item}")
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id or item_id in seen:
            errors.append(f"{name} contains missing or duplicate id: {item_id}")
        seen.add(item_id)
        if item.get("semantics_match") is not True or item.get("final_render_pass") is not True:
            errors.append(f"{name} contains failed item: {item.get('id') if isinstance(item, dict) else item}")
        if item.get("line_continuity_pass") is not True:
            errors.append(f"{name} contains an interrupted or masked line: {item_id}")
        if not item.get("kind") or not item.get("meaning"):
            errors.append(f"{name} item lacks kind or meaning: {item_id}")
        if item.get("directionality") not in {"directed", "undirected", "bidirectional"}:
            errors.append(f"{name} item has invalid directionality: {item_id}")
        required = item.get("arrowhead_required")
        present = item.get("arrowhead_present")
        if not isinstance(required, bool) or not isinstance(present, bool):
            errors.append(f"{name} item lacks arrowhead audit: {item_id}")
        elif required and not present:
            errors.append(f"{name} item misses required arrowhead: {item_id}")

        if name == "connection_audit":
            for field in ("source", "target", "source_anchor", "target_anchor"):
                if not item.get(field):
                    errors.append(f"{name} item lacks {field}: {item_id}")
            for field in ("source_endpoint_error_pt", "target_endpoint_error_pt"):
                value = item.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value > 0.5:
                    errors.append(f"{name} item {field} exceeds 0.5 pt: {item_id}")
            if item.get("non_target_crossings") != 0:
                errors.append(f"{name} item has non-target crossings: {item_id}")
            clearance = item.get("min_clearance_pt")
            if not isinstance(clearance, (int, float)) or isinstance(clearance, bool) or clearance < 2.5:
                errors.append(f"{name} item clearance below 2.5 pt: {item_id}")
            if (
                item.get("label_overlap") is not False
                or item.get("label_path_overlap") is not False
                or item.get("node_interior_overlap") is not False
            ):
                errors.append(f"{name} item has overlap: {item_id}")
        else:
            if not item.get("expected_direction"):
                errors.append(f"{name} item lacks expected_direction: {item_id}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--registry", default="审查/diagram-registry.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    registry_path = root / args.registry
    errors: list[str] = []
    if not registry_path.exists():
        registry = {}
        errors.append(f"diagram registry not found: {args.registry}")
    else:
        try:
            registry = read_json(registry_path)
        except Exception as exc:  # noqa: BLE001
            registry = {}
            errors.append(f"invalid diagram registry: {exc}")
    if registry.get("schema_version") not in {1, 2, 3}:
        errors.append("registry schema_version must be 1, 2 or 3")
    if registry.get("schema_version") in {2, 3} and registry.get("edge_schema_version") != 1:
        errors.append("registry edge_schema_version must be 1")
    diagrams = registry.get("diagrams")
    if not isinstance(diagrams, list) or not diagrams:
        errors.append("registry diagrams must be a non-empty list")
        diagrams = []

    seen: set[str] = set()
    checked = []
    for index, item in enumerate(diagrams):
        item_errors: list[str] = []
        if not isinstance(item, dict):
            errors.append(f"diagram[{index}] must be an object")
            continue
        diagram_id = item.get("id") or f"diagram[{index}]"
        if diagram_id in seen:
            item_errors.append("duplicate id")
        seen.add(diagram_id)
        if item.get("role") not in ALLOWED_ROLES:
            item_errors.append(f"invalid role: {item.get('role')}")
        if not item.get("purpose"):
            item_errors.append("missing single diagram purpose")
        if not isinstance(item.get("claim_ids"), list) or not item.get("claim_ids"):
            item_errors.append("claim_ids must be non-empty")

        draft = item.get("draft_dependency")
        if not isinstance(draft, dict):
            item_errors.append("draft_dependency must record post-draft drawing checks")
        else:
            if not str(draft.get("source_section_anchor", "")).strip():
                item_errors.append("draft_dependency.source_section_anchor is empty")
            for field in ("section_draft_stable", "symbols_formulas_checked", "rendered_after_draft"):
                if draft.get(field) is not True:
                    item_errors.append(f"draft_dependency.{field} must be true")

        renderer_choice = item.get("renderer_choice")
        if not isinstance(renderer_choice, dict):
            item_errors.append("renderer_choice must document TikZ-first routing")
        elif renderer_choice.get("tikz_considered") is not True:
            item_errors.append("renderer_choice.tikz_considered must be true")

        flow_profile = item.get("flowchart_profile")
        if item.get("role") in FIXED_FLOW_ROLES:
            if not isinstance(flow_profile, dict):
                item_errors.append("fixed flowchart role requires flowchart_profile")
            else:
                if flow_profile.get("visual_preset") != FIXED_FLOW_PRESET:
                    item_errors.append(f"flowchart visual_preset must be {FIXED_FLOW_PRESET}")
                if flow_profile.get("layout_variant") not in ALLOWED_FLOW_VARIANTS:
                    item_errors.append(f"invalid flowchart layout_variant: {flow_profile.get('layout_variant')}")
                if flow_profile.get("style_confirmation_required") is not False:
                    item_errors.append("style_confirmation_required must be false")
                if not str(flow_profile.get("semantic_innovation", "")).strip():
                    item_errors.append("flowchart_profile must explain semantic_innovation")

        family = item.get("style_family")
        if family not in {"tikz", "visio"}:
            item_errors.append(f"style_family must be tikz or visio: {family}")
        if isinstance(renderer_choice, dict):
            if renderer_choice.get("selected") != family:
                item_errors.append("renderer_choice.selected must match style_family")
            if family == "visio" and len(str(renderer_choice.get("fallback_reason", "")).strip()) < 12:
                item_errors.append("Visio requires a substantive reason why TikZ is unsuitable")
        source = item.get("source")
        source_path = root / source if isinstance(source, str) else None
        if not source_path or not source_path.exists():
            item_errors.append(f"missing source: {source}")
        else:
            suffix = source_path.suffix.lower()
            if family == "tikz" and suffix not in {".tex", ".tikz"}:
                item_errors.append(f"TikZ source must be .tex/.tikz: {source}")
            if family == "visio" and suffix not in {".vsdx", ".drawio"}:
                item_errors.append(f"Visio-style source must be .vsdx/.drawio: {source}")
        vector = item.get("vector_output")
        if not isinstance(vector, str) or Path(vector).suffix.lower() not in {".pdf", ".svg"} or not (root / vector).exists():
            item_errors.append(f"invalid or missing vector_output: {vector}")
        layout_rel = item.get("layout")
        layout_path = root / layout_rel if isinstance(layout_rel, str) else None
        if not layout_path or not layout_path.exists():
            item_errors.append(f"missing layout report: {layout_rel}")
            layout = {}
        else:
            try:
                layout = read_json(layout_path)
            except Exception as exc:  # noqa: BLE001
                layout = {}
                item_errors.append(f"invalid layout report: {exc}")

        width = item.get("insert_width_mm")
        if not isinstance(width, (int, float)) or not 55 <= width <= 166:
            item_errors.append(f"invalid insert_width_mm: {width}")
        font = item.get("final_min_font_pt")
        if not isinstance(font, (int, float)) or font < 8.5:
            item_errors.append(f"final_min_font_pt below 8.5: {font}")

        generation = item.get("generation")
        if not isinstance(generation, dict):
            item_errors.append("missing renderer provenance generation")
        else:
            if generation.get("mode") not in {"mcp", "script"}:
                item_errors.append("generation.mode must be mcp or script")
            if not generation.get("renderer") or not generation.get("tool"):
                item_errors.append("generation lacks renderer/tool")
            if generation.get("mode") == "mcp" and generation.get("health_pass") is not True:
                item_errors.append("MCP generation health_pass must be true")
            require_file(root, generation.get("spec_path"), "generation spec", item_errors)
            require_file(root, generation.get("provenance_manifest"), "provenance manifest", item_errors)

        visual = item.get("visual_review")
        if not isinstance(visual, dict):
            item_errors.append("missing visual_review")
        else:
            for field in (
                "actual_size_render", "full_page_render", "thumbnail_render", "grayscale_render"
            ):
                require_file(root, visual.get(field), f"visual_review.{field}", item_errors)
            if visual.get("publication_ready") is not True:
                item_errors.append("visual_review.publication_ready must be true")
            if visual.get("ocr_only_review") is not False:
                item_errors.append("visual_review.ocr_only_review must be false")

        vector_audit = item.get("vector_audit")
        if not isinstance(vector_audit, dict) or vector_audit.get("true_vector") is not True:
            item_errors.append("vector_audit.true_vector must be true")
        if isinstance(vector_audit, dict):
            distortion = vector_audit.get("aspect_ratio_distortion")
            if not isinstance(distortion, (int, float)) or isinstance(distortion, bool) or abs(distortion) > 0.002:
                item_errors.append("vector aspect-ratio distortion exceeds 0.002")

        if layout:
            if layout.get("pass") is not True:
                item_errors.append("layout pass is not true")
            checks = layout.get("checks")
            if not isinstance(checks, dict):
                item_errors.append("layout checks missing")
            else:
                for name in REQUIRED_LAYOUT_CHECKS:
                    if checks.get(name) is not True:
                        item_errors.append(f"layout check failed: {name}")
                if checks.get("latex_trim_required") is not False:
                    item_errors.append("latex_trim_required must be false")

            style = layout.get("style_audit")
            if not isinstance(style, dict):
                item_errors.append("style_audit missing")
            else:
                if style.get("family") != family:
                    item_errors.append("style_audit family mismatch")
                if not isinstance(style.get("final_min_font_pt"), (int, float)) or style.get("final_min_font_pt") < 8.5:
                    item_errors.append("style final_min_font_pt below 8.5")
                if not isinstance(style.get("line_width_levels"), int) or style.get("line_width_levels") > 2:
                    item_errors.append("line_width_levels must be at most 2")
                if not isinstance(style.get("color_count"), int) or not 1 <= style.get("color_count") <= 4:
                    item_errors.append("color_count must be 1..4")
                for field in ("gradients", "shadows", "decorative_icons", "rounded_card_system", "title_inside"):
                    if style.get(field) is not False:
                        item_errors.append(f"style.{field} must be false")
                for field in ("math_font_consistent", "final_vector", "final_page_checked"):
                    if style.get(field) is not True:
                        item_errors.append(f"style.{field} must be true")
                if family == "tikz" and style.get("tikz_stylesheet_used") is not True:
                    item_errors.append("TikZ diagram must use an explicit stylesheet")
                if family == "visio" and style.get("dynamic_connectors_and_snap") is not True:
                    item_errors.append("Visio diagram must use snap and dynamic connectors")
                if item.get("role") in FIXED_FLOW_ROLES and isinstance(flow_profile, dict):
                    layout_profile = layout.get("flowchart_profile")
                    if not isinstance(layout_profile, dict):
                        item_errors.append("layout flowchart_profile missing")
                    else:
                        for field in ("visual_preset", "layout_variant", "style_confirmation_required"):
                            if layout_profile.get(field) != flow_profile.get(field):
                                item_errors.append(f"layout flowchart_profile mismatch: {field}")
                    if style.get("visual_preset") != FIXED_FLOW_PRESET:
                        item_errors.append("style_audit fixed visual_preset mismatch")
                    if style.get("layout_variant") != flow_profile.get("layout_variant"):
                        item_errors.append("style_audit layout_variant mismatch")
                    for field in REQUIRED_FIXED_STYLE_TRUE:
                        if style.get(field) is not True:
                            item_errors.append(f"fixed flowchart style.{field} must be true")
                    for field in REQUIRED_FIXED_STYLE_FALSE:
                        if style.get(field) is not False:
                            item_errors.append(f"fixed flowchart style.{field} must be false")

            audit_items(layout, "connection_audit", item_errors)
            audit_items(layout, "line_semantics_audit", item_errors)
            overall = layout.get("overall_audit")
            required_overall = {
                "pass",
                "main_axis_clear",
                "visual_hierarchy_clear",
                "spacing_consistent",
                "whitespace_balanced",
                "thumbnail_readable",
                "full_page_render_checked",
            }
            if not isinstance(overall, dict) or any(overall.get(field) is not True for field in required_overall):
                item_errors.append("overall_audit incomplete or failed")

        checked.append({"id": diagram_id, "pass": not item_errors, "errors": item_errors})
        errors.extend(f"{diagram_id}: {message}" for message in item_errors)

    result = {
        "schema_version": 1,
        "pass": not errors,
        "registry": args.registry,
        "diagram_count": len(diagrams),
        "checked": checked,
        "errors": errors,
    }
    out_dir = root / "审查"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diagram-style-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# TikZ / Visio 图形风格审计", "", f"- 结果：{'PASS' if result['pass'] else 'FAIL'}", f"- 图数：{len(diagrams)}", ""]
    if errors:
        lines.extend(["## 阻断项", "", *[f"- {item}" for item in errors], ""])
    (out_dir / "diagram-style-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "diagram_count": len(diagrams), "error_count": len(errors)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
