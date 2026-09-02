---
name: cumcm-diagrams
description: 设计和审查 CUMCM 关系图、机理图、几何图与算法流程图。用于把复杂依赖、对象关系、决策分支或反馈迭代变成克制准确的可编辑矢量图，并逐条核对连接语义、文字密度和最终版面。
---

# CUMCM 结构图、机理图与流程图

先读 [../cumcm/references/flowchart-routing.md](../cumcm/references/flowchart-routing.md)、
[../cumcm/references/diagram-layout.md](../cumcm/references/diagram-layout.md)、
[../cumcm/references/geometry-diagram-routing.md](../cumcm/references/geometry-diagram-routing.md) 与
[../cumcm/references/diagram-connection-audit.md](../cumcm/references/diagram-connection-audit.md)，并完整读取
[references/tikz-visio-standard.md](references/tikz-visio-standard.md) 与
[references/fixed-flowchart-style.md](references/fixed-flowchart-style.md)。工作区启用论文绘图 MCP 时还要完整读取
[../cumcm/references/figure-mcp-routing.md](../cumcm/references/figure-mcp-routing.md)，先执行
[插图路由阶段](../cumcm-figure-router/STAGE.md)；`paper-figure-router` 可用时调用 MCP，否则运行确定性回退，
只把获准的结构图交给 `paper-visio` 或 `paper-tikz`。

当机理图进入特色主视觉时，同时执行
[../cumcm-figures/references/visual-identity-and-archetypes.md](../cumcm-figures/references/visual-identity-and-archetypes.md)
与特色图 registry v4 契约。结构/几何部分必须通过现有连接、锚点和数学一致性门禁，数值结果必须
来自数据后端；不得把流程图、机理图和曲线装饰性拼接，也不因“特色”降低任一 diagram gate。

## 先选图类

- 问题或模块共享变量：关系图；
- 物理对象、轨迹、边界与作用：机理图或几何图；
- 有三步以上依赖、判断或回退：算法流程图；
- 状态转移与控制策略：状态/决策图；
- 单一线性步骤、数值计算清单或分问目录：不用流程图。

国一/国奖模式另执行 [../cumcm/references/national-first-precision-and-visual-gates.md](../cumcm/references/national-first-precision-and-visual-gates.md)：
一问只要存在三个以上不可合并阶段、判断/循环/回退/早停、粗搜—细化、状态转移、递归再生或多层输入输出，
流程图即为必需证据，不是可选装饰。其审美要从本地 50 篇优秀论文提炼主轴、层级、留白和基础形状，
但不得复制具体图形或使用默认 Office/网络图主题。

用于问题分析章末时，先判断各问是否存在共享输入、前后承接、并行汇合或反馈。存在真实关系时画
“问题关系图”或“各问题关系与总体求解流程图”；各问只是并列目录时不画。关系图只表达分问之间
的数据、变量、模型或结果传递，不加入方法评价、最终数值、研究意义、论文写作和结果展示模块。

禁止绘制“读取附件—运行代码—生成图表—撰写论文—提交结果”等生产流程。

## 成稿后绘制

规划阶段只登记图的职责、正文锚点、真实节点/对象和所需数据；对应小节的文字、公式、符号、阈值、
判停与边界处理稳定后，才生成 TikZ/Visio 源并插入终稿。每完成一问即编译检查，不先凭题面或 OCR
猜节点，也不等全文结束后一次性补齐。注册表必须记录正文锚点、成稿状态、符号公式复核和实际绘制时序。

## 一手语料对照与雷点自查

按 [../cumcm/references/corpus-alignment.md](../cumcm/references/corpus-alignment.md) 执行：
规划流程图前从 `最终效果/高教杯优秀论文/流程图普查/AB优秀论文流程图汇总.md` 与
`流程图普查/all_paper_flowcharts.md` 查看同题型论文在哪些环节使用了流程图、承载什么职责；
每图定稿前对照 `流程图普查/AB优秀论文流程图十大雷点与写作禁忌.md` 逐条自查。材料缺失时
跳过并在门禁记录。"复杂算法必配流程图"以本技能非平凡分支/循环/回退判据为准，不是无条件必配。

## 信息层级

1. 每图只有一个主要职责，标题直接说对象和关系。
2. 先画 3--7 个主模块，再按需要展开局部分支；不要把整篇论文压进一张海报。
3. 节点写对象、状态、变量或判据，不写“进行分析”“建立模型”“得出结论”等空动作。
4. 节点文字超过两行时优先拆分、缩写或移到图后解释；公式只保留决定分支或机理的核心关系。
5. 复杂总体路线可拆为“共享关系图 + 局部算法流程”，避免蛇形长链和大段说明。

## 连接语义

- 箭头方向必须等于变量传递、因果、时序或状态转移方向；
- 判断菱形写可判定条件，分支标明“是/否”或实际阈值；
- 回退线必须回到真实更新节点，不能形成无出口死循环；
- 算法流程图必须有明确起点与终点节点（椭圆或圆角矩形），起点写真实输入对象、终点写
  输出量，不得方框悬空开局或悬空收尾；
- 无向共享关系不用伪装成单向因果；
- 每条引线和箭头都要在连接清单中逐项验收。

## 固定流程图视觉规范

