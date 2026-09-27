# 优秀论文一手语料对照路由

本规则规定写作各阶段如何直接对照 50 篇优秀论文的一手材料与雷点负面清单，而不是只依赖
统计摘要。目标是把结构选择、信息密度和表达纪律校准到真实获奖水平；对照永远不等于复制。

## 总体优先级

口径冲突依次服从：当年最新官方规则与 AI 使用规定；用户对本项目的最新明确确认；优秀论文一手
原页反复呈现的真实写法；项目内较早的统计阈值、负面清单和模板默认值。优秀论文主要裁定结构、
语言、信息密度、重点分配和算法表达，不以旧年份格式、明显错字、单位错误、编号错误或验证缺口
覆盖最新官方规则。旧技能与前三项冲突时修订旧技能，不建立并行口径。

语料根目录为 `最终效果/高教杯优秀论文/`。该目录不存在时跳过一手对照，只执行各技能内化的
内容标准，不阻塞写作，并在阶段门禁中记录 `corpus_alignment: "skipped_no_corpus"`。

## 时序与隔离边界

1. 求解与盲测阶段禁止读取同题（同年同题号）优秀论文全文、逐篇汇总中该题条目、答案基准
   与逐题评分标准（`cumcm-blind-benchmark/assets/grading-standards/`），隔离规则以
   `cumcm-blind-benchmark/STAGE.md` 为准；跨年评分共性
   （`cumcm/references/grading-profile.md`，无答案数值）全程可读。
2. 写作阶段的结构与风格对照优先选非同题篇目；同题篇目只有在
   `审查/盲测冻结清单.json`（由 `cumcm-blind-benchmark/scripts/freeze_submission.py` 生成，
   `status: FROZEN_BEFORE_REFERENCE`）已存在后才可用于结构对照，且只比较章节职责与信息密度。
3. 首次交付前运行 `python .agents/skills/cumcm/scripts/benchmark_corpus.py --root . --fail-on-similarity`；
   仅当前产物与审查依据绑定有效的 `PASS` 或 `PASS_WITH_MANUAL_REVIEW` 可放行。
   高相似度时核对来源并独立重写论证；覆盖缺口先补文本或报告未证明，不做机械同义替换。
4. 冻结后开放同题材料只适用于已经结束赛题的训练与评估。正在进行的正式竞赛，不得访问当届
   解题讨论或其他队伍方案，也不得委托另一代理获取；本队冻结结果不解除该限制。

## 阶段路由表

| 写作阶段 | 一手对照材料 | 雷点负面清单 |
|---|---|---|
| 封面标题（`paper-title.md`） | 先读 [已核对样例](verified-title-examples.md)；`题目普查/all_paper_titles.md` 仅作索引并回查原页 | `题目普查/AB优秀论文题目命名十大雷点与写作禁忌.md` |
| 摘要（`cumcm-paper → cumcm-abstract/STAGE.md`） | `摘要普查/all_paper_abstracts.md` | `摘要普查/AB优秀论文摘要十大雷点与写作禁忌.md` |
| 标题树（`cumcm-paper → cumcm-outline/STAGE.md`） | [已核对样例](verified-title-examples.md)；`标题结构普查/all_paper_outlines.md` 仅作索引并回查原页 | `标题结构普查/AB优秀论文标题结构十大雷点与写作禁忌.md` |
| 流程图（`cumcm-diagrams`） | `流程图普查/AB优秀论文流程图汇总.md`、`流程图普查/all_paper_flowcharts.md` | `流程图普查/AB优秀论文流程图十大雷点与写作禁忌.md` |
| 附录（`cumcm-paper → cumcm-appendix/STAGE.md`） | `附录普查/all_paper_appendixes.md` | `附录普查/AB优秀论文附录十大雷点与写作禁忌.md` |
| 逐问正文（模型成文阶段、`cumcm-results-validation`） | `全文脉络普查/question_chain_inventory.csv` | 使用既有内容标准，无独立雷点文件 |
| 数据图（`cumcm-figures`） | `图形普查/figure_inventory_final.csv` 同题型条目 | 视觉门禁已内化，无独立雷点文件 |
| 去 AI 味（`cumcm-deai`） | 各部分一手材料（同上），正文部分从同题型 PDF 就地抽 2--3 篇对应章节 | `cumcm-deai/references/corpus-voice-profile.md` 各部分"AI 味信号" |
| 图表题注与解读（`cumcm-paper`、`cumcm-results-validation`） | `图形普查/figure_inventory_final.csv` 图题列 | `cumcm/references/figure-table-narration.md`（题注句式、引用句式与解读组织，含语料统计） |

## 对照方法

1. 选篇：按题型（机理、优化、统计、仿真决策）选 3--5 篇，优先非同题；
2. 通读一手材料时回答三个问题：该阶段承担什么论证职责、信息密度多高（数值、方法名、
   对象词的占比）、优秀论文不写什么；
3. 初稿完成后对照对应雷点清单逐条自查，命中即改，并在阶段门禁 JSON 中记录
   `mine_checklist: pass`；
4. 对照期间禁止把语料论证句子摘录进草稿；连续 15 字以上重合优先复核来源、语境与必要性，
   非必要论证长句复用须独立重写，标准术语或正确引用不靠换符号、换词来制造差异。

## 已知口径矛盾裁定

雷点清单是负面模式教材，其中个别统计口径与清洗后普查冲突，以下裁定为准：

1. 题名字数：题名雷点文件中"均值 24.9 字、18--30 字最佳"为未清洗 OCR 口径；以
   `paper-title.md` 按稳定文件名回算的口径（均值约 16.4 字、观察范围 7--33 字）为准，
   不设字数合规线。
2. 标题结构雷点"目录与 PDF 页码精确匹配"：国赛电子版论文不设目录页，此条不适用；
   跨章编号连续性检查仍然执行。
3. 标题结构雷点"总页数 20~24 页最佳"：不采用。页数只按官方正文口径计算，即正文主体首页至
   附录开始前一页（含 AI 声明和参考文献、不含摘要与附录）；只设不超过 30 页的硬上限。
4. 流程图雷点"复杂算法必配流程图"：以
   `national-first-precision-and-visual-gates.md` 的判据为准——存在非平凡分支、循环、
   回退或多阶段依赖时流程图是必需证据，单一线性步骤不画。
5. 一切图形数量表述服从“待证明命题与不可替代职责决定、语料密度只作非阻断参照”；附录数量
   服从“页数由复现需求自然形成”原则，
   语料频率不转写为配额。
