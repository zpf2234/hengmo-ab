from __future__ import annotations

import json
import math
from pathlib import Path

import fitz

import tikz_server

OUT = Path(__file__).resolve().parent / "fidelity_outputs"
OUT.mkdir(parents=True, exist_ok=True)


def tangent_points(px: float, py: float, cx: float, cy: float, r: float):
    dx, dy = px - cx, py - cy
    d2 = dx * dx + dy * dy
    base_x = cx + r * r * dx / d2
    base_y = cy + r * r * dy / d2
    factor = r * math.sqrt(d2 - r * r) / d2
    return (
        (base_x - factor * dy, base_y + factor * dx),
        (base_x + factor * dy, base_y - factor * dx),
    )


def ray_endpoint(p, t, length=9.0):
    vx, vy = t[0] - p[0], t[1] - p[1]
    norm = math.hypot(vx, vy)
    return p[0] + length * vx / norm, p[1] + length * vy / norm


# 参考图 1：完全按原图的双浮体、外部受力和内部 PTO 结构组织，不擅自改物理符号。
heave_body = r"""
% water surface behind structures
\draw[draw=blue!72!black,line width=1.05pt]
  plot[domain=0.15:11.85,samples=240] (\x,{3.02+0.115*sin(255*(\x-0.15))});

% left and right floating bodies
\filldraw[fill=blue!16,draw=black!65,line width=.65pt] (2.05,1.55) rectangle (4.25,5.02);
\filldraw[fill=blue!78!black,draw=black!65,line width=.65pt] (2.05,1.55) -- (4.25,1.55) -- (3.15,.35) -- cycle;
\filldraw[fill=blue!16,draw=black!65,line width=.65pt] (7.35,1.55) rectangle (9.55,5.02);
\filldraw[fill=blue!78!black,draw=black!65,line width=.65pt] (7.35,1.55) -- (9.55,1.55) -- (8.45,.35) -- cycle;

% redraw water outside and across hulls, matching source line hierarchy
\draw[draw=blue!72!black,line width=1.05pt]
  plot[domain=0.15:11.85,samples=240] (\x,{3.02+0.115*sin(255*(\x-0.15))});

% heave indicator
\draw[draw=red!78!black,line width=1.05pt,{Stealth[length=2.2mm]}-{Stealth[length=2.2mm]}] (.65,1.72) -- (.65,4.36);
\node[rotate=90,font=\small] at (.30,3.05) {垂荡};

% left-body reference axes exactly as reference
\draw[->,draw=black!65,line width=.60pt] (3.15,2.72) -- (3.15,5.55);
\draw[->,draw=black!65,line width=.60pt] (3.15,2.72) -- (4.88,2.72);
\node[font=\small] at (3.48,5.35) {$X_1(t)$};
\node[font=\small] at (4.78,2.48) {$t$};
\fill (3.15,2.72) circle (.045); \node[font=\small] at (2.94,2.47) {$G$};

% left-body forces, with source labels and opposing directions
\draw[->,draw=red!78!black,line width=1.05pt] (2.65,3.20) -- (2.65,4.78);
\node[font=\small] at (2.40,4.60) {$f_e$};
\draw[->,draw=red!78!black,line width=1.05pt] (3.38,4.42) -- (3.38,3.12);
\node[font=\small] at (3.72,3.90) {$f_{cx}$};
\draw[->,draw=red!78!black,line width=1.05pt] (3.92,4.18) -- (3.92,3.03);
\node[font=\small] at (4.18,3.58) {$f_r$};
\draw[->,draw=red!78!black,line width=1.05pt] (4.48,3.35) -- (4.48,4.72);
\node[font=\small] at (4.75,4.52) {$Ma$};

% right-body displacement indicator
\draw[->,draw=black!55,line width=.70pt] (9.82,3.05) -- (9.82,4.72);
\node[font=\small] at (10.24,4.54) {$X_r(t)$};

% internal oscillator mass block
\filldraw[fill=white,draw=black!60,line width=.65pt] (7.82,2.02) rectangle (9.08,2.96);
\draw[->,draw=black!55,line width=.55pt] (8.45,2.50) -- (9.18,2.50);
\node[font=\scriptsize] at (9.09,2.30) {$t$};
\draw[->,draw=red!78!black,line width=1.0pt] (8.44,2.28) -- (8.44,3.68);
\node[font=\small] at (8.73,3.50) {$ma$};

% parallel spring-damper assembly, connected to the same mass and base
\draw[black!70,line width=.65pt] (8.02,2.02) -- (8.02,1.87);
\draw[black!70,line width=.65pt] (8.02,1.87) -- (8.13,1.79) -- (7.91,1.69) -- (8.13,1.59) -- (7.91,1.49) -- (8.13,1.39) -- (7.91,1.29) -- (8.13,1.19) -- (8.02,1.10);
\draw[black!70,line width=.65pt] (8.84,2.02) -- (8.84,1.78);
\draw[black!70,line width=.65pt] (8.66,1.78) -- (9.02,1.78) -- (9.02,1.39) -- (8.66,1.39);
\draw[black!70,line width=.65pt] (8.84,1.59) -- (8.84,1.10);
\draw[black!70,line width=.65pt] (7.75,1.10) -- (9.12,1.10);
\node[font=\scriptsize,fill=none,inner sep=.8pt] at (7.72,1.48) {$K_h$};
\node[font=\scriptsize,fill=none,inner sep=.8pt] at (9.17,1.48) {$C_h$};

% PTO and lower reaction forces, each with explicit action arrow
\draw[->,draw=red!78!black,line width=1.0pt] (8.14,1.42) -- (8.14,.66);
\node[font=\scriptsize,fill=none,inner sep=.8pt] at (7.72,.80) {$f_h$};
\draw[->,draw=red!78!black,line width=1.0pt] (8.76,1.42) -- (8.76,.66);
\node[font=\scriptsize,fill=none,inner sep=.8pt] at (9.18,.80) {$f_{Ch}$};
\draw[->,draw=red!78!black,line width=1.0pt] (8.45,2.00) -- (8.45,1.28);
\node[font=\scriptsize,fill=none,inner sep=.8pt] at (8.45,1.82) {$f_{PTO}$};

\node[font=\bfseries\small] at (5.95,-.40) {图2\quad 垂荡运动受力分析示意图};
"""

