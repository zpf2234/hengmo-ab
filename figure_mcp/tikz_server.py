from __future__ import annotations

import math
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from common import DVISVGM_EXE, XELATEX_EXE, ensure_dir, escape_tex, file_manifest, json_dump, json_result, number, points, run_process, safe_basename

mcp = FastMCP(
    "TikZ Paper Figure MCP",
    instructions="Generate precise editable 2D scientific geometry and relation figures with TikZ, returning source plus vector PDF/SVG and PNG preview.",
)

STYLE = {
    "font": "Microsoft YaHei",
    "font_size": "10pt",
    "line_width": "0.85pt",
    "strong_line_width": "1.25pt",
    "primary": "1F4E79",
    "accent": "C55A11",
    "fill": "none",
}


def tex_text(value: Any, raw: bool = False) -> str:
    """Escape ordinary text while preserving explicit $...$ math fragments."""
    text = str(value)
    if raw:
        return text
    parts = re.split(r"(\$[^$]*\$)", text)
    return "".join(part if part.startswith("$") and part.endswith("$") else escape_tex(part) for part in parts)


def fmt_point(item: Any) -> str:
    if isinstance(item, str):
        value = item.strip()
        if not value:
            return "(0,0)"
        return value if value.startswith("(") else f"({value})"
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return f"({number(item[0]):.8g},{number(item[1]):.8g})"
    return "(0,0)"


def numeric_xy(item: Any) -> tuple[float, float] | None:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return number(item[0]), number(item[1])
    return None


