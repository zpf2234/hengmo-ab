---
name: cumcm-paper
description: 数学建模国赛优秀论文导向的半自动撰写、章节编排与编译总控技能。仅在方法结果获用户确认后生成全文目录、大纲和页数方案；再次获确认后才把证据写入单一总稿并执行编译审查。
---

# CUMCM 论文阶段

只从证据写论文。证据不足就回 `cumcm-solve` 补算，不编造数值、文献、图表或验证。

## 冲突裁定总则

不同规则发生冲突时，依次采用：当年最新官方规范与 AI 使用规定；用户在当前项目中的最新明确
确认；本地优秀论文一手原页所展示的稳定结构、语言、篇幅和算法成文规律；项目内较早形成的统计
阈值、负面清单与模板默认值。后位规则不得反向覆盖前位规则。优秀论文用于裁定写作规律，不用其
旧年份格式、单位错误、编号错误或验证缺口覆盖最新官方要求。发现旧技能与最新口径冲突时直接修订
旧规则，不同时保留两套互相矛盾的要求。

## 先决条件

- `求解/求解计划.md`
- 每问可运行脚本、`结果/metrics.json` 和结果表
- `求解/证据矩阵.csv`
- `求解/图表清单.md`
- `求解/证据审计.md` 为 PASS
- `审查/用户确认节点.json` 中方法与结果确认有效；核验规则见
  [半自动论文工作流](../cumcm/references/semi-automatic-workflow.md)

## 章节阶段链

先完整读取 [references/section-chain-contract.md](references/section-chain-contract.md)，再按论证生成顺序调用：

```text
outline(STAGE) → restatement(STAGE) → analysis(STAGE) → assumptions(STAGE)
  → cumcm-notation → model-writing(STAGE) → cumcm-results-validation
  → cumcm-notation（全文公式复核）
  → evaluation(STAGE) → references(STAGE) → appendix(STAGE) → abstract(STAGE)
  → cumcm-deai → language-audit(STAGE) → 编译与 cumcm-review
```

阶段规则分别位于
[../cumcm-outline/STAGE.md](../cumcm-outline/STAGE.md)、
[../cumcm-restatement/STAGE.md](../cumcm-restatement/STAGE.md)、
[../cumcm-analysis/STAGE.md](../cumcm-analysis/STAGE.md)、
[../cumcm-assumptions/STAGE.md](../cumcm-assumptions/STAGE.md)、
[../cumcm-model-writing/STAGE.md](../cumcm-model-writing/STAGE.md)、
[../cumcm-language-audit/STAGE.md](../cumcm-language-audit/STAGE.md)、
[../cumcm-evaluation/STAGE.md](../cumcm-evaluation/STAGE.md)、
[../cumcm-references/STAGE.md](../cumcm-references/STAGE.md)、
[../cumcm-appendix/STAGE.md](../cumcm-appendix/STAGE.md) 和
[../cumcm-abstract/STAGE.md](../cumcm-abstract/STAGE.md)。按执行顺序完整读取对应阶段，不把它们
作为独立 skill 调用。

`cumcm-figures` 与 `cumcm-diagrams` 贯穿各阶段：图进入正文前必须通过对应门禁。不得跳过
阶段规则和保留的专项技能后用总控技能一次性自由生成全文。
所有章节子技能只向 `论文/论文.tex` 的对应 section 写入内容，不生成 `0.摘要.tex`、
`1.问题重述.tex` 等章节文件，也不使用章节级 `\input`、`\include` 或 subfiles。
职责链可以分阶段执行，但最终源码始终是一个总稿。
上一阶段门禁不通过时回退修订或补算，禁止用说明性文字遮盖证据缺口。
用户要求“直接生成整篇”也不覆盖本项目的半自动确认规则。方法结果确认后，先只生成全文目录、
逐节大纲和各问/共享章节页数判断并停下；用户再次确认无误并要求开始初稿后，才创建模板、执行
逐问清单、增量成文、编译和页数反馈闭环。规划上界不超过 30 页；成稿后页数只检查是否超过官方
上限，内容完整性由逐问门禁独立判断。

