---
name: cumcm-figures
description: 规划、生成和审查 CUMCM 数据图形。用于依据待证明命题、数据维度和不确定性选择图型，以本地 50 篇优秀论文的图形密度作漏图或冗余检查，并统一出版级配色、标注、分辨率和正文解释。
---

# CUMCM 数据图形

先读 [../cumcm/references/figure-routing.md](../cumcm/references/figure-routing.md) 与
[../cumcm-paper/references/section-chain-contract.md](../cumcm-paper/references/section-chain-contract.md)，
再完整读取 [references/aesthetic-standard.md](references/aesthetic-standard.md)。国一/国奖候选还必须读取
[references/visual-identity-and-archetypes.md](references/visual-identity-and-archetypes.md) 与
[references/signature-figure-standard.md](references/signature-figure-standard.md)，并复制
[templates/signature-figure-plan.md](templates/signature-figure-plan.md) 在普通图批量生成前规划特色主视觉；
特色必须来自真实模型和结果，不得用装饰性信息图替代科学证据。工作区启用论文绘图 MCP 时完整读取
[../cumcm/references/figure-mcp-routing.md](../cumcm/references/figure-mcp-routing.md)，并完整执行项目级
[插图路由阶段](../cumcm-figure-router/STAGE.md) 判断是否插图、图型、后端与正文位置。若独立 `paper-figure-router` MCP 可用则优先
调用；不可用时运行 `cumcm-figure-router/scripts/route_figures.py` 并登记
`router_mode: deterministic_fallback`。工程动态、轨迹、曲面和参数结果由求解侧 Python 绘图代码
（matplotlib）直接绘制，风格与保存契约复用 `figure_mcp/python_figure.py`。
结构图、机理图和流程图转交 `cumcm-diagrams`。

涉及临界构型、切点、垂足、碰撞或策略切换边界时，除非主图在最终宽度已经足够清楚，否则向
`cumcm-diagrams` 传递 `detail_inset` 契约，由同一结构化几何重绘局部，不得裁图放大。涉及算法、
关系或状态流程证据时，固定传递 `visual_preset: cumcm-classic-orthogonal`，并让 diagrams 按真实语义
选择 `layout_variant`；视觉统一，结构创新，不是某道题的固定流程模板。

## 先定义证据职责

每张图先写一句内部命题：它要证明趋势、差异、空间结构、分布、拟合、残差、收敛、敏感性、
方案结构还是不确定性。无法写出唯一主要命题的图先合并、拆分或删除。
路由返回 `should_insert=false` 时不再调用绘图工具；返回 true 时把 `insertion_point`、
`before_sentence_contract` 和 `after_paragraph_contract` 写入图形注册表，约束正文落点和解释顺序。

采用“先留证据位置、后按成稿绘制”的两阶段流程：成文前只确定该图要证明什么、需要哪些数据及
放在哪一段附近，不提前把标题、符号和节点文字画死；本节正文、公式、变量名、阈值和结论稳定后，
再生成结构化绘图说明并绘制终稿。每完成一问就制图、插入和编译复核，不把所有图拖到全文最后一次性补齐。

## 图型路由

- 时间演化或迭代：以曲线为主体，并至少加入事件、阈值、阶段区间、基线或不确定性中的一层；
- 两变量关系与拟合：散点图加模型曲线，残差另设诊断面板；
- 分布与组间差异：箱线图、小提琴图、直方图或经验分布；
- 参数扫描与敏感性：响应曲线、等高线或热力图；
- 空间路线与覆盖：真实坐标系中的路线、覆盖带、方向或误差图；
- 多方案精确比较：优先排序点图、区间图或表格；柱图只有在误差、原始观测或基线具有独立读数时保留；
- 收敛与稳健性：目标轨迹、多起点分布、扰动箱线图或区间图；
- 高质量三维曲面、空间散点或轨迹图在能提升空间理解、信息密度或核心结果展示时可以直接使用；
  不要求先证明二维完全不可替代，也不强制同时附等高线。三维不得只是装饰，视角和遮挡不能歪曲结论。

## 50 篇普查校准与证据职责门禁

760 个正式图形中，机理/几何、动态、空间路线、算法框架和参数曲线最常见；诊断、比较、敏感性与热图按题目需要出现。

### 数量权威与特色安排

1. **图形数量不设上下限**：正文可以没有图，也可以出现 4、6 幅或更多图。每幅图先绑定待证明
   命题、不可替代或互补职责、关键读数、来源和正文解释；同一命题的多图可分别承担整体趋势、
   局部边界、空间构型或诊断。`cumcm-review/scripts/audit_artifacts.py` 只把语料图密度作为非阻断的
   漏图/冗余复核参照，不计算数量门槛，不因图少或图多自动放行或阻断。
