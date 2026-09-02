# CUMCM 跨题型回归套件

这套 skills 的价值以跨题型稳定性衡量，不以单篇论文或单次得分衡量。重大修改后至少完成
3 个代表题的独立前向测试；发布候选版本完成全部 6 个案例。

## 本地确定性预检

任何公开技能、阶段模块、门禁、路由、模型目录、盲测基准、交付规则或绘图实现修改后先运行：

```bash
python .agents/skills/cumcm/scripts/run_skill_preflight.py --root . --no-write
```

预检统一检查公开技能的 frontmatter、`agents/openai.yaml`、默认触发提示和相对链接，并运行总控一致性、
相似度、原创性消费、语言、视觉、provenance、国一产物绑定、路由 parity、A/B 模型目录、单一总稿与
附件交付、ZIP 内 AI 详情、RAR 清单与哈希绑定、答案/评分基准、审查兼容性和 `figure_mcp` 全部测试。
预检不替代下方跨题型前向测试。

一次比赛是否真正覆盖模块，另由 `audit_skill_execution_plan.py` 审计。它区分公开 Skill、内部 STAGE、
必经模块和条件模块；“全部使用”只允许解释为“全部适用模块有执行证据，全部不适用模块有明确理由”，
不能解释为 26 个模块无条件全跑。

## 固定案例

| 案例 | 赛题 | 核心原型 | 必须出现的验证 | 邻近优秀论文 |
|---|---|---|---|---|
| 2023-A | 定日镜场的优化设计 | 三维光学机理、空间布局、约束优化 | 光学分量闭合、时点/网格收敛、功率约束复核 | 定日镜场系列 |
| 2023-B | 多波束测线问题 | 几何覆盖、地形拟合、航线优化 | 平坦/斜坡特例、覆盖率复算、漏测与重叠审计 | 多波束测线系列 |
| 2024-A | “板凳龙”闹元宵 | 曲线运动学、碰撞检测、路径优化 | 弦长残差、独立碰撞算法、步长收敛、速度约束 | 板凳龙系列 |
| 2024-B | 生产过程中的决策问题 | 抽样检验、递归决策、离散优化 | I/II 类错误、策略枚举交叉验证、参数不确定性 | 生产决策系列 |
| 2025-A | 烟幕干扰弹的投放策略 | 三维动力学、时空遮蔽、混合优化 | 几何遮蔽复算、多初值、可行性与时间离散收敛 | 2025 A 优秀论文 |
| 2025-B | 碳化硅外延层厚度的确定 | 光学机理、信号处理、逆问题 | 双角度一致性、峰值稳定性、合成信号回收、多光束诊断 | 2025 B 优秀论文 |

案例文件位于 `例题/23`、`例题/24`、`例题/25`。语料文件仅用于质量校准，不向前向测试
代理提供优秀论文正文、结论或数值。

## 三档测试

### 语料普查回归

涉及摘要、标题、架构、图表、验证或附录规则的修改，先运行：

```bash
python 最终效果/高教杯优秀论文/全文脉络普查/scan_full_paper.py
```

放行条件：

- `paper_count=50`，A/B 各 25，总 PDF 页数 2399，独立 PDF 内容 49；
- `paper_narrative_summary.csv` 覆盖 50 篇，参考文献和附录边界均为 50/50；
- 摘要报告与 `paper_abstract_summary.csv` 的均值、中位数和定量结果计数一致；
- 标题报告明确区分 2148 条宽口径候选与 1958 条严格结构记录；
- 不再出现“1000--1150 为黄金区间”“显式附录 44/50”“必须固定十章/流程图”等已纠正结论；
- OCR、标题显式下限、正文词项和页面人工抽检的证据等级有明确标注。

### 路由测试

输入题面与附件目录，只要求生成 `求解/任务契约.json` 和 `求解/求解计划.md`。检查：

- 问题数与官方输出文件识别正确；
- 每问原型不由 A/B 字母决定；
- 主验证和补充验证与问题结构匹配；
- 每问存在基线/主候选/异构挑战，或有可审计的唯一机理理由；候选淘汰条件在试算前确定；
- 没有从优秀论文泄漏模型名、结论或数值。

六个案例必须全部通过。该测试适合每次修改后快速执行。

将六份契约保存到隔离评测目录后运行：

```bash
python .agents/skills/cumcm/scripts/evaluate_routing_suite.py --contracts <六个任务契约路径> --min-contracts 6
```

`--contracts` 必须显式列出六份任务契约，不得用 `*.json` 把既有评测报告再次作为契约输入；
输出文件应放在输入目录中但使用独立文件名。

### 证据包测试

至少选择机理、统计/决策、优化各 1 题，执行到 `cumcm-solve` 结束。检查：

