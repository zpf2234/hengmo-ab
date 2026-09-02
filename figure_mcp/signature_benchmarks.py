from __future__ import annotations

"""Structured A/B signature-figure benchmarks rendered with matplotlib.

These are cross-problem archetypes, not expected answers for any contest problem. Every
benchmark has an evidence linkage contract; palette-only restyling and decorative panel
collages are rejected before rendering. These local benchmarks exercise the same deterministic
Python renderer used for production quantitative figures, and provenance is recorded as
``python-matplotlib``.
"""

import json
import re
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

import python_figure
from python_figure import BLUE, INK, ORANGE, PALE, TEAL

ROOT = Path(__file__).resolve().parent
SPEC_DIR = ROOT / "benchmarks" / "signature_specs"
OUT = ROOT / "signature_benchmark_outputs"

REQUIRED_KINDS = {
    "a_mechanism_result": {"mechanism", "event_series", "closure_series"},
    "b_strategy_landscape": {"x", "y", "value", "strategy"},
    "uncertainty_decision_linkage": {"sample_size", "uncertainty", "policy_values", "switches"},
}


def validate_signature_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    kind = spec.get("kind")
    if kind not in REQUIRED_KINDS:
        return [f"unsupported signature benchmark kind: {kind}"]
    for field in ("core_claim", "ten_second_takeaway"):
        if not isinstance(spec.get(field), str) or len(spec[field].strip()) < 8:
            errors.append(f"{field} must be substantive")
    order = spec.get("read_order")
    if not isinstance(order, list) or not 2 <= len(order) <= 5 or any(not isinstance(x, str) or len(x.strip()) < 2 for x in order):
        errors.append("read_order must contain 2..5 semantic steps")
    linkage = spec.get("data_linkage")
    if not isinstance(linkage, dict):
        errors.append("data_linkage must be an object")
    else:
        for field in ("source_fields", "element_links"):
            values = linkage.get(field)
            if not isinstance(values, list) or not values or any(not isinstance(x, str) or len(x.strip()) < 2 for x in values):
                errors.append(f"data_linkage.{field} must be non-empty")
    checks = spec.get("signature_checks")
    if not isinstance(checks, dict):
        errors.append("signature_checks must be an object")
    else:
        for field in ("integrated_narrative", "adds_explanatory_responsibility", "not_palette_only", "not_decorative_collage"):
            if checks.get(field) is not True:
                errors.append(f"signature_checks.{field} must be true")
    evidence = spec.get("evidence")
    missing = REQUIRED_KINDS[kind] - set(evidence) if isinstance(evidence, dict) else REQUIRED_KINDS[kind]
    if missing:
        errors.append(f"evidence missing fields: {sorted(missing)}")
    elif kind == "a_mechanism_result":
        mechanism = evidence.get("mechanism", {})
        event_series = evidence.get("event_series", {})
        closure = evidence.get("closure_series", {})
        if not isinstance(mechanism.get("boundary_equation"), str) or len(mechanism["boundary_equation"].strip()) < 4:
            errors.append("mechanism boundary_equation must be explicit")
        if not isinstance(closure.get("error_definition"), str) or len(closure["error_definition"].strip()) < 6:
            errors.append("closure_series.error_definition must identify the verified quantity")
        if not isinstance(closure.get("report_threshold"), (int, float)):
            errors.append("closure_series.report_threshold must be numeric")
        event_x = event_series.get("x", [])
        margins = event_series.get("boundary_margin", [])
        responses = event_series.get("response", [])
        critical_x = event_series.get("critical_x")
        if not event_x or len(margins) != len(event_x) or len(responses) != len(event_x):
            errors.append("event_series x/boundary_margin/response lengths must match")
        elif critical_x not in event_x:
            errors.append("event_series.critical_x must be an observed x value")
        else:
            critical_index = event_x.index(critical_x)
            margin_scale = max(1.0, max(abs(float(value)) for value in margins))
            if abs(float(margins[critical_index])) > 1e-9 * margin_scale:
                errors.append("event_series.critical_x must coincide with boundary_margin zero")
        resolution = closure.get("resolution", [])
        closure_error = closure.get("error", [])
        if not resolution or len(closure_error) != len(resolution):
            errors.append("closure_series resolution/error lengths must match")
        elif any(float(value) <= 0 for value in closure_error):
            errors.append("closure_series errors must be positive")
        else:
            if any(float(b) <= float(a) for a, b in zip(resolution, resolution[1:])):
                errors.append("closure_series resolution must strictly increase")
            if any(float(b) >= float(a) for a, b in zip(closure_error, closure_error[1:])):
                errors.append("closure_series error must strictly decrease")
            threshold = closure.get("report_threshold")
            if isinstance(threshold, (int, float)) and float(closure_error[-1]) > float(threshold):
                errors.append("closure_series final error must not exceed report_threshold")
    elif kind == "b_strategy_landscape":
        x, y = evidence.get("x", []), evidence.get("y", [])
        value, strategy = evidence.get("value", []), evidence.get("strategy", [])
        if len(value) != len(y) or len(strategy) != len(y) or any(len(row) != len(x) for row in value + strategy):
            errors.append("strategy landscape grids must match x/y dimensions")
        if len({cell for row in strategy for cell in row}) < 2:
            errors.append("strategy landscape must contain a real switching boundary")
        recommended = evidence.get("recommended", [])
        expected_strategy = evidence.get("recommended_strategy")
        minimum_margin = evidence.get("minimum_switch_margin_cells")
        if len(recommended) != 2 or recommended[0] not in x or recommended[1] not in y:
            errors.append("recommended point must lie on the audited x/y grid")
        else:
            ix, iy = x.index(recommended[0]), y.index(recommended[1])
            actual_strategy = strategy[iy][ix]
            if expected_strategy is not None and actual_strategy != expected_strategy:
                errors.append("recommended_strategy does not match strategy grid at recommended point")
            if isinstance(minimum_margin, int) and minimum_margin >= 1:
                distances = [
                    abs(row - iy) + abs(col - ix)
                    for row, values in enumerate(strategy)
                    for col, cell in enumerate(values)
                    if cell != actual_strategy
                ]
                boundary_margin = min(distances) if distances else None
                if boundary_margin is None or boundary_margin <= minimum_margin:
                    errors.append("recommended point lacks required switching boundary margin")
    elif kind == "uncertainty_decision_linkage":
        switches = evidence.get("switches", [])
        if not isinstance(switches, list) or not switches:
            errors.append("uncertainty linkage requires switch events")
        else:
            for switch in switches:
                if not isinstance(switch, dict) or not isinstance(switch.get("n"), (int, float)) or not isinstance(switch.get("uncertainty_threshold"), (int, float)):
                    errors.append("each switch must bind n to a numeric uncertainty_threshold")
                    break
        sample_size = evidence.get("sample_size", [])
        uncertainty = evidence.get("uncertainty", [])
        policy_values = evidence.get("policy_values", {})
        if not sample_size or len(uncertainty) != len(sample_size):
            errors.append("sample_size/uncertainty lengths must match")
        elif not isinstance(policy_values, dict) or len(policy_values) < 2 or any(len(values) != len(sample_size) for values in policy_values.values()):
            errors.append("policy_values must provide aligned values for at least two policies")
        elif isinstance(switches, list):
            policy_names = list(policy_values)
            winners = [max(policy_names, key=lambda name: float(policy_values[name][index])) for index in range(len(sample_size))]
            for switch in switches:
                if not isinstance(switch, dict) or switch.get("n") not in sample_size:
                    continue
                index = sample_size.index(switch["n"])
                threshold = switch.get("uncertainty_threshold")
                if isinstance(threshold, (int, float)) and not np.isclose(float(threshold), float(uncertainty[index]), rtol=1e-9, atol=1e-12):
                    errors.append("switch uncertainty_threshold does not match uncertainty series at n")
                if index == 0 or winners[index] == winners[index - 1]:
                    errors.append("switch n is not a policy argmax transition")
    return errors


