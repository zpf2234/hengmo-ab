from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from common import MATLAB_EXE, ensure_dir, file_manifest, json_dump, json_result, matlab_path, number, run_process, safe_basename

mcp = FastMCP(
    "MATLAB Paper Figure MCP",
    instructions="Generate reproducible award-paper-grade figures with MATLAB R2024b and export vector PDF/SVG plus PNG preview and source data.",
)

STYLE = {
    "font_name": "Microsoft YaHei",
    "font_size": 8.5,
    "axis_line_width": 0.72,
    "line_width": 1.15,
    "marker_size": 3.6,
    "figure_width_cm": 15.5,
    "figure_height_cm": 8.8,
    "palette": ["#355C7D", "#2A9D8F", "#D98254", "#6B7280", "#B44C43"],
}

# Stay below the MCP transport's 300 s deadline. common.run_process converts a stalled
# MATLAB process into structured timeout provenance instead of a transport exception.
MATLAB_HEALTH_TIMEOUT_SECONDS = 90
MATLAB_RENDER_TIMEOUT_SECONDS = 240


def q(value: Any) -> str:
    return str(value).replace("'", "''")


def m_array(values: list[float]) -> str:
    return "[" + " ".join(f"{number(v):.15g}" for v in values) + "]"


def validate_spec(spec: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    kind = str(spec.get("kind", "line2d"))
    allowed = {"line2d", "scatter2d", "trajectory2d", "bar", "heatmap", "surface3d", "contourf"}
    if kind not in allowed:
        errors.append(f"不支持的 kind: {kind}")
    if kind in {"line2d", "scatter2d", "trajectory2d"}:
        series = spec.get("series")
        if not isinstance(series, list) or not series:
            errors.append("series 必须为非空数组")
        else:
            for i, item in enumerate(series):
                if not isinstance(item, dict):
                    errors.append(f"series[{i}] 必须为对象")
                    continue
                x, y = item.get("x"), item.get("y")
                if not isinstance(x, list) or not isinstance(y, list) or len(x) != len(y) or not x:
                    errors.append(f"series[{i}] 的 x/y 必须等长且非空")
    elif kind == "bar":
        if not isinstance(spec.get("values"), list) or not spec.get("values"):
            errors.append("bar 需要非空 values")
    else:
        z = spec.get("z")
        if not isinstance(z, list) or not z or not all(isinstance(row, list) for row in z):
            errors.append(f"{kind} 需要二维 z 数组")
    return not errors, errors


def build_script(spec: dict[str, Any], out_dir: Path, base: str) -> str:
    kind = str(spec.get("kind", "line2d"))
    title = q(spec.get("title", ""))
    xlabel = q(spec.get("xlabel", ""))
    ylabel = q(spec.get("ylabel", ""))
    zlabel = q(spec.get("zlabel", ""))
    width = number(spec.get("width_cm"), STYLE["figure_width_cm"])
    height = number(spec.get("height_cm"), STYLE["figure_height_cm"])
    lines = [
        "set(groot,'defaultFigureColor','w');",
        "set(groot,'defaultAxesFontName','Microsoft YaHei','defaultTextFontName','Microsoft YaHei');",
        f"fig=figure('Visible','off','Units','centimeters','Position',[2 2 {width:.3f} {height:.3f}]);",
        "ax=axes(fig,'Position',[0.115 0.145 0.845 0.79]); hold(ax,'on'); box(ax,'on'); grid(ax,'on');",
        "ax.GridAlpha=0.07; ax.MinorGridAlpha=0.035; ax.LineWidth=0.72; ax.FontSize=8.5; ax.TickDir='out'; ax.Layer='top';",
        "palette=[0.2078 0.3608 0.4902; 0.1647 0.6157 0.5608; 0.8510 0.5098 0.3294; 0.4196 0.4471 0.5020; 0.7059 0.2980 0.2627];",
    ]
    legend_names: list[str] = []
    all_x: list[float] = []
    all_y: list[float] = []
    if kind in {"line2d", "scatter2d", "trajectory2d"}:
        for idx, item in enumerate(spec.get("series", []), start=1):
            x = [number(v) for v in item.get("x", [])]
            y = [number(v) for v in item.get("y", [])]
            all_x.extend(x)
            all_y.extend(y)
            name = q(item.get("name", f"序列 {idx}"))
            legend_names.append(name)
            color_idx = (idx - 1) % 5 + 1
            if kind == "scatter2d":
                lines.append(f"scatter(ax,{m_array(x)},{m_array(y)},24,palette({color_idx},:),'filled','MarkerFaceAlpha',0.76);")
            else:
                marker_names = ["o", "s", "^", "d", "v"]
                line_styles = ["-", "--", "-.", ":", "-"]
                marker_name = marker_names[(idx - 1) % len(marker_names)]
                line_style = str(item.get("line_style", line_styles[(idx - 1) % len(line_styles)]))
                marker = f"'{marker_name}','MarkerIndices',unique(round(linspace(1,numel(x),min(7,numel(x)))))" if bool(item.get("markers", kind == "trajectory2d")) else "'none'"
                lines += [
                    f"x={m_array(x)}; y={m_array(y)};",
                    f"plot(ax,x,y,'LineStyle','{q(line_style)}','LineWidth',1.15,'Color',palette({color_idx},:),'Marker',{marker},'MarkerSize',3.6,'MarkerFaceColor','white');",
                ]
        if kind == "trajectory2d":
            lines.append("axis(ax,'equal');")
    elif kind == "bar":
        vals = [number(v) for v in spec.get("values", [])]
        labels = [q(v) for v in spec.get("labels", [str(i + 1) for i in range(len(vals))])]
        lines += [f"vals={m_array(vals)};", "bar(ax,vals,0.66,'FaceColor',[0.1216 0.3059 0.4745],'EdgeColor','none');", f"ax.XTick=1:numel(vals); ax.XTickLabel={{{','.join(repr(v) for v in labels)}}};"]
    else:
        z = [[number(v) for v in row] for row in spec.get("z", [])]
        matrix = "[" + ";".join(" ".join(f"{v:.15g}" for v in row) for row in z) + "]"
        lines.append(f"Z={matrix};")
        if kind == "heatmap":
            lines += ["imagesc(ax,Z); axis(ax,'tight'); set(ax,'YDir','normal');", "colormap(ax,parula(256)); cb=colorbar(ax); cb.LineWidth=0.7;"]
        else:
            x = [number(v) for v in spec.get("x", list(range(1, len(z[0]) + 1)))]
            y = [number(v) for v in spec.get("y", list(range(1, len(z) + 1)))]
            lines += [f"x={m_array(x)}; y={m_array(y)}; [X,Y]=meshgrid(x,y);"]
            if kind == "surface3d":
                lines += ["surf(ax,X,Y,Z,'EdgeColor','none');", "view(ax,42,28); grid(ax,'on'); colormap(ax,parula(256)); colorbar(ax);"]
            else:
                lines += ["contourf(ax,X,Y,Z,16,'LineColor','none');", "colormap(ax,parula(256)); colorbar(ax);"]
    if title and bool(spec.get("show_title", False)):
        lines.append(f"title(ax,'{title}','FontWeight','normal','FontSize',9.8);")
    if xlabel:
        lines.append(f"xlabel(ax,'{xlabel}','FontSize',9);")
    if ylabel:
        lines.append(f"ylabel(ax,'{ylabel}','FontSize',9);")
    if zlabel and kind == "surface3d":
        lines.append(f"zlabel(ax,'{zlabel}','FontSize',9);")
    threshold = spec.get("threshold")
    if threshold is not None and kind in {"line2d", "scatter2d", "trajectory2d"}:
        threshold_value = number(threshold)
        threshold_label = q(spec.get("threshold_label", f"判停阈值 = {threshold_value:g}"))
        lines.append(f"yline(ax,{threshold_value:.15g},':','{threshold_label}','Color',[0.28 0.28 0.28],'LineWidth',0.8,'LabelHorizontalAlignment','left','FontName','Microsoft YaHei','FontSize',7.8);")
    if legend_names:
        names = ",".join(repr(name) for name in legend_names)
        lines.append(f"lgd=legend(ax,{{{names}}},'Location','northeast','Box','off','FontSize',8);")
        lines.append("try; lgd.ItemTokenSize=[14 8]; catch; end;")
    xlim_spec = spec.get("xlim")
    ylim_spec = spec.get("ylim")
    if isinstance(xlim_spec, list) and len(xlim_spec) == 2:
        lines.append(f"xlim(ax,{m_array([number(xlim_spec[0]), number(xlim_spec[1])])});")
    elif all_x:
        xmin, xmax = min(all_x), max(all_x)
        span = xmax - xmin
        pad = span * 0.035 if span > 0 else max(abs(xmin) * 0.035, 0.15)
        lines.append(f"xlim(ax,[{xmin - pad:.15g} {xmax + pad:.15g}]);")
    if isinstance(ylim_spec, list) and len(ylim_spec) == 2:
        lines.append(f"ylim(ax,{m_array([number(ylim_spec[0]), number(ylim_spec[1])])});")
    elif all_y:
        low = min(all_y + ([number(threshold)] if threshold is not None else []))
        high = max(all_y)
        span = high - low
        pad = span * 0.065 if span > 0 else max(abs(low) * 0.05, 0.025)
        lower = 0.0 if bool(spec.get("include_zero_y", False)) and low >= 0 else low - pad
        lines.append(f"ylim(ax,[{lower:.15g} {high + pad:.15g}]);")
    xticks_spec = spec.get("xticks")
    yticks_spec = spec.get("yticks")
    if isinstance(xticks_spec, list) and xticks_spec:
        lines.append(f"xticks(ax,{m_array([number(value) for value in xticks_spec])});")
    if isinstance(yticks_spec, list) and yticks_spec:
        lines.append(f"yticks(ax,{m_array([number(value) for value in yticks_spec])});")
    for ann in spec.get("annotations", []) if isinstance(spec.get("annotations"), list) else []:
        if not isinstance(ann, dict):
            continue
        x, y, text = number(ann.get("x")), number(ann.get("y")), q(ann.get("text", ""))
        dx, dy = number(ann.get("dx"), 0.65), number(ann.get("dy"), 0.08)
        lines.append(f"text(ax,{x + dx:.15g},{y + dy:.15g},'{text}','FontName','Microsoft YaHei','FontSize',7.8,'Color',[0.18 0.18 0.18],'HorizontalAlignment','left');")
        if bool(ann.get("arrow", True)):
            lines.append(f"plot(ax,[{x + dx * 0.82:.15g} {x:.15g}],[{y + dy * 0.75:.15g} {y:.15g}],'-','Color',[0.35 0.35 0.35],'LineWidth',0.65,'HandleVisibility','off');")
    lines += [
        f"set(fig,'Units','centimeters','Position',[2 2 {width:.3f} {height:.3f}],'PaperUnits','centimeters','PaperPosition',[0 0 {width:.3f} {height:.3f}],'PaperSize',[{width:.3f} {height:.3f}]);",
        f"print(fig,'{matlab_path(out_dir / (base + '.pdf'))}','-dpdf','-painters');",
        f"print(fig,'{matlab_path(out_dir / (base + '.svg'))}','-dsvg');",
        f"exportgraphics(fig,'{matlab_path(out_dir / (base + '.png'))}','Resolution',450,'BackgroundColor','white');",
        "close(fig);",
    ]
    return "\n".join(lines) + "\n"


@mcp.tool()
def health_check() -> str:
    """Verify the configured MATLAB executable and report the publication style preset."""
    command = [str(MATLAB_EXE), "-batch", "fprintf('VERSION=%s\\n',version); fprintf('RELEASE=%s\\n',version('-release')); fprintf('EXPORTGRAPHICS=%d\\n',exist('exportgraphics','file')); "]
    result = run_process(command, Path.cwd(), timeout=MATLAB_HEALTH_TIMEOUT_SECONDS)
    return json_result(ok=result["returncode"] == 0, matlab=str(MATLAB_EXE), style=STYLE, process=result)


@mcp.tool()
def render_figure(spec: dict[str, Any], output_dir: str = "", basename: str = "matlab_figure") -> str:
    """Render a structured award-paper figure to vector PDF/SVG, PNG preview, .m source and JSON data. Supports quantitative annotations and threshold evidence."""
    ok, errors = validate_spec(spec)
    if not ok:
        return json_result(ok=False, errors=errors)
    out = ensure_dir(output_dir)
    base = safe_basename(basename, "matlab_figure")
    spec_path, script_path = out / f"{base}.json", out / f"{base}.m"
    json_dump(spec_path, spec)
    script_path.write_text(build_script(spec, out, base), encoding="utf-8")
    process = run_process(
        [str(MATLAB_EXE), "-batch", f"run('{matlab_path(script_path)}')"],
        out,
        timeout=MATLAB_RENDER_TIMEOUT_SECONDS,
    )
    outputs = [out / f"{base}{ext}" for ext in (".pdf", ".svg", ".png", ".m", ".json")]
    return json_result(ok=process["returncode"] == 0 and all(p.exists() for p in outputs[:3]), files=file_manifest(outputs), process=process)


@mcp.tool()
def run_script(script: str, output_dir: str = "", basename: str = "custom_matlab") -> str:
    """Run explicit MATLAB code non-interactively and preserve source plus execution log."""
    out = ensure_dir(output_dir)
    base = safe_basename(basename, "custom_matlab")
    source = out / f"{base}.m"
    source.write_text(script, encoding="utf-8")
    process = run_process(
        [str(MATLAB_EXE), "-batch", f"run('{matlab_path(source)}')"],
        out,
        timeout=MATLAB_RENDER_TIMEOUT_SECONDS,
    )
    log = out / f"{base}.log.json"
    json_dump(log, process)
    return json_result(ok=process["returncode"] == 0, files=file_manifest([source, log]), process=process)


@mcp.tool()
def render_scene3d(spec: dict[str, Any], output_dir: str = "", basename: str = "matlab_scene3d") -> str:
    """Render structured 3D engineering geometry: axes, points, polylines/trajectories, Bezier curves, spheres, cylinders, sightline bundles and text labels. Exports .m/.json/PDF/SVG/PNG."""
    out = ensure_dir(output_dir)
    base = safe_basename(basename, "matlab_scene3d")
    spec_path, script_path = out / f"{base}.json", out / f"{base}.m"
    json_dump(spec_path, spec)
    lines = [
        "set(groot,'defaultFigureColor','w'); set(groot,'defaultAxesFontName','Microsoft YaHei','defaultTextFontName','Microsoft YaHei');",
        "fig=figure('Visible','off','Units','centimeters','Position',[2 2 15.5 9.5]); ax=axes(fig,'Position',[0.05 0.05 0.90 0.90]); hold(ax,'on'); axis(ax,'equal'); axis(ax,'off'); view(ax,38,23);",
        "primary=[0.1216 0.3059 0.4745]; accent=[0.7725 0.3529 0.0667]; gray=[0.35 0.35 0.35];",
    ]
    for el in spec.get("elements", []):
        if not isinstance(el, dict):
            continue
        kind = str(el.get("type", "point")); color = str(el.get("color", "primary"))
        if kind in {"polyline3d", "trajectory3d", "sightline_bundle"}:
            pts = el.get("points", [])
            if len(pts) >= 2:
                xs=m_array([number(p[0]) for p in pts]); ys=m_array([number(p[1]) for p in pts]); zs=m_array([number(p[2]) for p in pts])
                style = "--" if kind == "trajectory3d" or el.get("dashed") else "-"
                width = number(el.get("line_width"), 1.2)
                lines.append(f"plot3(ax,{xs},{ys},{zs},'{style}','Color',{color},'LineWidth',{width:.6g});")
                if bool(el.get("arrow", False)):
                    a,b=pts[-2],pts[-1]; lines.append(f"quiver3(ax,{number(a[0]):.8g},{number(a[1]):.8g},{number(a[2]):.8g},{number(b[0])-number(a[0]):.8g},{number(b[1])-number(a[1]):.8g},{number(b[2])-number(a[2]):.8g},0,'Color',{color},'LineWidth',{width:.6g},'MaxHeadSize',0.5);")
        elif kind == "bezier3d":
            cps=el.get("points", [])
            if len(cps)==4:
                rows=";".join(" ".join(f"{number(v):.8g}" for v in p[:3]) for p in cps)
                lines += [f"P=[{rows}]; t=linspace(0,1,120)'; B=(1-t).^3.*P(1,:)+3*(1-t).^2.*t.*P(2,:)+3*(1-t).*t.^2.*P(3,:)+t.^3.*P(4,:);", f"plot3(ax,B(:,1),B(:,2),B(:,3),'--','Color',{color},'LineWidth',{number(el.get('line_width'),1.1):.6g});"]
        elif kind == "point3d":
            p=el.get("at",[0,0,0]); lines.append(f"scatter3(ax,{number(p[0]):.8g},{number(p[1]):.8g},{number(p[2]):.8g},{number(el.get('size'),32):.8g},{color},'filled');")
        elif kind == "sphere3d":
            c=el.get("center",[0,0,0]); r=number(el.get("radius"),1)
            lines += ["[sx,sy,sz]=sphere(48);", f"surf(ax,{number(c[0]):.8g}+{r:.8g}*sx,{number(c[1]):.8g}+{r:.8g}*sy,{number(c[2]):.8g}+{r:.8g}*sz,'FaceColor',[0.55 0.58 0.62],'EdgeColor','none','FaceAlpha',0.92); camlight headlight; lighting gouraud;"]
        elif kind == "cylinder3d":
            c=el.get("center",[0,0,0]); r=number(el.get("radius"),0.35); h=number(el.get("height"),1.2)
            lines += [f"[cx,cy,cz]=cylinder({r:.8g},40);", f"surf(ax,{number(c[0]):.8g}+cx,{number(c[1]):.8g}+cy,{number(c[2])-h/2:.8g}+{h:.8g}*cz,'FaceColor',[0.92 0.92 0.92],'EdgeColor',[0.35 0.35 0.35]);"]
        elif kind == "text3d":
            p=el.get("at",[0,0,0]); text=q(el.get("text","")); lines.append(f"text(ax,{number(p[0]):.8g},{number(p[1]):.8g},{number(p[2]):.8g},'{text}','FontSize',8.5,'Color',[0.1 0.1 0.1]);")
        elif kind == "axis3d":
            o=el.get("origin",[0,0,0]); s=number(el.get("scale"),1)
            lines += [f"quiver3(ax,{number(o[0]):.8g},{number(o[1]):.8g},{number(o[2]):.8g},{s:.8g},0,0,0,'Color',gray,'MaxHeadSize',0.25);", f"quiver3(ax,{number(o[0]):.8g},{number(o[1]):.8g},{number(o[2]):.8g},0,{s:.8g},0,0,'Color',gray,'MaxHeadSize',0.25);", f"quiver3(ax,{number(o[0]):.8g},{number(o[1]):.8g},{number(o[2]):.8g},0,0,{s:.8g},0,'Color',gray,'MaxHeadSize',0.25);", f"text(ax,{number(o[0])+s:.8g},{number(o[1]):.8g},{number(o[2]):.8g},'x'); text(ax,{number(o[0]):.8g},{number(o[1])+s:.8g},{number(o[2]):.8g},'y'); text(ax,{number(o[0]):.8g},{number(o[1]):.8g},{number(o[2])+s:.8g},'z');"]
    lines += [f"exportgraphics(fig,'{matlab_path(out / (base+'.pdf'))}','ContentType','vector','BackgroundColor','white');", f"print(fig,'{matlab_path(out / (base+'.svg'))}','-dsvg');", f"exportgraphics(fig,'{matlab_path(out / (base+'.png'))}','Resolution',450,'BackgroundColor','white');", "close(fig);"]
    script_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    process=run_process(
        [str(MATLAB_EXE),"-batch",f"run('{matlab_path(script_path)}')"],
        out,
        timeout=MATLAB_RENDER_TIMEOUT_SECONDS,
    )
    files=[out/f"{base}{ext}" for ext in (".pdf",".svg",".png",".m",".json")]
    return json_result(ok=process["returncode"]==0 and all(p.exists() for p in files[:3]),files=file_manifest(files),process=process)


if __name__ == "__main__":
    mcp.run()