前置章节同时读 [references/front-section-content-standard.md](references/front-section-content-standard.md)，
逐问主体同时读 [references/model-result-content-standard.md](references/model-result-content-standard.md)，
并完整读取 [references/question-depth-and-pagination.md](references/question-depth-and-pagination.md)，
收束章节同时读 [references/closing-section-content-standard.md](references/closing-section-content-standard.md)。
这些统计只用于发现职责缺口和冗余，不能成为字数、标题数、图数或文献数配额。

同时读 [references/official-rules.md](references/official-rules.md)、
[references/sections.md](references/sections.md) 与
[references/a053-argument-chain.md](references/a053-argument-chain.md)。A053 只冻结可迁移的功能推进链，
不得复用其具体模型、符号、公式、数值、图表、标题或句子。LaTeX 细节见
[references/latex-template.md](references/latex-template.md)。本工作区的人工写作与排版硬规则见
[references/style-profile.md](references/style-profile.md)。若本地有优秀论文语料，同时读
[../cumcm/references/benchmarking.md](../cumcm/references/benchmarking.md) 和
[../cumcm/references/full-paper-census.md](../cumcm/references/full-paper-census.md)，
按全文职责链使用普查，不把显式标题率解释为内容缺失；并按
[../cumcm/references/corpus-alignment.md](../cumcm/references/corpus-alignment.md)
在标题、摘要、标题树、流程图和附录阶段执行一手语料对照与雷点自查，遵守其中的隔离边界
与口径矛盾裁定。
图形编排同时遵守
[../cumcm/references/figure-routing.md](../cumcm/references/figure-routing.md)。
工作区启用 `paper-figure-router`、`paper-visio` 和 `paper-tikz` 时，同时完整读取
[../cumcm/references/figure-mcp-routing.md](../cumcm/references/figure-mcp-routing.md)，按“命题与位置预留—小节成稿—
绘图生成—注册—插入—最终页面复核”的顺序调动；数据图由求解侧 Python 代码直接绘制。图中标题、
节点、符号和阈值不得先于对应小节成稿定死，也不允许到全文结束后批量补装饰图。
流程图编排同时遵守
[../cumcm/references/flowchart-routing.md](../cumcm/references/flowchart-routing.md)。
摘要写作同时遵守
[../cumcm/references/abstract-writing.md](../cumcm/references/abstract-writing.md)。
标题层级与章节路由同时遵守
[../cumcm/references/title-structure.md](../cumcm/references/title-structure.md)。
前置功能、独立符号章、跨问题验证职责、标题信息密度和篇幅路由同时遵守
[../cumcm/references/paper-architecture.md](../cumcm/references/paper-architecture.md)。
封面总标题同时遵守
[../cumcm/references/paper-title.md](../cumcm/references/paper-title.md)，方法词必须由模型、
实现与验证共同支撑。
几何图与流程图布局同时遵守
[../cumcm/references/diagram-layout.md](../cumcm/references/diagram-layout.md)，使用内嵌节点
文字、对象锚定标注、固定画布和同名布局审计文件。
几何机理图还须遵守
[../cumcm/references/geometry-diagram-routing.md](../cumcm/references/geometry-diagram-routing.md)，
锁定 Office 文本坐标，检查实际字形与轨迹、轮廓和实体的碰撞。
所有几何图、关系图和流程图还须遵守
[../cumcm/references/diagram-connection-audit.md](../cumcm/references/diagram-connection-audit.md)，
逐条验收引线、箭头、判断分支和反馈回路，核对有向/无向属性、箭头朝向与物理/算法含义，
再独立验收整图构图。
数据图还须完整读取
[../cumcm-figures/references/aesthetic-standard.md](../cumcm-figures/references/aesthetic-standard.md)。国一/国奖候选同时读取
[../cumcm-figures/references/signature-figure-standard.md](../cumcm-figures/references/signature-figure-standard.md)，
并完整读取 [../cumcm-figures/references/visual-identity-and-archetypes.md](../cumcm-figures/references/visual-identity-and-archetypes.md)，
复制规划模板，在标题树与图形职责预算阶段规划特色主视觉图，而不是正文完成后临时美化普通图。
特色图必须与核心命题、关键读数、机制解释或答案形成清楚联系，但不要求固定的前后说明顺序；若只是多张常规图拼接或仅换配色，
则不得计为特色图。确实不适合时允许经独立审查的有理由豁免，不为满足数量强制拼图。
结构图、机理图、几何图和流程图还须完整读取
[../cumcm-diagrams/references/tikz-visio-standard.md](../cumcm-diagrams/references/tikz-visio-standard.md)。
二者分别建立 `审查/figure-registry.json` 与 `审查/diagram-registry.json`，不能仅凭正文截图验收。
附录编排同时遵守
[../cumcm/references/appendix-structure.md](../cumcm/references/appendix-structure.md)。
全文内容、摘要语义强调、默认前置顺序和标题压缩同时遵守
[../cumcm/references/content-quality.md](../cumcm/references/content-quality.md)。
数学写作（变量引入、公式动机、推导叙事、数值精度）同时遵守
[../cumcm/references/mathematical-writing.md](../cumcm/references/mathematical-writing.md)。
论证叙事（段落职责、证据密度、连接词、跨问衔接）同时遵守
[../cumcm/references/argumentation-patterns.md](../cumcm/references/argumentation-patterns.md)。
表格设计（类型选择、列结构、排序、数值格式、图表分工）同时遵守
[../cumcm/references/table-design.md](../cumcm/references/table-design.md)。
模型选择与答案结论同时遵守
[../cumcm/references/model-selection-and-answer-quality.md](../cumcm/references/model-selection-and-answer-quality.md)，
只写真实试算过的候选与冻结后的选择证据。