CANVAS_W, CANVAS_H = 15.5, 8.8


def mechanism_render(spec: dict[str, Any], base: str, output_dir: Path | None = None) -> dict[str, Any]:
    ev = spec["evidence"]
    t = np.asarray(ev["event_series"]["x"], dtype=float)
    margin = np.asarray(ev["event_series"]["boundary_margin"], dtype=float)
    response = np.asarray(ev["event_series"]["response"], dtype=float)
    resolution = np.asarray(ev["closure_series"]["resolution"], dtype=float)
    error = np.asarray(ev["closure_series"]["error"], dtype=float)
    threshold = float(ev["closure_series"]["report_threshold"])
    error_definition = str(ev["closure_series"]["error_definition"])
    boundary_equation = str(ev["mechanism"]["boundary_equation"])
    event = float(ev["event_series"]["critical_x"])

    fig = python_figure.new_figure(CANVAS_W, CANVAS_H)
    gs = fig.add_gridspec(1, 3, left=0.055, right=0.955, top=0.93, bottom=0.15, wspace=0.5)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_xlim(0, 5)
    ax1.set_ylim(0, 4)
    ax1.set_aspect("equal")
    ax1.axis("off")
    ax1.add_patch(Rectangle((0.5, 0.55), 4.0, 0.30, facecolor=PALE, edgecolor="none"))
    ax1.plot([0.7, 4.25], [0.9, 3.15], "-", color=BLUE, linewidth=1.5)
    ax1.plot([0.7, 4.25], [3.15, 0.9], "--", color=INK, linewidth=0.9)
    ax1.plot([2.47], [2.03], "o", color=ORANGE, markerfacecolor=ORANGE, markersize=6)
    ax1.annotate("", xy=(2.47, 1.18), xytext=(2.47, 2.03), arrowprops={"arrowstyle": "-|>", "color": ORANGE, "linewidth": 1.2})
    ax1.text(0.7, 3.55, "(a) 机理定义", fontsize=8.5, fontweight="bold", color=INK)
    ax1.text(0.7, 3.20, boundary_equation, fontsize=8, color=BLUE)
    ax1.text(2.64, 2.20, "临界构型 x_c", fontsize=8, color=ORANGE)
    ax1.text(0.65, 0.22, "边界交会定义同一临界事件", fontsize=7.4, color=INK)

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(t, margin, "-", color=BLUE, linewidth=1.25)
    ax2.axhline(0.0, linestyle=":", color=INK, linewidth=0.8)
    ax2.set_ylabel("边界余量")
    ax2.set_xlabel("时间 / s")
    ax2.grid(True)
    ax2.tick_params(labelsize=8)
    right = ax2.twinx()
    right.plot(t, response, "-", color=TEAL, linewidth=1.25)
    right.tick_params(labelsize=8)
    ax2.axvline(event, linestyle="--", color=ORANGE, linewidth=1.1)
    ax2.text(0.04, 0.95, "(b) 事件检测：g(t_c)=0", transform=ax2.transAxes, fontsize=8, fontweight="bold", color=INK, va="top")
    ax2.text(0.52, 0.86, "青绿：状态响应", transform=ax2.transAxes, fontsize=7.3, color=TEAL)
    ax2.text(event + 0.18, float(np.interp(event, t, margin)) + 0.12, f"t_c = {event:.2f} s", fontsize=7.5, color=ORANGE)

    ax3 = fig.add_subplot(gs[0, 2])
    ax3.loglog(resolution, error, "-o", color=BLUE, markerfacecolor="white", linewidth=1.2, markersize=4)
    ax3.axhline(threshold, linestyle=":", color=ORANGE, linewidth=1.0)
    ax3.text(resolution[0], threshold * 1.25, f"阈值 {threshold:.1e}", fontsize=7.5, color=ORANGE)
    ax3.set_xlabel("分辨率")
    ax3.set_ylabel(error_definition)
    ax3.grid(True, which="both")
    ax3.tick_params(labelsize=8)
    ax3.text(0.05, 0.93, "(c) 独立误差闭合", transform=ax3.transAxes, fontsize=8, fontweight="bold", color=INK)
    ax3.text(0.42, 0.16, "低于报告阈值", transform=ax3.transAxes, fontsize=7.5, color=ORANGE)

    return python_figure.save_figure(fig, output_dir or OUT, base)


