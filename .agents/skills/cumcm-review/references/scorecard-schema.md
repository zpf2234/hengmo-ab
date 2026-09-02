# 结构化评分卡（v2，禁止自动伪造 PASS）

审查必须写 `审查/评分卡.json`。自动化只预填可观测指标、证据路径和 PDF 哈希，不替审查者给
主观项打分，也不依据“文件存在”推断优秀。未完成人工审查时必须使用 `REVIEW_REQUIRED`。

```json
{
  "schema_version": 2,
  "verdict": "REVIEW_REQUIRED",
  "hard_gates_pass": false,
  "automation_policy": "NO_AUTOMATIC_PASS_OR_SUBJECTIVE_SCORE",
  "pdf_binding": {"path": "论文/论文.pdf", "sha256": "64位小写十六进制"},
  "objective_metrics": {
    "registry_coverage_complete": true,
    "provenance_hashes_verified": true,
    "diagram_layout_machine_inventory_complete": true
  },
  "dimensions": {
    "题意与口径": {"assessment": "SUBJECTIVE", "score": null, "evidence": [], "status": "REVIEW_REQUIRED"},
    "数据理解": {"assessment": "SUBJECTIVE", "score": null, "evidence": [], "status": "REVIEW_REQUIRED"},
    "模型适配": {"assessment": "SUBJECTIVE", "score": null, "evidence": [], "status": "REVIEW_REQUIRED"},
    "数学严谨": {"assessment": "SUBJECTIVE", "score": null, "evidence": [], "status": "REVIEW_REQUIRED"},
    "求解实现": {"assessment": "AUTO_PREFILLED", "score": null, "evidence": ["求解/证据审计.json"], "status": "REVIEW_REQUIRED"},
    "验证强度": {"assessment": "AUTO_PREFILLED", "score": null, "evidence": ["求解/证据矩阵.csv"], "status": "REVIEW_REQUIRED"},
    "结果价值": {"assessment": "SUBJECTIVE", "score": null, "evidence": [], "status": "REVIEW_REQUIRED"},
    "证据追溯": {"assessment": "AUTO_PREFILLED", "score": null, "evidence": ["审查/provenance"], "status": "REVIEW_REQUIRED"},
    "可复现性": {"assessment": "AUTO_PREFILLED", "score": null, "evidence": ["求解/运行环境.json"], "status": "REVIEW_REQUIRED"},
    "写作原创": {"assessment": "SUBJECTIVE", "score": null, "evidence": [], "status": "REVIEW_REQUIRED"},
    "可视表达": {"assessment": "AUTO_PREFILLED", "score": null, "evidence": ["审查/figure-registry.json", "审查/diagram-registry.json"], "status": "REVIEW_REQUIRED"},
    "提交就绪": {"assessment": "AUTO_PREFILLED", "score": null, "evidence": ["审查/自动审查.json"], "status": "REVIEW_REQUIRED"}
  },
  "total": null,
  "review_required": ["题意与口径", "数据理解", "模型适配", "数学严谨", "求解实现", "验证强度", "结果价值", "证据追溯", "可复现性", "写作原创", "可视表达", "提交就绪"],
  "p0_findings": [],
  "p1_findings": []
}
```

## 自动预填边界

- 可预填：文件存在/哈希、registry 覆盖、按 `appendix:start - body:start` 计算的官方正文页数、
  脚本和证据审计状态、连接清单完整度、PDF 绑定。
- 不可自动判定：题意正确、模型合理、推导严谨、结果价值、原创性、视觉美学，也不可由客观指标直接换算 0--5 分。
- `AUTO_PREFILLED` 表示证据已整理，不表示该维度通过；所有分数仍由审查者核验后填写。
- 任一 `score=null`、`status=REVIEW_REQUIRED`、证据缺失、P0/P1 未关闭或 PDF 哈希失配时，统一审计必须 FAIL。

## 人工签发 PASS 的最低结构条件

审查者完成全部 12 维后，将每项 `status` 改为 `REVIEWED`，填写整数 0--5、审查者与审查时间，
再计算 `total`。国一候选要求总分不低于 57/60、`可视表达=5`、P0/P1 为空、硬门禁全过，且
`pdf_binding.sha256` 等于统一审计本次计算值。自动脚本不会代替审查者完成这些动作。