## 原创性约束

- 优秀论文只用于质量校准，不复用标题、摘要句式、段落结构、专属模型链、图号、数值或代码。
- 同题常用术语可以一致，但推导组织、解释和结论必须来自本项目证据。
- 禁止把参考论文的“首先—接着—然后—最后”段落替换少量词后使用。
- 成稿后必须运行相似度审计；高风险时重写相关段落，而不是机械同义替换。

## 去 AI 化

先执行 `cumcm-deai`：逐部分对照优秀论文同部分原文与
`cumcm-deai/references/corpus-voice-profile.md` 的声纹画像，改写 AI 味段落并通过
`audit_corpus_voice.py` 声纹审计（段首同构、句长节奏、连接词密度锚定 50 篇语料分布）。
再按 [语言审计阶段](../cumcm-language-audit/STAGE.md) 的项目内三层检查逐章复核，写 `审查/去AI化审查.json`。目标是让文字具体、自然、可辩护，不是迎合检测器：

- 摘要和正文采用参赛队员向评委讲述实际理解与求解过程的视角，允许自然、较多地使用“我们”；
  不设“我们”次数上限，也不把第一人称复数本身判为 AI 味；
- 删除无逻辑作用的“此外、值得注意的是、综上所述”和机械“首先—其次—最后”；
- 把“显著、卓越、具有重要意义、应用前景广阔”等空泛判断改成可观察结果、适用范围或局限；
- 删除“便于、有助于、本文报告、不声明、不构成证明、不能据此宣称”等自我评价或元叙事，
  只保留模型结构、数值事实和客观不确定性；
- 正文按 A053 式“对象/现象—数学关系—公式或算法—定量结果—局部检验”推进；
  原稿、重构、统一口径、计数闭合、证据边界、模型链和门禁说明只进审查文件；
- 避免每段同构、强凑三点、重复小结和同义词轮换，允许长短句自然变化；
- 智能算法的执行过程可以采用 `Step1`、`Step2` 等步骤列表；步骤规整本身不判为 AI 味，只要每步
  写清本题变量、运算、判断、约束处理和输出，不照抄通用算法原理，也不把简单算法强拆成四步；
- 保留技术术语、公式、数值、单位、引用和 `claim_id` 口径，不为“更像人”改动事实；
- 审查结果必须 `pass: true`，并列出已修改模式与仍保留表达的技术理由。

## 论文组织

总标题在证据稳定后确定，优先采用“对象 + 核心动作”或“基于核心机理的对象 + 核心动作”。
对象与动作必须出现；方法词是可选项，不为增加学术感堆叠算法，也不使用正文未严格兑现的
“非线性、智能、AI、深度学习”等升格词。

唯一正文模板资产位于：

```text
.agents/skills/cumcm-paper/assets/latex-template/论文.tex
.agents/skills/cumcm-paper/assets/latex-template/format.cls
.agents/skills/cumcm-paper/assets/latex-template/fonts/
```

论文前五个一级章固定如下；第五章内部再按问题依赖选择共享模型或逐问展开，后续结果验证、
评价与附录结构按真实证据量调整：