- 任务契约、逐问脚本、结果表、`metrics.json`、`运行环境.json`、证据矩阵齐全；
- 官方 Excel 模板被正确填充；
- 每问有主验证、补充检查和最终回答；
- 每问 `metrics.json` 含模型选择和答案充分性，挑战路线与主模型不是同一误差机制；
- 优化题有界、gap、缩小实例精确解或扩大邻域证据；无法证明全局最优时使用近优表述；
- 从原始附件重跑后关键数字在声明容差内一致。
- 按 `运行环境.json` 的逐问命令执行成功，声明的 Python 与依赖版本可核对。

对三个隔离项目运行：

```bash
python .agents/skills/cumcm/scripts/evaluate_evidence_suite.py --projects <机理项目> <统计或决策项目> <优化项目> --min-projects 3
```

### 全流程测试

至少 1 个从未参与 skill 设计的留出题，执行到最终 PDF。必须同时满足：

- 开写前逐问内容准备度已通过：输入、模型特有推导、参数来源、求解契约、预期输出、独立验证与边界
  均锚到题面、附件或求解证据；不得用待写正文反向自证，也不得出现页数、字数、公式数或图数配额；
- 半自动确认记录有效：方法与结果确认发生在论文规划之前；目录、大纲和页数确认发生在模板落盘与
  正文生成之前；两次确认均绑定当时证据哈希，系统自评或自动 PASS 未替代用户确认；
- 自动硬门槛全部 PASS；
- `审查/section-chain/manifest.json`、全部章节门禁、自动语言审计和章节链审计均为 PASS；
- `审查/逐问深度清单.json` 八项职责逐问闭合，`正文深度审计.json` 为最终阶段 PASS，且官方正文页数、
  PDF 总页数和 SHA-256 与当前编译成品一致；
- 使用数据图时 `figure-registry.json` 与 `figure-style-audit.json` 为 PASS；使用关系图、流程图、
  机理图或几何图时 `diagram-registry.json` 与 `diagram-style-audit.json` 为 PASS；
- 正文按 `appendix:start - body:start` 唯一计算，包含正文主体、AI 工具使用声明和参考文献，
  不含摘要与附录，并且不超过 30 页；
- 原创相似度 PASS；
- 语料声纹审计（`corpus-voice-audit.json`）硬项为零，去 AI 化审查 PASS，视觉审查明确图型适配 PASS；
- 问题分析按各问真实对象、约束、数学转化、难点与依赖自然组织；跨问重复句架、固定四步标签和
  “首先—然后—最后”式机械串联为零，不以 150 字上限或等长段落裁切内容；关系图只在确有信息增益时出现；
- 核心公式在局部上下文中可读：式前说明目的，符号先给语义与单位，复杂关系先定义中间量再写主式，
  式后解释结构、约束或用途；所有多重修饰、嵌套下标和一式多关系风险均已简化或留下可核验保留理由；
- 图表叙述审计（`figure-table-narration.json`）硬项为零：题注、编号引用与解读文字合规；
- 12 维评分总分不低于 54/60，且每维不低于 4；
- 独立评审代理未发现 P0/P1 问题；
- `审查/独立评审.json` 为 PASS，独立总分不低于 54/60 且最低维度不低于 4；
- 与 3-5 篇邻近优秀论文相比，题目回答覆盖、验证强度和证据追溯不弱。
- 正文只呈现最终采用的方法及必要理由；候选比较、试错过程与模型竞技记录仅保留在内部证据中。
- 数据图在最终宽度下字体、单位、色觉与灰度区分、图例遮挡和整页构图均通过；正式结构图为
  TikZ/Visio 风格，连接、线语义、对象锚点、缩略图和整页渲染全部通过。

### 冻结后盲测答案

留出题求解者只接收题面、附件、skills 和空目录。最终 `metrics.json`、结果表与 PDF 冻结后，
由独立评估者读取隐藏参考答案、官方校验量或独立高精度求解结果，写
`审查/盲测答案评估.json`。2018-2025 年 A/B 历史题的隐藏参考优先使用
`cumcm-blind-benchmark/assets/answer-benchmarks/<year><problem>.json`（获奖论文交叉基准，
confidence 与容差纪律见其 README；low 置信条目须另用独立实现复核）。文件至少包含：

```json
{
  "pass": true,
  "reference_visible_during_solve": false,
  "answer_frozen_before_reference": true,
  "constraints_pass": true,
  "questions": {
    "问题一": {"指标": "相对误差", "数值": 0.003, "阈值": 0.01, "通过": true}
  }
}
```

阈值在评估前按题型声明：可校验数值检查相对/绝对误差，优化检查可行性与目标差，预测检查
隐藏集误差，评价检查结论方向和稳定区间，逆问题检查参考值是否落在合理不确定度内。
若没有唯一真值，使用两种独立高精度实现或经验证的上下界，不强造“标准答案”。

冻结后评估者另加载同题 `cumcm-blind-benchmark/assets/grading-standards/<year><problem>.md`
（官方评阅要点，隔离纪律同答案基准），在数值判定之外按其“逐问加分点与扣分点”核对
候选解是否踩中官方点名的扣分模式；缺失年份按无评分标准处理，不引用非分级来源。
库结构校验：

