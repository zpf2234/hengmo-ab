from __future__ import annotations

import json
from pathlib import Path
import fitz
import tikz_server

OUT=Path(__file__).resolve().parent/'pixel_fidelity_outputs'; OUT.mkdir(parents=True,exist_ok=True)
S=0.02

def xy(x,y,h): return f"({x*S:.4f},{(h-y)*S:.4f})"
def box(x1,y1,x2,y2,h): return xy(x1,y1,h),xy(x2,y2,h)
def line(p1,p2,h,style='black!70,line width=.45pt',arrow=''):
    return f"\\draw[{style}{','+arrow if arrow else ''}] {xy(*p1,h)} -- {xy(*p2,h)};"
def node(x,y,h,text,opts='font=\\scriptsize'):
    return f"\\node[{opts}] at {xy(x,y,h)} {{{text}}};"

def compile(name,body,w,h):
    bb=f"\\path[use as bounding box] (0,0) rectangle ({w*S:.4f},{h*S:.4f});\n"
    result=json.loads(tikz_server.compile_tikz(bb+body,str(OUT),name,border_pt=0))
    if result.get('ok'):
        d=fitz.open(OUT/f'{name}.pdf')
        # exact screenshot pixel dimensions for direct overlay / SSIM
        matrix=fitz.Matrix(w/d[0].rect.width,h/d[0].rect.height)
        d[0].get_pixmap(matrix=matrix,alpha=False).save(str(OUT/f'{name}.png'))
    return result

# ---------- Reference 1: 791 x 427 ----------
W,H=791,427
b=[]
# water, behind bodies
b.append(r"\draw[draw=blue!65!black,line width=.62pt] plot[domain=3.25:12.25,samples=260] (\x,{4.98+.095*sin(280*(\x-3.25))});")
# float bodies precisely on reference pixel boxes
p1,p2=box(234,131,350,288,H); b.append(f"\\filldraw[fill=blue!14,draw=black!48,line width=.42pt] {p1} rectangle {p2};")
b.append(f"\\filldraw[fill=blue!62!black,draw=black!55,line width=.42pt] {xy(234,288,H)} -- {xy(350,288,H)} -- {xy(293,363,H)} -- cycle;")
p1,p2=box(430,132,547,287,H); b.append(f"\\filldraw[fill=blue!14,draw=black!48,line width=.42pt] {p1} rectangle {p2};")
b.append(f"\\filldraw[fill=blue!62!black,draw=black!55,line width=.42pt] {xy(430,287,H)} -- {xy(547,287,H)} -- {xy(490,362,H)} -- cycle;")
# wave visible across scene as in screenshot
b.append(r"\draw[draw=blue!65!black,line width=.62pt] plot[domain=3.25:12.25,samples=260] (\x,{4.98+.095*sin(280*(\x-3.25))});")
# heave double arrow at exact red component
b.append(line((198,127),(198,189),H,'draw=red!72!black,line width=.78pt','{Stealth[length=1.6mm]}-{Stealth[length=1.6mm]}'))
b.append(node(176,158,H,'垂荡','font=\\scriptsize,rotate=90'))
# left axes/G
b.append(line((293,207),(293,84),H,'draw=black!55,line width=.42pt','->'))
b.append(line((293,207),(388,207),H,'draw=black!55,line width=.42pt','->'))
b.append(rf"\fill {xy(293,207,H)} circle (.030);" )
b.append(node(284,217,H,'$G$'))
b.append(node(311,94,H,'$X_1(t)$'))
b.append(node(386,219,H,'$t$'))
# left forces exact component positions
for a,c,lbl,lx,ly in [((292,153),(292,124),'$f_e$',306,116),((271,185),(271,213),'$f_{cx}$',255,205),((315,185),(315,213),'$f_r$',330,203),((358,153),(358,126),'$Ma$',374,119)]:
    b.append(line(a,c,H,'draw=red!72!black,line width=.75pt','->')); b.append(node(lx,ly,H,lbl))
