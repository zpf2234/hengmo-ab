# CUMCM 答案基准库（评估者专用，求解阶段禁读）

覆盖 2018-2025 年 A/B 共 16 题，数据来自 `最终效果/高教杯优秀论文` 的 50 篇获奖论文摘要（48 篇文本层提取 + 2025 两篇扫描版视觉读取），共 66 个数值检查条目。

## 隔离规则（与 SKILL.md 一致，fail-closed）

1. 求解者在冻结（`freeze_submission.py`）成功之前，禁止读取本目录任何文件。读过即失去盲测资格，只能标记为开发样本。
2. 本库仅供独立评估者在验证冻结清单后，用于填写 `审查/盲测答案评估.json` 的逐问参考。
3. 这些数值是获奖论文的交叉共识，不是官方标准答案。单源条目（confidence=low）与优秀论文本身的错误可能同时存在，评估者必须结合独立高精度实现复核，不得把本库当唯一真值。

## Schema 要点（schema_version=1）

- 每题一个文件 `<year><A|B>.json`，`sources` 逐篇给出语料 PDF 路径（校验器检查文件存在）。
- 每问 `evaluation_mode` ∈ numeric / optimization / estimation / strategy / design_open，且必须有 `checks` 或 `qualitative_criteria`。
- 数值检查两种形态：
  - `reference_value` + `tolerance`（relative/absolute）：有近似唯一真值的量；
  - `reference_band{low,high}` + `better_direction`：启发式优化的优秀论文水平带。
- `values` 逐源记录原始提取值（null 表示该源摘要未给出），`source_note` 说明出处。
- confidence 纪律：`high` 要求 ≥2 个独立来源且散布 ≤ 2×容差（校验器强制）；单源或散布大只能 medium/low。

## 已知语料事实（写基准时已核对）

- （A229）与（A401）是同一篇论文的重复文件，2018A 只计一个独立来源。
- 2025A/2025B 为扫描版（无文本层），条目来自摘要页视觉读取，单源。
- A092/B311/B477 部分摘要数值嵌在公式图片中，文本层缺失，相应条目已降级或改为定性判据。
- 跨篇不可比的量（2021A 接收比、2024B 利润口径、2019A 双喷嘴角速度多解）不设数值检查，只留方向性/一致性判据，原因写在 notes。

## 使用与校验

```bash
# 结构校验（写 审查/答案基准库校验.json）
python .agents/skills/cumcm-blind-benchmark/scripts/validate_answer_benchmarks.py --root .

# 校验器 fail-closed 自测（写 审查/答案基准库自测.json）
python .agents/skills/cumcm-blind-benchmark/scripts/selftest_answer_benchmarks.py
```

新增年份时：按 schema 写 `<year><A|B>.json`，跑校验通过后在本 README 更新覆盖范围。多篇可交叉时优先提高 confidence，不允许为凑 high 而删掉离群源——把离群值留在 `values` 里并降级。
