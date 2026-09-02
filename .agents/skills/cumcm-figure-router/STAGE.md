---
name: cumcm-figure-router
description: CUMCM 论文插图的确定性判定、图型选择与绘图路线路由技能（Python 数据图代码 + TikZ/Visio MCP）。用于从题面、证据矩阵、变量维度、几何约束、步骤分支和待证明命题判断是否需要图、选择绘图路线、生成结构化绘图契约，并在绘制后登记可编辑源、矢量成品、正文位置和最终页视觉验收。
---

# CUMCM 自动判图与 MCP 路由

## 目标

先判断“这项结论是否需要图、图承担什么证据职责”，再决定图型和后端。禁止先画图再寻找正文用途，也禁止为使用三种软件而制造无意义复合图。

## 输入契约

每个候选图写成 JSON，至少包含：

```json
{
  "figure_id": "F01",
  "section": "模型建立与求解",
  "claim_id": "Q2-C3",
  "claim": "首次接触附近最小有符号间隙连续跨越零点",
  "figure_role": "quantitative_evidence",
  "data_shape": "time_series",
  "object_count": 2,
  "step_count": 1,
  "shared_outputs": 0,
  "has_geometry": false,
  "has_decision": false,
  "has_loop": false,
  "has_spatial_coordinates": false,
  "needs_exact_labels": false,
  "existing_figure_overlap": false
}
```

`claim` 必须唯一且可检验；没有 claim_id 或证据来源的图不得进入正式路由。
当命题同时含几何、判断和数据时，`figure_role` 必须显式填写：`quantitative_evidence`
优先 Python/matplotlib 数据几何，`mechanism` 与 `algorithm` 默认优先 TikZ。定量职责缺少受支持
`data_shape` 时直接拒绝，禁止用装饰性三维或示意图冒充结果证据。规划阶段只保留命题、数据和正文位置；
对应小节成稿、符号与公式稳定后才绘制最终图。

以上扁平字段是规范形态；`paper-figure-router` MCP 与确定性回退脚本同时接受早期调用方的嵌套形态
（`geometry.{coordinates,angles,tangency,projection,collision_boundary,dimensions}`、
`data.{time_series,trajectory,surface,matrix,distribution,comparison,sensitivity,uncertainty}`、
`relations.{steps,branches,feedback,shared_outputs,object_count}`、`duplicates_existing_figure`），
两种形态在路由前归一化到同一判定表。`section` 接受常见中文章节名及其变体，按关键词归一化；
`data_shape` 取值见 `scripts/route_figures.py` 的 `DATA_TYPES` 表。MCP 与回退脚本必须对同一契约
给出相同判定，该等价性由 `scripts/selftest_router_parity.py` 锁定。

## 是否插图

默认不插图并被路由直接拒绝：摘要、问题重述、模型假设、符号说明、模型评价、参考文献、附录。
同样不插图：简单闭式代入、两三句可说清的线性步骤、与现有图完全重复的结果。

满足任一条件时优先插图：

- 趋势、分布、误差、收敛、敏感性、不确定性或方案差异需要读数；
- 空间路径、覆盖、构型、场、临界位置或过程演化不能由表格直接表达；
- 几何对象、切线、投影、角度、尺寸、碰撞边界参与公式定义；
- 三个以上不可合并阶段，或存在判断、循环、反馈、回退、状态转移；
- 三个以上问题/模块存在共享输入、输出或递进依赖；
- 国一模式缺少过程状态、临界构型、验证诊断或机理—结果特色图。

## 绘图路线选择

### Python 数据图（求解侧直接生成）

用于真实数据和数值计算：时间序列、迭代、轨迹、空间布局、热图、等高线、曲面、参数扫描、方案比较、残差、收敛、敏感性、不确定性。所有点由结构化数据或模型计算产生；由求解侧 Python/matplotlib 脚本直接生成，并保留 `.py/.json/.pdf/.svg/.png`。风格、物理画布和保存契约复用 `figure_mcp/python_figure.py`，renderer 如实登记为 `python-matplotlib`。