```text
摘要
一、问题重述
二、问题分析
三、模型假设
四、符号说明
五、模型的建立与求解
结果检验（仅在题目确实需要跨问检验时独立设章）
模型评价、改进与推广
AI工具使用声明（2026 年置于参考文献之前；按官方二选一原文填写）
参考文献
附录与支撑材料清单
```

问题重述与问题分析必须使用两个独立一级章。问题重述固定采用“一、问题重述—1.1 问题背景—
1.2 问题提出”的标题结构：背景只用一个紧凑段落交代对象与场景；问题提出先概括共同条件，
再以段内加粗的“问题一：”“问题二：”逐问重述对象、输入、约束、任务和输出。各分问不得升为
三级标题。重述必须用自己的话重新组织，不得照抄题面，也不得写问题分析、模型、求解、结果、
验证、评价、改进或推广。问题分析另行说明数据特征、难点、问题依赖和模型路线。
不得使用“问题重述与分析”合并章，也不得在模型假设
标题中加入“计算口径、说明、若干问题”等解释性词。默认先写模型假设、再写符号说明；
只有符号定义是理解假设不可缺少的前提时例外并记录理由。符号说明不得
埋入其他章节；第四章标题后直接放“符号—含义—单位”三列表，“含义”按内容写物理含义或数学
含义，无单位项写“—”。主符号优先简洁，能由上下文区分时不加下标，只在真实对象或编号需要时
保留一层必要索引。必要说明只陈述共同约定或适用范围且保持一至两句，不作评价。具体公式推导、参数求取和数值求解过程
集中放入第五章；问题分析只保留高层思路与路线。各问的结果检验优先就地完成；只有题目确实需要跨问检验且存在
两类以上实质内容时，才独立设“结果检验”章。
一级标题由模板显示为中文序数，目录深度控制在三级。第五章通常以“问题一”“问题二”作为二级标题；
只有短任务名确能帮助定位时才写“问题一：临界角求解”这类形式。每问默认不设或只设 1--3 个三级标题，
同一问题超过 3 个时先检查能否连续成文或改用段内短语；语料中的标题数和分问页数不是填充目标。
固定一级章顺序不变，但第五章内的小标题须在正文稳定后从真实内容中提取。优先使用“受力分析”
“运动方程”“目标函数”“参数辨识”“数值求解”“误差分析”等简洁、可展示的学科表达，一般
4--10 个汉字；不强行拼成“对象 + 关系/动作 + 必要条件”的满载标题。不得使用“问题一模型的建立与求解”
“问题二求解与分析”，也不得把“口径、审计、闭环、证据链、门禁、误差预算、作答映射”等内部职责写进标题。
问题标题后可直接进入正文，不强制补路线段，也不为避免标题相邻而制造过渡话。正文从本题对象、条件、
关系或本队实际计算动作起句；只有路线确实复杂时才用一两句交代。审计结论、原稿与重构说明、口径核对、
门禁状态、证据边界或模型链总结一律留在 `审查/`，不得改写成正文中的读者导航。
成文前先按各问的推导难度、结果重要性和必要检验量确定大致页数区间，并说明判断依据；再把前置
章节、评价、AI 声明和参考文献计入共享篇幅，确认规划上界不超过 30 页。实际成稿不要求各问等长，也不要求八项职责
分别单独占章。承上启下或直接复用前问模型的问题可以短写；承担核心机理、关键优化、分段讨论或
主要验证的问题应获得更多篇幅。职责即使合并在同一节或同一段中，仍须在逐问深度清单中逐项可追溯。
成文前由总控自行判断核心问题，不等待用户指定：综合考察该问对后续问题的依赖中心性、本题特有
推导量、求解与结论风险、题面输出的重要性以及解释和验证所需证据量，区分核心问、支撑问和过渡问。
该判断只用于内部篇幅路由，不在论文中出现“核心问判定、评分权重、审计结论”等过程性措辞。

每问必须闭环：

1. 界定口径、变量、目标和约束；
2. 说明方法为何适配；
   当候选路线实质影响答案时，给出决定性比较和取舍；
3. 给出必要且连续的数学表达；
4. 说明求解过程与参数来源；
5. 展示关键结果及不确定性；
6. 用独立验证支撑可信度；
7. 用具体结论直接回答原问，不设置“本问回答”“本文的回答”等模板标签。

