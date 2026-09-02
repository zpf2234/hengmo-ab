---
name: cumcm-review
description: 数学建模国赛优秀论文候选审查技能。用于审查 CUMCM 求解包、单一总稿 LaTeX 论文、PDF 和附件，检查官方格式、匿名性、原创相似度、模型适配、数值一致性、证据链、验证强度、可复现性、表达密度与视觉排版，并生成分级整改清单驱动回退修复。
---

# CUMCM 优秀论文候选审查

以评委和复现者双重视角审查最终产物。审查阶段不发明模型或结果，只定位问题并回退修复。
存在本地优秀论文语料时，先读
[../cumcm/references/benchmarking.md](../cumcm/references/benchmarking.md)。
同时读
[../cumcm/references/full-paper-census.md](../cumcm/references/full-paper-census.md)，
区分标题显式下限、正文词项命中和页面人工抽检证据。
图形审查使用
[../cumcm/references/figure-routing.md](../cumcm/references/figure-routing.md) 的职责、图型与
源文件门槛，不以图数多少代替论证质量。
若项目使用论文绘图 MCP，同时读取
[../cumcm/references/figure-mcp-routing.md](../cumcm/references/figure-mcp-routing.md)，抽查每幅图是否先有
唯一命题与路由记录，后端是否匹配，插入位置是否符合契约；Visio 图的 `publication_ready` 和
同名布局审计未通过时直接记为图形门禁失败。
流程图审查同时使用
[../cumcm/references/flowchart-routing.md](../cumcm/references/flowchart-routing.md)，核对功能、
节点、分支、判停、回退、图表清单登记和成品可读性。
摘要审查使用
[../cumcm/references/abstract-writing.md](../cumcm/references/abstract-writing.md)，核对逐问
定量答案、分段、一页成品、关键词与证据一致性。
附录审查使用
[../cumcm/references/appendix-structure.md](../cumcm/references/appendix-structure.md)，核对
正文索引、真实环境、完整代码、身份清理、可搜索性和渲染可读性。
标题结构审查使用
[../cumcm/references/title-structure.md](../cumcm/references/title-structure.md)，检查结构是否
来自问题依赖、每问是否闭环以及标题是否写明对象与动作。
论文架构审查使用
[../cumcm/references/paper-architecture.md](../cumcm/references/paper-architecture.md)，检查
前置功能、独立符号章、三级标题上限和跨问题验证职责。
封面总标题审查使用
[../cumcm/references/paper-title.md](../cumcm/references/paper-title.md)，先排除 OCR 正文误识别，
再核对对象、动作以及每个方法词的正文兑现。
几何图与流程图布局审查使用
[../cumcm/references/diagram-layout.md](../cumcm/references/diagram-layout.md)，检查框文单体、
对象锚点、固定画布、同名布局报告和最终插入尺寸。
几何图同时使用
[../cumcm/references/geometry-diagram-routing.md](../cumcm/references/geometry-diagram-routing.md)，
审查实际字形包围盒、轨迹压字、实体遮字和 Office 文本框坐标回缩。
全部几何图、关系图和流程图还使用
[../cumcm/references/diagram-connection-audit.md](../cumcm/references/diagram-connection-audit.md)，
逐连接核查端点、穿越、间距与分支文字，逐线核查方向、箭头与语义，并在全部通过后单独核查整图。
全文逐段审查使用
[../cumcm/references/content-quality.md](../cumcm/references/content-quality.md)，核对摘要强调
职责、符号与假设顺序、最少充分标题、逐问证据闭环和摘要—正文—代码一致性。
模型选择和答案充分性审查使用
[../cumcm/references/model-selection-and-answer-quality.md](../cumcm/references/model-selection-and-answer-quality.md)，
检查候选是否真实执行、择优标准是否预先确定，以及稳定性是否被误当作最优性。
章节职责与交接审查使用
[../cumcm-paper/references/section-chain-contract.md](../cumcm-paper/references/section-chain-contract.md)，
逐项核对章节清单、源文件、阶段门禁和改动传播状态。
逐问内容深度与页数反馈审查完整使用
[../cumcm-paper/references/question-depth-and-pagination.md](../cumcm-paper/references/question-depth-and-pagination.md)，
核对八项职责、官方口径实编正文/总页数、迭代记录和当前 PDF 哈希绑定。
数据图审美审查完整使用
[../cumcm-figures/references/aesthetic-standard.md](../cumcm-figures/references/aesthetic-standard.md)。国一/国奖候选还按
[../cumcm-figures/references/signature-figure-standard.md](../cumcm-figures/references/signature-figure-standard.md)
审查全篇视觉辨识度：核对特色图是否确有核心命题、十秒结论、真实数据链和清晰阅读顺序，
并检查其是否替代或合并了重复常规图。只有配色变化、面板拼接或装饰增强的图不得计为特色图。
同时读取 [../cumcm-figures/references/visual-identity-and-archetypes.md](../cumcm-figures/references/visual-identity-and-archetypes.md)，
核对 registry v3 的全局视觉身份、archetype、数据字段联动、缩略图和最终页检查。豁免必须有具体理由、
claim/审查证据和独立批准；豁免不降低科学、provenance、图表正文交互及可视表达门禁。
流程图、关系图、机理图与几何图完整使用
[../cumcm-diagrams/references/tikz-visio-standard.md](../cumcm-diagrams/references/tikz-visio-standard.md)。