2. **多阶段演化优先多面板拼图 (Subfigures)**：对涉及多时间节点、状态演化或临界状态对比的证据，
   优先用单图号下的多面板拼图集中呈现；面板数量完全按数据逻辑灵活选择（2、3、4 面板均可），
   严禁为凑格式机械拼图，也不得为省图号把无共享事件或阈值的数据硬拼。
   单面板不设图内标题；两幅强耦合且职责一眼可辨时，可由总图题用“左/右”说明；三幅及以上或
   面板条件不同，则把 `(a)(b)…` 小标题统一居中置于各面板下方，再在整组下方放总图题。
3. **30 页上限内的特色版面**：正文只按官方口径计算，即正文主体首页至附录开始前一页，
   包含 AI 工具使用声明和参考文献，不含摘要与附录，并且不超过 30 页。图形不承担凑页职责。
   版面质感借鉴国一优秀论文，但具体图型按 `references/visual-identity-and-archetypes.md` 的原型库依证据
   结构选择：前置模型决策流程图、多阶段演化联排拼图、临界构型与边界图、机理—结果联图等均为候选原型而非
   固定套图；题目证据不支持某一原型时按 `references/signature-figure-standard.md` 记录具名豁免，
   不为版面张力强制拼图。

以下密度分位数来自旧“参考文献前页数”普查，只作历史视觉参照，不直接进入现行门禁。正式二次
审计必须把候选稿与同题参考稿都按官方正文口径重算“正文图数 ÷ 正文页数”：

- 机理或优化证据占主导时，0.55 / 0.71 / 0.88 可作下四分位、中位数、上四分位参照；
- 数据分析或决策证据占主导时，0.41 / 0.60 / 0.80 可作相应参照；
- 密度明显低于同类 Q1 时触发漏图复核，明显高于 Q3 时触发冗余复核；两者均不阻断，放行依据
  始终是证据职责、非重复性、可追溯性、最终可读性和正文解读。

## 审美与真实性

- 白底或极浅底，黑灰文字，使用一套克制主色和一套强调色；
- 同类变量颜色、线型、点型全篇一致；颜色不能成为唯一区分手段；
- 坐标轴写变量和单位，图例命名与正文一致，字号在最终插入尺寸可读；
- 图题写法（名词短语、限定条件入题、长度校准）与正文引用解读遵守
  [../cumcm/references/figure-table-narration.md](../cumcm/references/figure-table-narration.md)；
- 误差条、置信带和样本量在适用时明确；不截断坐标轴制造差异；
- 数值点必须由结果文件生成，不在 PowerPoint 或绘图软件中手动移动；
- 优先 PDF/SVG 矢量输出；位图按最终尺寸确保清晰，避免截图和插值放大；机器门禁须同时核对目标宽度、目标高度与纵横比，三者误差均不得超过 0.2%，仅纵横比一致不能证明最终字号/线宽正确。

最终字号、线宽、插入宽度、色觉安全配色和各图型专属检查严格按 `aesthetic-standard.md` 执行。
默认软件主题、彩虹色、图内大标题、三维柱、无单位坐标或只展示最好一次的随机优化曲线不得放行。
默认单折线、默认单柱图同样不得放行；若连续曲线确有必要，注册表必须记录第二证据层、关键读数及
不能由表格或一句文字替代的理由。

## 正文解释

图形应与正文自然交互，可用于呈现对象、支撑读数、解释空间或数量关系、推进判据或承接结论；
不要求每张图固定配置图前命题和图后四步分析。关键数值、机制和答案影响在本问整体论证中交代即可。
不得逐点念图，也不得只写“由图可知模型效果良好”。同一结果不再用一张图和一张表完整重复。

## 门禁

为每张图记录数据来源、生成命令、主要命题、正文定位和可编辑源文件，并建立
`审查/figure-registry.json`。schema v4 在根级登记全局视觉身份与 signature policy，在逐图登记
`signature_figure/core_claim/ten_second_takeaway/read_order/data_linkage/signature_checks`。字段结构可复制
[assets/figure-registry.example.json](assets/figure-registry.example.json) 后替换为本项目真实路径和检查证据。运行：

```bash
python .agents/skills/cumcm-figures/scripts/audit_figure_style.py --root .
# 国一/国奖候选必须显式开启特色图门禁
python .agents/skills/cumcm-figures/scripts/audit_figure_style.py --root . --track national-first
```

每次正文 figure、源数据、生成脚本或矢量输出变化后先运行
`python .agents/skills/cumcm-review/scripts/sync_review_artifacts.py --root .`。该命令生成
provenance v2 的逐文件 SHA-256；哈希仅证明文件身份和链路，不替代图型适配、审美和科学性人工复核。

自动报告与人工整页复核均通过后写 `gates/figures.json`。检查图型适配、数值可追溯、标注单位、
色觉与灰度可辨、最终尺寸清晰、语料密度参照和逐图正文解释。国一模式至少一张特色图，确实不适合时允许
记录具体科学理由、关联证据和独立审查批准的豁免；豁免不降低任何科学、provenance 或最终页面门禁，
也不得为满足数量强制拼图。仅换配色、装饰增强或无共享事件/阈值的数据拼接一律拒绝。
