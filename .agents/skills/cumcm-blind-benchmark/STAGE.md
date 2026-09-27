---
name: cumcm-blind-benchmark
description: CUMCM 冻结后盲测与隐藏答案评估技能。用于在求解者看不到同题答案、优秀论文模型链和关键数值的条件下冻结代码、结果与 PDF，再由独立评估者使用官方校验量、隐藏参考或独立高精度实现逐问核验；防止看答案返工冒充前向能力。
---

# CUMCM 冻结后盲测

本阶段由 `cumcm` 总控在答案冻结后执行，并由 `cumcm-review` 消费评估结果；不得独立绕过隔离顺序触发。

## 隔离原则

本阶段评价完整求解能力。用户只检验历史题建模思路时，改用
[独立思路冻结与遗漏评估](../cumcm-model-tournament/references/historical-idea-benchmark.md)，
其候选快照和覆盖结果不能替代本阶段的完整产物冻结或 PASS；参考后修订只计开发结果。

求解阶段不得向求解者提供同题优秀论文正文、答案、参数、现有解题代码或整改结论。结构统计和官方公开题面可以使用。评估者与求解/写作者隔离，隐藏参考只在冻结成功后开放。

## 冻结

运行：

```bash
python .agents/skills/cumcm-blind-benchmark/scripts/freeze_submission.py --root .
```

生成 `审查/盲测冻结清单.json`，绑定题面、附件、任务契约、逐问代码、结果、metrics、证据矩阵和论文 PDF 的 SHA-256。冻结后任何受控文件变化都会使盲测失效；看参考后修改的项目只能标为开发样本。

## 独立评估

评估者先验证冻结清单，再读取官方答案、隐藏校验量或独立高精度结果。逐问预先声明指标和阈值：可校验数值使用绝对/相对误差；优化检查可行性与目标差；预测检查隐藏集误差；评价检查方向和扰动稳定性；逆问题检查参考值是否落在不确定度内。没有唯一真值时使用两个独立高精度实现或经验证的界，不强造标准答案。

## 答案基准库

`assets/answer-benchmarks/` 收录 2018-2025 年 A/B 共 16 题的隐藏参考（源自 50 篇获奖论文摘要交叉提取，66 个数值检查条目），schema 与 confidence 纪律见目录内 README。使用规则：

- 求解者冻结前禁读本目录；读过即降级为开发样本。历史真题盲测时评估者以对应 `<year><problem>.json` 为参考骨架：`reference_value`+`tolerance` 条目按误差判定，`reference_band` 条目按水平带与 `better_direction` 判定，`qualitative_criteria` 逐条核对。
- 库值是获奖论文共识而非官方答案：`confidence=low` 或单源条目必须再用独立实现复核后才可给结论；候选答案落在容差外不自动判死，需评估者写明是候选错误还是基准局限。
- 结构校验 `scripts/validate_answer_benchmarks.py --root .` 必须通过（写 `审查/答案基准库校验.json`），校验器自身用 `scripts/selftest_answer_benchmarks.py` 回归。

## 评分标准库

`assets/grading-standards/` 收录同一 16 题的官方评阅要点与命题人讲评转写（来源分级
与隔离纪律见目录内 README）。使用规则：

- 逐题文件含标准模型链与答案数值，**隔离级别与答案基准库相同**：求解者冻结前禁读
  同题文件，读过即降级为开发样本；跨年共性（无数值）见
  `cumcm/references/grading-profile.md`，求解与写作全程可读。
- 评估者冻结后加载同题 `<year><problem>.md`，把"逐问加分点与扣分点"作为
  `qualitative_criteria` 之外的评分口径补充：数值对错之外，还核对候选解是否踩中
  官方点名的扣分模式（如算法黑箱、无误差分析、结果无检验）。
- 缺失年份按无评分标准处理（fail-closed，评估只用答案基准库口径），不得引用
  非分级来源替代。
- 结构校验 `scripts/validate_grading_standards.py` 必须通过（写
  `审查/评分标准库校验.json`）。

写 `审查/盲测答案评估.json`，至少包含 `pass`、`reference_visible_during_solve=false`、`answer_frozen_before_reference=true`、`constraints_pass`、`freeze_manifest_sha256`、评估者、时间和逐问记录。逐问记录必须给出指标、数值、阈值、参考来源与通过状态。

## 门禁

冻结哈希有效、参考在冻结前不可见、约束通过且每问通过，才可 PASS。参考可见后返工、缺逐问阈值、用同一实现自证或冻结文件变化均为 `BLOCK_BLIND_BENCHMARK`。
