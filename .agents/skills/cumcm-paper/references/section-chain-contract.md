# CUMCM 章节技能链契约

## 目标

把论文写作拆成可验收的职责链。每一节只消费已经落盘的证据，只向同一个
`论文/论文.tex` 写入本节应承担的内容，并用结构化门禁向下一节交接。章节技能是职责分工，
不是文件拆分机制；语言流畅不能替代题意闭环、数值证据或独立验证。

各成文阶段共同遵守 [论证叙事规范](../../cumcm/references/argumentation-patterns.md)：全文以
A053 为风格主锚，用参赛队向评委解释本题理解与真实求解的书面口吻展开；按章节职责自然呈现，
起草时执行，改写时保留必要论证。模型相关阶段同时执行
[建模完整性](../../cumcm/references/per-question-understanding.md#建模完整性)，逐问逆查题面
输出、关系、条件/分支、参数/可解性、求解与输出恢复、验证作答；共享或短写不豁免适用职责。

## 论文页序与执行顺序

论文页序通常为：摘要 → 问题重述 → 问题分析 → 模型假设 → 符号说明 → 各问建模、
求解、结果与验证 → 评价、改进与推广 → AI 工具使用声明 → 参考文献 → 附录。

实际执行顺序为：

0. 核验方法与结果已获用户明确确认；未确认时停在求解阶段，不调用论文模板或章节链；
1. `cumcm-paper` 按 `cumcm-outline/STAGE.md` 建立标题树、全文大纲和页数计划，完整展示给用户并
   正式项目等待第二次确认；确认前不创建 `论文/论文.tex`、不写摘要和正文。模拟项目只有在
   `.cumcm_state.json` 明确标记 `workflow_policy.mode=simulation` 后才可跳过该停点；
2. 依次执行 `cumcm-restatement/STAGE.md`、`cumcm-analysis/STAGE.md`、
   `cumcm-assumptions/STAGE.md`，再调用 `cumcm-notation` 完成前置章节；
3. [模型成文阶段](../../cumcm-model-writing/STAGE.md) 与 `cumcm-results-validation` 逐问闭环，并共同填写
   `审查/逐问深度清单.json`；公式稳定后回到 `cumcm-notation` 完成全文公式可读性审计；
4. 按 `cumcm-evaluation/STAGE.md`、`cumcm-references/STAGE.md`、
   `cumcm-appendix/STAGE.md` 收束全文；
5. 结论与数值冻结后按 `cumcm-abstract/STAGE.md` 定稿摘要，并确认 AI 工具使用声明已经进入总稿；
6. 全部正文口径内容完成后，以 `audit_section_chain.py --phase content` 检查内容阶段；使用
   `compile_paper.py --root <项目目录>` 实际两遍编译并生成 `审查/编译绑定.json`，再
   记录 PDF 页数与哈希。合格构建仅为 `INTERNAL_REVIEW_CANDIDATE`、`deliverable=false`；超过
   官方上限的产物为 `INTERNAL_FAILED_BUILD`。内容缺口回到对应章节补强并重编译；
7. `cumcm-deai` 与 [语言审计阶段](../../cumcm-language-audit/STAGE.md) 完成全文表达和事实语义复核，
   逐项处置自动信号；如实区分 AI 审查与参赛队人工核验，不伪造后者；
8. 改稿后用同一编译器封装两遍编译并刷新页数与 PDF 哈希，对当前 PDF 做全语料全文相似度检查，按
   [逐问深度协议](question-depth-and-pagination.md) 绑定当前总稿、PDF、基线和审查报告；
   `check_first_draft_gate.py` 放行后才首次交付初稿，再运行 `audit_section_chain.py --phase final`、
   全文公式、正文深度和视觉审计，交给 `cumcm-review`。正文、PDF 或审查证据变化须重新核验绑定。

`cumcm-figures` 与 `cumcm-diagrams` 是跨阶段技能：有相应图形时，在图进入正文前完成验收。
数据图写入 `审查/figure-registry.json`，关系图、机理图、几何图与流程图写入
`审查/diagram-registry.json`；注册表不是图表目录的重复，而是把命题、来源、生成方式、最终尺寸、
风格和整页复核绑定到每一幅正式图。

## 章节清单

由 `cumcm-paper` 按 `cumcm-outline/STAGE.md` 创建
`审查/section-chain/manifest.json`。最终论文只允许单文件 LaTeX：
`paper_source` 必须为 `论文/论文.tex`，所有阶段的 `source_files` 也只能写这个文件；
用 `source_anchors` 记录该阶段对应的 section 标签。最低结构为：

```json
{
  "schema_version": 1,
  "question_ids": ["q1"],
  "body_page_plan": {
    "official_body_max": 30,
    "shared_sections_page_range": [4, 6],
    "basis": "前置章节、评价、AI 声明和参考文献的合计估计"
  },
  "question_architecture": {
    "q1": {
      "role": "core",
      "chain_type": "boundary-optimization",
      "progression_axis": "foundation",
      "route_summary": "由边界条件构造单变量约束优化，并用粗细搜索和邻域复核确定临界参数",
      "planned_page_range": [4, 6],
      "page_basis": "关键边界推导、参数搜索与独立复核所需篇幅",
      "planned_subsections": ["边界条件", "参数搜索", "约束分析"],
      "inheritance": {"status": "none", "objects": []}
    }
  },
  "paper_source": "论文/论文.tex",
  "depth_manifest": "审查/逐问深度清单.json",
  "stages": {
    "restatement": {
      "required": true,
      "source_files": ["论文/论文.tex"],
      "source_anchors": ["sec:restatement"],
      "gate": "审查/section-chain/gates/restatement.json"
    }
  },
  "cross_cutting": {
    "figures_used": true,
    "diagrams_used": false,
    "figure_registry": "审查/figure-registry.json",
    "diagram_registry": null
  }
}
```

完整阶段键为 `outline`、`restatement`、`analysis`、`assumptions`、`notation`、
`model-writing`、`results-validation`、`evaluation`、`references`、`appendix`、`abstract`、
`deai`、`language-audit`。评价或推广不适合独立设章时仍保留门禁，记录其合并位置与理由。

## 阶段门禁

每个子技能写入 `审查/section-chain/gates/<stage>.json`：

```json
{
  "schema_version": 1,
  "stage": "analysis",
  "status": "pass",
  "source_files": ["论文/论文.tex"],
  "source_anchors": ["sec:analysis"],
  "claim_ids": ["C-Q1-01"],
  "checks": [
    {"id": "separate_from_restatement", "pass": true, "evidence": "一级标题独立"}
  ],
  "blocking_issues": [],
  "handoff": "assumptions"
}
```

- `status` 只能在全部硬检查通过时写 `pass`。
- `claim_ids` 必须能回到 `求解/证据矩阵.csv`；无结论职责的前置节可为空。
- `evidence` 写可核对的文件、表图编号、公式编号或具体位置，不写“已检查”。
- 任何 `blocking_issues` 非空时停止交接，回到求解或本节修订。
- `model-writing` 与 `results-validation` 的门禁必须逐问引用深度清单中的对应职责和证据锚点；
  不能用一个全文级 `pass` 掩盖某一问缺推导、验证或最终作答。

## 全文不变量

0. 默认采用半自动工作流。方法结果确认和目录/大纲/页数确认均须有效，且绑定文件哈希未变化；
   系统自评和自动门禁不得替代用户确认。
1. 问题重述与问题分析必须是两个独立一级章节。
2. 默认顺序固定为“模型假设 → 符号说明”；符号理解若确为假设前提，记录例外理由。
3. 标题采用最少充分层级。第五章的问题层使用简短二级标题，每问按需要设置 0--3 个三级标题；
   连续论证优先用正文或段首短语承载。
4. 分问连续排版，不因“问题一”“问题二”强制换页。
5. 摘要粗体只强调核心方法与最终结论；普通参数、中间值和过程动作不加粗。
6. 正文只写数学对象、方法、推导、结果、验证和边界，不写生产过程、审查过程或读者导航。
7. 正文不得暴露附件名、文件名、路径、代码、脚本、CSV、JSON、运行命令、支撑材料清单或生成方式。
8. 未经实际运行的候选模型不得写入论文；模型选择只保留真正影响答案且有比较证据的取舍。
9. 图表必须承担唯一主要证据职责。数值图从结果文件生成；结构图只表达真实依赖、机理或算法分支。
10. 正文结论必须能追溯到公式、结果表或图以及独立验证；无法追溯的判断删除或补算。
11. `figures_used=true` 时，`figure-style-audit.json` 必须晚于注册表且为 PASS；
    `diagrams_used=true` 时同理要求 `diagram-style-audit.json`。正式关系图、流程图、机理图和
    几何图的最终风格族只允许 TikZ 或 Visio，最终成品必须为 PDF/SVG 矢量图。
12. 图形自动报告只证明字段与显式检查已完成，不能替代最终 PDF 的原尺寸、缩略图、灰度和整页复核。
13. 用户要求直接生成整篇也不得跳过两次确认，以及“逐问清单—两遍编译—记录页数与 PDF 哈希—按缺失职责补写—
    重新编译”闭环。正文只按官方口径计数并与 PDF 总页数分开记录；页数较短不自动补写，只有内容
    门禁发现真实缺口时才补推导、参数、求解、解释、验证、边界和答案映射。
13A. `审查/首份可交付初稿门禁.json` 必须为 `PASS_FIRST_DELIVERABLE_DRAFT`、`build_status` 为
     `FIRST_DRAFT_CANDIDATE` 且 `deliverable=true`，并只能由当前 PDF、AUX、逐问深度清单和写作
     阶段 gate 及绑定的表达、语义、原创性报告重新计算。编译记录本身始终 `deliverable=false`，
     不具有放行权限。页数较短不单独阻断，但内容或首次交付审查不完整时不得产生初稿身份。
14. 2026 年 AI 工具使用声明必须位于参考文献之前，二者纳入本项目正文区计量；参考文献和声明不要求
    各自另起一页。官方硬约束是正文从第四页开始且不超过 30 页；摘要和附录不计入本项目正文区，
    附录起始页以 `appendix:start` 标记。
15. 论文顶层只允许 `论文/论文.tex` 一个 TeX 总稿。禁止章节级 `\input`、`\include`
    和 subfiles；章节技能在总稿的 section 锚点内增量写入，参考文献与纸面附录也保留在总稿。
    图片、模板类、字体与附件可以是外部资产。
16. 标题树生成时必须为每一问选择与题型相符的职责链，并在内部记录核心问、支撑问或过渡问；
    按跨问依赖、本题特有推导、求解风险、输出重要性和验证负担规划每问大致页数区间，再连同共享
    章节检查规划上界不超过 30 页。不得按题号平均分配，计划区间也不作为成稿硬配额。
17. 第五章的问题层标题默认只写“问题一”“问题二”，短任务名有展示价值时再补充；每问按实际内容
    设置 0--3 个简短三级标题。按 [逐问题意理解与建模入口](../../cumcm/references/per-question-understanding.md)，
    每问标题后必须先写一段概述，说明任务、决定性关系和求解主线，再进入公式或三级标题；后文须兑现主线。
    标题和正文均不得写审计、原稿、重构、统一口径、计数闭合、门禁、证据边界和模型链等内部过程。
18. 每问结束前必须出现可定位的结果解释、独立验证或独立复核、风险/适用边界和题面逐项作答；
    这些内容优先嵌入该问，不为凑章名单独占用一级篇章。
18A. 局部检验在进入下一问前完成。只有题目确实需要跨问检验，且存在两类以上实质内容时，才设置紧凑的
     “结果检验”章。不为算术核对、口径统一、证据边界或模型链总结单独设章。模型评价只总结有结果支撑的优点、
     失效条件、对应改进和有条件推广，不能替代逐问检验。
19. 临界、碰撞、边界优化和能力上限问题在搜索前必须说明候选范围为何足够；依据可以是几何排除、
    单调性、上下界、对称性、必要条件或已验证的全域粗扫。只有程序循环起止值而没有数学或数据依据不得放行。
20. 优化问题必须报告哪些约束在最优点活跃、其余约束的余量或乘子信息，并复算最优点邻域及至少一个
    越界/反例情形；仅有求解器 `success`、一条收敛曲线或多初值命中同一点不能单独证明最优性。
21. 前问输出进入后问时，必须记录继承对象、来源问题、单位、有效数字和口径；后问使用前先做一致性复核。
    禁止重新估计同一参数却仍宣称继承，也禁止只写“沿用前问结果”而不说明传递了什么。
22. 每问必须记录相对前问的主要升级轴：机理情形、信息完备度、参与者数量、空间真实性、参数不确定性，
    或明确为首问基础/相互独立。只有题面条件确实使原模型不再充分时才升级模型；原模型仍足够时只修改
    必要参数、约束或求解范围，不以算法名称的新旧制造虚假推进。

## 硬禁表达

下列表达及其近义改写不得进入摘要或正文：

- “本文的回答”“本问回答”；
- “计算口径”“满足问题一对模型建立和可计算性的要求”；
- “前者回答……后者回答……”“不因……预设结论”；
- “在表中列出的……在首次出现处定义”“首次出现处定义”“见下文定义”；
- “完整程序见附录”“详见附件”“代码实现如下”；
- “本文采用 AI/人工智能工具”“提示词”“生成过程”“审查流程”；
- 只用于评价写作本身的“便于读者理解”“使论文结构更加清晰”“体现了模型的有效性”。

需要表达相同事实时，直接陈述物理条件、数学关系、数值结果、误差、边界或模型局限。

## 50 篇语料的使用边界

语料只校准职责、密度和常见组织方式，不复制标题、句式、段落骨架、图形布局或模型链。
统计频率不是配额：摘要字数、章节数、图数、公式数和附录页数均由当前题目的证据决定。

## 改动传播

结果、符号、假设或模型变化后，至少重开以下门禁：

- 数值变化：`results-validation`、`abstract`、`language-audit`；
- 符号或单位变化：`notation`、`model-writing`、`results-validation`、`abstract`；
- 假设变化：`assumptions` 及全部下游阶段；
- 标题树变化：`outline` 及受影响章节；
- 图形变化：对应 `figures` 或 `diagrams` 门禁以及引用该图的章节。
- 图源、尺寸、字体、配色、连接或画布变化：更新注册表，重跑对应风格审计，并重新打开引用章节与视觉审查门禁。
- 主方法或最终结果变化：方法结果确认失效；全文目录、逐节大纲或页数计划变化：目录页数确认失效。
