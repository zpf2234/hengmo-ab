---
name: cumcm-outline
description: 为 CUMCM 论文建立证据驱动的标题树、章节职责和子技能交接清单。用于正文写作前规划结构，或在标题过多、问题关系不清、章节职责重叠时重构全文脉络；依据题目依赖和本项目证据选择结构，不套用固定获奖目录。
---

# CUMCM 论文架构

先读 [../cumcm-paper/references/section-chain-contract.md](../cumcm-paper/references/section-chain-contract.md)、
[../cumcm/references/title-structure.md](../cumcm/references/title-structure.md) 与
[../cumcm/references/full-paper-census.md](../cumcm/references/full-paper-census.md)，并读取
[../cumcm-paper/references/front-section-content-standard.md](../cumcm-paper/references/front-section-content-standard.md)
中的标题树与前置章节证据，并完整读取
[../cumcm-paper/references/question-depth-and-pagination.md](../cumcm-paper/references/question-depth-and-pagination.md)。
同时读取 [../cumcm-paper/references/a053-argument-chain.md](../cumcm-paper/references/a053-argument-chain.md)，
只迁移功能推进链，不复用 A053 的模型、公式、符号、数值、标题、图表或句子。

## 一手语料对照与雷点自查

按 [../cumcm/references/corpus-alignment.md](../cumcm/references/corpus-alignment.md) 执行：
定架构前从 `最终效果/高教杯优秀论文/标题结构普查/all_paper_outlines.md` 通读 3--5 篇
同题型标题树，只校准结构流派选择（分问题一级章、总章统领、模块驱动）与标题信息密度；
架构定稿前对照 `标题结构普查/AB优秀论文标题结构十大雷点与写作禁忌.md` 逐条自查。
材料缺失时跳过并在门禁记录。语料中"目录页码匹配"一条不适用于无目录的国赛电子版。

## 输入

- `审查/用户确认节点.json` 中方法与结果确认有效；先运行
  `audit_user_confirmations.py --phase paper-plan`，未通过时不得开始本阶段；
- 题面任务契约、赛题地图和歧义清单；
- `求解/证据矩阵.csv`、模型选择记录与图表清单；
- 各问之间的变量、数据、模型和验证依赖。

缺少逐问答案或证据矩阵时只输出暂定架构，并阻止后续成文。

## 架构方法

1. 为每问写一句“输入—核心动作—输出—验证”，并把题面每个输出、约束、情形和精度要求拆成
   `requirements` 条目，预先绑定 `claim_id`；不写成正文。
2. 根据跨问依赖中心性、本题特有推导量、求解风险、题面输出重要性和验证负担，将每问内部标记为
   `core`、`support` 或 `transition`；再从 `foundational-mechanism`、`critical-feasibility`、
   `boundary-optimization`、`composite-piecewise`、`capacity-upper-bound`、`experimental-inference`、
   `sequential-decision`、`spatial-layout`、`uncertainty-feedback` 中选择最贴近的职责链。
   题型不属于这些类别时用 `custom` 并写明本题推进链。角色和职责链只进入内部清单，不进入论文标题。
3. 按上述难度、推导、结果和验证负担为每问确定大致页数区间并写明依据；再估计前置章节、评价、
   AI 声明与参考文献的共享篇幅，确认规划上界不超过 30 页。区间只用于安排轻重，不作为成稿配额。
4. 判定共享程度：共享机理、变量和求解器较多时用总章统领；各问相对独立时用分问题一级章；题目按功能模块组织时用模块驱动。
5. 固定前五个一级章：问题重述、问题分析、模型假设、符号说明、模型的建立与求解，顺序不得倒置或合并。问题重述章固定只设“问题背景”和“问题提出”两个二级标题；各分问使用“问题一：”等段内加粗标签，不升为三级标题。问题分析章按“问题一的分析、问题二的分析……”逐问设置二级标题，不再机械拆分分析思路与求解过程的三级标题。模型假设章不设任何下级标题，只保留一个连续编号列表；局部适用范围在假设句中按需自然说明。符号说明章标题后直接放三列表格。第五章按共享模型或分问依赖组织具体模型与求解过程。
6. 第五章的问题层二级标题默认使用“问题一”“问题二”，短任务名有展示价值时再补在冒号后；
   每问按真实论证转折设置 0--3 个简短三级标题。问题标题后可以直接进入正文，不预制路线段，
   不把“推导—求解—结果—验证—作答”机械拆成固定小节。
7. 跨两问以上且证据类型不少于两类时，才考虑独立综合验证章。
8. 评价、改进、推广按实际内容合并；没有新职责时不设独立结论章。
9. 标记图、表、公式和 `claim_id` 的归属，避免同一结果在多节重复。

## 标题门禁