上述职责必须在进入下一问前完成：本问结果给出现实含义，再按需要用复算、对照、扰动或边界情形检验，
最后直接回答原问。不得把所有结果解释和局部检验推迟到全文末尾。只有题目确实需要跨问检验，且存在两类以上实质内容时，
才设置紧凑的“结果检验”或等价章节。不为汇总计数、评述证据边界或总结模型链单独设章。

以上七步还须落入逐问深度清单的八项结构化门槛：题面要求、模型特有推导、参数来源、求解契约、
结果解释、独立验证、风险响应和最终作答映射。独立验证与风险响应是两个职责：前者排查同源错误，
后者说明结论在扰动、边界或失效情形下如何变化。

不按固定公式数、图数或字数填充。公式服务于可复现推导，图表服务于关键结论；按官方唯一口径
计算的正文不得超过 30 页，不另设页数下限。

模型选择跨越多问时放在问题分析；只影响单问时放在该问模型小节。只写最终采用路线及真正影响
答案的简短理由，不在正文制作候选模型、方法选择或验证结果对照表，也不展示内部试错、文件名或
审查门禁。若基本规律唯一，用一句话说明主模型和独立复算路线即可。

模型评价与逐问验证不得混为一体。逐问验证回答结果是否可信；全文评价则按“结构/方法—已展示证据—
可靠性”“触发条件—受影响结论—证据范围”“局限—新增信息或处理—可验证改进”组织，推广再说明
保持不变的机制和必须重估的参数、假设或约束。不重复摘要，不罗列未实现方法。

## 增量成文纪律

- 先运行 `audit_user_confirmations.py --phase paper-plan`；未通过时不得进入 outline 或接触论文模板。
  通过后按 [../cumcm-outline/STAGE.md](../cumcm-outline/STAGE.md) 创建
  `审查/逐问深度清单.json`；按 [references/a053-argument-chain.md](references/a053-argument-chain.md)
  逐问冻结角色、计划页数区间及依据、题目化小节树、完整推导路径、结果命题、验证/边界计划、表达载体、题面要求以及
  八项职责的本题实质任务与求解侧来源证据，再运行 `audit_question_depth.py --phase prewrite`。未得到 `PASS_PREWRITE_READINESS`
  时回 `cumcm-solve` 补证据，不得开始自由铺写正文。计划页数只控制各问轻重，不是成稿配额；
  同一来源可支撑相邻职责，但每项任务、预期结论和验证对象必须分别可核对；结构性条件不适用时
  必须写明理由，且不得拿尚未成文的论文正文自证。将全文目录、逐节大纲、各问及共享章节页数
  判断完整展示给用户后停下，不创建 `论文/论文.tex`。
- 用户明确确认目录、大纲和页数无误并要求开始初稿后，记录第二次确认并运行
  `audit_user_confirmations.py --phase draft`。未通过时不得继续；通过后才从单一总稿模板落盘
  `论文/论文.tex`，写入摘要并完成首次编译，再写正文；不得长时间只在
  内存中组织整篇稿件。
- 每完成一问，先运行
  `audit_question_depth.py --phase question --question-id qN`；该问八项职责都具备
  `论文/论文.tex#具体锚点` 且条件门禁闭合，得到 `PASS_QUESTION_CONTENT` 后再继续下一问。
  八项是责任覆盖，不是八个同形小节；允许同一段、公式、图表或证据同时承担多项责任。
  全部问题完成后再运行 `audit_question_depth.py --phase content`，确认整篇逐问闭环；
  每完成 1--2 个 section 就在同一 `论文/论文.tex` 中保存并编译，及时修复语法、引用、字体、
  图片和越界问题。
- 模型、结果和验证公式稳定后回到 `cumcm-notation`，运行全文公式可读性审计；随后完成评价、AI 工具
  使用声明、参考文献、附录和定稿摘要。所有计入或影响官方正文口径的章节完成之前，增量编译只作诊断，
  不执行完整初稿放行。
- 第一份可交付初稿候选只能在上述章节全部完成后两遍编译，再用 `audit_question_depth.py --record-compile` 记录
  `appendix:start - body:start`、PDF 总页数和当前 PDF SHA-256。正文与总页数必须分开报告。