### TikZ

用于精确解析几何和数学机理：坐标、圆弧、切线、投影、角度、尺寸、向量、碰撞边界、分段路径、局部放大和公式关系。对象坐标应来自公式或结构化 spec，不凭视觉拖动。

路由为“临界事件、接触/切换边界、切点/垂足或局部几何判据”且主图最终尺寸无法清楚标注时，
在输出绘图契约中加入 `detail_inset`。契约至少含 `source_center/source_width/source_height`、
`inset_center/inset_width/inset_height`、`scale` 和原生 `elements`；缺一则退回重建，不允许以截图替代。

### TikZ 流程与结构图

问题关系、模块结构、算法流程、判断分支、循环反馈和状态转移默认也由 TikZ 生成。判断框必须有真实条件和分支文字；节点不得写“数据处理—建立模型—得到结论”空泛模板。

获准的流程图统一传递 `visual_preset: cumcm-classic-orthogonal`。路由器根据节点、目标/约束、判断、
反馈和阶段分组自动选择 `layout_variant`；风格固定，结构随本题证据创新，纯并列目录仍不得套流程图。

### Visio 回退

仅当对象极多、TikZ 规则布局仍无法形成清楚层级，且团队确需图形界面继续协作时使用。契约必须设置
`requires_manual_layout=true` 并填写具体 `visio_fallback_reason`；未说明理由时仍路由到 TikZ。

### 复合图

仅当同一核心命题同时需要数值结果与精确机理/高层结构时采用。Python/TikZ 生成数值或几何面板，Visio 只等比组合和添加编辑结构，不重画数据。必须记录面板来源和形变率，形变率大于 0.2% 失败。

## 图型决策表

- 一维有序变量 → 折线/置信带/事件标记；
- 两变量关系 → 散点+拟合，残差另设诊断；
- 组间分布 → 箱线/小提琴/ECDF；
- 多方案精确比较 → 排序点图或条形图；
- 二参数响应 → 等高线；只有矩阵单元语义明确才用热图；
- 空间路线/构型 → 等比例坐标轨迹与关键状态；
- 临界事件 → 全局构型+局部放大或阈值穿越；
- 几何推导 → TikZ 精确对象图；
- 判断/回退/循环 → TikZ 流程图；
- 问题共享关系 → TikZ 关系图；复杂人工编排按上述条件回退 Visio。

## 执行

```bash
python .agents/skills/cumcm-figure-router/scripts/route_figures.py \
  --input 求解/候选图契约.json --output 论文/figures/figure_routes.json
```

路由到 TikZ/Visio 时先调用对应 MCP 的 `health_check`；路由到 Python 时直接运行求解侧绘图脚本。每张图保留：结构化 JSON、生成源（`.py/.tex/.vsdx`）、PDF/SVG、PNG 预览、MCP 调用清单或生成命令、source_data、claim_id、正文插入点、成稿后绘制记录和最终页视觉记录。

修改 `figure_mcp/figure_router_server.py` 或 `scripts/route_figures.py` 后必须运行 parity 自测，
确认 MCP 与确定性回退对同一批契约给出相同的 `should_insert/renderer/figure_type`：

```bash
python .agents/skills/cumcm-figure-router/scripts/selftest_router_parity.py --root .
```

## 门禁

只有以下全部满足才能 `publication_ready=true`：路由需要该图；后端与证据类型匹配；数据/几何可追溯；可编辑源与真矢量成品存在；原尺寸、论文宽度、缩略和灰度检查通过；图前提出命题、图后给出定量解释；最终编译页无裁切、重叠、字体压缩和连接错误。

系统能力还必须通过跨题型回归：至少一幅 A 类解析几何 inset、一幅 B 类决策边界 inset、一幅 A 类
数值迭代流程和一幅 B 类策略优化流程。单题样图通过不能证明 `detail_inset` 或
`cumcm-classic-orthogonal` 可用。