# right displacement
b.append(line((520,230),(520,203),H,'draw=black!50,line width=.43pt','->')); b.append(node(546,197,H,'$X_r(t)$'))
# internal mass block on exact visible bbox
p1,p2=box(443,225,540,274,H); b.append(f"\\filldraw[fill=white,draw=black!52,line width=.42pt] {p1} rectangle {p2};")
b.append(line((489,249),(530,249),H,'draw=black!45,line width=.38pt','->')); b.append(node(537,256,H,'$t$'))
# ma upward
b.append(line((489,249),(489,169),H,'draw=red!72!black,line width=.75pt','->')); b.append(node(504,174,H,'$ma$'))
# spring and damper exact compact lower assembly
# spring path pixels
pts=[(468,274),(468,280),(474,284),(462,290),(474,296),(462,302),(474,308),(462,314),(468,320)]
b.append('\\draw[black!60,line width=.42pt] '+' -- '.join(xy(x,y,H) for x,y in pts)+';')
b.extend([line((511,274),(511,282),H,'draw=black!60,line width=.42pt'),line((501,282),(521,282),H,'draw=black!60,line width=.42pt'),line((501,282),(501,304),H,'draw=black!60,line width=.42pt'),line((521,282),(521,304),H,'draw=black!60,line width=.42pt'),line((511,293),(511,320),H,'draw=black!60,line width=.42pt'),line((456,320),(524,320),H,'draw=black!60,line width=.42pt')])
b.append(node(450,294,H,'$K_h$')); b.append(node(532,294,H,'$C_h$'))
# PTO/reaction arrows matching original compact bottom
for x,lbl,lx in [(481,'$f_h$',468),(499,'$f_{Ch}$',518)]:
    b.append(line((x,248),(x,276),H,'draw=red!72!black,line width=.72pt','->')); b.append(node(lx,279,H,lbl))
b.append(line((490,248),(490,276),H,'draw=red!72!black,line width=.72pt','->')); b.append(node(490,288,H,'$f_{PTO}$','font=\\tiny,fill=none,inner sep=.6pt'))
# caption at reference bbox y388-408
b.append(node(388,399,H,'图 2\quad 垂荡运动受力分析示意图','font=\\bfseries\\small'))
res1=compile('pixel_ref1_heave','\n'.join(b),W,H)

# ---------- Reference 2: 963 x 443 ----------
W,H=963,443; b=[]
# axes exact Hough endpoints: origin (283,362)
b.append(line((283,362),(167,432),H,'draw=black!42,line width=.38pt','->')); b.append(node(159,433,H,'$x$'))
b.append(line((283,362),(653,362),H,'draw=black!42,line width=.38pt','->')); b.append(node(662,362,H,'$y$'))
b.append(line((283,362),(283,87),H,'draw=black!42,line width=.38pt','->')); b.append(node(283,77,H,'$z$'))
b.append(node(287,378,H,'假目标 $O$','font=\\tiny,fill=none,inner sep=.5pt'))
# missile point approx (205,114), trajectory to O
b.append(rf"\fill {xy(205,114,H)} circle (.032);"); b.append(node(197,91,H,'导弹 $M_j$','font=\\tiny'))
b.append(rf"\draw[->,draw=black!42,dashed,line width=.42pt] {xy(205,114,H)} .. controls {xy(235,200,H)} and {xy(270,300,H)} .. {xy(283,362,H)};")
b.append(node(218,248,H,'导弹轨迹','font=\\tiny,fill=none,inner sep=.5pt'))
# LOS bundle exact lines to target
b.append(line((205,114),(727,383),H,'draw=black!58,line width=.58pt'))
b.append(line((214,107),(718,376),H,'draw=black!48,line width=.36pt'))
b.append(node(440,264,H,'目标视线束','font=\\tiny,fill=none,inner sep=.5pt,rotate=-27'))
# UAV symbol around (400,138), source-like small
b.append(r"\begin{scope}[shift={(8.02,6.10)},rotate=-12,scale=.55]\draw[black!60,line width=.45pt](-.33,-.10)rectangle(.33,.10);\draw[black!60,line width=.45pt](-.08,-.34)rectangle(.08,.34);\draw[black!60,line width=.45pt](.33,0)--(.48,0);\end{scope}")
b.append(line((401,126),(401,102),H,'draw=black!35,line width=.32pt')); b.append(node(401,89,H,'无人机 $FY_i$','font=\\tiny'))
# flight / release path (400,145)->(585,269)
b.append(rf"\draw[->,draw=black!40,dashed,line width=.38pt] {xy(400,145,H)} .. controls {xy(465,135,H)} and {xy(530,180,H)} .. {xy(585,269,H)};")
b.append(node(528,129,H,'等高直线航迹','font=\\tiny,fill=none,inner sep=.5pt'))
b.append(rf"\fill {xy(470,183,H)} circle (.026);"); b.append(node(468,204,H,'投放点 $R$','font=\\tiny,fill=none,inner sep=.5pt'))
# red smoke exact bbox x553..614,y253..314 center 583.5,283.5 r30.5
b.append(rf"\fill[gray!10] {xy(583.5,283.5,H)} circle ({30.5*S:.4f});")
b.append(rf"\draw[red!70!black,line width=.62pt] {xy(583.5,283.5,H)} circle ({30.5*S:.4f});")
b.append(rf"\fill[gray!35] {xy(583,267,H)} circle (.026);")
b.append(line((583,267),(630,242),H,'draw=black!35,line width=.30pt')); b.append(node(651,238,H,'起爆点 $B$','font=\\tiny'))
b.append(node(548,323,H,'有效烟幕弹','font=\\tiny,fill=none,inner sep=.5pt'))
b.append(line((583,286),(583,349),H,'draw=red!70!black,line width=.62pt','->')); b.append(node(606,340,H,'下沉','font=\\tiny,text=red!65!black,fill=none,inner sep=.5pt'))
# target cylinder exact bbox ~651..730,335..384
b.extend([line((651,337),(651,383),H,'draw=black!50,line width=.36pt'),line((729,337),(729,383),H,'draw=black!50,line width=.36pt')])
b.append(rf"\draw[black!50,line width=.36pt] {xy(690,337,H)} ellipse [x radius={39*S:.4f},y radius={7*S:.4f}];")
b.append(rf"\draw[black!50,line width=.36pt] {xy(651,383,H)} arc[start angle=180,end angle=360,x radius={39*S:.4f},y radius={7*S:.4f}];")
b.append(rf"\draw[black!35,dashed,line width=.30pt] {xy(729,383,H)} arc[start angle=0,end angle=180,x radius={39*S:.4f},y radius={7*S:.4f}];")
b.append(line((658,344),(722,379),H,'draw=black!38,line width=.30pt')); b.append(node(690,414,H,'真目标圆柱','font=\\tiny'))
res2=compile('pixel_ref2_scene','\n'.join(b),W,H)

