from __future__ import annotations
import json
from pathlib import Path
import fitz
import tikz_server, python_figure

OUT=Path(__file__).resolve().parent/'reference_outputs'; OUT.mkdir(parents=True,exist_ok=True)

heave={"elements":[
 {"type":"sine_wave","from":[0,2.7],"to":[13,2.7],"amplitude":0.13,"cycles":7,"style":"paperline"},
 {"type":"rectangle","from":[2,1.4],"to":[4.2,5.0],"style":"draw=paperblue,fill=paperfill,line width=0.8pt"},
 {"type":"polygon","points":[[2,1.4],[4.2,1.4],[3.1,0.2]],"style":"draw=paperblue,fill=paperblue!85"},
 {"type":"rectangle","from":[8,1.4],"to":[10.2,5.0],"style":"draw=paperblue,fill=paperfill,line width=0.8pt"},
 {"type":"polygon","points":[[8,1.4],[10.2,1.4],[9.1,0.2]],"style":"draw=paperblue,fill=paperblue!85"},
 {"type":"arrow","from":[0.8,1.6],"to":[0.8,4.2],"style":"draw=paperorange,line width=1.2pt,<->"},
 {"type":"node","at":[0.45,2.9],"text":"垂荡","options":"rotate=90"},
 {"type":"arrow","from":[3.1,2.5],"to":[3.1,5.5],"style":"draw=black!65"},
 {"type":"arrow","from":[3.1,2.5],"to":[4.8,2.5],"style":"draw=black!65"},
 {"type":"node","at":[3.35,5.35],"text":"$x_1(t)$","options":""},
 {"type":"node","at":[4.65,2.25],"text":"$t$","options":""},
 {"type":"node","at":[3.1,2.2],"text":"$G$","options":""},
 {"type":"arrow","from":[2.55,3.1],"to":[2.55,4.6],"style":"draw=paperorange,line width=1.2pt"},
 {"type":"node","at":[2.3,4.5],"text":"$f_e$","options":""},
 {"type":"arrow","from":[3.55,4.4],"to":[3.55,3.0],"style":"draw=paperorange,line width=1.2pt"},
 {"type":"node","at":[3.85,3.65],"text":"$f_r$","options":""},
 {"type":"rectangle","from":[8.45,2.0],"to":[9.75,3.05],"style":"draw=black!55,fill=white,line width=0.7pt"},
 {"type":"spring","from":[8.75,2.0],"to":[8.75,1.1],"style":"draw=black!70","coils":6},
 {"type":"damper","from":[9.45,2.0],"to":[9.45,1.1],"style":"draw=black!70"},
 {"type":"node","at":[8.45,1.35],"text":"$K_h$","options":""},
 {"type":"node","at":[9.78,1.35],"text":"$C_h$","options":""},
 {"type":"arrow","from":[9.1,2.35],"to":[9.1,3.7],"style":"draw=paperorange,line width=1.2pt"},
 {"type":"node","at":[9.35,3.55],"text":"$ma$","options":""},
 {"type":"node","at":[9.1,0.65],"text":"$f_{PTO}$","options":""},
 {"type":"node","at":[6.5,-0.35],"text":"图 2  垂荡运动受力分析示意图","options":"font=\\bfseries"}
]}

projection={"elements":[
 {"type":"sphere","center":[5.1,3.0],"radius":1.15,"color":"gray!38"},
 {"type":"circle","center":[1.1,5.45],"radius":0.055,"style":"draw=black,fill=black"},
 {"type":"node","at":[0.75,5.75],"text":"$P_1$","options":""},
 {"type":"line","from":[1.1,5.45],"to":[9.0,5.2],"style":"draw=black!80,->"},
 {"type":"line","from":[1.1,5.45],"to":[3.7,0.2],"style":"draw=black!80,->"},
 {"type":"line","from":[1.1,5.45],"to":[9.0,0.75],"style":"draw=black!70,dashed"},
 {"type":"node","at":[5.1,3.0],"text":"$C$","options":""},
 {"type":"arrow","from":[5.1,3.0],"to":[5.8,3.85],"style":"draw=black!75"},
 {"type":"node","at":[5.75,3.4],"text":"$r$","options":""},
 {"type":"cylinder","center":[8.25,1.0],"width":0.8,"height":1.3,"ellipse_height":0.16,"style":"draw=black!75,fill=white"},
 {"type":"node","at":[8.8,0.25],"text":"$P_2$","options":""}
]}

scene={"elements":[
 {"type":"axis3d","origin":[0,0,0],"scale":2.4},
 {"type":"point3d","at":[-1.2,1.3,3.1],"color":"gray","size":34},
 {"type":"text3d","at":[-1.35,1.3,3.35],"text":"导弹 M_j"},
 {"type":"trajectory3d","points":[[-1.2,1.3,3.1],[-0.9,0.9,2.3],[-0.4,0.35,1.0],[0,0,0]],"color":"gray","arrow":True},
 {"type":"text3d","at":[-0.65,0.6,1.9],"text":"导弹轨迹"},
 {"type":"sightline_bundle","points":[[-1.2,1.3,3.1],[3.7,3.2,0.7],[6.4,4.3,0.25]],"color":"gray","line_width":1.4},
 {"type":"sightline_bundle","points":[[-1.1,1.4,3.15],[3.8,3.35,0.82],[6.5,4.45,0.35]],"color":"gray","line_width":0.8},
 {"type":"text3d","at":[1.0,2.05,2.0],"text":"目标视线束"},
 {"type":"point3d","at":[1.0,2.5,2.7],"color":"primary","size":42},
 {"type":"text3d","at":[1.1,2.5,2.95],"text":"无人机 FY_i"},
 {"type":"bezier3d","points":[[1.0,2.5,2.7],[2.4,3.0,2.5],[3.2,3.1,1.4],[3.8,3.2,0.8]],"color":"gray","line_width":1.1},
 {"type":"point3d","at":[2.4,2.95,2.25],"color":"gray","size":28},
 {"type":"text3d","at":[2.5,2.95,2.35],"text":"投放点 R"},
 {"type":"point3d","at":[3.8,3.2,0.8],"color":"accent","size":60},
 {"type":"text3d","at":[4.0,3.2,1.0],"text":"起爆点 B"},
 {"type":"cylinder3d","center":[6.4,4.35,0.2],"radius":0.38,"height":1.2},
 {"type":"text3d","at":[6.6,4.4,0.8],"text":"真实目标"},
 {"type":"polyline3d","points":[[3.8,3.2,0.8],[3.8,3.2,-0.8]],"color":"accent","arrow":True},
 {"type":"text3d","at":[3.95,3.2,-0.15],"text":"下沉"}
]}

results={
 'heave':json.loads(tikz_server.render_geometry(heave,str(OUT),'ref1_heave_force')),
 'scene3d':python_figure.render_scene3d(scene,str(OUT),'ref2_uav_missile_scene'),
 'projection':json.loads(tikz_server.render_geometry(projection,str(OUT),'ref3_sphere_projection')),
}
for name in ('ref1_heave_force','ref3_sphere_projection'):
 p=OUT/f'{name}.pdf'; d=fitz.open(p); d[0].get_pixmap(matrix=fitz.Matrix(3,3),alpha=False).save(str(OUT/f'{name}.png'))
print(json.dumps({k:{'ok':v.get('ok'),'files':v.get('files',[])} for k,v in results.items()},ensure_ascii=False,indent=2))
raise SystemExit(0 if all(v.get('ok') for v in results.values()) else 1)
