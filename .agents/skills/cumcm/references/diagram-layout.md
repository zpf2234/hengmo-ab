# 几何图与流程图布局约束

本规则适用于几何机理图、坐标关系图、问题关系图、算法流程图和计算框图。数据图的坐标轴
排版仍按 `figure-routing.md` 执行。

所有连接还必须执行 [diagram-connection-audit.md](diagram-connection-audit.md)：
先逐条登记与验收引线、箭头、分支和反馈，再做整图构图审查；两层任一失败均停止导出。

## 单一对象与锚定

- 有边框的节点必须把文字写入形状自身的 `TextFrame`，不得用独立文本框覆盖在矩形或
  菱形上。形状移动、缩放和字体替换时，边框与文字必须作为同一对象变化。
- 节点文字水平、垂直居中，四周保留安全内边距；标题和说明可使用同一文本框中的不同段落，
  不拆成多个浮动文本框。
- 流程节点只写一个动作、条件或输入输出，默认使用统一字号与字重，主动控制在一至两行。
  不采用“大标题 + 小号解释”的卡片式层级；参数含义、方法理由和结果解释放在图前后正文。
- 连接线从节点边界锚点出发并终止于另一节点边界，不从节点中心穿过，不依赖视觉上“差不多
  对齐”的绝对坐标。
- 流程箭头的起点与终点必须绑定节点外轮廓锚点；箭头尖端止于目标框边界，箭头线段和尖端
  均不得伸入目标框内部。反馈线先在节点外侧正交绕行，再从指定边界锚点接入。
- 几何标注必须记录被标注对象的锚点。标注放在对象外部时使用细引线；不得把文字直接压在
  轨迹、边界线、圆周、箭头或其他标签上。
- 所有线条按完整几何一次性连续绘制，标签作为独立透明对象放在线路周边；不得把标签插入路径后
  截断线段，也不得用页面同色遮罩制造线条缺口。

## 固定画布

- 生成器显式设置画布宽高和纵横比，所有对象坐标均相对于该画布。
- Office 文本框写入文字后必须再次显式设置 `Left/Top/Width/Height`，并关闭自动适应。
  PowerPoint 可能在写入中文时先收缩文本框；只在创建时传入坐标不足以锁定成品位置。
- 文本检查使用实际字形包围盒，不用名义文本框代替；字形四周至少保留 1--2 pt 安全距离。
- 文本框不得旋转，字体、字号、水平对齐、垂直锚定、换行和段前段后距均显式设置。
- 导出 PDF/SVG 时保持原画布，不使用 `bbox_inches="tight"`、Office 自动裁边或其他会改变
  页面坐标原点的紧边界导出。
- 示意图和流程图在 LaTeX 中只允许 `page` 与 `width`/`height` 的等比例缩放；禁止使用
  `trim`、`clip`、非等比 `resizebox` 修补源图留白或错位。应回到源图调整画布。

## 成品字号与占位尺度

- 50 篇优秀论文中可直接读取的图内矢量文字以宋体为主，数学与拉丁字符主要为 Times New Roman、
  Cambria Math 或 LaTeX 数学字体；图内字号中位约 9.4--9.7 pt。语料中 6--8 pt 小字视为可读性缺陷，
  本项目不模仿。
- 普通节点、对象名和概率标签以 9--10.5 pt 为主；成品最小字号不得低于 8.5 pt。短标签可以增至
  10.5--12 pt，但不得通过字号差制造卡片式层级。
- 图宽分三档：半宽并排 `0.44--0.49\textwidth`，中等图 `0.62--0.82\textwidth`，通栏图
  `0.90--1.00\textwidth`。几何图通常优先 11--13.5 cm，流程/状态图通常优先 14.5--16 cm；
  高而窄的流程图可用 8--11 cm 宽，成品高度通常不超过 `0.80\textheight`。