def landscape_render(spec: dict[str, Any], base: str, output_dir: Path | None = None) -> dict[str, Any]:
    ev = spec["evidence"]
    x = np.asarray(ev["x"], dtype=float)
    y = np.asarray(ev["y"], dtype=float)
    value = np.asarray(ev["value"], dtype=float)
    strategy = np.asarray(ev["strategy"], dtype=float)
    cx, cy = (float(v) for v in ev["current"])
    rx, ry = (float(v) for v in ev["recommended"])
    grid_x, grid_y = np.meshgrid(x, y)

    fig = python_figure.new_figure(CANVAS_W, CANVAS_H)
    gs = fig.add_gridspec(1, 4, left=0.06, right=0.97, top=0.92, bottom=0.15, wspace=0.55)

    ax1 = fig.add_subplot(gs[0, :3])
    cmap = ListedColormap([(0.87, 0.91, 0.94), (0.82, 0.93, 0.90), (0.97, 0.89, 0.82)])
    ax1.contourf(grid_x, grid_y, strategy, levels=[0.5, 1.5, 2.5, 3.5], cmap=cmap)
    contours = ax1.contour(grid_x, grid_y, value, levels=7, colors=[(0.42, 0.45, 0.47)], linewidths=0.55)
    ax1.clabel(contours, fontsize=7, colors=[INK])
    ax1.contour(grid_x, grid_y, strategy, levels=[1.5, 2.5], colors=[INK], linewidths=1.35)
    ax1.plot([cx], [cy], "o", color=INK, markerfacecolor="white", markersize=6, markeredgewidth=1.1)
    ax1.plot([rx], [ry], "*", color=ORANGE, markerfacecolor=ORANGE, markersize=11)
    ax1.text(cx, cy, "  当前：策略 A", fontsize=8, color=INK)
    ax1.text(rx, ry, "  推荐：策略 B", fontsize=8, color=ORANGE)
    ax1.text(0.76, 0.12, "策略 A", fontsize=8, color=INK)
    ax1.text(1.12, 0.27, "策略 B", fontsize=8, color=INK)
    ax1.text(1.34, 0.78, "策略 C", fontsize=8, color=INK)
    ax1.set_xlabel("需求水平")
    ax1.set_ylabel("风险权重")
    ax1.set_xlim(x[0], x[-1])
    ax1.set_ylim(y[0], y[-1] + 0.05 * (y[-1] - y[0]))
    ax1.tick_params(labelsize=8)
    ax1.text(
        x[0] + 0.02 * (x[-1] - x[0]),
        y[-1] - 0.04 * (y[-1] - y[0]),
        "最优策略区（底色）·价值等高线·切换边界（粗线）",
        fontsize=7.8,
        color=INK,
        va="top",
    )

    ax2 = fig.add_subplot(gs[0, 3])
    region_best = [float(value[strategy == level].max()) for level in (1, 2, 3)]
    ax2.barh([1, 2, 3], region_best, height=0.55, color=BLUE, edgecolor="none")
    ax2.set_yticks([1, 2, 3])
    ax2.set_yticklabels(["策略 A", "策略 B", "策略 C"])
    ax2.set_xlabel("区域最优价值")
    ax2.grid(True, axis="x")
    ax2.tick_params(labelsize=8)
    best_index = int(np.argmax(region_best))
    ax2.plot([region_best[best_index]], [best_index + 1], "*", color=ORANGE, markerfacecolor=ORANGE, markersize=9)

    return python_figure.save_figure(fig, output_dir or OUT, base)