- 记录后必须执行 `check_first_draft_gate.py --root .`。该命令是阶段转换的唯一机器闸门：只有
  `PASS_FIRST_DELIVERABLE_DRAFT` 才首次产生初稿。超过 30 页的 PDF 记为 `INTERNAL_FAILED_BUILD`、
  `deliverable=false`；页数较短不自动失败，但逐问门禁有缺口时仍须回到相应推导、参数来源、求解
  契约、结果解释、独立验证、风险边界或漏答项，完成后重新编译。
- 页数只使用官方正文定义，不再建立第二套“实质正文”页数或语料软校准带。页数合规后仍须
  逐问通过八项深度门槛；正文主体、AI 声明、参考文献和附录完成后再做收敛编译、最终深度审计与逐页视觉验收。
- 初稿内部修订若改变用户已确认的主方法、最终结果、全文目录或页数计划，立即停止写作并退回对应
  确认点；仅修复措辞、排版、引用或不改变上述内容的局部错误时无需重复确认。

## 摘要

摘要不得超过官方规定的一页。先写每问的四元组，再压缩成自然段：

```text
问题目标 + 方法及选择理由 + 关键定量结果（含单位） + 验证/稳健性结论
```

首段交代总问题和统一思路，末段只总结最重要的决策与适用边界。禁止主观自夸、公式、引用、
未在 `metrics.json` 中出现的数字和参考论文句式。字数由模板实排决定，不设脱离版式的固定配额。

关键词按模板使用整行黑体，标签与关键词内容均加粗；这是首页指定格式，不计入摘要正文的语义强调。摘要正文粗体只标记核心方法与最终结论；最终结论可包含决定答案的数值、
单位和不确定性。优先使用 `\keymethod{...}` 与 `\keyresult{...}`，每问原则上各突出一个。
普通参数、中间数值、过程动作和验证细节不加粗，禁止整段或连续粗体。摘要不得出现 AI、
人工智能、提示词、prompt、工具名、辅助过程、审查过程或写作策略。

## 正文密度

- 正文只按官方口径计算：`appendix:start - body:start`，即正文主体首页至附录开始前一页；
  其中包含正文主体、AI 工具使用声明和参考文献，不含摘要与附录。
- 30 页及当年更低的官方上限是唯一页数硬门槛；项目不设页数下限。不得用重复题面、放大图表或
  稀疏排版制造篇幅。
- 50 篇语料的 PDF 总页数最小值/Q1/中位数/Q3 为 24/34/42/56；旧脚本所得“参考文献前页数”
  近似中位数 23 页不符合现行官方正文定义，只保留为历史记录，不进入页数门禁或扩写目标。
- AI 工具使用声明置于参考文献之前，二者紧凑连续排版，不强制各自另起一页；保留
  `\label{ai-statement:start}` 与 `\label{references:start}` 作为顺序锚点，但页数边界只由
  `\label{body:start}` 和 `\label{appendix:start}` 决定。
- 各分问章节连续排版；问题一、问题二等章节之间不使用 `\newpage`、`\clearpage` 或章节末尾
  `\FloatBarrier` 强制换页。页尾空间足够容纳标题和至少两行正文时，下一问直接接排。
- 从附录首页起不设页数上限；附录页数按完整代码和支撑材料自然形成，仅受文件大小、完整性和可读性约束。
- 语料页数、图表数只作校准，不追求达到中位数或上四分位数。
- 前置重述、分析、假设和符号通常控制在约 4 页以内；这是密度检查，不得以缩小字号或
  删除必要定义实现。
- 每一幅编号图和每一张编号表都应与正文形成自然交互：正文可用其呈现对象、支撑读数、推进推导、
  说明判据或承接结论，不要求逐项套用固定分析段。图表题注、
  编号引用句式与解读文字同时遵守
  [../cumcm/references/figure-table-narration.md](../cumcm/references/figure-table-narration.md)：
  题注为简洁名词短语（禁空泛题注），凡编号图表必被正文引用；自动审计只硬查题注、编号引用和
  基本交互，不以固定“观察—数值—原因—影响”句式判定失败。
- 删除重复题面、教科书式算法介绍、无数据评价、重复流程图和不参与结论的装饰图。
- 摘要和正文不得出现附件文件名、工作表名、代码、程序、脚本、CSV、JSON、文件路径、
  生成过程、运行命令或“完整程序见附录”等制作痕迹。必要的数据指代改写为材料、角度、
  时段、区域或实验条件；实现与文件信息只放附录。