- 概率、分支标签、角度、点名、公式和普通注释一律透明背景；先移动到连线净空区，必要时用短引线，
  不得用白色矩形遮住底层线条。画布可以是论文白纸，但节点和数学标签不建立白色覆盖层。

## 源端检查

每个正式示意图或流程图必须在同目录生成同名 `.layout.json`，至少包含：

```json
{
  "pass": true,
  "canvas_pt": [720, 405],
  "flowchart_profile": {
    "visual_preset": "cumcm-classic-orthogonal",
    "layout_variant": "horizontal-feedback",
    "style_confirmation_required": false
  },
  "style_audit": {
    "white_background": true,
    "white_node_fill": false,
    "transparent_node_fill": true,
    "math_labels_transparent": true,
    "line_continuity_unmasked": true,
    "labels_outside_line_paths": true,
    "orthogonal_connectors": true,
    "classic_shape_semantics": true,
    "no_grid_background": true,
    "group_frames_dashed_only": true,
    "feedback_lines_solid": true,
    "stage_badges": false,
    "focus_cards": false,
    "colored_decision_nodes": false
  },
  "checks": {
    "objects_inside_canvas": true,
    "node_text_embedded": true,
    "text_inside_parent": true,
    "node_lines_max_2": true,
    "uniform_node_text_style": true,
    "decision_lines_max_2": true,
    "annotation_anchors": true,
    "leader_endpoint_on_target": true,
    "arrow_endpoints_on_node_boundary": true,
    "arrowheads_outside_node_interior": true,
    "connection_inventory_complete": true,
    "non_target_crossings_zero": true,
    "branch_label_clearance": true,
    "final_render_connections_checked": true,
    "line_direction_semantics_complete": true,
    "arrow_direction_matches_meaning": true,
    "line_style_matches_meaning": true,
    "text_line_clearance": true,
    "line_continuity_unmasked": true,
    "labels_outside_line_paths": true,
    "label_object_clearance": true,
    "final_font_size_readable": true,
    "composition_balance": true,
    "latex_trim_required": false
  }
}
```

生成器在导出前执行：

1. 所有形状和文本的边界位于画布内；
2. 节点文本的实际包围盒不超过节点扣除内边距后的可用区域；
3. 所有流程节点不超过两行且使用统一字号与字重；判断菱形超过两行时，先缩短判断语句或放宽菱形，
   不通过自动压缩字号容纳；
4. 独立注释框互不重叠，并且都有对象锚点或明确的轴标签职责；
5. 实际字形包围盒不与轨迹、视线、轮廓、箭头或非目标实体相交；
6. 箭头不穿过非目标节点，回路线从节点外侧正交绕行；
7. 几何引线的目标端点位于对应线段、圆周、轮廓或关键点上，不能只停在目标附近；
8. 流程箭头逐条检查“源节点边界—节点外部连线—目标节点边界”，箭头尖端不得越过边界；
9. 节点主轴、反馈回路和画布留白形成可辨识层级，不把全部对象机械铺满；
10. 最小字号按论文实际插入宽度换算后仍不低于 8.5 pt。
11. 每条线从起点到终点连续可见，标签字形包围盒不与所属线路相交；文字放在线路周边，净距不低于 2.5 pt。

任一检查失败时停止导出，不通过缩小字体或 LaTeX 裁边掩盖。

`.layout.json` 还必须包含 `diagram-connection-audit.md` 规定的 `connection_audit` 与
`line_semantics_audit`、`overall_audit`。不得只写汇总布尔值而省略逐连接与逐线族 `items`。

## 成品检查

- 先把矢量图按论文实际宽度插入，再渲染整页 PDF；只看源 PPT 或单独打开 PDF 不算验收。
- 至少在 100% 页面视图和缩略图视图各检查一次：框内居中、引线归属、箭头端点、文字压线、
  节点间距、图题间距和页面留白。
- 修改字体、文字、节点尺寸、画布、导出软件或 LaTeX 插入尺寸后，布局审计和整页渲染必须
  重新执行。
