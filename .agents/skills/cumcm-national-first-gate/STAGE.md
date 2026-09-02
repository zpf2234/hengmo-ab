---
name: cumcm-national-first-gate
description: CUMCM 国一竞争候选的最终 fail-closed 放行技能。用于汇总盲测、同类基准、逐问证据、精度、图表职责与解读、MCP 图质量、对抗评审、12 维评分、P0/P1、复现和最终 PDF 哈希；缺项或 REVIEW_REQUIRED 一律不得包装为国一候选 PASS。
---

# CUMCM 国一总门禁

本阶段仅由 `cumcm-review` 在全部前置审查完成后执行，不作为独立可发现技能。

## 原则

这是最终放行器，不替代求解、论文或评审。缺证据不是警告，而是失败。自动脚本不得代替主观评分，也不得生成虚假的 PASS。

## 必需输入

- `求解/证据审计.json`、逐问 metrics 和证据矩阵；
- `审查/盲测冻结清单.json` 与 `盲测答案评估.json`；
- `审查/优秀论文对标.json` 和 `REVISION_ACTIONS.md` 闭环；
- 自动审查、复现抽查、章节链、原创、语言、语料声纹（`corpus-voice-audit.json`）、
  图表叙述（`figure-table-narration.json`）和视觉审查；
- figure/diagram registry、provenance 与最终页视觉记录（实际使用时）；
- 三路对抗评审和无未关闭 P0/P1 的汇总；
- 恰含 12 维、无 REVIEW_REQUIRED 的 `评分卡.json`；
- 未参与求解写作的 `独立评审.json`；
- 最终 `论文/论文.pdf`。

## 放行阈值

同时满足：硬门禁全过；总分不低于 57/60；每维不低于 4；可视表达 5/5；独立评审总分不低于 57 且最低维不低于 4；P0/P1 为 0；逐问盲测通过；结果精度至少比报告末位高一个数量级；正文深度、图表证据职责和逐图逐表解读通过；复杂流程图及特色主视觉要求通过；最终 PDF 哈希与审计绑定一致。图密度仅作非阻断参照。

## 执行

```bash
python .agents/skills/cumcm-national-first-gate/scripts/check_gate.py --root .
```

生成 `审查/NATIONAL_FIRST_SCORECARD.json`、`审查/FINAL_GATE_REPORT.md` 和 `审查/PDF_HASH.json`。脚本只核验已有证据，不填写主观分数。

## 唯一合法状态

- `PASS_NATIONAL_FIRST_CANDIDATE`：全部条件通过；仅表示内部国一竞争力门禁通过，不承诺获奖。
- `REVISE_NATIONAL_FIRST_CANDIDATE`：产物存在但有可修复缺口，同时写明 `REVISION_ACTIONS.md`。
- `BLOCKED`：答案真实性、参考隔离、关键输入或运行条件无法确认。

不得先称完整国一成品，再在后文撤回。
