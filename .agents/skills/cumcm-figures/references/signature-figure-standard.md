# CUMCM A/B 特色主视觉图标准

## 定义

特色主视觉图不是“复杂、多面板、颜色特别”的图，而是以真实模型和结构化结果为基础，在一个连续阅读链中压缩核心命题、关键边界/事件与最终答案的高信息密度证据图。普通稿可选；国一/国奖候选必须规划，确实不适合时允许有证据、经独立批准的豁免，禁止为满足数量强制拼图。

全局颜色语义、A/B 原型目录与豁免规则以 [visual-identity-and-archetypes.md](visual-identity-and-archetypes.md) 为唯一来源；开工复制 [../templates/signature-figure-plan.md](../templates/signature-figure-plan.md)。

## 合格条件

1. `core_claim` 绑定真实 `claim_ids`，单图承担不可替代的核心结论；
2. `ten_second_takeaway` 在 8--12 秒内说清对象、关键变化/临界点和答案；
3. `read_order` 写机制/状态/结论等语义步骤，不写“左—中—右”；
4. `data_linkage` 绑定源字段，并说明跨面板或图元如何共享事件、阈值或因果链；
5. 比普通图新增解释职责，可合并重复证据但不得删除必要诊断；
6. 缩略浏览轮廓清楚，最终页面的字号、图例、标注、图题和留白全部通过；
7. 保留原生数据、spec/生成源、PDF/SVG、PNG 预览及 provenance v2。

## 机械字段（figure registry schema v4）

```json
{
  "signature_figure": true,
  "signature_archetype": "a_mechanism_result",
  "core_claim": "边界触发关键事件并使误差在报告精度内闭合",
  "ten_second_takeaway": "越过临界边界后误差降至阈值内",
  "read_order": ["机制与边界", "关键事件", "结论与残差"],
  "data_linkage": {
    "claim_ids": ["C-Q1-03"],
    "source_fields": ["time", "boundary_margin", "error"],
    "panel_links": ["边界零点->事件时刻", "事件时刻->残差闭合"],
    "pass": true
  },
  "signature_checks": {
    "integrated_narrative": true,
    "mechanism_to_result": true,
    "adds_explanatory_responsibility": true,
    "not_palette_only": true,
    "not_decorative_collage": true,
    "thumbnail_silhouette_pass": true,
    "ten_second_read_pass": true,
    "final_page_visual_pass": true
  }
}
```

A 类 `a_*` 原型额外要求 `mechanism_to_result=true`。B 类策略景观或不确定性联动必须让策略区/切换点可回溯到源数据。

## 明确拒绝

以下任一项不得计为特色图：

- 只改变配色、字体、渐变、阴影、背景或装饰图标；
- 柱图、折线、热力图简单拼接，面板之间没有共享事件/阈值/因果链；
- 阅读顺序只有“左图—中图—右图”；
- 数值不能回溯到结构化结果，或为美观手工移动数据几何；
- 以装饰性三维、商业仪表盘、信息图插画替代科学证据；
- 缩略图没有主次，最终页面字体低于 8 pt、裁切或图题漂移；
- 为展示多个软件而增加无意义面板。

## 数量与豁免

- 普通稿：特色图可选，但声明为特色图时仍须通过字段审计；
- 国一/国奖候选：至少 1 张合格图，复杂证据通常 2--3 张；这是规划范围，不是强制拼图配额；
- 不适合时在 registry 根级 `signature_policy.exemption` 记录具体理由、关联证据、独立审查者和 `APPROVED`；
- 豁免仅免除特色图数量，不降低科学、provenance、逐图正文解读、最终页面或评分门禁。

运行国一门禁：

```bash
python .agents/skills/cumcm-figures/scripts/audit_figure_style.py --root . --track national-first
```