def uncertainty_render(spec: dict[str, Any], base: str, output_dir: Path | None = None) -> dict[str, Any]:
    ev = spec["evidence"]
    n = np.asarray(ev["sample_size"], dtype=float)
    uncertainty = np.asarray(ev["uncertainty"], dtype=float)
    names = list(ev["policy_values"])
    switches = ev["switches"]

    fig = python_figure.new_figure(CANVAS_W, CANVAS_H)
    gs = fig.add_gridspec(2, 1, left=0.075, right=0.97, top=0.94, bottom=0.12, hspace=0.32)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(n, uncertainty, "-o", color=BLUE, markerfacecolor="white", linewidth=1.2, markersize=3.5)
    ax1.set_ylabel("不确定性上界 U(n)")
    ax1.grid(True)
    ax1.tick_params(labelsize=8)
    ax1.text(n[1], uncertainty[1] * 1.08, "(a) 信息增加，不确定性收缩", color=INK, fontsize=8, fontweight="bold")

    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)
    colors = [BLUE, TEAL, ORANGE]
    for index, name in enumerate(names):
        values = np.asarray(ev["policy_values"][name], dtype=float)
        ax2.plot(n, values, "-", color=colors[index % len(colors)], linewidth=1.2, label=name)
    policy_top = max(max(ev["policy_values"][name]) for name in names)
    for switch in switches:
        threshold = float(switch["uncertainty_threshold"])
        event_n = float(switch["n"])
        ax1.axhline(threshold, linestyle=":", color=ORANGE, linewidth=0.8)
        ax1.text(n[-1], threshold, f"U={threshold:.3f}", fontsize=7, color=ORANGE, ha="right", va="bottom")
        ax1.axvline(event_n, linestyle="--", color=INK, linewidth=0.8)
        ax2.axvline(event_n, linestyle="--", color=INK, linewidth=0.8)
        ax2.text(event_n + 3, policy_top * 0.97, str(switch["label"]), color=INK, fontsize=7.0, va="top")
    ax2.set_xlabel("样本量 n")
    ax2.set_ylabel("稳健价值")
    ax2.grid(True)
    ax2.tick_params(labelsize=8)
    ax2.legend(loc="lower right", frameon=False, fontsize=8)
    ax2.text(n[0], policy_top * 0.99, "(b) 风险阈值穿越 → 策略价值占优", color=INK, fontsize=8, fontweight="bold")

    return python_figure.save_figure(fig, output_dir or OUT, base)