# ---------- Reference 3: 566 x 308 ----------
W,H=566,308; b=[]
# exact screenshot geometry P1=(151,103), sphere C=(255,183), r=47, cylinder center=(360,266)
# fixed P1 marker and label
b.append(rf"\fill {xy(151,103,H)} circle (.032);"); b.append(node(132,95,H,'$P_1$','font=\\small'))
# exact apparent ray directions from Hough (top to 409,180; bottom to 273,305)
b.append(line((151,103),(409,180),H,'draw=black!72,line width=.46pt','->'))
b.append(line((151,103),(273,305),H,'draw=black!72,line width=.46pt','->'))
# center axis exact to P2
b.append(line((151,103),(368,270),H,'draw=black!48,dashed,line width=.42pt'))
# sphere center/radius exact detected
b.append(rf"\shade[ball color=gray!38,draw=black!62,line width=.44pt] {xy(255,183,H)} circle ({47*S:.4f});")
b.append(rf"\fill {xy(255,183,H)} circle (.024);"); b.append(node(267,191,H,'$C$','font=\\small'))
b.append(line((255,183),(284,146),H,'draw=black!60,line width=.40pt','->')); b.append(node(273,161,H,'$r$','font=\\small'))
# cylinder exact x333..388, y242..298; center projection point on dashed line
b.extend([line((333,249),(333,289),H,'draw=black!60,line width=.38pt'),line((388,249),(388,289),H,'draw=black!60,line width=.38pt')])
b.append(rf"\draw[black!60,line width=.38pt] {xy(360.5,249,H)} ellipse [x radius={27.5*S:.4f},y radius={7*S:.4f}];")
b.append(rf"\draw[black!60,line width=.38pt] {xy(333,289,H)} arc[start angle=180,end angle=360,x radius={27.5*S:.4f},y radius={7*S:.4f}];")
b.append(rf"\draw[black!40,dashed,line width=.30pt] {xy(388,289,H)} arc[start angle=0,end angle=180,x radius={27.5*S:.4f},y radius={7*S:.4f}];")
b.append(rf"\fill {xy(360,264,H)} circle (.025);"); b.append(node(382,294,H,'$P_2$','font=\\small'))
res3=compile('pixel_ref3_projection','\n'.join(b),W,H)
print(json.dumps({'ref1':res1.get('ok'),'ref2':res2.get('ok'),'ref3':res3.get('ok')},ensure_ascii=False,indent=2))
raise SystemExit(0 if all(x.get('ok') for x in (res1,res2,res3)) else 1)