## 自动审计

```bash
python .agents/skills/cumcm-solve/scripts/audit_evidence.py --root .
python .agents/skills/cumcm/scripts/benchmark_corpus.py --root . --fail-on-similarity
python .agents/skills/cumcm-language-audit/scripts/audit_language.py --root .
python .agents/skills/cumcm-deai/scripts/audit_corpus_voice.py --root .
python .agents/skills/cumcm-paper/scripts/audit_figure_table_narration.py --root .
python .agents/skills/cumcm-paper/scripts/check_first_draft_gate.py --root .
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --phase final
python .agents/skills/cumcm-figures/scripts/audit_figure_style.py --root . --track national-first
python .agents/skills/cumcm-diagrams/scripts/audit_diagram_style.py --root .
python .agents/skills/cumcm-paper/scripts/audit_section_chain.py --root .
python .agents/skills/cumcm-paper/scripts/audit_single_tex_delivery.py --root . --phase final
python .agents/skills/cumcm/scripts/audit_skill_execution_plan.py --root .
python .agents/skills/cumcm-review/scripts/audit_artifacts.py --root .
```

普通模式保持兼容：缺少国一 registry/评分卡时只给预警，不用国一门槛误伤常规稿。目标为国一/国奖/一等奖时必须显式运行：

```bash
python .agents/skills/cumcm-review/scripts/init_national_review.py --root .
python .agents/skills/cumcm-review/scripts/sync_review_artifacts.py --root .
# 自动同步正文 figure 环境、registry、图源/数据/生成脚本/layout/最终矢量 SHA-256，
# 并预填客观证据；主观项及全部分数保持 REVIEW_REQUIRED。
python .agents/skills/cumcm-review/scripts/audit_suite.py --root . --track national-first
```

国一模式中，正式图先按正文 `figure` 环境（必须有图片、caption、label）盘点；registry、provenance、最终尺寸视觉复审和正文解读逐图核验。图数不设上下限，图密度只生成 `REVIEW_LOW/REVIEW_HIGH/WITHIN_REFERENCE` 非阻断参照；真正阻断的是职责缺口、重复、无来源、不可读或无正文分析。provenance v2 必须同时绑定正文 TeX、源数据、生成/可编辑源、layout（适用时）和最终矢量；任一输入或输出变更都会被哈希门禁拒绝。正文深度只按写前完整论证规划和逐问八项证据门槛核验，不再用同题页数 Q1 建立第二套正文口径。`评分卡.json` 必须恰含 12 维；自动化只能预填客观证据和指标，不得给主观项打分或写 PASS。全部 `REVIEW_REQUIRED` 由具名审查者完成后，才能计算总分并签发 verdict；总分不低于 57、可视表达 5/5、P0/P1 为空，并以 SHA-256 绑定本次实际审计的 `论文/论文.pdf`。审计后替换 PDF 必须重跑门禁。

国一模式还必须执行 [对抗评审阶段](../cumcm-adversarial-review/STAGE.md)，由未参与求解和写作的题意、数学、表达三路角色分别生成
`审查/对抗评审_题意.json`、`审查/对抗评审_数学.json`、`审查/对抗评审_表达.json`。作者不得自行
关闭 P0/P1。全部整改完成后执行 [国一总门禁阶段](../cumcm-national-first-gate/STAGE.md) 的 fail-closed 总门禁；常规
`PASS_EXCELLENT_CANDIDATE` 不能替代 `PASS_NATIONAL_FIRST_CANDIDATE`。