def label_segment(raw_points: list[Any]) -> tuple[Any, Any]:
    """Choose a real route segment for an adjacent label without splitting the path."""
    candidates: list[tuple[float, int]] = []
    for index, (start, end) in enumerate(zip(raw_points, raw_points[1:])):
        a, b = numeric_xy(start), numeric_xy(end)
        if a is not None and b is not None:
            candidates.append((math.hypot(b[0] - a[0], b[1] - a[1]), index))
    if candidates:
        index = max(candidates)[1]
    else:
        index = max(0, len(raw_points) // 2 - 1)
    return raw_points[index], raw_points[index + 1]


def adjacent_label(label: Any, start: Any, end: Any, element: dict[str, Any]) -> str:
    """Place transparent text beside a continuous line, never inside its path."""
    label_tex = tex_text(label, bool(element.get("raw_tex", False)))
    raw_options = str(element.get("label_options", "inner sep=1pt,text=black!85")).strip()
    side = str(element.get("label_side", "")).strip().lower()
    a, b = numeric_xy(start), numeric_xy(end)
    if side not in {"above", "below", "left", "right"}:
        side = "above" if a is not None and b is not None and abs(b[0] - a[0]) >= abs(b[1] - a[1]) else "right"
    offset = max(number(element.get("label_offset_cm"), 0.12), 2.5 / 72 * 2.54)
    shifts = {
        "above": (0.0, offset, "south"),
        "below": (0.0, -offset, "north"),
        "left": (-offset, 0.0, "east"),
        "right": (offset, 0.0, "west"),
    }
    dx, dy, anchor = shifts[side]
    midpoint = f"($ {fmt_point(start)}!0.5!{fmt_point(end)} + ({dx:.8g},{dy:.8g}) $)"
    options = ",".join(filter(None, ("paperlabel", raw_options, "fill=none", "draw=none", f"anchor={anchor}")))
    return f"\\node[{options}] at {midpoint} {{{label_tex}}};"


def build_from_spec(spec: dict[str, Any]) -> str:
    elements = spec.get("elements", [])
    body: list[str] = []
    canvas = spec.get("canvas")
    if isinstance(canvas, dict):
        width = number(canvas.get("width"), 12)
        height = number(canvas.get("height"), 7)
        body.append(f"\\path[use as bounding box] (0,0) rectangle ({width:.8g},{height:.8g});")
    for el in elements if isinstance(elements, list) else []:
        if not isinstance(el, dict):
            continue
        kind = str(el.get("type", "line"))
        style = str(el.get("style", "paperline"))
        if kind in {"line", "arrow"}:
            raw_start, raw_end = el.get("from", [0, 0]), el.get("to", [1, 0])
            raw_waypoints = el.get("waypoints", []) if isinstance(el.get("waypoints", []), list) else []
            raw_points = [raw_start, *raw_waypoints, raw_end]
            start, end = fmt_point(raw_start), fmt_point(raw_end)
            arrow = ",->" if kind == "arrow" else ""
            waypoints = [fmt_point(point) for point in raw_waypoints]
            route = " -- ".join([start, *waypoints, end])
            body.append(f"\\draw[{style}{arrow}] {route};")
            label = el.get("label")
            if label:
                label_start, label_end = label_segment(raw_points)
                body.append(adjacent_label(label, label_start, label_end, el))
        elif kind == "bezier":
            start = fmt_point(el.get("from", [0, 0]))
            end = fmt_point(el.get("to", [1, 0]))
            c1 = fmt_point(el.get("control1", [0.33, 0]))
            c2 = fmt_point(el.get("control2", [0.66, 0]))
            arrow = ",->" if bool(el.get("arrow", False)) else ""
            body.append(f"\\draw[{style}{arrow}] {start} .. controls {c1} and {c2} .. {end};")
        elif kind in {"polyline", "polygon"}:
            pts = [fmt_point(p) for p in el.get("points", [])]
            if len(pts) >= 2:
                tail = " -- cycle" if kind == "polygon" else ""
                body.append(f"\\draw[{style}] " + " -- ".join(pts) + tail + ";")
        elif kind == "circle":
            body.append(f"\\draw[{style}] {fmt_point(el.get('center',[0,0]))} circle ({number(el.get('radius'),1):.8g});")
        elif kind == "ellipse":
            center = fmt_point(el.get("center", [0, 0]))
            rx, ry = number(el.get("rx"), 1), number(el.get("ry"), 0.5)
            body.append(f"\\draw[{style}] {center} ellipse [x radius={rx:.8g},y radius={ry:.8g}];")
        elif kind == "rectangle":
            if "x" in el or "y" in el or "width" in el or "height" in el:
                x, y = number(el.get("x")), number(el.get("y"))
                width, height = number(el.get("width"), 1), number(el.get("height"), 1)
                name = str(el.get("id", el.get("name", ""))).strip()
                text = tex_text(el.get("text", ""), bool(el.get("raw_tex", False)))
                opts = str(el.get("options", style))
                n = f" ({name})" if name else ""
                body.append(
                    f"\\node[{opts},minimum width={width:.8g}cm,minimum height={height:.8g}cm]{n} "
                    f"at ({x + width/2:.8g},{y + height/2:.8g}) {{{text}}};"
                )
            else:
                p1, p2 = fmt_point(el.get("from", [0, 0])), fmt_point(el.get("to", [1, 1]))
                body.append(f"\\draw[{style}] {p1} rectangle {p2};")
        elif kind == "cylinder":
            center = el.get("center", [0, 0])
            cx, cy = number(center[0]), number(center[1])
            w, h = number(el.get("width"), 1), number(el.get("height"), 2)
            ry = number(el.get("ellipse_height"), 0.22)
            left, right, top, bottom = cx-w/2, cx+w/2, cy+h/2, cy-h/2
            body += [
                f"\\draw[{style}] ({left:.8g},{bottom:.8g}) -- ({left:.8g},{top:.8g});",
                f"\\draw[{style}] ({right:.8g},{bottom:.8g}) -- ({right:.8g},{top:.8g});",
                f"\\draw[{style}] ({cx:.8g},{top:.8g}) ellipse [x radius={w/2:.8g},y radius={ry:.8g}];",
                f"\\draw[{style}] ({left:.8g},{bottom:.8g}) arc[start angle=180,end angle=360,x radius={w/2:.8g},y radius={ry:.8g}];",
                f"\\draw[{style},dashed] ({right:.8g},{bottom:.8g}) arc[start angle=0,end angle=180,x radius={w/2:.8g},y radius={ry:.8g}];",
            ]
        elif kind == "sine_wave":
            start = el.get("from", [0, 0]); end = el.get("to", [6, 0])
            x1, y1, x2 = number(start[0]), number(start[1]), number(end[0])
            amp, cycles = number(el.get("amplitude"), 0.12), number(el.get("cycles"), 5)
            body.append(f"\\draw[{style}] plot[domain={x1:.8g}:{x2:.8g},samples=160] (\\x,{{{y1:.8g}+{amp:.8g}*sin({360*cycles/(x2-x1):.8g}*(\\x-{x1:.8g}))}}); ")
        elif kind == "spring":
            start, end = el.get("from", [0, 0]), el.get("to", [0, -1])
            x1,y1,x2,y2 = number(start[0]),number(start[1]),number(end[0]),number(end[1])
            coils, amp = int(number(el.get("coils"), 6)), number(el.get("amplitude"), 0.10)
            pts = [(x1,y1)]
            for i in range(1, coils*2):
                t=i/(coils*2); pts.append((x1+(x2-x1)*t + (amp if i%2 else -amp), y1+(y2-y1)*t))
            pts.append((x2,y2))
            body.append(f"\\draw[{style}] " + " -- ".join(f"({x:.8g},{y:.8g})" for x,y in pts) + ";")
        elif kind == "damper":
            start, end = el.get("from", [0, 0]), el.get("to", [0, -1])
            x1,y1,x2,y2 = number(start[0]),number(start[1]),number(end[0]),number(end[1])
            ym=(y1+y2)/2
            body += [f"\\draw[{style}] ({x1:.8g},{y1:.8g}) -- ({x1:.8g},{ym+0.18:.8g});", f"\\draw[{style}] ({x1-0.16:.8g},{ym+0.18:.8g}) -- ({x1+0.16:.8g},{ym+0.18:.8g}) -- ({x1+0.16:.8g},{ym-0.18:.8g}) -- ({x1-0.16:.8g},{ym-0.18:.8g});", f"\\draw[{style}] ({x1:.8g},{ym:.8g}) -- ({x2:.8g},{y2:.8g});"]
        elif kind == "sphere":
            center = fmt_point(el.get("center", [0, 0])); radius = number(el.get("radius"), 1)
            body.append(f"\\shade[ball color={el.get('color','gray!45')},draw=black!75,line width=0.7pt] {center} circle ({radius:.8g});")
        elif kind == "tangent_rays":
            point, center = el.get("point", [0, 0]), el.get("center", [2, 0])
            px, py, cx, cy = number(point[0]), number(point[1]), number(center[0]), number(center[1])
            radius, length = number(el.get("radius"), 1), number(el.get("length"), 8)
            dx, dy = px-cx, py-cy; distance2 = dx*dx+dy*dy
            if distance2 > radius*radius:
                bx, by = cx + radius*radius*dx/distance2, cy + radius*radius*dy/distance2
                factor = radius*math.sqrt(distance2-radius*radius)/distance2
                tangent_points = [(bx-factor*dy, by+factor*dx), (bx+factor*dy, by-factor*dx)]
                for tx,ty in tangent_points:
                    norm=math.hypot(tx-px,ty-py); ex,ey=px+length*(tx-px)/norm,py+length*(ty-py)/norm
                    body.append(f"\\draw[{style},->] ({px:.8g},{py:.8g}) -- ({ex:.8g},{ey:.8g});")
                    if bool(el.get("show_contact", False)):
                        body.append(f"\\fill[black!65] ({tx:.8g},{ty:.8g}) circle (.025);")
        elif kind == "uav":
            at=el.get("at",[0,0]); x,y=number(at[0]),number(at[1]); scale=number(el.get("scale"),1); angle=number(el.get("angle"),-12)
            body += [f"\\begin{{scope}}[shift={{({x:.8g},{y:.8g})}},rotate={angle:.8g},scale={scale:.8g}]", "\\draw[black!70,line width=.55pt] (-.33,-.10) rectangle (.33,.10);", "\\draw[black!70,line width=.55pt] (-.08,-.34) rectangle (.08,.34);", "\\draw[black!70,line width=.55pt] (.33,0) -- (.48,0);", "\\end{scope}"]
        elif kind == "axis3d":
            origin = el.get("origin", [0,0]); ox,oy=number(origin[0]),number(origin[1]); scale=number(el.get("scale"),1)
            body += [f"\\draw[->,black!70] ({ox:.8g},{oy:.8g}) -- ({ox-0.8*scale:.8g},{oy-0.55*scale:.8g}) node[below] {{$x$}};", f"\\draw[->,black!70] ({ox:.8g},{oy:.8g}) -- ({ox+1.1*scale:.8g},{oy:.8g}) node[right] {{$y$}};", f"\\draw[->,black!70] ({ox:.8g},{oy:.8g}) -- ({ox:.8g},{oy+1.2*scale:.8g}) node[above] {{$z$}};"]
        elif kind == "arc":
            center = fmt_point(el.get("center", [0, 0]))
            body.append(f"\\draw[{style}] {center} ++({number(el.get('start_angle')):.8g}:{number(el.get('radius'),1):.8g}) arc[start angle={number(el.get('start_angle')):.8g},end angle={number(el.get('end_angle'),90):.8g},radius={number(el.get('radius'),1):.8g}];")
        elif kind == "node":
            at = fmt_point(el.get("at", [0, 0]))
            text = tex_text(el.get("text", ""), bool(el.get("raw_tex", False)))
            opts = str(el.get("options", "paperbox"))
            name = str(el.get("name", "")).strip()
            n = f" ({name})" if name else ""
            body.append(f"\\node[{opts}]{n} at {at} {{{text}}};")
        elif kind == "dimension":
            raw_start, raw_end = el.get("from", [0, 0]), el.get("to", [1, 0])
            start, end = fmt_point(raw_start), fmt_point(raw_end)
            body.append(f"\\draw[dim] {start} -- {end};")
            if el.get("label"):
                body.append(adjacent_label(el.get("label"), raw_start, raw_end, el))
        elif kind == "angle":
            vertex = fmt_point(el.get("vertex", [0, 0]))
            radius = number(el.get("radius"), 0.65)
            start = number(el.get("start_angle"), 0)
            end = number(el.get("end_angle"), 45)
            label = tex_text(el.get("label", ""), bool(el.get("raw_tex", False)))
            mid = (start + end) / 2
            body.append(f"\\draw[accentline] {vertex} ++({start:.8g}:{radius:.8g}) arc[start angle={start:.8g},end angle={end:.8g},radius={radius:.8g}];")
            body.append(f"\\node[paperlabel,fill=none,draw=none] at ($ {vertex} + ({mid:.8g}:{radius * 1.32:.8g}) $) {{{label}}};")
        elif kind == "detail_inset":
            # Reusable analytic local enlargement.  The caller supplies the
            # source ROI and the inset's local primitives; both are native
            # TikZ geometry, never a pasted raster crop.
            source_center = fmt_point(el.get("source_center", [0, 0]))
            source_width = number(el.get("source_width"), 0.8)
            source_height = number(el.get("source_height"), 0.8)
            inset_center_raw = el.get("inset_center", [8, 3])
            ix, iy = number(inset_center_raw[0]), number(inset_center_raw[1])
            inset_width = number(el.get("inset_width"), 4.2)
            inset_height = number(el.get("inset_height"), 3.0)
            scale = number(el.get("scale"), 1.8)
            title = tex_text(el.get("title", "局部放大"), bool(el.get("raw_tex", False)))
            # Resolve numeric source center for the ROI and leader anchors.
            source_raw = el.get("source_center", [0, 0])
            sx = number(source_raw[0]) if isinstance(source_raw, (list, tuple)) else 0.0
            sy = number(source_raw[1]) if isinstance(source_raw, (list, tuple)) else 0.0
            body += [
                f"\\draw[draw=black!45,densely dashed,line width=.55pt] "
                f"({sx-source_width/2:.8g},{sy-source_height/2:.8g}) rectangle "
                f"({sx+source_width/2:.8g},{sy+source_height/2:.8g});",
                f"\\draw[draw=black!28,line width=.5pt] ({sx+source_width/2:.8g},{sy+source_height/2:.8g}) -- "
                f"({ix-inset_width/2:.8g},{iy+inset_height/2:.8g});",
                f"\\draw[draw=black!28,line width=.5pt] ({sx+source_width/2:.8g},{sy-source_height/2:.8g}) -- "
                f"({ix-inset_width/2:.8g},{iy-inset_height/2:.8g});",
                f"\\begin{{scope}}[shift={{({ix:.8g},{iy:.8g})}}]",
                f"\\path[fill=none,draw=black!35,line width=.55pt] "
                f"({-inset_width/2:.8g},{-inset_height/2:.8g}) rectangle "
                f"({inset_width/2:.8g},{inset_height/2:.8g});",
                f"\\node[anchor=south west,fill=none,draw=none,font=\\footnotesize\\bfseries] "
                f"at ({-inset_width/2+0.12:.8g},{inset_height/2-0.34:.8g}) {{{title}}};",
                f"\\begin{{scope}}[scale={scale:.8g}]",
            ]
            local_spec = {"elements": el.get("elements", [])}
            local_body = build_from_spec(local_spec)
            if local_body:
                body.append(local_body)
            body += ["\\end{scope}", "\\end{scope}"]
    return "\n".join(body)


def document(body: str, title: str = "", width_cm: float = 15.5, border_pt: float = 4.0) -> str:
    title_node = f"\\node[font=\\bfseries] at (current bounding box.north) [yshift=5mm] {{{escape_tex(title)}}};" if title else ""
    width = max(0.1, number(width_cm, 15.5))
    content = str(body).strip()
    fixed_box = rf"""\coordinate (paper-bbox-south) at (current bounding box.south);
\coordinate (paper-bbox-north) at (current bounding box.north);
\pgfresetboundingbox
\path[use as bounding box] (0,0 |- paper-bbox-south) rectangle ({width:g}cm,0 |- paper-bbox-north);"""
    complete = re.fullmatch(r"\s*\\begin\{tikzpicture\}(?:\[[^\]]*\])?.*\\end\{tikzpicture\}\s*", content, flags=re.DOTALL)
    if complete:
        # A complete picture may already declare an exact canvas.  Injecting a
        # second reset-bounding-box block after that canvas can collapse the
        # exported page to the standalone border (a 4 pt "empty" PDF).  Trust
        # an explicit use-as-bounding-box contract; otherwise fix only width.
        injected = title_node if "use as bounding box" in content else f"{title_node}\n{fixed_box}"
        content = re.sub(
            r"\\end\{tikzpicture\}\s*$",
            lambda _: f"{injected}\n\\end{{tikzpicture}}",
            content,
            count=1,
        )
        picture = content
    else:
        # Structured specs with an explicit canvas already own their exact
        # bounding box.  Do not append the fixed-width reset, which otherwise
        # collapses a valid canvas to the standalone border.
        bbox = "" if "use as bounding box" in content else fixed_box
        picture = rf"""\begin{{tikzpicture}}[x=1cm,y=1cm,>=Stealth]
{content}
{title_node}
{bbox}
\end{{tikzpicture}}"""
    return rf"""\documentclass[tikz,border={number(border_pt, 4.0):.8g}pt]{{standalone}}
\usepackage{{fontspec}}
\usepackage{{amsmath}}
\setmainfont{{Microsoft YaHei}}
\usetikzlibrary{{arrows.meta,calc,angles,quotes,positioning,fit,backgrounds,shadings,shapes.geometric}}
\definecolor{{paperblue}}{{HTML}}{{1F4E79}}
\definecolor{{paperorange}}{{HTML}}{{C55A11}}
\tikzset{{
  paperline/.style={{draw=paperblue,line width=0.85pt,line cap=round,line join=round}},
  accentline/.style={{draw=paperorange,line width=1.15pt,line cap=round}},
  dim/.style={{draw=black!70,line width=0.7pt,{{Stealth[length=2mm]}}-{{Stealth[length=2mm]}}}},
  paperbox/.style={{draw=paperblue,fill=none,rounded corners=1.5pt,line width=0.8pt,inner sep=4pt,align=center}},
  paperlabel/.style={{draw=none,fill=none,text=black!85,inner sep=1pt}},
  mathlabel/.style={{draw=none,fill=none,text=black,inner sep=.6pt}},
  every node/.style={{font=\small}}
}}
\begin{{document}}
{picture}
\end{{document}}
"""


def compile_tex(source: Path, out: Path, base: str) -> dict[str, Any]:
    first = run_process([str(XELATEX_EXE), "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(out), str(source)], out, timeout=180)
    pdf = out / f"{base}.pdf"
    svg = out / f"{base}.svg"
    if first["returncode"] == 0 and pdf.exists():
        svg_proc = run_process([str(DVISVGM_EXE), "--pdf", "--font-format=woff", "--exact", "--output=" + str(svg), str(pdf)], out, timeout=180)
        pdftocairo = shutil.which("pdftocairo")
        if pdftocairo:
            # Poppler on Windows can read a PDF from a Unicode path but may fail to
            # create a PNG at one. Render to an ASCII temporary prefix, then copy.
            with tempfile.TemporaryDirectory(prefix="paper_tikz_") as temporary:
                preview_prefix = Path(temporary) / "preview"
                png_proc = run_process([pdftocairo, "-png", "-singlefile", "-r", "450", str(pdf), str(preview_prefix)], out, timeout=180)
                preview = preview_prefix.with_suffix(".png")
                if png_proc["returncode"] == 0 and preview.exists():
                    shutil.copy2(preview, out / f"{base}.png")
        else:
            png_proc = {"returncode": -1, "stdout": "", "stderr": "pdftocairo unavailable"}
    else:
        svg_proc = {"returncode": -1, "stdout": "", "stderr": "PDF compilation failed"}
        png_proc = {"returncode": -1, "stdout": "", "stderr": "PDF compilation failed"}
    return {"xelatex": first, "dvisvgm": svg_proc, "pdftocairo": png_proc}


@mcp.tool()
def health_check() -> str:
    """Verify XeLaTeX, TikZ and dvisvgm availability."""
    probe = run_process([str(XELATEX_EXE), "--version"], Path.cwd(), timeout=60)
    kpse = run_process([str(XELATEX_EXE.parent / "kpsewhich.exe"), "tikz.sty"], Path.cwd(), timeout=60)
    return json_result(ok=probe["returncode"] == 0 and bool(kpse["stdout"].strip()), xelatex=str(XELATEX_EXE), dvisvgm=str(DVISVGM_EXE), tikz=kpse["stdout"].strip(), style=STYLE, process=probe)


@mcp.tool()
def render_geometry(spec: dict[str, Any], output_dir: str = "", basename: str = "tikz_figure") -> str:
    """Render publication schematics with optional fixed canvas. Supports line/arrow, bezier, polygon, circle/ellipse, rectangle, cylinder, sphere, exact tangent_rays, sine_wave, spring, damper, uav, axis3d, arc, node, dimension and angle."""
    out = ensure_dir(output_dir)
    base = safe_basename(basename, "tikz_figure")
    tex = out / f"{base}.tex"
    spec_file = out / f"{base}.json"
    json_dump(spec_file, spec)
    tex.write_text(document(build_from_spec(spec), str(spec.get("title", "")), number(spec.get("width_cm"), 15.5)), encoding="utf-8")
    process = compile_tex(tex, out, base)
    files = [tex, spec_file, out / f"{base}.pdf", out / f"{base}.svg", out / f"{base}.png", out / f"{base}.log"]
    return json_result(ok=all(process[key]["returncode"] == 0 for key in ("xelatex", "dvisvgm", "pdftocairo")), files=file_manifest(files), process=process)


@mcp.tool()
def compile_tikz(tikz_body: str, output_dir: str = "", basename: str = "custom_tikz", title: str = "", border_pt: float = 4.0) -> str:
    """Compile an explicit TikZ picture body or complete tikzpicture into editable source plus PDF/SVG/PNG."""
    out = ensure_dir(output_dir)
    base = safe_basename(basename, "custom_tikz")
    tex = out / f"{base}.tex"
    body = str(tikz_body).strip()
    tex.write_text(document(body, title, border_pt=border_pt), encoding="utf-8")
    process = compile_tex(tex, out, base)
    files = [tex, out / f"{base}.pdf", out / f"{base}.svg", out / f"{base}.png", out / f"{base}.log"]
    return json_result(ok=all(process[key]["returncode"] == 0 for key in ("xelatex", "dvisvgm", "pdftocairo")), files=file_manifest(files), process=process)


if __name__ == "__main__":
    mcp.run()
