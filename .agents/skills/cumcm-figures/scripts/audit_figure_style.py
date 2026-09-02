#!/usr/bin/env python3
"""Audit the evidence, style and final-size registry for CUMCM data figures."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


CATEGORIES = {
    "time_series",
    "parameter_curve",
    "optimization_sensitivity",
    "statistical_diagnostic",
    "bar_comparison",
    "heatmap_field",
    "surface_3d",
    "route_spatial",
    "network_state",
    "image_recognition",
    "distribution",
    "uncertainty_interval",
    "other_evidence",
}

STYLE_TRUE = {
    "colorblind_safe",
    "data_geometry_untouched",
    "units_complete",
    "final_page_checked",
    "grayscale_pass",
}

STYLE_FALSE = {
    "title_inside",
    "decorative_effects",
    "legend_occludes_data",
    "default_software_theme",
    "manual_data_point_editing",
}

SIGNATURE_ARCHETYPES = {
    "a_mechanism_result", "a_critical_configuration", "a_spatiotemporal_evolution",
    "a_phase_map", "a_convergence_closure", "b_strategy_landscape",
    "b_strategy_fingerprint", "b_uncertainty_decision", "b_probability_flow",
    "b_pareto_strategy_map", "cross_type_uncertainty_decision",
}

SIGNATURE_CHECKS_TRUE = {
    "integrated_narrative", "adds_explanatory_responsibility", "not_palette_only",
    "not_decorative_collage", "thumbnail_silhouette_pass", "ten_second_read_pass",
    "final_page_visual_pass",
}

PANEL_MODES = {"single", "shared_caption_left_right", "subcaptions_below"}
BASIC_PLOT_CATEGORIES = {"time_series", "parameter_curve", "bar_comparison"}
CURVE_EVIDENCE_LAYERS = {
    "event_marker", "threshold", "feasible_boundary", "uncertainty_band",
    "baseline", "phase_interval", "inset", "secondary_state", "sample_points",
}
COMPARISON_EVIDENCE_LAYERS = {
    "uncertainty_interval", "raw_observations", "baseline", "effect_size", "threshold",
}


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def require_file(root: Path, value: object, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value or not (root / value).exists():
        errors.append(f"missing {label}: {value}")


def nonempty_text(value: object, minimum: int = 4) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def valid_iso_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def audit_panel_layout(item: dict, errors: list[str]) -> None:
    panel = item.get("panel_layout")
    if not isinstance(panel, dict):
        errors.append("panel_layout must be an object")
        return
    count = panel.get("panel_count")
    mode = panel.get("mode")
    roles = panel.get("panel_roles")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        errors.append("panel_layout.panel_count must be a positive integer")
        return
    if mode not in PANEL_MODES:
        errors.append(f"invalid panel_layout.mode: {mode}")
    if not isinstance(roles, list) or len(roles) != count or any(not nonempty_text(value, 2) for value in roles):
        errors.append("panel_layout.panel_roles must name every panel")
    if panel.get("panel_titles_inside") is not False:
        errors.append("panel_layout.panel_titles_inside must be false")
    if panel.get("gutter_consistent") is not True:
        errors.append("panel_layout.gutter_consistent must be true")
    if panel.get("shared_claim") is not True:
        errors.append("panel_layout.shared_claim must be true")
    alignment = panel.get("subcaption_alignment")
    if count == 1:
        if mode != "single" or alignment != "not-applicable":
            errors.append("single panel requires mode=single and no subcaption")
    elif count == 2:
        if mode not in {"shared_caption_left_right", "subcaptions_below"}:
            errors.append("two panels require a left/right shared caption or subcaptions below")
        expected = "centered-below" if mode == "subcaptions_below" else "not-applicable"
        if alignment != expected:
            errors.append(f"two-panel subcaption_alignment must be {expected}")
    elif mode != "subcaptions_below" or alignment != "centered-below":
        errors.append("three or more panels require centered subcaptions below each panel")


def audit_basic_plot_enrichment(item: dict, errors: list[str]) -> None:
    category = item.get("category")
    if category not in BASIC_PLOT_CATEGORIES:
        return
    evidence = item.get("evidence_enrichment")
    if not isinstance(evidence, dict):
        errors.append(f"{category} requires evidence_enrichment")
        return
    layers = evidence.get("layers")
    if evidence.get("bare_basic_plot") is not False:
        errors.append("bare standalone line/bar plots are not publication-ready")
    if (
        not isinstance(layers, list)
        or any(not isinstance(value, str) or not value for value in layers)
        or len(set(layers)) < 2
    ):
        errors.append("evidence_enrichment.layers must contain at least two distinct layers")
        layer_set: set[str] = set()
    else:
        layer_set = set(layers)
    if not nonempty_text(evidence.get("key_readout"), 4):
        errors.append("evidence_enrichment.key_readout must be substantive")
    if not nonempty_text(evidence.get("why_not_table_or_text"), 8):
        errors.append("evidence_enrichment.why_not_table_or_text must justify the plot")
    required = COMPARISON_EVIDENCE_LAYERS if category == "bar_comparison" else CURVE_EVIDENCE_LAYERS
    if not layer_set.intersection(required):
        errors.append(f"{category} lacks a threshold, boundary, uncertainty, baseline or equivalent evidence layer")


def audit_signature_policy(registry: dict, track: str, figures: list[dict], errors: list[str]) -> dict:
    """Fail closed for national-first identity while allowing accountable no-collage exemption."""
    signature_items = [item for item in figures if item.get("signature_figure") is True]
    summary = {"track": track, "signature_count": len(signature_items), "exempted": False, "status": "NOT_REQUIRED"}
    if track != "national-first":
        return summary
    identity = registry.get("visual_identity")
    if not isinstance(identity, dict):
        errors.append("national-first registry lacks visual_identity")
    else:
        for field in ("identity_id", "primary_color", "support_color", "conclusion_color"):
            if not nonempty_text(identity.get(field), 3):
                errors.append(f"visual_identity.{field} must be non-empty")
        if identity.get("semantic_consistency_pass") is not True:
            errors.append("visual_identity.semantic_consistency_pass must be true")
    policy = registry.get("signature_policy")
    if not isinstance(policy, dict):
        errors.append("national-first registry lacks signature_policy")
        return {**summary, "status": "FAIL"}
    minimum = policy.get("minimum_count", 1)
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 0:
        errors.append("signature_policy.minimum_count must be a non-negative integer")
        minimum = 1
    exemption = policy.get("exemption")
    if not signature_items:
        evidence = exemption.get("evidence") if isinstance(exemption, dict) else None
        valid = isinstance(exemption, dict) and (
            nonempty_text(exemption.get("reason"), 12)
            and isinstance(evidence, list) and bool(evidence)
            and all(nonempty_text(value, 2) for value in evidence)
            and nonempty_text(exemption.get("approved_by"), 3)
            and exemption.get("review_status") == "APPROVED"
        )
        if not valid:
            errors.append("national-first requires a signature figure or substantive reason/evidence/independent approval")
        else:
            summary.update({"exempted": True, "status": "EXEMPTED_NO_FORCED_COLLAGE"})
        return summary
    if len(signature_items) < minimum:
        errors.append(f"signature figure count below declared minimum: {len(signature_items)} < {minimum}")
    summary["status"] = "PASS" if len(signature_items) >= minimum else "FAIL"
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--registry", default="审查/figure-registry.json")
    parser.add_argument("--track", choices=("standard", "national-first"), default="standard")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    registry_path = root / args.registry
    errors: list[str] = []
    if not registry_path.exists():
        registry = {}
        errors.append(f"figure registry not found: {args.registry}")
    else:
        try:
            registry = read_json(registry_path)
        except Exception as exc:  # noqa: BLE001
            registry = {}
            errors.append(f"invalid figure registry: {exc}")

    if registry.get("schema_version") not in {1, 2, 3, 4}:
        errors.append("registry schema_version must be 1, 2, 3 or 4")
    figures = registry.get("figures")
    if not isinstance(figures, list) or not figures:
        errors.append("registry figures must be a non-empty list")
        figures = []

    signature_summary = audit_signature_policy(
        registry, args.track, [item for item in figures if isinstance(item, dict)], errors
    )
    seen: set[str] = set()
    checked = []
    for index, item in enumerate(figures):
        prefix = f"figure[{index}]"
        item_errors: list[str] = []
        if not isinstance(item, dict):
            errors.append(f"{prefix}: item must be an object")
            continue
        figure_id = item.get("id")
        if not isinstance(figure_id, str) or not figure_id:
            item_errors.append("missing id")
            figure_id = prefix
        elif figure_id in seen:
            item_errors.append("duplicate id")
        seen.add(figure_id)
        if item.get("category") not in CATEGORIES:
            item_errors.append(f"invalid category: {item.get('category')}")
        if not item.get("purpose"):
            item_errors.append("missing single evidence purpose")
        claim_ids = item.get("claim_ids")
        if not isinstance(claim_ids, list) or not claim_ids:
            item_errors.append("claim_ids must be non-empty")
        elif any(not isinstance(value, str) or not value for value in claim_ids):
            item_errors.append("claim_ids must contain non-empty strings")

        audit_panel_layout(item, item_errors)
        audit_basic_plot_enrichment(item, item_errors)

        for field in ("source_data",):
            values = item.get(field)
            if not isinstance(values, list) or not values:
                item_errors.append(f"{field} must be non-empty")
                continue
            for relative in values:
                if not isinstance(relative, str) or not (root / relative).exists():
                    item_errors.append(f"missing {field}: {relative}")
        generator = item.get("generator")
        if not isinstance(generator, str) or not (root / generator).exists():
            item_errors.append(f"missing generator: {generator}")
        elif Path(generator).suffix.lower() not in {".py", ".m", ".r", ".jl", ".tex"}:
            item_errors.append(f"unsupported generator source: {generator}")
        vector = item.get("vector_output")
        if not isinstance(vector, str) or Path(vector).suffix.lower() not in {".pdf", ".svg"} or not (root / vector).exists():
            item_errors.append(f"invalid or missing vector_output: {vector}")
        raster = item.get("raster_output")
        if raster:
            if Path(raster).suffix.lower() != ".png" or not (root / raster).exists():
                item_errors.append(f"invalid or missing raster_output: {raster}")
            dpi = item.get("raster_dpi")
            if not isinstance(dpi, (int, float)) or dpi < 300:
                item_errors.append(f"raster_dpi below 300: {dpi}")

        width = item.get("insert_width_mm")
        if not isinstance(width, (int, float)) or not 55 <= width <= 160:
            item_errors.append(f"invalid insert_width_mm: {width}")
        font = item.get("final_min_font_pt")
        if not isinstance(font, (int, float)) or font < 8:
            item_errors.append(f"final_min_font_pt below 8: {font}")

        style = item.get("style")
        if not isinstance(style, dict):
            item_errors.append("missing style audit")
            style = {}
        if style.get("background") != "white":
            item_errors.append("background must be white")
        colors = style.get("color_count")
        if not isinstance(colors, int) or colors < 1 or colors > 6:
            item_errors.append(f"color_count must be 1..6: {colors}")
        for field in STYLE_TRUE:
            if style.get(field) is not True:
                item_errors.append(f"style.{field} must be true")
        for field in STYLE_FALSE:
            if style.get(field) is not False:
                item_errors.append(f"style.{field} must be false")

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
            if args.track == "national-first" and item.get("signature_figure") is True:
                if visual.get("review_mode") != "manual":
                    item_errors.append("national-first signature subjective review must be manual, not automated")
                if not nonempty_text(visual.get("reviewed_by"), 3):
                    item_errors.append("national-first signature visual_review.reviewed_by must identify a reviewer")
                if not valid_iso_datetime(visual.get("reviewed_at")):
                    item_errors.append("national-first signature visual_review.reviewed_at must be ISO-8601")
                require_file(root, visual.get("manual_review_record"), "visual_review.manual_review_record", item_errors)

        vector_audit = item.get("vector_audit")
        if not isinstance(vector_audit, dict) or vector_audit.get("true_vector") is not True:
            item_errors.append("vector_audit.true_vector must be true")
        if isinstance(vector_audit, dict):
            distortion = vector_audit.get("aspect_ratio_distortion")
            if not isinstance(distortion, (int, float)) or isinstance(distortion, bool) or abs(distortion) > 0.002:
                item_errors.append("vector aspect-ratio distortion exceeds 0.002")

        checks = item.get("role_specific_checks")
        if not isinstance(checks, list) or not checks:
            item_errors.append("role_specific_checks must be non-empty")
        else:
            for check in checks:
                if not isinstance(check, dict) or check.get("pass") is not True or not check.get("id") or not check.get("evidence"):
                    item_errors.append(f"failed or incomplete role check: {check}")

        if item.get("signature_figure") is True:
            if item.get("signature_archetype") not in SIGNATURE_ARCHETYPES:
                item_errors.append(f"invalid signature_archetype: {item.get('signature_archetype')}")
            for field in ("core_claim", "ten_second_takeaway"):
                if not nonempty_text(item.get(field), 8):
                    item_errors.append(f"signature {field} must be substantive")
            read_order = item.get("read_order")
            if not isinstance(read_order, list) or not 2 <= len(read_order) <= 6 or any(not nonempty_text(value, 2) for value in read_order):
                item_errors.append("signature read_order must contain 2..6 substantive steps")
            linkage = item.get("data_linkage")
            if not isinstance(linkage, dict):
                item_errors.append("signature data_linkage must be an object")
            else:
                linked_claims = linkage.get("claim_ids")
                fields = linkage.get("source_fields")
                panel_links = linkage.get("panel_links")
                if linkage.get("pass") is not True:
                    item_errors.append("signature data_linkage.pass must be true")
                if not isinstance(linked_claims, list) or not set(linked_claims).intersection(claim_ids or []):
                    item_errors.append("signature data_linkage must bind a registered claim_id")
                if not isinstance(fields, list) or not fields or any(not nonempty_text(value, 1) for value in fields):
                    item_errors.append("signature data_linkage.source_fields must be non-empty")
                if not isinstance(panel_links, list) or not panel_links or any(not nonempty_text(value, 4) for value in panel_links):
                    item_errors.append("signature data_linkage.panel_links must explain cross-element linkage")
            signature_checks = item.get("signature_checks")
            if not isinstance(signature_checks, dict):
                item_errors.append("signature_checks must be an object")
            else:
                for field in SIGNATURE_CHECKS_TRUE:
                    if signature_checks.get(field) is not True:
                        item_errors.append(f"signature_checks.{field} must be true")
                if str(item.get("signature_archetype", "")).startswith("a_") and signature_checks.get("mechanism_to_result") is not True:
                    item_errors.append("A-class signature figure must connect mechanism to result")

        checked.append({"id": figure_id, "pass": not item_errors, "errors": item_errors})
        errors.extend(f"{figure_id}: {message}" for message in item_errors)

    result = {
        "schema_version": 1,
        "pass": not errors,
        "registry": args.registry,
        "track": args.track,
        "figure_count": len(figures),
        "signature": signature_summary,
        "checked": checked,
        "errors": errors,
    }
    out_dir = root / "审查"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "figure-style-audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# 数据图形风格审计", "", f"- 结果：{'PASS' if result['pass'] else 'FAIL'}", f"- 图数：{len(figures)}", ""]
    if errors:
        lines.extend(["## 阻断项", "", *[f"- {item}" for item in errors], ""])
    (out_dir / "figure-style-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "figure_count": len(figures), "error_count": len(errors)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
