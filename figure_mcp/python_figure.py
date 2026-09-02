from __future__ import annotations

"""Primary matplotlib renderer for CUMCM paper data figures.

Production quantitative figures route directly to Python/matplotlib.
This module provides deterministic local benchmarks and the shared publication contract:
white background, Microsoft YaHei, restrained blue/teal/orange palette, exact physical
canvas size, vector PDF/SVG output and a 450 dpi PNG preview. Renderer provenance is
recorded as ``python-matplotlib``.

The physical size is a contract: figures are saved without bbox_inches="tight" so
nothing can silently re-fit the canvas (the matplotlib equivalent of refusing
MATLAB's '-bestfit').
"""

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

CM_PER_INCH = 2.54

# Palette shared with the signature benchmarks and QUALITY_STANDARD.md.
BLUE = (0.2078, 0.3608, 0.4902)
TEAL = (0.1647, 0.6157, 0.5608)
ORANGE = (0.8510, 0.5098, 0.3294)
INK = (0.19, 0.21, 0.23)
PALE = (0.93, 0.95, 0.96)

# 3D scene palette shared by the Python scene renderer and signature benchmarks.
SCENE_COLORS = {
    "primary": (0.1216, 0.3059, 0.4745),
    "accent": (0.7725, 0.3529, 0.0667),
    "gray": (0.35, 0.35, 0.35),
}


def number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            # Keep text as text so fonts stay declared and editable in the SVG.
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "axes.edgecolor": (0.30, 0.32, 0.34),
            "axes.linewidth": 0.8,
            "axes.labelsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "grid.color": (0.2, 0.2, 0.2),
            "grid.alpha": 0.08,
        }
    )


def new_figure(width_cm: float = 15.5, height_cm: float = 8.8) -> Figure:
    apply_style()
    return plt.figure(figsize=(width_cm / CM_PER_INCH, height_cm / CM_PER_INCH))