# 参考图 2：使用 2.5D TikZ 精确控制屏幕投影、符号、层级和遮挡。
scene_body = r"""
% axes in background: x down-left, y right, z up
\coordinate (O) at (2.15,1.10);
\draw[->,draw=black!45,line width=.55pt] (O) -- (.55,.12) node[below] {$x$};
\draw[->,draw=black!45,line width=.55pt] (O) -- (10.85,1.10) node[right] {$y$};
\draw[->,draw=black!45,line width=.55pt] (O) -- (2.15,5.20) node[above] {$z$};
\node[font=\scriptsize,fill=none,inner sep=1pt] at (2.38,.83) {假目标 $O$};

% missile symbol and dashed trajectory
\fill (1.12,4.85) circle (.055); \node[font=\scriptsize] at (.78,5.16) {导弹 $M_j$};
\draw[->,draw=black!45,dashed,line width=.70pt] (1.12,4.85) .. controls (1.35,3.70) and (1.78,2.20) .. (2.15,1.10);
\node[font=\scriptsize,fill=none,inner sep=1pt] at (1.20,3.00) {导弹轨迹};

% target LOS bundle: two close straight rays
\draw[draw=black!68,line width=.90pt] (1.12,4.85) -- (9.45,1.62);
\draw[draw=black!55,line width=.55pt] (1.17,4.94) -- (9.48,1.80);
\node[font=\scriptsize,fill=none,inner sep=1pt,rotate=-20] at (4.80,3.27) {目标视线束};

% UAV line-art icon: tilted fuselage and wing
\begin{scope}[shift={(4.35,4.53)},rotate=-12]
  \draw[black!70,line width=.55pt] (-.33,-.10) rectangle (.33,.10);
  \draw[black!70,line width=.55pt] (-.08,-.34) rectangle (.08,.34);
  \draw[black!70,line width=.55pt] (.33,0) -- (.48,0);
\end{scope}
\draw[black!40,line width=.45pt] (4.35,4.86) -- (4.35,5.12);
\node[font=\scriptsize] at (4.35,5.30) {无人机 $FY_i$};

% level flight and released-object trajectory
\draw[->,draw=black!45,dashed,line width=.60pt] (4.35,4.53) .. controls (5.25,4.72) and (6.25,4.56) .. (7.12,3.45);
\node[font=\scriptsize,fill=none,inner sep=1pt] at (6.12,4.70) {等高直线航迹};
\fill (5.30,4.50) circle (.042); \node[font=\scriptsize,fill=none,inner sep=1pt] at (5.30,4.20) {投放点 $R$};

% effective smoke region, detonation point and guide
\fill[gray!13] (7.12,3.03) circle (.58);
\draw[draw=red!75!black,line width=.95pt] (7.12,3.03) circle (.58);
\fill[gray!35] (7.12,3.38) circle (.045);
\draw[black!45,line width=.45pt] (7.12,3.38) -- (7.76,3.72);
\node[font=\scriptsize,fill=none,inner sep=1pt] at (8.00,3.86) {起爆点 $B$};
\node[font=\scriptsize,fill=none,inner sep=1pt] at (6.30,2.63) {有效烟幕弹};
\draw[->,draw=red!75!black,line width=1.0pt] (7.12,2.95) -- (7.12,1.78);
\node[font=\scriptsize,text=red!65!black,fill=none,inner sep=1pt] at (7.47,2.05) {下沉};

% true target cylinder with internal diagonal, placed over y-axis
\draw[black!65,line width=.60pt] (9.05,.62) -- (9.05,1.82);
\draw[black!65,line width=.60pt] (9.78,.62) -- (9.78,1.82);
\draw[black!65,line width=.60pt] (9.415,1.82) ellipse [x radius=.365,y radius=.14];
\draw[black!65,line width=.60pt] (9.05,.62) arc[start angle=180,end angle=360,x radius=.365,y radius=.14];
\draw[black!45,dashed,line width=.50pt] (9.78,.62) arc[start angle=0,end angle=180,x radius=.365,y radius=.14];
\draw[black!50,line width=.45pt] (9.10,1.65) -- (9.72,.78);
\node[font=\scriptsize,fill=none,inner sep=1pt] at (9.42,.30) {真目标圆柱};
"""

