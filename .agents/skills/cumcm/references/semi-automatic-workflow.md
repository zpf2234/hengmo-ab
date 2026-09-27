# 半自动论文工作流

本项目正式模式采用半自动流程。系统负责分析、求解、检查和生成，但论文阶段存在两个必须由用户明确
确认的停点；自动审查通过、模型评分较高或系统自行判断均不能代替用户确认。

## 模拟项目例外

模拟题项目可以在根目录 `.cumcm_state.json` 中明确写入：

```json
{
  "workflow_policy": {
    "mode": "simulation",
    "method_result_confirmation_required": false,
    "outline_page_confirmation_required": false
  }
}
```

该标记只取消两次用户停点，不取消方法结果、证据矩阵、验证、篇幅、编译、AI 表达审查或最终交付门禁。
`audit_user_confirmations.py --phase paper-plan|draft` 在该模式下返回已跳过确认的审计结果；状态缺失或无效时
仍按正式模式要求确认。

## 确认点一：方法与结果

求解阶段完成后，先向用户提交方法与结果审阅包，至少包括：

- 各问最终采用的方法、关键假设和选择理由；
- 最终数值、单位、精度与题目要求的结构化答案；
- 独立验证、稳健性或最优性证据；
- 尚存风险、适用边界和国一竞争力判断依据。
- 现有 `求解/创新贡献表.md` 中的方法差异简报：常规路线与本题改造、数学依据、公平对照、收益与
  成本、边界及采用/拒绝状态；无实测收益时不把新设想包装成已成立贡献。
- 实际 AI 参与的建模、代码、图表和文字环节，以及参赛队尚需核验的关键内容。只有真实反馈可
  记录为参赛队核验；模型或另一个 AI 的复核不能替代该事实。

此时不得创建论文模板、调用论文章节链、生成正式目录或铺写正文。只有用户明确确认方法与结果
达到其认可的国一目标，并明确要求进入模板与论文 skills 阶段后，才记录
`method_result_confirmation=confirmed`。系统自评“达到国一水平”不构成确认。

确认记录必须绑定用户实际审阅的求解证据文件及其 SHA-256。任何已绑定文件变化都会使确认失效，
须重新向用户说明变化并再次确认。

## 确认点二：目录、大纲与页数

确认点一通过后，调用 `cumcm-paper` 和 outline 阶段，只生成并展示：

1. 全文完整目录；
2. 各节写作大纲，包括每问准备写入的模型、推导、结果、验证与结论；
3. 各问和共享章节的预计页数区间、判断依据及合计上界。

计划页数按实际难度和证据量分配，不平均切分；合计上界不得超过 30 页。此阶段可以创建内部
章节清单和页数计划，但不得把模板复制到 `论文/论文.tex`，也不得开始摘要或正文。

只有用户明确确认目录、大纲和页数安排无误，并要求开始初稿后，才记录
`outline_page_confirmation=confirmed` 并进入模板落盘与增量成文。目录、逐问大纲或页数计划发生
实质变化时，原确认失效，必须重新确认。

## 确认记录

统一使用 `审查/用户确认节点.json`，由
`scripts/audit_user_confirmations.py` 初始化、记录和核验：

```bash
python .agents/skills/cumcm/scripts/audit_user_confirmations.py --root . --init
python .agents/skills/cumcm/scripts/audit_user_confirmations.py --root . --record method-result --confirmation-note "用户已明确确认方法与结果并要求进入论文规划" --evidence 求解/证据矩阵.csv --evidence 求解/证据审计.json
python .agents/skills/cumcm/scripts/audit_user_confirmations.py --root . --phase paper-plan
python .agents/skills/cumcm/scripts/audit_user_confirmations.py --root . --record outline-page --confirmation-note "用户已明确确认目录、大纲和页数并要求开始初稿" --evidence 审查/section-chain/manifest.json --evidence 审查/逐问深度清单.json
python .agents/skills/cumcm/scripts/audit_user_confirmations.py --root . --phase draft
```

`confirmation-note` 只写简短事实，不复制长段对话。记录命令仅在当前对话中确有对应明确确认时
执行；“继续看看”“先这样”“你判断即可”不视为确认。

确认点二通过后，初稿生成内部可继续执行章节门禁、增量编译和缺口修复，不再为普通技术细节反复
打断用户；但方法、最终结果、全文结构或页数计划发生实质改变时，退回相应确认点。
首稿交付前的表达、语义和相似度检查不增加第三个常规确认点。内部审查可由 AI 执行并如实注明
审查者类型；首次交付仍是辅助稿，不代表参赛队已逐项完成最终人工核验或已具备正式提交资格。