def save_figure(fig: Figure, output_dir: str | Path, basename: str, dpi: int = 450) -> dict[str, Any]:
    """Save PDF/SVG vector outputs plus a PNG preview at the exact physical size."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {suffix: out / f"{basename}.{suffix}" for suffix in ("pdf", "svg", "png")}
    # No bbox_inches="tight": the canvas size is the publication contract.
    fig.savefig(paths["pdf"])
    fig.savefig(paths["svg"])
    fig.savefig(paths["png"], dpi=dpi)
    plt.close(fig)
    return {name: str(path) for name, path in paths.items()}


SERIES_COLORS = (BLUE, ORANGE, TEAL, INK)


def render_line2d(spec: dict[str, Any], output_dir: str | Path, basename: str) -> dict[str, Any]:
    """Render a 2D line/convergence figure from a structured spec.

    Spec vocabulary stays compatible with the live MATLAB line2d kind: series (name/x/y/markers),
    threshold + threshold_label, annotations (x/y/text/dx/dy), xlabel/ylabel/xlim/ylim.
    """
    fig = new_figure(number(spec.get("width_cm"), 15.5), number(spec.get("height_cm"), 8.8))
    ax = fig.add_axes((0.09, 0.13, 0.88, 0.82))
    for index, series in enumerate(spec.get("series", [])):
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        ax.plot(
            series.get("x", []),
            series.get("y", []),
            "-o" if series.get("markers") else "-",
            color=color,
            linewidth=1.3,
            markersize=3.5,
            markerfacecolor="white",
            label=str(series.get("name", f"系列{index + 1}")),
        )
    threshold = spec.get("threshold")
    if threshold is not None:
        ax.axhline(number(threshold), linestyle="--", color=INK, linewidth=0.9)
        if spec.get("threshold_label"):
            ax.text(0.985, number(threshold), str(spec["threshold_label"]), transform=ax.get_yaxis_transform(), fontsize=7.5, color=INK, ha="right", va="bottom")
    for note in spec.get("annotations", []):
        x, y = number(note.get("x")), number(note.get("y"))
        ax.annotate(
            str(note.get("text", "")),
            xy=(x, y),
            xytext=(x + number(note.get("dx"), 0.4), y + number(note.get("dy"), 0.05)),
            fontsize=7.5,
            color=INK,
            arrowprops={"arrowstyle": "-", "color": (0.45, 0.47, 0.49), "linewidth": 0.6},
        )
    if spec.get("title") and spec.get("show_title", True):
        ax.set_title(str(spec["title"]), fontsize=9)
    ax.set_xlabel(str(spec.get("xlabel", "")))
    ax.set_ylabel(str(spec.get("ylabel", "")))
    if isinstance(spec.get("xlim"), list) and len(spec["xlim"]) == 2:
        ax.set_xlim(number(spec["xlim"][0]), number(spec["xlim"][1]))
    if isinstance(spec.get("ylim"), list) and len(spec["ylim"]) == 2:
        ax.set_ylim(number(spec["ylim"][0]), number(spec["ylim"][1]))
    ax.grid(True)
    if any(series.get("name") for series in spec.get("series", [])):
        ax.legend(loc="upper right", frameon=False)

    out = Path(output_dir)
    files = save_figure(fig, out, basename)
    spec_path = out / f"{basename}.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    files["json"] = str(spec_path)
    ok = all(Path(path).exists() and Path(path).stat().st_size > 0 for path in files.values())
    return {"ok": ok, "renderer": "python-matplotlib", "files": [{"path": path} for path in files.values()]}


def _cubic_bezier(points: list[list[float]], samples: int = 120) -> np.ndarray:
    p = np.asarray(points, dtype=float)[:, :3]
    t = np.linspace(0.0, 1.0, samples)[:, None]
    return ((1 - t) ** 3) * p[0] + 3 * ((1 - t) ** 2) * t * p[1] + 3 * (1 - t) * (t**2) * p[2] + (t**3) * p[3]


def _scene_color(value: Any) -> tuple[float, float, float]:
    return SCENE_COLORS.get(str(value or "primary"), SCENE_COLORS["primary"])


def render_scene3d(spec: dict[str, Any], output_dir: str | Path, basename: str = "scene3d") -> dict[str, Any]:
    """Render structured 3D engineering geometry with matplotlib.

    Element vocabulary stays compatible with the live MATLAB backend: axis3d, point3d, text3d,
    polyline3d, trajectory3d, sightline_bundle, bezier3d, sphere3d, cylinder3d.
    """
    fig = new_figure(15.5, 9.5)
    ax = fig.add_axes((0.02, 0.02, 0.96, 0.96), projection="3d")
    ax.view_init(elev=23, azim=-52)
    ax.set_axis_off()

    tracked: list[list[float]] = []

    def track(points: Any) -> None:
        for point in points:
            tracked.append([number(point[0]), number(point[1]), number(point[2])])

    for element in spec.get("elements", []):
        if not isinstance(element, dict):
            continue
        kind = str(element.get("type", "point"))
        color = _scene_color(element.get("color"))
        if kind in {"polyline3d", "trajectory3d", "sightline_bundle"}:
            pts = element.get("points", [])
            if len(pts) < 2:
                continue
            track(pts)
            arr = np.asarray([[number(v) for v in p[:3]] for p in pts])
            style = "--" if kind == "trajectory3d" or element.get("dashed") else "-"
            width = number(element.get("line_width"), 1.2)
            ax.plot(arr[:, 0], arr[:, 1], arr[:, 2], style, color=color, linewidth=width)
            if bool(element.get("arrow", False)):
                a, b = arr[-2], arr[-1]
                ax.quiver(*a, *(b - a), color=color, linewidth=width, arrow_length_ratio=0.25)
        elif kind == "bezier3d":
            cps = element.get("points", [])
            if len(cps) == 4:
                track(cps)
                curve = _cubic_bezier(cps)
                ax.plot(curve[:, 0], curve[:, 1], curve[:, 2], "--", color=color, linewidth=number(element.get("line_width"), 1.1))
        elif kind == "point3d":
            p = element.get("at", [0, 0, 0])
            track([p])
            ax.scatter([number(p[0])], [number(p[1])], [number(p[2])], s=number(element.get("size"), 32), color=[color], depthshade=False)
        elif kind == "sphere3d":
            c = element.get("center", [0, 0, 0])
            r = number(element.get("radius"), 1.0)
            track([[number(c[0]) - r, number(c[1]) - r, number(c[2]) - r], [number(c[0]) + r, number(c[1]) + r, number(c[2]) + r]])
            u, v = np.meshgrid(np.linspace(0, 2 * np.pi, 49), np.linspace(0, np.pi, 25))
            ax.plot_surface(
                number(c[0]) + r * np.cos(u) * np.sin(v),
                number(c[1]) + r * np.sin(u) * np.sin(v),
                number(c[2]) + r * np.cos(v),
                color=(0.55, 0.58, 0.62),
                alpha=0.92,
                linewidth=0,
                shade=True,
            )
        elif kind == "cylinder3d":
            c = element.get("center", [0, 0, 0])
            r = number(element.get("radius"), 0.35)
            h = number(element.get("height"), 1.2)
            track([[number(c[0]) - r, number(c[1]) - r, number(c[2]) - h / 2], [number(c[0]) + r, number(c[1]) + r, number(c[2]) + h / 2]])
            theta, z = np.meshgrid(np.linspace(0, 2 * np.pi, 41), np.linspace(-h / 2, h / 2, 2))
            ax.plot_surface(
                number(c[0]) + r * np.cos(theta),
                number(c[1]) + r * np.sin(theta),
                number(c[2]) + z,
                color=(0.92, 0.92, 0.92),
                edgecolor=(0.35, 0.35, 0.35),
                linewidth=0.2,
            )
        elif kind == "text3d":
            p = element.get("at", [0, 0, 0])
            ax.text(number(p[0]), number(p[1]), number(p[2]), str(element.get("text", "")), fontsize=8.5, color=(0.1, 0.1, 0.1))
        elif kind == "axis3d":
            o = element.get("origin", [0, 0, 0])
            s = number(element.get("scale"), 1.0)
            ox, oy, oz = number(o[0]), number(o[1]), number(o[2])
            track([[ox, oy, oz], [ox + s, oy + s, oz + s]])
            gray = SCENE_COLORS["gray"]
            for dx, dy, dz, label in ((s, 0, 0, "x"), (0, s, 0, "y"), (0, 0, s, "z")):
                ax.quiver(ox, oy, oz, dx, dy, dz, color=gray, arrow_length_ratio=0.12, linewidth=1.0)
                ax.text(ox + dx * 1.05, oy + dy * 1.05, oz + dz * 1.05, label, fontsize=8.5, color=(0.1, 0.1, 0.1))

    if tracked:
        arr = np.asarray(tracked)
        spans = np.maximum(arr.max(axis=0) - arr.min(axis=0), 1e-6)
        ax.set_xlim(arr[:, 0].min(), arr[:, 0].max())
        ax.set_ylim(arr[:, 1].min(), arr[:, 1].max())
        ax.set_zlim(arr[:, 2].min(), arr[:, 2].max())
        ax.set_box_aspect(tuple(spans))

    out = Path(output_dir)
    files = save_figure(fig, out, basename)
    spec_path = out / f"{basename}.json"
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    files["json"] = str(spec_path)
    ok = all(Path(path).exists() and Path(path).stat().st_size > 0 for path in files.values())
    return {"ok": ok, "renderer": "python-matplotlib", "files": [{"path": path} for path in files.values()]}