```bash
python .agents/skills/cumcm-blind-benchmark/scripts/validate_grading_standards.py
```

正文结构还必须通过以下人工反馈回归：

- 摘要粗体能区分核心方法与最终结论，普通数字和过程信息不被批量加粗；
- 摘要、正文不含 AI、提示词、工具名、生成过程或审查策略；
- 问题重述、问题分析、模型假设、符号说明、逐问建模求解、结果验证、评价、引用、附录和摘要均由对应子技能门禁验收；
- 自动语言审计对“计算口径”“本文的回答”“前者回答……后者回答……”“首次出现处定义”以及正文中的附件、文件、代码和脚本痕迹为零命中；
- 模型假设默认位于符号说明之前；例外有明确结构理由；
- 每问二级标题默认 2--4 个，超过 5 个已逐项证明不可合并；正文二级标题超过 24 个时有
  合并审查记录；
- 至少一名审查者逐节阅读正文，而不是仅依赖摘要、标题树和自动脚本。
- 开写前先按各问难度、推导量、结果量和验证需求规划页幅，再统筹共享章节；计划上界不得超过 30 页。
  至少保留一次官方口径的实际编译页数反馈；内容补强只能对应推导、参数、求解、解释、验证、风险边界
  或漏答项，不得以背景、重复题面、装饰图或版式拉伸补页。
- 首份可交付初稿门禁必须证明“内部失败构建（不可交付）→ 自动回到已冻结论证缺口 → 新 PDF 哈希 → 首次放行”的闭环；
  若失败构建曾获得初稿身份，或生成链没有继续到 `PASS_FIRST_DELIVERABLE_DRAFT`，回归失败。

## 防污染

- 前向测试代理只接收题面、附件、skills 和空项目目录。
- 不提供参考论文正文、预期模型、预期答案、现有解题代码或整改结论。
- 同一案例的产物不复用于下一次独立测试。
- 隐藏参考、同题优秀论文数值和 `盲测答案评估.json` 在答案冻结前对求解者不可见；看到后返工的
  项目转为开发样本，不计作留出题。
- 2024-A 可作为开发样本，但不能作为唯一全流程证明；至少保留 2025-B 或新增年份题作留出题。

## 发布门槛

同时满足才称为“优秀论文级 skill 候选版本”：

1. 六案例路由测试 6/6；
2. 三类证据包测试 3/3；
3. 留出题全流程测试至少 1/1；
4. 冻结后盲测答案评估至少 1/1；
5. 所有脚本语法、skill 格式和相对链接校验通过；
6. 数据图与 TikZ/Visio 图形审计均各有一个应通过的正例和至少两个应拒绝的反例；
   流程图固定风格另须通过 `cumcm-classic-orthogonal` 正例，并拒绝缺失 profile、未知版型、
   装饰性阶段徽标/焦点卡片和虚线反馈；
   特色主视觉图另须通过 A 类机理—结果、B 类策略景观、不确定性—决策联动三个结构化 spec，
   并明确拒绝仅换配色、无联动的装饰性拼图和缺科学证据的伪特色图；
7. 回归汇总中不存在未解释的分数下降或新增硬错误。

视觉审计脚本的隔离正反例已由统一预检调用；需要单独定位时运行：

```bash
python .agents/skills/cumcm/scripts/selftest_visual_audits.py --root .
python .agents/skills/cumcm/scripts/selftest_language_audit.py --root .
python .agents/skills/cumcm/scripts/selftest_provenance_registry.py
python .agents/skills/cumcm-deai/scripts/selftest_corpus_voice.py
python .agents/skills/cumcm-notation/scripts/selftest_formula_readability.py
python .agents/skills/cumcm-paper/scripts/selftest_figure_table_narration.py
python .agents/skills/cumcm-paper/scripts/selftest_question_depth.py --root . --no-write
python .agents/skills/cumcm-paper/scripts/selftest_first_draft_gate.py --root . --no-write
python .agents/skills/cumcm-paper/scripts/selftest_section_chain_bindings.py
```

`selftest_visual_audits.py` 的国一分支必须覆盖 schema v4 正例、配色伪特色、装饰拼图、缩略图失败、
有理由豁免与无理由豁免。MCP 目录另运行 `pytest -q test_signature_benchmarks.py` 和
`python signature_benchmarks.py`，后者是明确标注为 `python-matplotlib` 的本地兼容回归，必须真实生成
三套 JSON/PDF/SVG/PNG；生产数据图按当前总控统一由 Python（matplotlib）从结构化结果直接绘制，
并保留真实脚本、输入数据和 renderer provenance，不得把回归产物冒充其他后端产物。

最后一个测试必须先验证真实产物，再临时篡改图源或最终矢量，确认 provenance 审计失败，恢复字节后
再次通过。负面测试只能在临时副本或带 `finally` 恢复的文件上执行，并保存篡改前后报告。