# Reference 3 with analytically exact tangent rays.
p1 = (1.05, 4.95)
c = (4.95, 2.85)
r = 1.10
t1, t2 = tangent_points(*p1, *c, r)
e1 = ray_endpoint(p1, t1, 8.5)
e2 = ray_endpoint(p1, t2, 8.5)
# Put P2 cylinder center exactly on the P1-C centerline extension.
vx, vy = c[0]-p1[0], c[1]-p1[1]
scale = 1.78
p2 = (p1[0]+scale*vx, p1[1]+scale*vy)
projection_body = rf"""
% exact analytical tangents from P1 to circle(C,r)
\coordinate (Pone) at ({p1[0]:.6f},{p1[1]:.6f});
\coordinate (C) at ({c[0]:.6f},{c[1]:.6f});
\fill (Pone) circle (.055); \node[font=\small] at ({p1[0]-0.32:.6f},{p1[1]+0.28:.6f}) {{$P_1$}};

% rays below sphere in z-order
\draw[->,black!80,line width=.72pt] (Pone) -- ({e1[0]:.6f},{e1[1]:.6f});
\draw[->,black!80,line width=.72pt] (Pone) -- ({e2[0]:.6f},{e2[1]:.6f});
\draw[black!58,dashed,line width=.62pt] (Pone) -- ({p2[0]:.6f},{p2[1]:.6f});

% shaded sphere covers hidden centerline, then centerline segment is lightly restored as internal construction
\shade[ball color=gray!42,draw=black!70,line width=.70pt] (C) circle ({r:.6f});
\draw[black!48,dashed,line width=.48pt] ({t1[0]:.6f},{t1[1]:.6f}) -- ({t2[0]:.6f},{t2[1]:.6f});
\fill (C) circle (.035); \node[font=\small,fill=none,inner sep=.6pt] at ({c[0]-0.18:.6f},{c[1]-0.12:.6f}) {{$C$}};
\draw[->,black!72,line width=.60pt] (C) -- ({c[0]+0.68:.6f},{c[1]+0.86:.6f});
\node[font=\small,fill=none,inner sep=.6pt] at ({c[0]+0.56:.6f},{c[1]+0.40:.6f}) {{$r$}};

% exact tangent contact markers, subtle
\fill[black!65] ({t1[0]:.6f},{t1[1]:.6f}) circle (.027);
\fill[black!65] ({t2[0]:.6f},{t2[1]:.6f}) circle (.027);

% P2 cylinder centered exactly on centerline extension
\draw[black!72,line width=.62pt] ({p2[0]-0.34:.6f},{p2[1]-0.58:.6f}) -- ({p2[0]-0.34:.6f},{p2[1]+0.58:.6f});
\draw[black!72,line width=.62pt] ({p2[0]+0.34:.6f},{p2[1]-0.58:.6f}) -- ({p2[0]+0.34:.6f},{p2[1]+0.58:.6f});
\draw[black!72,line width=.62pt] ({p2[0]:.6f},{p2[1]+0.58:.6f}) ellipse [x radius=.34,y radius=.13];
\draw[black!72,line width=.62pt] ({p2[0]-0.34:.6f},{p2[1]-0.58:.6f}) arc[start angle=180,end angle=360,x radius=.34,y radius=.13];
\draw[black!48,dashed,line width=.50pt] ({p2[0]+0.34:.6f},{p2[1]-0.58:.6f}) arc[start angle=0,end angle=180,x radius=.34,y radius=.13];
\fill ({p2[0]:.6f},{p2[1]:.6f}) circle (.032);
\node[font=\small] at ({p2[0]+0.55:.6f},{p2[1]-0.62:.6f}) {{$P_2$}};
"""


def compile_one(name: str, body: str):
    result = json.loads(tikz_server.compile_tikz(body, str(OUT), name))
    pdf = OUT / f"{name}.pdf"
    if result.get("ok") and pdf.exists():
        doc = fitz.open(pdf)
        doc[0].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).save(str(OUT / f"{name}.png"))
    return result


results = {
    "heave": compile_one("fidelity_ref1_heave", heave_body),
    "scene": compile_one("fidelity_ref2_scene", scene_body),
    "projection": compile_one("fidelity_ref3_projection", projection_body),
}
print(json.dumps({k: {"ok": v.get("ok"), "files": v.get("files", [])} for k, v in results.items()}, ensure_ascii=False, indent=2))
raise SystemExit(0 if all(v.get("ok") for v in results.values()) else 1)
