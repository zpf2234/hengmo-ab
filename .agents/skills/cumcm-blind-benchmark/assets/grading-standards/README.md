# CUMCM 评分标准库（grading-standards）

2018-2025 年 A/B 题的评阅要点与评阅导向材料，共 16 题（与 `../answer-benchmarks/`
同题对齐）。每题一个 markdown 文件，命名 `<年份><题号>.md`。

## 内容结构

每个文件固定包含：

1. **来源清单**：URL、来源类型、获取方式（文字 / 图片转写）；
2. **评阅要点全文**：官方评阅要点原文或命题人解析的评阅导向内容，逐问组织，
   尽量保留原文措辞；
3. **逐问加分点与扣分点摘录**：原文中"……应予以鼓励 / 值得鼓励"（加分）与
   "……不是好的做法 / 不是好的结果"（扣分）类判据逐条列出；
4. **置信度评估**：来源级别与多源一致性。

## 来源级别（从高到低）

| 级别 | 含义 |
| --- | --- |
| official_text | 全国组委会评阅要点原文的文字版转载（多源核验） |
| official_image_transcribed | 官方评阅要点扫描图或命题人官方讲评（教育部"中国大学生在线"发布）的视觉转写 |
| authored_analysis | 命题人在《数学建模及其应用》等期刊发表的问题解析（含阅卷点评）转载 |
| third_party | 高质量第三方解读（仅在无更高来源时使用，须显式标注） |

已知排除项：网传"2024 年 BZD 赛区 ABCDE 评分细则"自述为 AI 生成模拟件，一律不采用。

## 隔离纪律（与 answer-benchmarks 相同，fail-closed）

评阅要点文件**包含关键数值答案与标准模型链**。因此：

- **盲测期间（`审查/盲测冻结清单.json` 生成之前），求解者与写作者不得读取同题的
  grading-standards 文件**，违者视同接触隐藏答案，盲测记录作废；
- 评估者在冻结后使用同题文件作为评分口径补充；
- 历史题练习（非盲测）不受限制；
- 跨题共性提炼见 `cumcm/references/grading-profile.md`（不含任何具体题目数值），
  求解与写作全程可读。

## 覆盖状态

- 已收录：2018-2025 年 A/B 全部 16 题。
- 已知缺口（文件内均已如实标注）：
  - 2019A 问题 3 评阅要点原文缺失（以官方编者按旁证还原）；
  - 2021A 仅有降级来源（third_party：获奖队对官方要点的转述，单源），使用其判据时
    须按 README 来源级别折减置信，数值口径不得单独作为判定依据；
  - 2020A、2020B 无评阅要点公文原文，以命题人官方讲评（official_image_transcribed）
    为主体来源；2023A、2023B 同理（官方讲评/命题人期刊解析）。

## 维护

新增或修订后运行：

```bash
python .agents/skills/cumcm-blind-benchmark/scripts/validate_answer_benchmarks.py
python .agents/skills/cumcm-blind-benchmark/scripts/validate_grading_standards.py
```