- 不出现“相关说明”“计算口径”“若干问题”“本文的回答”等空泛标题。
- 问题重述的标题树必须为“一、问题重述—1.1 问题背景—1.2 问题提出”，不得增加“研究意义、任务概览”等同级标题。
- 问题分析的标题树必须为“二、问题分析—2.1 问题一的分析—2.2 问题二的分析……”。章末问题关系图作为图处理，不为一幅图单设空洞章节。
- 模型假设只作为独立一级标题进入标题树；不得增加“基本假设、问题一假设、假设说明”等二级标题。
- 符号说明只作为第四个独立一级标题，标题下直接安排符号表，不增加空洞二级标题。
- 第五个一级标题固定为“模型的建立与求解”；内部优先按问题设置二级标题，共享机理确实减少重复时才先设共享模型标题。
- 不把模型建立、求解、结果和验证机械拆成大量三级标题。
- 小标题优先使用 4--10 字的学科自然表达，只展示一个中心；不把对象、方法、条件、结果、验证和边界堆入同一标题。
- 标题中不出现口径、审计、闭环、证据链、门禁、作答映射等内部职责或生产措辞。
- 不把图表名直接当章节名，不用算法名堆叠学术感。
- 问题一与问题二之间不设置强制换页。
- 每个标题下面必须有独立论证职责；只有一两句过渡时改成段首短语。

## 输出

创建 `审查/section-chain/manifest.json`：`paper_source` 固定为 `论文/论文.tex`，所有阶段
`source_files` 也只登记该总稿，并用 `source_anchors` 区分 section；不得为章节创建其他 TeX。
清单同时列出题目编号、标题树、`claim_id` 与跨阶段图表归属。再创建
`审查/逐问深度清单.json`：在任何正文成文前，完整填写 `architecture`、
`argument_plan` 与 `prewrite_readiness`，冻结本题推导路径、逐项结果命题、验证/边界计划和表达载体；
完成态职责仍保持 `pass: false`，不得在正文尚未写成时预先勾选通过。写入 `gates/outline.json`，至少检查：

`manifest.json` 还必须包含 `body_page_plan` 和 `question_architecture`。`body_page_plan` 记录共享章节
页数区间、依据和 30 页官方上限；逐问记录 `role`、`chain_type`、`progression_axis`、`route_summary`、
`planned_page_range`、`page_basis`、`planned_subsections` 和 `inheritance`。其中 `progression_axis`
取 `foundation`、`mechanism-regime`、`information-state`、`actor-count`、`spatial-fidelity`、
`parameter-uncertainty` 或 `independent`，说明相对前问真正增加的复杂度；`route_summary` 用一句话写清数学转化、
决定路线的关系、求解动作和输出；`planned_subsections` 数量由真实论证转折决定。`inheritance.status` 必须明确为
`none` 或 `used`；使用前问结果时，逐项记录来源问题、继承的状态/参数/可行域/约束、单位与精度口径，
以及进入本问前的一致性复核。`custom` 链必须另写 `custom_chain`，不得留空。

`argument_plan.structure_anchor` 固定为 `A053-structure-only`，`adaptation_basis` 说明当前题为什么
采用相应功能链以及删去了哪些不适用环节；`derivation_path` 从定义、规律或数据事实推进到最终模型；
`result_claims` 覆盖全部题面 `claim_id`；`validation_plan` 冻结主要风险、独立检查与边界/压力检查；
`presentation_plan` 为每个待证明命题选择 `prose/formula/table/figure/diagram`。图数不设上下限，同一命题
允许 4、6 幅或更多互补图，但每幅必须有独立职责并与正文形成合理交互。

- 两个前置章节独立；
- 单一总稿及全部 section 锚点已登记，未规划章节级 TeX 或导入命令；
- 假设先于符号；
- 各问均可定位到建模、求解、结果、验证和最终结论；
- 标题层级最少充分；
- 二级编号随所属章递增且连续，无跨章续号或断号；
- 压轴问不因写作顺序靠后而只留占位小节，其建模、求解、结果、验证职责与前问同等完整；
- 深度清单逐项覆盖题面要求，且每问均预留推导、参数、求解契约、结果解释、独立验证、风险响应
  和最终作答位置；
- 每问均已记录角色、职责链、完整 argument plan 和最少充分标题；核心问获得更高的推导与验证预算，
  支撑问和过渡问只压缩重复内容，不删除最终作答；
- 每问和共享章节均已有合理篇幅区间及依据，规划上界不超过 30 页；各问不是平均分配；
- 后问已标明主要升级轴；若原模型仍足够，只改变必要的参数、约束或求解范围，不为展示算法而换模；
- 临界、碰撞、边界优化和能力上限问已预留“搜索范围依据”；边界优化与能力上限问还预留
  活跃约束、约束余量或乘子、最优点邻域及界外反例复核位置；
- 使用前问输出时，继承对象及其来源、单位、有效数字和口径检查可定位；未继承时明确记为 `none`；
- 无强制分问换页；
- 无空标题和生产过程标题。

通过后先向用户完整展示全文目录、逐节大纲、每问和共享章节页数区间、判断依据及计划总上界。
此时必须停下，不创建或改写 `论文/论文.tex`，也不调用后续章节阶段。只有用户明确确认目录、
大纲和页数无误并要求开始初稿，记录 `outline-page` 确认且
`audit_user_confirmations.py --phase draft` 通过后，才由 `cumcm-paper` 继续执行
[../cumcm-restatement/STAGE.md](../cumcm-restatement/STAGE.md)。