自动脚本只负责可确定的门槛。模型合理性、文字原创性、验证质量和图表解释必须人工复核。
图形审计命令仅在对应 `cross_cutting` 标记为 true 时运行；标记为 true 却缺注册表或 PASS 报告直接阻断。
只读诊断时给三个脚本追加 `--no-write`。审查脚本从主 TeX 的 `\yearinput{YYYY}` 推断赛事年度，也可用
`--contest-year` 显式指定；年度配置统一控制官方正文页数上限、文件大小和 AI 披露规则。本项目不另设
正文页数下限。官网规则变化时，先更新年度配置；临时核验可用 `--body-page-max`、
`--size-limit-mb` 覆盖并同步
[../cumcm-paper/references/official-rules.md](../cumcm-paper/references/official-rules.md)。最终 LaTeX 只接受
`论文/论文.tex` 单一总稿；摘要按实际 `abstract` 环境识别，不依赖 `0.摘要.tex`。必须保留
`body:start`、`ai-statement:start`、`references:start`、`appendix:start` 与纸面附录/支撑材料清单，
且 `附件/` 中存在实际支撑材料。公式引出冒号和
句末标点属于语境化警告，只有正文明确称为联立方程组/约束组时才强制左大括号。

## Gate 1：提交合规

任一命中即 FAIL：

- 电子版第一页不是摘要专用页，官方口径正文超过 30 页或超过当年更低的官方页数上限；
- 缺少 `body:start` 或 `appendix:start`，无法按官方口径核验正文页数；AI 声明不在参考文献之前；
- 出现目录、身份信息、未完成标记、缺失图片、断裂引用或错误页码；
- PDF/支撑材料超过当年大小限制；
- 缺少纸面附录或支撑材料清单，附件为空，或附录声称承载的完整程序/材料实际不存在；
- 摘要或正文主体展示 AI 提示词、工具名、辅助脚注或生成过程；2026 年缺少置于参考文献前的
  如实 AI 工具使用声明，或实际使用 AI 却未在支撑材料压缩包内提供 `AI工具使用详情.pdf`；
- LaTeX 编译错误、空白页、文字/公式/图表越界或不可读。

从附录首页起不设页数上限，不得因 PDF 总页数超过 30 而判错；附录仍须满足文件大小、完整性和可读性要求。

## Gate 2：原创性

- 优秀论文摘要 8 字符 containment `>=0.30` 或最高风险论文全文 12 字符 containment
  `>=0.20`：FAIL；
- 摘要 `0.15-0.30` 或全文 `0.10-0.20`：逐句人工审查后才能通过；
- 标题、段落骨架、图号序列、专属模型链或异常一致数值明显复刻：FAIL；
- 只做同义词替换而保留原句逻辑和节奏：FAIL。

正式查重结果优先于本脚本。

## Gate 3：科学与模型

不得只读摘要和标题树。逐节阅读正文，并逐问检查：

- 口径是否回答题面真实问题，歧义选择是否有证据；
- 假设是否必要、可解释，并在适用边界或敏感性中被回应；
- 方法是否由问题结构推出，复杂度是否受数据和验证支持；
- 主模型是否先通过科学硬门槛，再在同口径候选中依据独立验证择优；论文只展示真实执行的比较；
- 推导、单位、定义域、约束和数值精度是否一致；
- 优化解是否可行，预测是否防止泄漏，评价排名是否稳定，仿真是否收敛；
- 优化是否提供界、gap、小规模精确解或诚实的近优声明；逆问题是否可识别并经异构估计挑战；
- 每问是否给出明确答案，而不只展示过程。
- 每问题面要求、模型特有推导、参数来源、求解精度/停止/边界处理、结果解释、独立验证、
  风险响应和最终作答映射是否全部有具体证据锚点；不得以全文平均内容掩盖某一问缺项。
- 每段是否承担定义/口径、推导、求解、证据、结论或边界之一；无职责段落是否删除；
- 摘要方法与结论是否能在正文公式、实现、验证和结果中逐项兑现。

## Gate 4：证据与复现

从论文反向抽取每个关键数字和结论，逐一核对：