算法流程图、问题关系图、模型结构图和状态决策图默认执行
[固定流程图风格与语义版型](references/fixed-flowchart-style.md)：固定使用
`visual_preset: cumcm-classic-orthogonal`，按真实语义自动选择 `layout_variant`，并设置
`style_confirmation_required=false`。今后不再向用户重复确认风格，只确认节点内容、连接语义与最终渲染。
创新应发生在本题特有的目标—约束—状态—反馈结构和解释责任上，不得通过装饰、配色或复杂算法名称制造。

## 通用视觉规范

- 白底，黑灰线条，必要时用冷蓝突出唯一主路径；
- 使用基础矩形、菱形、圆点和直角连接，避免渐变、阴影、圆角卡片、装饰图标和饱和配色；
- 同层节点等宽对齐，留白均匀，主阅读方向保持从左到右或从上到下；
- 文字直接嵌入节点，不用独立文本框覆盖空框；标注锚定具体对象；
- 数学公式、变量和阈值必须作为原生 LaTeX/TikZ 文本或 Visio 原生文本存在；不得粘贴公式截图，也不得
  用白底矩形遮挡底层图形。TikZ 公式节点默认透明背景，确需避线时先移动或以短引线外置，不能靠白块盖线。
- 任何线段、曲线、轨迹、轮廓、尺寸线、引线和流程箭头都必须连续绘制，不得因公式、变量、阈值、
  分支文字或普通标签而断开、留白或被遮罩；文字放在线路周边的净空区，与线保持成品至少 2.5 pt 间距，
  必要时用短引线说明归属。
- TikZ 核心机理图必须有足够的对象层、构造层、判据层和标签层；关键切点、垂足、角弧、尺寸线及局部
  放大均由同一命名坐标计算，禁止只凭视觉摆放形成“粗略示意”。
- 流程图的目标是 10 秒内读出唯一主轴和关键分支。采用短节点、标准形状、正交细实线和透明分支标签；
  连接正确只是底线，缩略图不清楚或像默认 Office 模板时仍判失败。
- 需要局部放大时使用 `paper-tikz` 的 `detail_inset`，让主图 ROI 与放大窗共享结构化几何对象；流程图
  默认也由 `paper-tikz` 按 `cumcm-classic-orthogonal` 与语义版型生成。二者属于
  整体 MCP 能力，不为单题硬编码坐标、文字或模型名称。
- 导出 PDF/SVG 并保留 drawio、TikZ 或脚本源文件；正式结构图不使用 PPTX 作为源文件，不得靠 LaTeX `trim/clip` 修图。

最终风格只允许 `tikz` 或 `visio`。关系图、流程图、几何图与公式结构默认优先 TikZ；只有对象极多、
规则布局无法达到清楚层次且团队确需图形界面协作时回退 Visio，并登记具体理由。TikZ 使用统一样式表，Visio 使用基础形状、动态连接线、
吸附和两级线宽；禁止默认 Office 主题、彩色卡片和手工移动数值几何。若 TikZ 坐标取自 GeoGebra (GGB) 导出，必须先运行 `python .agents/skills/cumcm-diagrams/scripts/sanitize_ggb_tikz.py` 过滤长浮点数、裁剪外框并统一规范样式。

问题分析章末的跨问关系同样先尝试 TikZ；不得同时制作两幅内容相同、仅工具不同的图。

正式 Visio 图调用 `render_diagram` 时设置 `strict_audit=true`。每条边提供稳定 id、连接类型、
方向语义、源目标和分支文字；生成后先检查 `.layout.json`，再按最终插入宽度查看 PNG/PDF，
用 `record_visual_review`记录原尺寸、缩略图、文字避让和连接复核。`publication_ready=false` 时停止交接。

## 从 A/B 现有图继承的原则

保留共享模型—分问题递进的清楚层级，以及全局搜索—局部细化—稳定性复核的真实反馈回路。
当总体技术路线包含多层长句、多个阈值和最终数值时，将数值证据移回结果图表与正文，只在流程图保留决定路线的判据，
必要时拆成两图。几何图继续采用对象、轨迹、角度、边界和关键公式分层，但必须消除标签与线段碰撞。

## 门禁

为每图建立 `审查/diagram-registry.json`，字段结构见
[assets/diagram-registry.example.json](assets/diagram-registry.example.json)；生成同名布局审计和连接清单，运行：

```bash
python .agents/skills/cumcm-diagrams/scripts/audit_diagram_style.py --root .
```

连接清单统一采用 `edge_schema_version: 1`：每条边必须含稳定 `id`、`kind`、`source`、`target`、
两端 anchor、`directionality`、`direction`、`meaning`、箭头要求/实测，以及端点误差、交叉、间距、
重叠、语义和最终渲染结果。旧 layout 的 `from/to/points/label` 只作为原始几何，运行
`python .agents/skills/cumcm-review/scripts/sync_review_artifacts.py --root .` 后转换为统一
`connection_audit.items`；无法机器确认的字段必须为 `null`/`REVIEW_REQUIRED`，禁止补成 true。

自动报告通过后写 `gates/diagrams.json`。检查唯一职责、TikZ/Visio 风格族、节点信息量、连接方向、
判断分支、回退出口、数学锚点、对齐留白、最终字号、矢量输出和可编辑源文件。任一连接、线语义、
数学一致性或风格检查失败不得进入正文。
