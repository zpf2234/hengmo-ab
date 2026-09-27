---
name: cumcm
description: 数学建模国赛（CUMCM）优秀论文导向的半自动总控技能。用于用户提供赛题与附件、要求开始求解、完成国赛论文、冲击国奖或用历年优秀论文校准质量时；先完成方法结果并等待确认，再经目录篇幅确认后串联成文与审查。
---

# CUMCM 优秀论文总控

当前稳定适用范围聚焦 CUMCM **A/B 题**：A 类侧重机理、几何、物理和高精度数值闭合；B 类侧重统计、决策、优化、生产过程和不确定性证据链。C/D/E 题不自动宣称同等稳定性，除非另行完成对应回归语料与门禁。

进入任何正式求解、论文或审查流程前，先读取
[references/current-knowledge-2026-09.md](references/current-knowledge-2026-09.md) 与
[../cumcm-paper/references/official-rules.md](../cumcm-paper/references/official-rules.md)。前者区分官方事实、
方法学参考和项目内部口径，后者只保留当前 CUMCM 格式、纪律和 AI 合规要点；规则、赛程或提交入口变化时，
按来源表重新联网核验，不把模型内置记忆或二手解读当作当年硬约束。

目标是产出具备优秀论文竞争力的完整候选稿，不承诺奖项。评价顺序固定为：
题意正确 > 模型适配 > 结果可信 > 回答完整 > 原创可复现 > 表达与排版。

## 核心原则

1. 参考优秀论文的质量分布，不复制其文字、模型链、参数、结果、代码或图形。
2. 不按 A/B 字母或算法高级感预设方法。先识别机理、预测、评价、优化、仿真或决策本质，
   支持建模视角、模型结构、求解算法三类创新，不要求基线先失败才探索；按
   [创新与组合规则](../cumcm-model-tournament/references/innovation-and-composition.md)
   验证题目依据、可行性和实际收益。硬门槛通过后比较收益与新增成本，收益相当时优先简单路线；
   基线已达标仍可因精度、速度、稳健性等有价值的改善采用新路线，不按“智能”标签加分。
3. 以官方“正文从第四页开始且不超过 30 页”为硬约束；项目构建用从正文主体首页至附录开始前一页的
   `appendix:start - body:start` 计量正文区，包含正文主体、AI 工具使用声明和参考文献，不含摘要与附录。
   项目不设页数下限；图数、表数和公式数不作配额，语料统计只用于发现职责缺口。