- `求解/证据矩阵.csv` 的 claim_id；
- `metrics.json` 的模型选择与答案充分性记录；
- 对应 `metrics.json` 字段和结果表；
- 图表路径与生成脚本；
- 验证方法、阈值、结果与通过状态。
- 题目要求的答案表与必要参数表必须由结果文件生成；随机抽取至少一张数值表逐单元格核对，不接受手抄近似值。
- 实现必须兑现任务契约承诺的方法和搜索范围；硬编码单一答案、用预设分配验证预设分配、或把失败的求解器状态写成“收敛”均为 FAIL。
- 主候选与挑战路线必须使用同一题意口径和可比数据；只保存胜者、试算后倒改淘汰阈值、
  或用同一实现换随机种子冒充独立验证，均为 FAIL。

读取 `求解/运行环境.json`，按其中已声明的解释器与逐问命令重跑；缺包、版本未记录、命令只在个人绝对路径下可用或 `verified` 不为 true 均为 FAIL。

随机选择至少一问，从原始数据重跑主入口。结果应在说明的数值容差内复现。
断链、结果冲突、无法运行或验证无判定标准均为 FAIL。
题目提供的 `result*.xlsx` 等官方输出模板必须逐一存在、含有效数值，并保持要求的 sheet、
行列、单位和精度。

## Gate 5：表达与视觉

- 总标题同时含研究对象和核心动作；方法词在摘要、正文模型、代码与验证中均有实质支撑，
  不照抄赛题名，不堆算法，不用“非线性、智能、AI”等无证据升格词；
- 摘要逐问含目标、方法理由、定量结果、单位和可信度信息；
- 摘要关键词可见；正文粗体只强调核心方法与最终结论，普通参数、中间数字和验证细节不加粗；
- 摘要优先使用 `\keymethod`、`\keyresult` 区分强调职责，每问原则上各突出一个；
- 摘要各问可快速定位方法、核心答案和验证；经验字数只作软校准，最终必须完整停留在第一页；
- 摘要和正文不出现 AI、人工智能、提示词、prompt、工具名、生成过程或审查策略；
- 正文没有重复题面、教科书式堆砌、无职责图表或空泛评价；
- 正文没有“便于、有助于、本文报告、不声明、不构成证明”等自我评价或评审元叙事；
- 所有独立展示公式均编号，引出句以冒号结束，公式末尾无标点，引用格式统一；
- 各问必须有可定位的具体结论，但禁止使用“本问回答”“本文的回答”等模板标签；结论直接
  承接结果、验证或不确定度。
- 问题重述与问题分析必须是两个独立一级章；模型假设标题不得附加“计算口径”或其他解释词。
- 摘要和正文不得出现附件文件名、工作表名、代码、程序、脚本、CSV、JSON、文件路径、
  生成过程、运行命令、支撑材料清单或“完整程序见附录”等制作痕迹。必要的数据指代必须
  改为材料、角度、场景、区域或实验条件。
- 正文不得出现“满足问题一对模型建立和可计算性的要求”等面向任务清单、评审或写作过程
  的自证句。
- 正文不得用“前者回答……后者回答……”“不因……预设结论”解释段落或判据的写作意图；
  条件、判据、结果和边界应直接构成论证。
- 正文不得出现“首次出现处定义”“见下文定义”“未在表中列出的量另行定义”等阅读指引；
  变量必须在实际出现位置完成定义，不预告定义安排。
- 所有段内 `\paragraph{...}` 和列表项加粗引导语均以中文冒号引出说明，不使用句号；
- 同一语义组中的多条坐标、约束或状态方程使用左大括号与 `aligned`，共用一个公式编号；
- 大括号公式内部各行末尾不留逗号、句号或分号；
- 复杂求解流程使用白底、黑灰线、普通矩形、标准菱形和直线/正交箭头的人工学术流程图，
  默认不使用颜色编码，不使用 AI 模板化装饰；
- 问题关系、分题求解、算法迭代、数值计算和状态决策职责没有混在同一条长链；流程节点
  能对应脚本步骤，所有判断出边有条件，正文解释关键回退；
- 正文流程图不展示任务契约、结果文件、Excel、支撑材料、模板检查或结果交付等生产流水线；
- 流程图已在 `求解/图表清单.md` 登记并保留可编辑源，最终 PDF 缩放后文字和箭头可读；
- 流程节点的边框与文字为同一形状对象，框内文字实际包围盒不越过安全内边距；箭头接边界
  锚点，回路线不穿框，示意图外置标注均有对象锚线；