- 删除“满足问题一对模型建立和可计算性的要求”“由此证明本文写法正确”等面向任务清单
  或评审的解释句。结论只保留模型事实、定量结果、验证和边界。
- 删除“前者回答……后者回答……”“不因……预设结论”等替读者解释论证意图的元叙事；
  物理条件、数据判据和结果直接陈述，不再补一句说明它们分别“回答什么”。
- 符号和参数应在符号表或首次使用处直接定义，但正文不得写“首次出现处定义”“见下文定义”
  “未在表中列出的量另行定义”等阅读指引或写作安排。
- 对关键假设、参数和约束给出来源、范围或敏感性影响。
- 各问最终答案和结论性数值使用克制的粗体强调，中间参数和普通计算值保持常规字重。
- 中文 LaTeX 使用宋体正文时，先确认 `\textbf` 在最终 PDF 中确实产生可见粗体；若字体无粗体
  字形，应对关键词、核心方法和关键结果切换黑体或启用模板已有的伪粗体，不能只在源码中形式加粗。
- 先区分问题关系、分题求解、算法迭代、数值计算和状态决策，再决定是否画图；只有真实
  复杂依赖、三个以上不可合并步骤、判断或回退才使用流程图。禁止把任务契约、结果文件、
  Excel、支撑材料和结果交付拼成论文流程图。
- 三个以上相互依赖的对象、变量或问题若用图能明显缩短说明，优先制作关系图、结构图或
  机理图；表格仍用于精确比较，公式仍用于定义和推导。图形必须替代一段真实说明，不能
  与正文重复，也不能为增加图数而可视化简单列表。
- 问题关系复杂时至少规划一幅关系图、结构图或机理图；复杂算法再增加流程图。不得把
  “1--2 幅流程图”机械设为每篇配额。
- 保留 `.drawio`、TikZ、Python 或 `.vsdx` 等可编辑源文件和 PDF/SVG 矢量输出；禁止渐变、
  阴影、圆角卡片、装饰图标和模板化彩色流程图；流程图默认使用白底黑灰线和基础几何。
- 节点文字必须内嵌在矩形或菱形自身，不得用独立文本框覆盖空框；示意图标注使用对象锚线。
  源图留白在生成器中解决，LaTeX 不得用 `trim`、`clip` 或非等比缩放修图。
- 图内公式和数学标签一律透明，放在相应线条周边；任何线段、轨迹、轮廓、尺寸线和箭头不得被
  文字遮断或为标签留白。
- 按 `style-profile.md` 的 A/B 制图路由做漏图与冗余检查：图数不设上下限，完全由待证明命题和
  不可替代证据职责决定。正文可以出现 4、6 幅或更多图；同一命题的多图须职责互补且与正文合理交互，
  不能为“版面饱满”增加重复图。语料密度只作非阻断参照。
- 对显示不同演化过程、多时间节点或多临界状态的证据，优先采用单图号下的多面板子图拼图（Subfigures）
  集中呈现；面板数量完全按数据逻辑灵活选择（2、3、4 面板均可），严禁为凑格式机械拼图。
- 单面板不放图内标题；两幅强耦合图可由总图题以“左/右”说明，三幅及以上或条件不同的面板
  在各面板下方居中放小标题，再在整组下方放总图题。
- 不用默认单折线或默认柱图补版面；连续曲线必须同时呈现事件、阈值、边界、阶段、基线或
  不确定性中的至少一层，方案比较优先点—区间图或表格。
- 官方口径正文（正文主体首页至附录开始前一页，包含 AI 声明和参考文献）不得超过 30 页；
  篇幅由当前题目的完整论证自然形成。版面质感借鉴国一优秀论文，但具体图型按
  `cumcm-figures/references/visual-identity-and-archetypes.md` 的原型库依证据结构选择，
  模型决策流程图、多阶段演化拼图、临界构型图、机理—结果联图均为候选原型而非固定套图。
- 几何机理、关系图和流程图默认优先 TikZ；只有复杂人工编排确有必要时回退 draw.io 或 Visio，
  并登记理由。正式结构图不使用 PowerPoint/PPTX。工程三维、动态曲线、统计诊断和批量数值图统一由 Python 代码
  （matplotlib）直接绘制；数值图不得在演示软件中手工调整数据位置。