BUILDERS = {
    "a_mechanism_result": mechanism_render,
    "b_strategy_landscape": landscape_render,
    "uncertainty_decision_linkage": uncertainty_render,
}


def _svg_length_cm(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(cm|mm|in|pt|px)?\s*", value)
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2) or "px"
    factors = {"cm": 1.0, "mm": 0.1, "in": 2.54, "pt": 2.54 / 72.0, "px": 2.54 / 96.0}
    return number * factors[unit]


def audit_rendered_signature(
    pdf_path: Path,
    svg_path: Path,
    width_cm: float = 15.5,
    height_cm: float = 8.8,
    require_microsoft_yahei: bool = False,
) -> dict[str, Any]:
    """Machine-check objective render facts only; never infer subjective visual quality."""
    errors: list[str] = []
    pdf_info: dict[str, Any] = {}
    svg_info: dict[str, Any] = {}
    if not pdf_path.exists() or not svg_path.exists():
        return {"pass": False, "errors": ["required PDF/SVG render missing"], "pdf": pdf_info, "svg": svg_info}

    doc = fitz.open(pdf_path)
    if doc.page_count != 1:
        errors.append("PDF must contain exactly one page")
    if doc.page_count:
        page = doc[0]
        expected_width_pt = width_cm / 2.54 * 72.0
        expected_height_pt = height_cm / 2.54 * 72.0
        expected_ratio = width_cm / height_cm
        actual_ratio = page.rect.width / page.rect.height
        ratio_distortion = abs(actual_ratio / expected_ratio - 1.0)
        width_size_error = abs(page.rect.width / expected_width_pt - 1.0)
        height_size_error = abs(page.rect.height / expected_height_pt - 1.0)
        embedded_images = len(doc.get_page_images(0, full=True))
        drawing_count = len(page.get_drawings())
        text_chars = len(page.get_text().strip())
        pdf_fonts = sorted({font[3] for font in doc.get_page_fonts(0, full=True) if len(font) > 3})
        microsoft_yahei_embedded = any("MicrosoftYaHei" in name.replace(" ", "") for name in pdf_fonts)
        pdf_info = {
            "pages": doc.page_count,
            "width_pt": round(page.rect.width, 3),
            "height_pt": round(page.rect.height, 3),
            "page_size_distortion": ratio_distortion,
            "width_size_error": width_size_error,
            "height_size_error": height_size_error,
            "embedded_images": embedded_images,
            "drawing_count": drawing_count,
            "text_chars": text_chars,
            "fonts": pdf_fonts,
            "microsoft_yahei_embedded": microsoft_yahei_embedded,
        }
        if ratio_distortion > 0.002:
            errors.append(f"PDF aspect-ratio distortion {ratio_distortion:.6f} exceeds 0.002")
        if width_size_error > 0.002 or height_size_error > 0.002:
            errors.append(
                "PDF final-size error exceeds 0.002 "
                f"(width={width_size_error:.6f}, height={height_size_error:.6f})"
            )
        if embedded_images:
            errors.append(f"PDF contains {embedded_images} embedded raster image(s)")
        if drawing_count == 0 and text_chars == 0:
            errors.append("PDF has no inspectable vector/text content")
        if require_microsoft_yahei and text_chars and not microsoft_yahei_embedded:
            errors.append("PDF text does not use embedded Microsoft YaHei")
    doc.close()

    svg_text = svg_path.read_text(encoding="utf-8", errors="replace")
    root_match = re.search(r"<svg\b([^>]*)>", svg_text, re.IGNORECASE)
    attrs = root_match.group(1) if root_match else ""
    width_match = re.search(r'\bwidth=["\']([^"\']+)', attrs, re.IGNORECASE)
    height_match = re.search(r'\bheight=["\']([^"\']+)', attrs, re.IGNORECASE)
    width = _svg_length_cm(width_match.group(1)) if width_match else None
    height = _svg_length_cm(height_match.group(1)) if height_match else None
    svg_ratio_distortion = abs((width / height) / (width_cm / height_cm) - 1.0) if width and height else None
    svg_width_size_error = abs(width / width_cm - 1.0) if width else None
    svg_height_size_error = abs(height / height_cm - 1.0) if height else None
    raster_images = len(re.findall(r"<image\b", svg_text, re.IGNORECASE))
    svg_text_blocks = re.findall(r"<text\b[^>]*>.*?</text>", svg_text, re.IGNORECASE | re.DOTALL)
    microsoft_yahei_text_styles = bool(svg_text_blocks) and all(
        re.search(r"font-family(?:\s*:\s*|\s*=)[^>]*Microsoft YaHei", block, re.IGNORECASE)
        for block in svg_text_blocks
    )
    svg_info = {
        "width_cm": width,
        "height_cm": height,
        "aspect_ratio_distortion": svg_ratio_distortion,
        "width_size_error": svg_width_size_error,
        "height_size_error": svg_height_size_error,
        "embedded_raster_images": raster_images,
        "microsoft_yahei_declared": "Microsoft YaHei" in svg_text,
        "microsoft_yahei_text_styles": microsoft_yahei_text_styles,
    }
    if svg_ratio_distortion is None:
        errors.append("SVG width/height are not measurable")
    elif svg_ratio_distortion > 0.002:
        errors.append(f"SVG aspect-ratio distortion {svg_ratio_distortion:.6f} exceeds 0.002")
    if (
        svg_width_size_error is not None
        and svg_height_size_error is not None
        and (svg_width_size_error > 0.002 or svg_height_size_error > 0.002)
    ):
        errors.append(
            "SVG final-size error exceeds 0.002 "
            f"(width={svg_width_size_error:.6f}, height={svg_height_size_error:.6f})"
        )
    if raster_images:
        errors.append(f"SVG contains {raster_images} embedded raster image(s)")
    if require_microsoft_yahei and svg_text_blocks and not microsoft_yahei_text_styles:
        errors.append("SVG text elements do not consistently declare Microsoft YaHei")
    return {"pass": not errors, "errors": errors, "pdf": pdf_info, "svg": svg_info}