- `.layout.json` 的逐连接数量、已检查数量和明细数量完全一致，失败数为 0；每条连接的
  两端误差、非目标交叉、文字间距、节点内部侵入和最终渲染结果均通过；
- 逐线语义清单覆盖运动、边界、引线、主轴、分支和反馈等全部线族；有向线箭头方向正确且
  可见，无向线不误加箭头，线型含义与正文和代码一致；
- 整图审计不能替代逐连接审计；移动任一节点、标签、连接或画布后，必须重新检查全部连接；
- 每个正式几何图、关系图和流程图都有同名 `.layout.json` 且 `pass=true`；LaTeX 未使用
  `trim`、`clip` 或非等比缩放修复源图；
- 几何示意图采用固定画布、固定纵横比和对象锚定标注；正文仅等比例缩放，最终渲染无错位、
  压线、遮挡或越界；
- 每一幅编号图和每一张编号表都在正文中被编号引用，并与对象、读数、关系、判据或结论形成合理
  交互；不要求逐项套固定分析段。完全脱离上下文的“见图/表”转人工复核；
- 图型与变量维度、比较任务和读数方式匹配，不因 A/B 题号套图；热力图仅在二维结构和颜色变量均不可替代时使用并说明理由；
- 三个以上对象、变量或问题之间存在依赖，而正文仍以长段逐项解释时，检查关系图、结构图
  或机理图能否更直接表达；可视化应替代重复文字，不把简单列表强制画图。
- A 题存在关键坐标、受力、投影、遮挡或截面判据时，检查是否有与模型定义一致的解释图；
  B 题存在路径、调度、定位或空间分配时，检查是否有可直接核验的方案图；
- 数值图可追溯到结果文件和生成脚本，示意图保留可编辑源文件；不得在演示软件中手工移动
  数据点或改变数值几何关系；
- 数据图注册表逐图记录唯一证据命题、claim_id、源数据、生成器、矢量成品、最终插入宽度和
  最小字号；背景、配色、单位、灰度、色觉安全、图例遮挡与最终页面检查全部通过；
- 关系图、流程图、机理图和几何图只采用 TikZ 或 Visio 风格族；TikZ 使用统一样式表，Visio
  使用基础形状、吸附和动态连接线；最终 PDF/SVG 无渐变、阴影、装饰图标、圆角卡片体系或默认主题；
- 图形审美以最终插入尺寸为准：刻度和图例不低于 8 pt，线型、点型和颜色在灰度打印下仍可区分，
  原尺寸、缩略图与整页三种视图均完成复核；
- 标题层级、符号、图表编号、有效数字和术语统一；
- 标题树属于分问题、总章统领、问题嵌入或模块驱动中的合理一种，并与各问共享关系一致；
  不把优秀论文常见标题机械拼接成固定目录；
- 一级标题承担论证阶段，二级标题承担问题或模块，三级标题承担关键定义、求解、结果或验证；
  不存在只有一两句的空节和公式级碎片标题；
- 标题采用最少充分层级：每问默认 2--4 个二级标题，超过 5 个逐项证明不能合并；正文二级
  标题超过 24 个时必须有压缩审查记录；三级标题只服务至少两个并列且内容充实的子模块；
- 符号说明独立成章，使用“符号—含义—单位”三列表；含义按内容写物理或数学含义，无单位项写“—”；
- 默认模型假设位于符号说明之前；例外须说明为何必须先定义符号才能准确陈述假设；
- 最后一问之后能定位跨问题验证与共同边界；存在两类以上实质性跨问题证据时独立设章，
  否则允许在逐问验证后用一节汇总，不为满足章名伪造收敛、扰动或复算实验；
- 一级标题采用中文序数，二级和三级分别采用两段、三段编号，编号目录不深入第四级；
- 一级、二级标题不使用“模型的建立”“算法的实施”“计算结果”等无对象的空泛名称；
- 版面紧凑但可读，不通过重复题面、放大图表、缩小字体、修改边距或行距规避官方 30 页上限。
- 问题一、问题二等分问章节之间不得存在 `\newpage`、`\clearpage` 或章节末尾
  `\FloatBarrier` 造成的固定换页；上一问结束后仍有可用空间却把下一问推到新页，记为 P2。
- 附录有支撑材料索引、运行环境、逐问命令和按问题组织的真实代码；代码页无越界且没有
  身份、外部署名、个人路径或删节占位。
- 代码注释密度自然，只保留关键公式、边界、非显然参数和易错步骤；不存在统一套用的
  “输入—输出—对应公式”注释块、逐行释义、长分隔线、对话语气或无意义封装。
