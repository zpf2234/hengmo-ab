from __future__ import annotations

import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "benchmark_outputs"

REQUIRED = {
    "python": ["benchmark_python_convergence.pdf", "benchmark_python_convergence.svg", "benchmark_python_convergence.png", "benchmark_python_convergence.json"],
    "tikz": ["benchmark_tikz_geometry.pdf", "benchmark_tikz_geometry.svg", "benchmark_tikz_geometry.tex", "benchmark_tikz_geometry.json"],
    "visio": ["benchmark_visio_flowchart.pdf", "benchmark_visio_flowchart.svg", "benchmark_visio_flowchart.png", "benchmark_visio_flowchart.vsdx", "benchmark_visio_flowchart.json", "benchmark_visio_flowchart.layout.json"],
}


def inspect_pdf(path: Path) -> dict:
    doc = fitz.open(path)
    page = doc[0]
    return {
        "pages": doc.page_count,
        "embedded_images": len(doc.get_page_images(0, full=True)),
        "text_chars": len(page.get_text()),
        "width_pt": round(page.rect.width, 2),
        "height_pt": round(page.rect.height, 2),
    }


def main() -> int:
    report = {"ok": True, "checks": {}, "errors": []}
    for family, names in REQUIRED.items():
        missing = [name for name in names if not (OUT / name).exists() or (OUT / name).stat().st_size == 0]
        report["checks"][family] = {"missing": missing}
        if missing:
            report["ok"] = False
            report["errors"].append(f"{family} 缺少文件: {missing}")
        pdf = OUT / names[0]
        if pdf.exists():
            info = inspect_pdf(pdf)
            report["checks"][family]["pdf"] = info
            if info["pages"] != 1 or info["embedded_images"] != 0 or info["text_chars"] == 0:
                report["ok"] = False
                report["errors"].append(f"{family} PDF 未通过真矢量门禁: {info}")

    python_json = json.loads((OUT / "benchmark_python_convergence.json").read_text(encoding="utf-8"))
    if "$" in python_json.get("xlabel", ""):
        report["ok"] = False
        report["errors"].append("数据图（Python）横轴含未处理的 $ 数学定界符")
    if not python_json.get("annotations") or python_json.get("threshold") is None:
        report["ok"] = False
        report["errors"].append("数据图（Python）缺少阈值或量化标注")

    tikz_text = (OUT / "benchmark_tikz_geometry.tex").read_text(encoding="utf-8")
    for token in (r"|AB|=d", r"L=|OB|", r"\theta"):
        if token not in tikz_text:
            report["ok"] = False
            report["errors"].append(f"TikZ 缺少严谨标注: {token}")

    visio_spec = json.loads((OUT / "benchmark_visio_flowchart.json").read_text(encoding="utf-8"))
    decisions = [n for n in visio_spec.get("nodes", []) if n.get("type") == "decision"]
    labels = {e.get("label") for e in visio_spec.get("edges", [])}
    feedback = [e for e in visio_spec.get("edges", []) if e.get("dashed")]
    if not decisions or not {"是", "否"}.issubset(labels) or not feedback:
        report["ok"] = False
        report["errors"].append("Visio 缺少标准判断分支或反馈回路")
    for edge in feedback:
        pts = edge.get("waypoints", [])
        if len(pts) < 2 or not (pts[0][0] == pts[1][0] or pts[0][1] == pts[1][1]):
            report["ok"] = False
            report["errors"].append("Visio 反馈回路不是正交路径")
    visio_layout = json.loads((OUT / "benchmark_visio_flowchart.layout.json").read_text(encoding="utf-8"))
    if not visio_layout.get("pass"):
        report["ok"] = False
        report["errors"].append("Visio 自动布局门禁未通过")
    if visio_layout.get("connection_audit", {}).get("failed") != 0:
        report["ok"] = False
        report["errors"].append("Visio 存在未通过的连接审计项")

    path = OUT / "quality_gate_report.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