4. 每个关键结论必须有可运行脚本、结构化指标和图/表证据；论文只写已落盘证据。
5. 采用“独立求解—独立审查”闭环。审查不得替求解阶段发明结果。
6. 最多回退修复 3 轮；仍未通过时交付当前最佳版本并列出剩余风险。
7. 图型由数据结构和待证明结论决定，不由 A/B 题号决定；逐部分成文时检查表达，首次交付前完成全文语义、语言和原创性复核，保留事实、公式、数值和证据口径。
8. 使用 [../cumcm-paper/references/style-profile.md](../cumcm-paper/references/style-profile.md)
   统一摘要强调、客观表达、公式编号、流程图和标题层级；按
   [论证叙事规范](references/argumentation-patterns.md) 从起草起采用参赛队向评委讲述题目理解与
   求解的书面口吻，以 A053 为风格主锚；逐问按
   [建模完整性](references/per-question-understanding.md#建模完整性) 核对适用关系、条件、参数、
   求解与验证，短写或润色不免除必要职责；按
   [简洁符号与下标](references/mathematical-writing.md#简洁符号与下标) 从变量设计起不用复杂
   下标公式，保留必要短索引并拆解复杂关系；正文不展示 AI 提示词或辅助脚注。
9. 摘要使用 [references/abstract-writing.md](references/abstract-writing.md)：从逐问证据
   五元组写作，以一页成品、定量答案、清晰分段和口径一致性放行，不把经验字数写成硬规则。
10. A/B 题制图使用 [references/figure-routing.md](references/figure-routing.md)：先判图的论证
   职责和变量维度，再用 50 篇优秀论文的分布做漏图检查；经验先验不得变成固定图数或套图。
11. 流程图使用 [references/flowchart-routing.md](references/flowchart-routing.md)：区分问题关系、
    分题求解、算法迭代、数值计算和状态决策，禁止用文件生产或交付流水线替代数学逻辑。
12. 论文标题树使用 [references/title-structure.md](references/title-structure.md)：先判断各问
    的共享关系，再选择分问题一级章、总章统领、问题嵌入或模块驱动，不套固定获奖目录。
13. 附录使用 [references/appendix-structure.md](references/appendix-structure.md)：建立正文到
    逐问代码的索引，写明真实环境与命令，完整代码可超过语料均值但不得用原始数据灌页。
14. 论文架构使用 [references/paper-architecture.md](references/paper-architecture.md)：
    前置功能、独立符号章、三级标题上限、结构流派、跨问题验证职责和附录反向引用按证据层级执行；
    十章模板、标题数、流程图数和分问页数只作校准。
15. 封面总标题使用 [references/paper-title.md](references/paper-title.md)：先验证标题普查的
    OCR 与文件名，再按“对象 + 动作 + 可选核心机理”生成；不把方法词数量或未经清洗的字数
    均值设为硬规则。
15A. 用户目标为国一、国奖或一等奖时，必须完整执行
    [references/national-first-precision-and-visual-gates.md](references/national-first-precision-and-visual-gates.md)。
    此规则将结果精度、逐问证据完整性、图示必要性与公式/脚本一致性、图表正文交互和 MCP 最终图质量升级为阻断门禁，
    并覆盖本文件中“图数/流程图只作软校准”的旧措辞。低于门槛只能标记
    `REVISE_NATIONAL_FIRST_CANDIDATE`，不得 PASS。
15B. 国一模式不得直接从读题跳入单题求解。依次调用 `cumcm-contest-operations` 建立限时检查点、
    `cumcm-problem-selection` 完成候选题同口径最小试算和止损冻结，再由 `cumcm-model-tournament`
    对关键问题执行基线—主候选—异构挑战竞技。答案冻结后按
    [盲测阶段](../cumcm-blind-benchmark/STAGE.md) 执行隔离评估，成文后由 `cumcm-review` 按
    [对抗评审阶段](../cumcm-adversarial-review/STAGE.md) 复核，最终按
    [国一总门禁阶段](../cumcm-national-first-gate/STAGE.md) 签发国一竞争候选状态。
16. 几何图与流程图使用 [references/diagram-layout.md](references/diagram-layout.md)：框与
    框内文字必须为单一对象，标注锚定几何对象，固定画布导出，并生成同名布局审计文件；
    不用 LaTeX 裁边修复源图。
17. 几何机理图同时使用
    [references/geometry-diagram-routing.md](references/geometry-diagram-routing.md)：按对象、
    轨迹、判据和注释分层，锁定 Office 文本坐标，执行字形—线段和标签—实体碰撞检查。
18. 所有几何图、关系图和流程图还须使用
    [references/diagram-connection-audit.md](references/diagram-connection-audit.md)：先对每条
    引线、箭头、判断分支和反馈回路做连接级审计，核对每条线的方向与含义，再做整图级审计；
    任一连接或线语义失败不得入正文。
19. 全文内容使用 [references/content-quality.md](references/content-quality.md)：默认先模型
    假设、后符号说明；摘要只突出核心方法与最终结论；标题采用最少充分层级；逐段检查定义、
    推导、证据、结论与边界职责。
20. 使用本地 50 篇语料时先读
    [references/full-paper-census.md](references/full-paper-census.md)：按全文职责解释摘要、
    前置章节、逐问闭环、验证、评价、引用与附录；标题和关键词命中只作显式下限，不把
    频率转成固定目录或配额。
21. 模型选择与答案充分性使用
    [references/model-selection-and-answer-quality.md](references/model-selection-and-answer-quality.md)：
    在同题答案不可见时建立基线、主候选和异构挑战，先做科学硬淘汰，再用独立验证、稳健性、
    可识别性或最优性证据择优；答案冻结后才允许隐藏参考评估。
22. 论文成文使用 [../cumcm-paper/references/section-chain-contract.md](../cumcm-paper/references/section-chain-contract.md)：
    由 `cumcm-paper` 按 STAGE references 建立清单并执行重述、分析、假设、评价、引用、附录和摘要；
    符号、结果验证与去 AI 味（`cumcm-deai`，语料正样本对照与声纹审计）保留专项技能；
    建模求解与语言硬审计分别按 `cumcm-model-writing/STAGE.md`、`cumcm-language-audit/STAGE.md` 执行；
    模型、结果与验证公式稳定后必须回到 `cumcm-notation` 完成全文公式可读性复核；
    `cumcm-figures` 和 `cumcm-diagrams` 作为跨阶段图形门禁。不得跳过章节门禁后一次性自由生成全文。
    问题分析不设 1--2 句或固定段长，篇幅随各问的真实转化负担变化；关系图与流程图也只有在
    图能带来明确的信息增益时才使用。
23. 章节具体内容同时使用 `cumcm-paper/references/front-section-content-standard.md`、
    `model-result-content-standard.md` 和 `closing-section-content-standard.md`；语料字符量与命中率只触发
    漏项或冗余复核，真正放行依据仍是当前题目的证据职责。
23A. 直接成文同时使用
    [../cumcm-paper/references/question-depth-and-pagination.md](../cumcm-paper/references/question-depth-and-pagination.md)：
    逐问建立实质深度清单，实际编译后记录官方口径正文页数、PDF 总页数与哈希，再按缺失证据回退补强。
    用户要求“直接生成”不得成为跳过篇幅规划或编译反馈的理由；开写前先规划每问与共享章节的大致
    页数区间，成稿后只检查是否超过 30 页。页数较短不自动补写，内容缺口仍须补真实论证。
24. 数据图审美使用 `cumcm-figures/references/aesthetic-standard.md`，结构图、流程图、机理图和
    几何图使用 `cumcm-diagrams/references/tikz-visio-standard.md`；流程图另强制执行
    `cumcm-diagrams/references/fixed-flowchart-style.md`，固定经典正交视觉，只允许语义结构创新。
    正式结构图最终只允许 TikZ
    或 Visio 风格族；两类图均须注册、自动审计并在最终 PDF 中复核，不能把“美观”留作主观承诺。
24A. 国一/国奖候选还须执行 `cumcm-figures/references/signature-figure-standard.md`：在题目证据允许时，
    规划通常 2--3 张具有论文辨识度的特色主视觉图，至少一张将核心机理/模型结构与最终结论放在
    同一阅读链中。特色图必须来自真实数据、临界关系、策略景观、时空演化或不确定性联动；不得把
    渐变、图标、装饰性三维或商业仪表盘当成特色。若题目不适合复合主视觉，必须记录豁免理由，
    不为满足数量强制拼图。
24B. 同时执行 `cumcm-figures/references/visual-identity-and-archetypes.md` 并复制规划模板：全篇先冻结
    变量—颜色/线型语义，再从 A 类机理—结果、临界构型、时空演化，或 B 类策略景观、策略指纹、
    不确定性—决策联动等原型中按证据结构选择。国一 registry 使用 schema v4；特色图门禁必须显式
    `--track national-first`，仅换配色或装饰性拼图不得通过，有理由豁免也不降低科学与 provenance 门禁。
25. 结构图使用 `paper-visio` 与 `paper-tikz` MCP，数据图由求解侧 Python 代码（matplotlib）直接
    绘制，不再经 MATLAB MCP。完整读取
    [references/figure-mcp-routing.md](references/figure-mcp-routing.md)，并先执行项目级
    [插图路由阶段](../cumcm-figure-router/STAGE.md)；若独立 `paper-figure-router` MCP 可用则优先使用，不可用时运行确定性回退脚本并
    如实登记。路由器先判断插图必要性、绘图路线和正文位置，再生成、注册和审查；路由拒绝的候选图不得
    因装饰需要保留。
26. 数学写作使用 [references/mathematical-writing.md](references/mathematical-writing.md)：统一变量
    引入顺序、公式动机、推导叙事、边界条件表达、参数来源和数值精度报告，使正文读起来像连贯
    的数学论证而不是代码注释；语料建模段定义信号 92.9%、数值词密度 60.46/千字是校准标准。
27. 论证叙事使用 [references/argumentation-patterns.md](references/argumentation-patterns.md)：每段
    只承担一个职责（定义/推导/求解/证据/结论/边界），每个结论性断言在 ±2 段内有证据支持，
    跨问衔接写在后问开头，连接词承载因果而非装饰。
28. 表格设计使用 [references/table-design.md](references/table-design.md)：正文表格优先承担题目要求的
    结构化答案，必要时保留参数表、数据描述表和符号表；完整候选清单和内部试算留在证据包，
    证明方法选择、实质改进或独立验证所必需的公平对照可以入正文。同列同精度、单位在列头，表图不重复同一信息。
29. **A/B 题多假设试算与精准精选**：在求解探索阶段显式设计与测试多组合理假设及异构候选模型；
    成文时仅精选最合理、最准确的假设与最正确的模型作为正文主解，彻底剔除废弃假设与试算冗余。
30. **模型选择呈现决定性证据**：完整候选清单和淘汰过程留在内部证据；正文说明最终路线及
    决定性理由，可保留证明创新贡献所需的模型/算法对照、消融和收敛结果，不机械禁止比较表。
31. **图形数量不设上下限，由证据职责裁定**：正文可以没有图，也可以出现 4、6 幅或更多图；
    数量本身不加分也不阻断。每幅正式图必须绑定待证明命题、不可替代或互补的表达职责、真实来源、
    正文定位和合理交互；同一命题使用多图时，各图须分别承担整体趋势、局部边界、空间构型或诊断等
    不同职责。优秀论文图密度只用于触发漏图或冗余人工复核，不产生数量下限或配额。
    见 [references/figure-routing.md](references/figure-routing.md) 与
    [references/national-first-precision-and-visual-gates.md](references/national-first-precision-and-visual-gates.md)。
32. **多阶段演化与子图拼图 (Subfigures)**：对涉及多时间点、状态演化或对比的题目，使用多面板子图拼图 (Subfigures)。**子图面板数量完全按数据逻辑灵活选择（如 (a)(b) 2 面板、(a)(b)(c) 3 面板、(a)(b)(c)(d) 4 面板）**，严禁为凑格式而机械凑图。
33. **官方口径正文篇幅安排**：正文页数按“正文主体首页至附录开始前一页”唯一计算，包含 AI 工具
    使用声明和参考文献，不含摘要与附录。开写前先规划每问和共享章节的大致区间，成稿后严格检查
    不超过 30 页，不另设页数下限。
    借鉴国一优秀论文的版面质感，但具体图型按规则 24B 的原型库依证据结构选择：前置模型决策流程图、
    多阶段演化联排拼图、临界构型与边界图、机理—结果联图等均为候选原型而非固定套图；
    题目证据不支持某一原型时，按规则 24A 记录具名豁免理由，不为版面张力强制拼图。
34. **正式模式默认半自动、两次确认；模拟模式可跳过停点**：完整执行
    [半自动论文工作流](references/semi-automatic-workflow.md)。第一次只在方法、结果、验证和风险提交
    用户审阅后停下；用户明确确认达到其认可的国一目标并要求进入论文阶段，才调用模板和论文 skills。
    第二次只提交全文目录、大纲和页数判断；用户明确确认无误并要求开始初稿后，才落盘模板和正文。
    正式模式下自动评分、门禁 PASS 或系统自评不能替代用户确认；项目根目录 `.cumcm_state.json` 的
    `workflow_policy.mode` 明确为 `simulation` 且两个 `confirmation_required` 均为 `false` 时，
    `audit_user_confirmations.py` 可以跳过这两个用户停点，但仍须生成方法/结果、目录/页数和全部证据审查记录。
    状态缺失或无效时一律按正式模式处理；已确认的证据、目录或页数计划变化时退回相应确认点。

## 标准目录

```bash
python .agents/skills/cumcm/scripts/init_project.py --root .
```

国一赛程启动后还要建立项目级执行计划：

```bash
python .agents/skills/cumcm/scripts/audit_skill_execution_plan.py --root . --init
python .agents/skills/cumcm/scripts/audit_skill_execution_plan.py --root .
```

`审查/skill-execution-plan.json` 必须覆盖当前库中的每个公开 Skill 和内部 STAGE。覆盖不等于无条件
调用：总控、赛程、选题、竞技、求解、成文、专项写作、审查及国一阶段是必经；`cumcm-figures`、
`cumcm-diagrams` 等按当前题目接受的图形职责条件触发，不适用时明确记录
`skipped-not-applicable + reason`。禁止为了“用上所有 Skills”制造无意义图、流程或模型。

```text
工作目录/
├── 题目/                      工作过程目录
├── 数据/                      工作过程目录
├── 求解/                      工作过程目录
├── 论文/                      最终产出 1：论文.tex 单一总稿与论文.pdf
├── 附件/                      最终产出 2：支撑材料与规则要求的提交件
├── 审查/                      工作过程目录
└── 最终效果/高教杯优秀论文/   可选的本地基准语料
```

## 阶段 0：优秀论文校准

若本地语料存在，先读
[references/benchmarking.md](references/benchmarking.md)，再运行：

```bash
python .agents/skills/cumcm/scripts/benchmark_corpus.py --root .
python .agents/skills/cumcm/scripts/build_section_content_profiles.py --corpus 最终效果/高教杯优秀论文
```

从报告中形成当前题目的质量预算：需要回答的关键问题、必须出现的验证类型、适合的图表职责、
正文密度和附录规模。不得把邻近论文的专属内容写进求解计划。
同时按 [references/figure-routing.md](references/figure-routing.md) 建立图形职责预算：
模型解释图、方案结果图和诊断验证图分别需要证明什么，以及哪些候选图应删除。
若计划关系图或流程图，再按 [references/flowchart-routing.md](references/flowchart-routing.md)
逐图指定唯一主要职责、对应脚本步骤、判断条件、回退路径和可编辑源文件。
所有几何图、关系图和流程图同时按
[references/diagram-layout.md](references/diagram-layout.md) 执行源端包含检查和最终插入
尺寸验收。
几何图另按 [references/geometry-diagram-routing.md](references/geometry-diagram-routing.md)
建立对象—标签锚点表，并在导出前完成碰撞检查。
所有连接按 [references/diagram-connection-audit.md](references/diagram-connection-audit.md)
建立逐连接清单；移动任一节点、标签或画布后必须全量重审，不只复查被修改位置。
正式模式此阶段只记录语料中的结构规律和当前题目的问题依赖，不生成供用户确认的全文目录、正式大纲或
页数计划。三者须等方法与结果通过第一次用户确认后，由论文规划阶段依据冻结证据统一生成；模拟模式可
按同一证据链自动进入规划，但仍需落盘目录与页数判断。
本地 50 篇语料存在时，再用
[references/full-paper-census.md](references/full-paper-census.md) 核对全文职责链、统计口径
和 OCR/自动识别边界；冲突时以官方规则、题目结构和项目证据优先。
同时读取 `最终效果/高教杯优秀论文/内容职责普查/section_content_profiles.json`，按章节检查输入、
输出、方法、证据与边界信号；不得复制报告来源段落或把字符分位数变成写作配额。
标题、摘要、标题树、流程图和附录阶段按 [references/corpus-alignment.md](references/corpus-alignment.md)
执行一手语料对照与雷点自查：先通读同题型优秀论文的对应部分校准信息密度，再对照雷点负面清单
逐条自查；同题材料的读取时序、复制红线与口径矛盾裁定以该路由为准。
求解证据稳定后按 [references/paper-title.md](references/paper-title.md) 拟定总标题，逐个核对
标题方法词能否在摘要、公式、代码和验证中兑现。
摘要成稿前按 [references/abstract-writing.md](references/abstract-writing.md) 抽取逐问证据；
附录生成前按 [references/appendix-structure.md](references/appendix-structure.md) 建立正文引用、
代码模块、环境和支撑材料索引。

修改或评估本套 skills 时，同时读取
[references/regression-suite.md](references/regression-suite.md)，不得用单题表现证明跨题型能力。
修改任一公开技能、阶段模块、门禁、路由、模型目录、盲测基准、交付规则或绘图实现后，统一运行
本地确定性预检；它覆盖公开技能元数据与链接、总控一致性、相似度与原创性消费、图形审计、路由
parity、国一产物绑定、A/B 模型目录、单一总稿与附件交付、答案/评分基准及 figure runtime：

```bash
python .agents/skills/cumcm/scripts/run_skill_preflight.py --root . --no-write
```

预检通过只证明本地工程门禁未回退，不替代六案例路由、三类证据包、留出题全流程和冻结后盲测。

## 阶段 1：独立求解

调用 `cumcm-solve`，完成：

- 题面、附件和提交要求的全量读取；
- 按 [逐问题意理解与建模入口](references/per-question-understanding.md) 在选模前记录每问的
  任务含义、信息限制、决定性困难、数学转化与检验依据，供问题分析和第五章各问入口消费；
- 赛题地图、歧义清单、变量/单位/约束字典；逐问"评阅视角验收标准"按
  [references/grading-profile.md](references/grading-profile.md)（跨年评分共性，
  无答案数值，全程可读；同题逐题评阅要点受盲测隔离约束）；
- `求解/任务契约.json`，锁定题面问题、附件角色、官方输出和逐问验证；
- 候选方法比较、主模型和可执行降级方案；
- 冻结的候选模型比较、淘汰依据和异构挑战路线；
- 按创新与组合规则在现有 `求解/创新贡献表.md` 中整理方法差异简报：常规参照、本题改造、数学依据、
  对照收益与成本、边界和采用状态。关键问优先探索有依据的结构差异，基础规律不为避重而改动；
  不承诺与未知队伍不重复，不通过浏览当届解题讨论来做方法碰撞检查；
- 逐问可复现代码、结果表、图形、`metrics.json`；
- `求解/运行环境.json`：实际验证的 Python 与依赖版本、逐问命令和验证状态；
- `求解/证据矩阵.csv`：题目要求—结论—指标—图表—脚本的映射；
- 至少一种与题型匹配的独立验证，而不是笼统写“效果良好”。
- 每问通过题面闭环、可行性、独立验证、数值分辨率、替代路线挑战和不确定性/最优性六项答案门禁。

运行：

```bash
python .agents/skills/cumcm-solve/scripts/audit_evidence.py --root .
```

只有题目每一问都有明确答案、证据矩阵无断链、关键指标可解析时，才整理方法与结果审阅包交给
用户，连同方法差异简报和实际 AI 参与内容供参赛队核验；AI 自审不得写成参赛队已人工核验。
正式模式此处必须停下，不得自动调用 `cumcm-paper`、复制模板或生成正式目录。用户明确确认方法与
结果达到其认可的国一目标并要求进入论文阶段后，按
[半自动论文工作流](references/semi-automatic-workflow.md) 记录第一次确认，再进入阶段 2；模拟模式
由项目状态明确跳过该停点后，可按同一证据链进入阶段 2。

## 阶段 2：证据成文

先运行 `audit_user_confirmations.py --phase paper-plan`。通过后调用 `cumcm-paper` 的规划部分，先向
用户给出全文目录、逐节大纲和页数判断；正式模式此时不创建 `论文/论文.tex`，也不写摘要或正文。只有用户
明确确认这三项无误并要求开始初稿，记录第二次确认并通过 `--phase draft` 后，才使用模板并按章节
子技能链逐门禁成文；模拟模式由项目状态明确跳过该停点后，可直接执行同一模板和章节门禁。只从证据矩阵和结果文件写作：

- 第一页为摘要专用页，摘要覆盖每问的方法理由、关键结果和验证信息；
- 摘要粗体只标记核心方法和最终结论，不突出普通数字、过程动作或验证细节；
- 正文按真实论证需要组织；开写前规划每问与共享章节篇幅，成稿后按官方唯一口径检查不超过 30 页；
- `cumcm-paper` 先按 [../cumcm-outline/STAGE.md](../cumcm-outline/STAGE.md) 创建逐问深度清单，
  [模型成文阶段](../cumcm-model-writing/STAGE.md) 与 `cumcm-results-validation`
  分别填写推导/参数/求解和结果/验证/边界/最终作答；任一问不得只完成标题级闭环；
- 默认先写模型假设、再写独立符号说明；各级标题按内容设置，不规定每问数量；
- 所有章节子技能只更新 `论文/论文.tex`；禁止分章 TeX、章节级 `\input`/`\include`
  和 subfiles，参考文献与纸面附录也直接保留在总稿；
- 变量先由当前题目的对象、角色、索引和单位生成 `审查/符号语义台账.csv`，保留必要标准
  符号，不从同题论文或技能示例复制变量体系，也不为制造差异使用生僻符号；
- 每个问题形成“题意理解与数学转化—对象与变量—建立模型—求解—验证—结论”的闭环；
- 对真正影响答案的模型选择，在问题分析或对应问题中说明决定性理由；保留证明改进或验证所必需的对照，不展示完整探索流水账；
- 正文按“正文主体首页至附录开始前一页”计算，包含 AI 工具使用声明和参考文献，不含摘要与附录；
  该唯一口径不得超过 30 页或当年更低的官方上限，从附录首页起不设页数上限，附录包含支撑材料清单和完整可运行代码；
- 使用 `cumcm-paper/scripts/compile_paper.py --root <项目目录>` 实际执行 XeLaTeX 两遍编译并生成
  源稿—依赖—PDF/AUX 绑定，再修复错误、越界、缺字、引用和大面积异常空白。
- 每次完整编译后记录 `appendix:start - body:start`、PDF 总页数和 SHA-256。超过官方上限的产物记为
  `INTERNAL_FAILED_BUILD`；页数较短不自动失败，仍按逐问内容门禁判断是否需要回退。
- 评价、AI 工具使用声明、参考文献、附录和定稿摘要全部完成后，两遍编译只得到内部待审候选，
  不能仅凭内容与页数通过就交付初稿。先完成去 AI 表达、事实语义复核、语言扫描与逐项处置；
  改稿后重编译，对当前 PDF 执行全语料全文相似度检查，再按逐问深度协议绑定源稿、PDF、基线和审查报告。
  随后运行 `python .agents/skills/cumcm-paper/scripts/check_first_draft_gate.py --root .`。
  只有状态为 `PASS_FIRST_DELIVERABLE_DRAFT` 才产生第一份可交付初稿并进入最终独立评阅；
  其他阻断状态按 `missing_depth_items/actions` 回到真正缺失职责所在阶段，补强、两遍编译并复跑
  门禁，不得向用户展示为稿件版本；若修订改变已确认的方法、结果、目录或页数计划，则退回对应
  用户确认点。
- 正文各部分成稿后先执行 `cumcm-deai`：逐部分对照优秀论文同部分原文与声纹画像改写
  AI 味段落，并通过 `cumcm-deai/scripts/audit_corpus_voice.py` 声纹审计。
- 图表题注、编号引用与解读文字按 `cumcm/references/figure-table-narration.md` 执行，
  编译前运行 `cumcm-paper/scripts/audit_figure_table_narration.py`。
- 编译前运行 `cumcm-language-audit/scripts/audit_language.py` 和
  适用的章节检查；完整 `cumcm-paper/scripts/audit_section_chain.py` 在首次初稿放行后运行，避免
  用尚未生成的初稿报告反过来阻断内部编译。硬禁表达、生产痕迹或任一章节门禁失败时不得进入最终候选审查。

## 阶段 3：优秀论文候选审查

调用 `cumcm-review`，运行：

```bash
python .agents/skills/cumcm-solve/scripts/audit_evidence.py --root .
python .agents/skills/cumcm/scripts/benchmark_corpus.py --root . --fail-on-similarity
python .agents/skills/cumcm-language-audit/scripts/audit_language.py --root .
python .agents/skills/cumcm-deai/scripts/audit_corpus_voice.py --root .
python .agents/skills/cumcm-notation/scripts/audit_formula_readability.py --root .
python .agents/skills/cumcm-paper/scripts/audit_figure_table_narration.py --root .
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --phase final
python .agents/skills/cumcm-figures/scripts/audit_figure_style.py --root .
python .agents/skills/cumcm-diagrams/scripts/audit_diagram_style.py --root .
python .agents/skills/cumcm-paper/scripts/audit_section_chain.py --root .
python .agents/skills/cumcm-paper/scripts/audit_single_tex_delivery.py --root . --phase final
python .agents/skills/cumcm-review/scripts/audit_artifacts.py --root .
```

两项图形审计只在项目实际使用相应图类时运行；使用却缺注册表、风格报告或最终页面复核即失败。

审查四类门槛：

- 合规门槛：匿名、格式、官方口径正文不超过 30 页、文件大小、AI 使用声明与支撑材料；
- 科学门槛：假设、推导、验证、稳健性、约束与结论有效；
- 答案门槛：主模型经异构路线挑战，数值误差小于报告精度，优化有界差或诚实的近优声明；
- 证据门槛：数值、图表、代码和论文可双向追溯；
- 原创门槛：无参考论文复刻和高相似长句。
- 内容门槛：逐节阅读正文，标题最少充分，段落职责明确，摘要—正文—证据同口径。
- 深度门槛：逐问八项职责全部有可定位证据，且最终深度审计绑定当前编译 PDF；正文与总页数
  分开报告，不能以附件或附录页数掩盖短正文。

任一硬门槛失败或优秀论文评分未达标，按整改清单回退对应阶段。

## 最终交付

最终输出只归拢为“论文”和“附件”两类；`题目/`、`数据/`、`求解/`、`审查/` 是工作过程目录，
不作为最终产出：

- `论文/`：`论文.tex` 单一总稿、`论文.pdf`、编译必需的 `format.cls`、字体和图片资产；
  顶层不得出现其他章节 TeX，总稿不得用 `\input`、`\include` 或 subfiles 拼接正文；
- `附件/`：`支撑材料.zip`，只归拢完整源程序、题目要求提交的结果文件、论文实际使用的
  自主查阅数据或必要补充材料、简短运行说明，以及按当年规则放入压缩包内部的
  `AI工具使用详情.pdf`；提交清单、哈希与检查记录留在工作目录。

正式提交仍是两个电子文件：一个非压缩的 `论文.pdf`（第一页摘要，随后为正文主体、AI 工具使用
声明、参考文献和附录）与一个 `支撑材料.zip`/`.rar`。`论文.tex`、模板、字体和提交清单是内部
交付与复现资产，不作为额外官方上传文件；`AI工具使用详情.pdf` 只放在支撑材料压缩包内。
优先使用可直接审计成员列表的 ZIP；若最终采用 RAR，必须写 `审查/RAR内容复核.json`，用最终
RAR 的 SHA-256 绑定人工核验的成员清单、检查工具、复核人、时间和结论。缺记录、清单漏项或
压缩包哈希变化均不得放行。

支撑材料按白名单从 `求解/` 归拢，不复制整个工作目录。`metrics.json`、任务契约、运行环境
JSON、证据矩阵、模型比较、图形注册表与布局 JSON、检查报告、日志、缓存、临时文件、测试文件、
重复图表和废弃程序均留在工作目录，不随支撑材料外发。只有题目明确要求 JSON 作为正式答案，
或程序运行确实依赖该配置且无法合理改为代码内参数时，才允许相应 JSON 进入压缩包。运行环境和
逐问命令面向评委整理为简短的 `运行说明.txt` 或 `运行说明.pdf`。
缺少编译器或依赖时，仍交付完整源码、可运行说明和已验证产物，并在审查报告中明确阻塞点。

## Skill 发布门槛

只有本地确定性预检通过，且 [references/regression-suite.md](references/regression-suite.md) 中六案例路由、三类证据包、
留出题全流程和冻结后盲测答案门槛全部通过，才能声称该
版本具有稳定的优秀论文级产出能力。原创性一项只接受两种放行：相似度实测落在 `benchmarking.md` 的
可接受带，或落在人工检查带且 `审查/原创性人工复核.json` 有独立评审的 `pass` 记录；
`NOT_RUN`、空语料、同题对照全部无文本层都记为未证明，不得放行。

对已完成的独立项目运行：

```bash
python .agents/skills/cumcm/scripts/evaluate_skill_suite.py --projects <机理题项目> <统计或决策题项目> <优化题项目> --min-projects 3
```