- 最终支撑材料按白名单归拢，不含 `metrics.json`、任务契约、证据矩阵、运行环境 JSON、
  图形注册表、布局记录、检查报告、日志、缓存、测试文件、临时文件、重复产物或废弃版本；
  题目明确要求的正式文件或运行必需配置除外。
- 核心模型、关键结果和决定性验证均在正文闭环，附录只承载复现与补充材料；不得为了引用
  附录而在各问结尾重复暴露程序、代码或文件信息。
- `审查/去AI化审查.json` 为 PASS；不存在成片模板连接词、空泛拔高、机械排比、重复小结或聊天式残留。

官方口径不超过 30 页是页数放行门槛，不设置页数下限或 23--27 页等第二软区间。与邻近优秀论文
对比的是论证覆盖率和证据强度，PDF 总页数不参与正文放行。

## 12 维评分卡

每维 0-5 分。`5` 表示优秀论文竞争力，`4` 表示高质量可提交，`3` 表示明显短板。

打分前审查者先读
[../cumcm/references/grading-profile.md](../cumcm/references/grading-profile.md)，按官方
评阅视角复核：章程四标准（假设合理性、建模创造性、结果正确性、表述清晰性）对应到
各维度；逐问核对该画像第三节的跨年扣分模式（算法黑箱、无误差分析、外推失控、重复
计数、只报最优值不给方案、方法堆积、套路化表面文章等），命中项写入整改清单并压低
对应维度分。历史真题项目在盲测冻结后，还应加载同题
`cumcm-blind-benchmark/assets/grading-standards/<year><problem>.md` 的逐问加分/扣分点
逐条比对；非历史题或未冻结时不得读取该库。

| 维度 | 5 分标准 |
|---|---|
| 题意与口径 | 难点和歧义被识别，选择有验证且每问精准闭环 |
| 数据理解 | 字段、单位、异常和数据限制均有依据 |
| 模型适配 | 候选由题目结构产生，先过科学硬门槛，主模型经真实异构路线挑战 |
| 数学严谨 | 推导连续，定义域、约束、单位和边界一致 |
| 求解实现 | 算法设置透明，数值分辨率、收敛以及最优性/可识别性证据充分 |
| 验证强度 | 有独立交叉验证与稳健性证据，判定标准清楚 |
| 结果价值 | 答案充分性全部通过，结果直接回答题目并含不确定性、近优性和适用边界 |
| 证据追溯 | 结论、指标、图表和脚本双向可追踪 |
| 可复现性 | 从原始数据可重跑，结果在容差内一致 |
| 写作原创 | 表达独立、紧凑，无复刻或模板腔 |
| 可视表达 | 图表必要、可读、定量且服务论证 |
| 提交就绪 | 匿名、格式、编译、附录和文件大小全部合规 |

判定：

- `PASS_EXCELLENT_CANDIDATE`：硬门槛全过，总分 ≥54/60，且每一维度 ≥4；
- `PASS_HIGH_QUALITY_DRAFT`：硬门槛全过，总分 ≥48/60，且每一维度 ≥3；
- `FAIL`：其余情况。

## 审查报告

写 `审查/审查报告.md`，并按
[references/scorecard-schema.md](references/scorecard-schema.md) 写 `审查/评分卡.json`：

```markdown
# CUMCM 优秀论文候选审查报告

## 结论
## 硬门槛
## 原创性
## 逐问科学性
## 数值与证据链
## 复现抽查
## 摘要与正文
## 全文逐段内容审查
## 逐问深度与编译页数反馈
## 排版视觉
## 图型适配与去 AI 化
## 12 维评分卡
## 整改清单
```

整改项按 `P0 合规/真实性`、`P1 结论与验证`、`P2 表达与排版` 排序，并明确回退到求解或论文阶段。
逐节阅读完成后按
[../cumcm/references/content-quality.md](../cumcm/references/content-quality.md)
写 `审查/内容审查.json`；未声明 `full_text_read: true`、章节未全覆盖或仍有 P0/P1 时，
不得评为高水平候选。

最终发布还必须由未参与求解和写作的只读评审者生成 `审查/独立评审.json`。该文件需包含
`pass`、`total`、`minimum_dimension`、`p0_findings`、`p1_findings` 和数值抽查记录；存在任何 P0/P1 时不得放行。