## 公式排版硬规则

- 行内公式不编号；所有独立展示公式必须编号，禁止 `\[...\]` 和带星号的无编号环境。
- 引出展示公式的最后一句必须以中文冒号“：”结束。
- 公式末尾不得保留句号、逗号、分号或中文标点；编号后不追加标点。
- 正文引用统一写“式（1）”；多行推导用一个编号环境包裹 `aligned` 或 `split`。
- 同组并列坐标、约束、状态方程或分段条件使用左大括号和 `aligned`，整组共用一个编号；
  连续推导不机械添加大括号。
- 段内 `\paragraph{...}` 或列表项加粗短语用于引出说明时，末尾统一使用中文冒号。

## 参考文献与附录

- 只引用实际阅读并在正文使用的真实来源；逐条核对作者、题名、年份和引用位置。
- 文献数量由方法与背景需要决定，不设为凑数目标。
- 附录列出支撑材料，并收录建模实际使用的完整可运行源程序；不得使用省略号占位。
- 正文不暴露附录文件名、代码入口、程序路径或运行过程。附录可以自成复现体系，但不得让
  “完整程序见附录”成为每问结尾的机械收口。
- 摘要和正文主体不展示 AI 提示词、工具名、辅助脚注或生成过程。2026 年按官方规则在参考文献前
  设置“AI工具使用声明”，从 [official-rules.md](references/official-rules.md) 复制官方二选一原文；
  已使用时只在论文声明中简述用途，并在支撑材料压缩包内提供 `AI工具使用详情.pdf`。
  AI 工具不列入参考文献，不向第三方平台上传论文做查重或 AIGC 检测。
- 论文数值表不得手抄。由结果 CSV/JSON 生成 LaTeX 表，或由构建脚本写出表格片段；结果重跑后必须重新生成并核对。

## 编译与视觉验收

编译前运行：

```bash
python .agents/skills/cumcm-paper/scripts/audit_single_tex_delivery.py --root . --phase source
python .agents/skills/cumcm-deai/scripts/audit_corpus_voice.py --root .
python .agents/skills/cumcm-language-audit/scripts/audit_language.py --root .
python .agents/skills/cumcm-notation/scripts/audit_formula_readability.py --root .
python .agents/skills/cumcm-paper/scripts/audit_figure_table_narration.py --root .
python .agents/skills/cumcm-figures/scripts/audit_figure_style.py --root .
python .agents/skills/cumcm-diagrams/scripts/audit_diagram_style.py --root .
python .agents/skills/cumcm-paper/scripts/audit_section_chain.py --root .
```

只运行项目实际使用的图形审计；所有适用项与章节链都通过后再编译。自动扫描通过仍不能替代逐章、
最终尺寸与整页人工复核。

```bash
cd 论文
xelatex -interaction=nonstopmode 论文.tex
xelatex -interaction=nonstopmode 论文.tex
cd ..
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --record-compile
python .agents/skills/cumcm-paper/scripts/check_first_draft_gate.py --root .
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --phase final
```

验收：

- `论文/` 顶层只有 `论文.tex` 一个 TeX 总稿，且不含章节级导入命令；
- `论文.log` 无 LaTeX Error，引用与编号已收敛；
- 摘要不超过一页，官方口径正文不超过 30 页或当年更低的官方上限；
- PDF 非空且满足文件大小限制；
- 逐页检查空白页、越界、重叠、缺字、低清图、表头断裂和异常留白；
- 数值、单位、有效数字与证据矩阵一致；
- `审查/公式可读性审计.json` 为 PASS，记录的 `tex_sha256` 与当前 `论文/论文.tex` 一致；
- `审查/正文深度审计.json` 为 PASS，最新编译反馈与当前 PDF 页数和 SHA-256 一致；
- 逐节执行内容审查，确认段落职责、标题必要性、方法兑现、结论证据和适用边界；
- 运行优秀论文相似度审计并通过。
- `附件/` 已归拢实际支撑材料；最终运行
  `audit_single_tex_delivery.py --root . --phase final` 并通过。

缺少编译环境时，保留完整源码和资产，在审查报告记录未完成的视觉与编译检查。