def render_one(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_signature_spec(spec)
    if errors:
        return {"ok": False, "errors": errors, "spec": str(path)}
    OUT.mkdir(parents=True, exist_ok=True)
    base = path.stem
    (OUT / f"{base}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    BUILDERS[spec["kind"]](spec, base, OUT)
    required = [OUT / f"{base}{suffix}" for suffix in (".pdf", ".svg", ".png", ".json")]
    artifact_ok = all(output.exists() and output.stat().st_size > 0 for output in required)
    render_audit = audit_rendered_signature(
        OUT / f"{base}.pdf",
        OUT / f"{base}.svg",
        require_microsoft_yahei=True,
    ) if artifact_ok else {
        "pass": False,
        "errors": ["render outputs incomplete"],
    }
    return {
        "ok": artifact_ok and render_audit["pass"],
        "errors": render_audit.get("errors", []),
        "renderer": "python-matplotlib",
        "render_audit": render_audit,
        "benchmark_spec": spec,
        "required_outputs": [str(output) for output in required],
    }


def main() -> int:
    paths = sorted(SPEC_DIR.glob("*.json"))
    results = {path.stem: render_one(path) for path in paths}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "signature_benchmark_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {name: {"ok": value.get("ok"), "errors": value.get("errors", [])} for name, value in results.items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if len(results) >= 3 and all(value.get("ok") for value in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
