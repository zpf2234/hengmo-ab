# 逐问内容深度与编译页数反馈契约

## 目录

1. [语料结论与页数口径](#语料结论与页数口径)
2. [成文前实质准备度](#成文前实质准备度)
3. [逐问实质内容门槛](#逐问实质内容门槛)
4. [验证与风险响应路由](#验证与风险响应路由)
5. [直接成文闭环](#直接成文闭环)
6. [结构化清单](#结构化清单)
7. [编译后的回退职责](#编译后的回退职责)
8. [放行判定](#放行判定)
9. [首次交付前的质量复核记录](#首次交付前的质量复核记录)

## 语料结论与页数口径

本规则依据本地 50 篇一等奖论文的全文边界普查和代表页面复核。50 个 PDF 共 2399 页，
其中 49 份为独立 PDF 内容；以下统计只用于校准信息密度，不是写作配额：

| 口径 | 最小值 | Q1 | 中位数 | Q3 | 最大值 |
|---|---:|---:|---:|---:|---:|
| PDF 总页数 | 24 | 34 | 42 | 56 | 139 |
| 历史脚本“参考文献前页数”（近似，非现行口径） | 15 | 20 | 23 | 26 | 41 |

语料页数只用于判断常见信息密度，不能转化为最低页数。紧凑稿与较长稿都要回到当前题目的推导、
结果和验证判断是否完整。因此：

- 项目构建口径使用 `appendix:start - body:start`，即正文主体首页至附录开始前一页；
  正文主体、AI 工具使用声明和参考文献均计入，摘要与附录不计入。官方硬约束是正文从第四页开始且
  不超过 30 页。
- 官方上限为 30 页；项目不另设正文页数下限，也不存在第二套“实质正文”页数或 23--27 页等
  语料软校准带。
- 表中的历史“参考文献前页数”只说明旧普查为何曾产生错误的短篇判断，不得再进入现行审计、
  图表决策或扩写决策。
- PDF 总页数与官方正文页数分开记录。总页数不设目标，附录按可复现性自然形成。
- 任何“预计有二十多页”的文字判断无效，只有实际编译后的 PDF、`.aux` 页码标签和哈希有效。
- 开写前先按问题的核心程度、推导长度、分类数量、结果解释和验证需求，为每一问确定大致页数区间，
  再把重述、分析、假设、符号、评价、声明和参考文献计入共享篇幅；规划上界必须在 30 页以内。
  该区间用于控制写作轻重，不是成稿配额；允许重点问明显更长、过渡问明显更短，也允许多项职责
  在同一节完成。

## 成文前实质准备度

页数只能在编译后精确得到，但篇幅计划与完整性必须在写第一段正文前建立。顶层
`body_page_plan` 先记录共享章节页数区间、依据和官方上限；每问的 `architecture` 再记录
`planned_page_range` 与 `page_basis`。随后逐问冻结
[A053 思路链结构锚点](a053-argument-chain.md) 的题型适配结果，再在 `architecture`、
`argument_plan` 与 `prewrite_readiness` 中共同完成：本题小节树、从定义/规律/数据到最终模型的
推导路径、逐项结果命题、结果解释任务、独立验证、风险/边界检查、最终作答映射和各命题的最适
表达载体。图、表、公式和文字按职责选择，不设数量配额。这一步建立的是完整论证体系，不是先
写出十几页后再寻找可补内容。

- 八项是责任覆盖，不是八个同形小节，也不要求八段或八组公式。同一来源可支撑相邻职责，但
  每项任务、推导位置、预期结论和验证对象必须分别可核对；不能用同一条泛化证据把八格形式填满。
- 基础八项均须 `status: ready`；搜索范围说明和活跃约束核查属于条件职责。结构上不适用时可记
  `status: not-applicable`，但必须给出本题理由；由推进链触发时不得豁免。
- `source_evidence` 只能指向题面、数据、求解、结果或独立验证等成文前已存在材料，统一使用
  `相对路径#具体锚点`。不得读取或反向引用 `论文/` 内文件为准备度自证。
- `planned_subsections` 必须存在且为列表；内容较短的问题允许为空。`argument_plan.derivation_path/`
  `result_claims/validation_plan/presentation_plan` 任一缺失，`blocking_gaps` 非空、任务只写“完成/见证据”，
  或用“写满若干页/字/图/公式”表示准备度时，一律阻断并回求解阶段补证据。

成文前执行：

```bash
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --phase prewrite
```

只有返回 `PASS_PREWRITE_READINESS` 才开始正文。该状态不代表初稿完成，也不替代最终实际页数。

## 逐问实质内容门槛

每一问都必须在 `审查/逐问深度清单.json` 中覆盖下列八项。职责可以合并在少量标题下，
但不能因没有同名标题而省略内容：

1. **题面要求对齐**：把该问的每个输出、约束、情形和精度要求拆成可核对条目，并绑定
   `claim_id`。压轴问与前问使用同一门槛，不得只留结论或占位小节。
2. **模型特有推导**：展开由本题对象、机理、几何、统计结构或决策逻辑产生的关键关系；
   标准算法原理和教材公式不能替代本题推导。按
   [建模完整性](../../cumcm/references/per-question-understanding.md#建模完整性) 核对题面条件、
   适用分支、参数可解性及原题输出恢复，推导须与实际计算一致；共享关系或短问仍保留必要连接。
3. **参数来源**：逐项说明题面给定、数据估计、标定、文献来源、合理范围或无量纲化关系；
   来源不明的数值不得进入模型。
4. **求解契约**：写清报告精度、停止条件以及边界/约束处理。解析解也须说明定义域、残差或
   代回判据，不得用“无需迭代”跳过精度检查。
5. **结果逐问解释**：不仅报数，还要写关键读数、形成原因以及它如何改变该问答案；图表不能
   独自承担解释。
6. **独立验证**：至少一种与主求解不共享同一错误机制的验证，并报告方法、独立性来源、指标、
   阈值、观测值和判定。
7. **风险响应**：至少完成灵敏度、稳健性、收敛性、约束/边界检查、不确定性或失效边界之一；
   类型由该问主要风险决定，不机械给所有题套参数扰动。
8. **最终作答映射**：题面要求逐项对应最终答案、`claim_id` 和正文/结果证据；不得只写一段笼统
   总结，也不得用“本问回答如下”等模板标签。

任一项缺失时，优先回 `cumcm-solve` 补算或补证据。不能通过改写措辞、增加背景或放大图表把
证据缺口伪装成篇幅。

每完成一问立即执行：

```bash
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --phase question --question-id qN
```

内容职责除求解侧来源证据外，还必须含 `论文/论文.tex#具体锚点`，证明该职责已经进入唯一总稿；
只在清单中写 `pass: true` 或只指向求解结果，不能得到 `PASS_QUESTION_CONTENT`。全部问题逐一通过后，
再用 `--phase content` 检查整篇逐问闭环。

八项基础职责之外，每问还必须先声明其在全文中的角色、推进链类型和一句话路线；再按题型触发
以下条件门禁：

1. **搜索范围说明**：临界、碰撞、边界优化、容量上界等依赖数值搜索的问，必须先用几何、
   单调性、上下界、对称性、必要条件或经核验的全局粗扫说明搜索域为何覆盖目标；经验区间还须
   扩大边界或给出域外反例，不能只写“在某范围内遍历”。
2. **活跃约束核查**：边界优化和容量上界问题必须指出最优点由哪些约束卡住，报告可得的余量或
   乘子，并检查邻域及域外点究竟是不可行还是目标更差；求解器 `success` 不能替代这一解释。
3. **跨问继承核查**：若本问沿用前问的状态、参数、可行域或约束，必须记录来源问、继承对象，
   并核对单位、有效数字和定义口径；没有继承时明确记为 `none`，不得用“沿用前问”含混带过。

上述内容是逐问论证链的一部分，不要求在论文中机械设置同名小节。`custom` 推进链由作者根据
实际模型显式判断两个条件门禁是否适用。

## 验证与风险响应路由

| 主要风险 | 独立验证优先项 | 风险响应优先项 |
|---|---|---|
| 机理、几何、物理 | 守恒、解析特例、独立几何/数值复算 | 极限构型、边界条件、步长/网格收敛 |
| 统计、预测 | 严格留出、时间外推、重采样或异构估计 | 残差、校准、样本扰动、分布漂移边界 |
| 优化 | 可行性复算、上下界/gap、小规模精确解 | 多起点、邻域扩大、参数/约束扰动、近优区间 |
| 逆问题 | 合成信号回收、不同观测窗口或异构估计 | 可识别性、正则强度、噪声和窗口边界 |
| 决策、仿真 | 小规模枚举、独立状态递推、蒙特卡洛误差 | 情景切换、状态边界、样本量收敛、策略稳定区间 |

同一代码只换随机种子、同一公式重复计算、求解器返回 `success` 或只展示单条收敛曲线，均不能
单独充当独立验证。

## 直接成文闭环

正式项目即使用户要求“直接生成整篇”，也必须先完成两次用户确认，再执行以下闭环。第一次确认方法与结果，
第二次确认全文目录、大纲和页数判断；第二次确认前不得落盘论文模板或开始正文。模拟项目只有在
`.cumcm_state.json` 明确标记为 `simulation` 时才可跳过这两个停点，但仍须完成同样的证据和内容门禁。

“初稿”只指第一份内容完整、页数合规且已完成表达、语义、原创性和 AI 使用披露复核的可交付稿，
不指生成链第一次产生的 PDF。超过 30 页或有真实内容缺口的产物记为 `INTERNAL_FAILED_BUILD`；
内容和页数完整的编译产物也只记为 `INTERNAL_REVIEW_CANDIDATE`，二者均 `deliverable=false`。
只有当前源码、PDF 及复核记录共同得到 `PASS_FIRST_DELIVERABLE_DRAFT` 后，系统才对外称为“初稿”。

1. 方法结果确认有效后，`cumcm-paper` 按 `../../cumcm-outline/STAGE.md` 创建逐问清单，冻结题面要求；按
   [a053-argument-chain.md](a053-argument-chain.md) 只迁移适配的功能推进，逐问填写题目化小节树、
   完整 `argument_plan`、八项职责的实质任务和求解侧来源证据。运行 `--phase prewrite`；准备度失败
   时先补算，不开写正文。把全文目录、逐节大纲和页数判断交给用户；用户确认前仍不开写正文。
2. 用户确认目录、大纲和页数无误并要求开始初稿，且 `audit_user_confirmations.py --phase draft`
   通过后，[模型成文阶段](../../cumcm-model-writing/STAGE.md) 填写模型特有推导、参数来源和求解契约；
   `cumcm-results-validation` 填写结果解释、独立验证、风险响应和最终作答映射。每完成一问即运行
   `--phase question --question-id qN`，补齐未进入唯一总稿的职责后再写下一问。
3. 全部问题通过单问门禁后，运行整篇内容阶段审计：

   ```bash
   python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --phase content
   ```

4. 完成评价、AI 工具使用声明、参考文献、附录和定稿摘要，并在公式稳定后完成全文公式可读性审计。
   这些内容尚未完成时，增量编译只用于排错，不据此放行完整初稿。
5. 用受控编译入口完成两遍真实编译，生成 `审查/编译绑定.json`，绑定当前源码、实际读取的图片/类文件等
   依赖、PDF 和 AUX；不能手填哈希给旧 PDF 补签。读取 `appendix:start - body:start` 和 PDF 总页数，
   用 `--record-compile` 把本轮
   官方正文页数与 SHA-256 写回清单；若内容审查发现真实缺口，可同时记录缺失项和实质动作：

   ```bash
   python .agents/skills/cumcm-paper/scripts/compile_paper.py --root .
   python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --record-compile --missing-depth-item "q2: 参数来源尚未闭合" --action "补充标定区间、误差传播及其对最终方案的影响"
   ```

6. 以上构建是内部待审候选，不需要先获得“初稿 PASS”才能做去 AI 或语言审查。先冻结未改写基线，
   执行 `cumcm-deai` 的真实性和声纹审计，逐段核对来源、条件及结论强度，完成语言扫描和复核；
   语言修订改变正文后重新编译、刷新页数与哈希，再在同一版 PDF 上运行全库原创性审计。按下节补齐
   现有 deai/language 阶段记录，检查 AI 声明与实际使用详情。随后运行阶段转换门禁：

   ```bash
   python .agents/skills/cumcm-paper/scripts/check_first_draft_gate.py --root .
   ```

   任何非 `PASS_FIRST_DELIVERABLE_DRAFT` 状态都不得宣称初稿完成或交给最终独立评奖审查；
   可在已确认范围内继续内部成文、去 AI、语义及语言复核。若修复改变主方法、最终结果、目录或
   页数计划，则停止并退回相应确认点。不为了把审查字段填成 PASS 而编造具名复核或参赛队确认。
7. 内容缺口按记录回到
   对应子技能补算、完成缺失推导、解释、验证或边界，再重新编译和记录；不得在事后新增页数职责、
   凑字、凑图或拆公式。最新一轮页数、PDF 哈希与清单不一致时，最终审计必须失败。
8. 首份初稿交付后才进入独立最终审查与官方提交验收；初稿 PASS 不等于国奖竞争力已获证明，
   也不等于参赛队已经人工核验全部 AI 参与内容。任何正文改动后必须重新编译、刷新哈希并复跑受影响
   门禁。页数只判断是否超出上限，不作为评分或“越多越好”的依据。

每轮都以实际 PDF 为准。修改模型、结果、图表或排版后，旧页数反馈立即失效，必须重新编译记录。

## 结构化清单

清单使用 `schema_version: 1`，顶层至少包含：

```json
{
  "schema_version": 1,
  "question_ids": ["q1"],
  "body_page_plan": {
    "official_body_max": 30,
    "shared_sections_page_range": [4, 6],
    "basis": "前置章节、评价、AI 声明与参考文献的合计估计"
  },
  "questions": {
    "q1": {
      "architecture": {
        "planned_page_range": [4, 6],
        "page_basis": "本问含关键几何推导、参数搜索和独立复核",
        "planned_subsections": ["几何边界", "目标函数", "参数搜索"]
      },
      "argument_plan": {
        "structure_anchor": "A053-structure-only",
        "adaptation_basis": "本问只迁移边界优化的功能推进，不复用原模型",
        "derivation_path": [],
        "result_claims": [],
        "validation_plan": {},
        "presentation_plan": []
      },
      "prewrite_readiness": {
        "status": "ready",
        "blocking_gaps": [],
        "responsibilities": {
          "model_specific_derivation": {
            "status": "ready",
            "substantive_task": "由本题几何关系推出临界约束",
            "source_evidence": ["求解/问题一/结果/metrics.json#critical_constraint"]
          }
        },
        "conditional_responsibilities": {
          "active_constraint_check": {
            "status": "not-applicable",
            "reason": "本问不求边界最优或容量上界"
          }
        }
      }
    }
  },
  "compile_feedback": {
    "iterations": []
  }
}
```

顶层必须含 `body_page_plan`；其共享章节页数区间与所有分问计划页数区间相加后的上界不得超过
`official_body_max`。每问对象必须含 `architecture`、`argument_plan`、`search_scope_justification`、`active_constraint_check`、
`prewrite_readiness`、`requirements`、`model_specific_derivation`、`parameter_sources`、
`solver_contract`、`result_interpretation`、`independent_validation`、
`stress_or_failure_boundary` 和 `final_answer_mapping`。各职责对象写 `pass: true`、具体字段及
`evidence`；证据统一写成 `相对路径#具体锚点`，例如
`论文/论文.tex#式(12)` 或 `求解/问题一/结果/metrics.json#validation.relative_error`。
只写“已检查”“见正文”或不存在的文件路径不得通过。

`architecture.role` 取 `core/support/transition`；`chain_type` 可取基础机理、临界可行、边界优化、
复合分段、容量上界、实验推断、序贯决策、空间布设、不确定性反馈或 `custom` 对应的英文枚举值。
`progression_axis` 取 `foundation/mechanism-regime/information-state/actor-count/spatial-fidelity/`
`parameter-uncertainty/independent`，用于说明本问相对前问为何需要升级或为何独立。
`architecture.planned_page_range` 与 `page_basis` 在开写前确定该问的大致篇幅和依据，实际成稿可随
论证需要浮动，不按该区间作逐问硬验收。`architecture.planned_subsections` 记录实际需要的简短小标题，
允许空列表，不承担论证职责清单；`argument_plan` 固定
`structure_anchor: A053-structure-only`，并填写当前题适配理由、推导路径、逐项结果命题、验证/边界
计划和表达载体。载体可为 `prose/formula/table/figure/diagram`；同一命题允许多幅互补图，不要求有图。
`inheritance.status` 取 `none/used`。后两个门禁均以 `applicable` 控制；一旦为 `true`，其结论字段
和证据定位必须完整。

上例只展示字段形状；正式清单的 `responsibilities` 必须列全八项。八项可复用同一来源证据，不按
职责生成八个标题。完成态组件及最终作答映射还须含 `论文/论文.tex#具体锚点`；准备度中的
`source_evidence` 则不得指向 `论文/`。

可先由脚本生成待填骨架：

```bash
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --init --question-id q1 --question-id q2
```

若章节链清单已有 `question_ids`，可省略 `--question-id`。初始化不覆盖已有深度清单。

## 编译后的回退职责

页数较短不自动触发补写；只有逐问清单发现真实内容缺口时，才回到写前已冻结但尚未兑现的论证项。
补入后必须重新运行模型或验证并更新证据：

1. 题目特有的定义、关键推导、近似依据和边界条件；
2. 参数来源、标定过程、取值范围和误差传播；
3. 离散、初始化、停止条件、约束修复与报告精度；
4. 结果的关键读数、机制解释、决策含义和跨问衔接；
5. 独立复算、收敛、外样本、可行性、上下界或不确定性证据；
6. 灵敏度、稳健区间或模型失效边界；
7. 题面要求到最终答案的遗漏映射；
8. 附录中缺失的完整代码、环境和补充表图；附录不计入官方正文页数。

禁止补写：重复题面、背景常识、教材式算法介绍、未运行的候选模型、空泛评价、重复图表、
强制换页、放大字号/行距/边距、装饰图以及把附录材料搬进正文。

## 放行判定

- `≤30` 页：页数状态记为 `PASS_OFFICIAL_BODY_LIMIT`；只有逐问完整论证和全部阶段同时通过，才进一步
  进入 `INTERNAL_REVIEW_CANDIDATE`，并在首次交付前质量复核通过后签发 `PASS_FIRST_DELIVERABLE_DRAFT`。
  页数较短不自动失败，页数高低本身也不加分。
- `>30` 页或超过当年更低官方上限：只允许 `INTERNAL_FAILED_BUILD`、`deliverable=false`，优先压缩
  重复职责，不删除关键证据。

最终报告为 `审查/正文深度审计.json`。其中同时记录 `body_pages`、`body_start_page`、
`appendix_start_page`、`total_pdf_pages`、`page_status`、PDF SHA-256 和逐问深度清单 SHA-256；
不得用总页数替代官方正文页数。报告、清单或 PDF 任一变化后都必须重新运行最终审计。

## 源稿与编译产物的对应关系

内部候选与改稿重编译统一使用：

```bash
python .agents/skills/cumcm-paper/scripts/compile_paper.py --root .
python .agents/skills/cumcm-paper/scripts/audit_question_depth.py --root . --record-compile
```

`compile_paper.py` 实际执行两遍带 recorder 的 XeLaTeX，只在成功且两遍间输入稳定时写
`审查/编译绑定.json`，绑定单一源稿、`.fls` 记录的源/图片/数据等依赖、PDF 和 AUX。
外部素材和 TeX 环境文件同样绑定哈希，不能把项目外路径一律当成可忽略的系统依赖。
编译失败撤销旧绑定，保留旧 PDF 供诊断，但旧 PDF 不可作为本次新稿放行。

`measure_compilation` 核对绑定后才返回 `tex_sha256`、`compilation_binding_verified:true` 与
`compile_manifest:{path,sha256}`。源稿、依赖、PDF 或 AUX 改变时必须真实重编译；不能把新源稿的
语义报告和旧 PDF 的原创性报告拼在一起。绑定不评价内容和页数；超页构建仍可测量并记录为
`INTERNAL_FAILED_BUILD`，避免检查与编译互相等待。

## 首次交付前的质量复核记录

`check_first_draft_gate.py` 输出 schema v2；只消费现有 `审查/section-chain/gates/deai.json`、
`gates/language-audit.json` 和自动报告，不额外建立第三个用户确认停点。记录中的 `pass`、具名审核、
逐段阅读、语义判断和信号处置由实际完成检查的审核者填写，脚本不得自动设置。

两个阶段 gate 均增加当前总稿原始字节的 `tex_sha256`、当前 `论文/论文.pdf` 的 `pdf_sha256`；
`status=pass` 且 `blocking_issues=[]`。JSON 报告通过 `audit_reports` 引用，每项为
`{"path":"项目内相对路径","sha256":"该报告原始字节 SHA-256"}`：

- deai：`authentic_expression` 指向 `审查/section-chain/authentic-expression-audit.json`，
  `corpus_voice` 指向 `审查/section-chain/corpus-voice-audit.json`；另含 `baseline:{path,sha256}`，
  指向独立保存的改写前总稿，以及 `evidence_matrix_sha256` 绑定当前 `求解/证据矩阵.csv`。
- language-audit：`language_scan` 指向 `审查/section-chain/language-audit.json`。
- 真实性报告必须含当前 `paper_sha256` 和 `integrity.baseline_sha256`。这两个字段沿用生产脚本的
  UTF-8 解码及换行归一化哈希算法；gate 的文件引用与其余哈希使用原始字节。缺基线、`NOT_RUN` 或
  `FAIL` 不放行；完整性 `REVIEW` 还须填写 `deduplication_review`，逐条保留被删位置、保留位置、
  未损失的结论和理由，不能靠退出码 0 代替。
- 声纹及语言自动报告自身必须含 `paper_source:{path:"论文/论文.tex",sha256:"原始字节哈希"}`，
  扫到总稿且没有硬失败。仅修改 stage gate 的哈希，不能把旧扫描记录重新认定为本轮有效。

deai 的 `semantic_fact_review`、`expression_review`，以及 language-audit 的 `manual_review`
使用同一复核记录结构。以下是待完成字段示意，不是可以直接复制的通过记录：

```json
{
  "pass": false,
  "reviewer": "",
  "reviewer_type": "ai",
  "reviewed_at": "",
  "scope": "",
  "full_text_read": false,
  "unresolved_issues": ["待逐段复核"],
  "evidence": [],
  "evidence_sha256": {},
  "signal_resolutions": []
}
```

`reviewer_type` 只取 `ai/participant`，如实区分 AI 内部阅读与参赛队员人工核验。
`evidence` 使用真实 `文件#具体锚点`；`evidence_sha256` 以这些文件的项目相对路径为键，保留审核当时
的原始字节 SHA-256。来源材料即使没有被 TeX 直接读取，只要改变就要重新审阅；不能重跑首稿门禁时
自动用新来源哈希沿用旧语义 PASS。语义记录另要求 `evidence_matrix_checked` 和
`sources_conditions_claim_strength_checked` 均经实际核对。每条自动信号须对应一项
`signal_resolutions:{signal,disposition,reason}`；`disposition` 取
`retained/rewritten/moved/verified`，理由解释本题技术职责，不能只写“已检查”。信号定位格式为：

- `authentic_expression:semantic_review.changes[0]`（交给语义复核）；
- `authentic_expression:expression_review.findings[0]`、`corpus_voice:records[0].soft[0]`（交给表达复核）；
- `language_scan:records[0].soft[0]`（交给语言复核）。

完整性去重复核同样记录审核者，并在 `retained_claims` 列表逐项写
`signal/removed_count/removed_location/retained_location/claim/reason`；`signal` 形如
`authentic_expression:integrity.categories.numbers.removed[0]`，`removed_count` 与该项报告的
`count` 一致。所有删除信号都须覆盖，不能只解释其中一个数字；缺少删除明细的 `REVIEW` 报告不放行。
自动信号只定位风险；没有信号仍要阅读来源、
条件和结论强度，既不删除必要验证，也不制造试错经历或用同义替换伪装原创。

原创性使用 `审查/优秀论文对标.json` schema v2：候选 PDF 双重哈希与当前稿一致，
`similarity.coverage` 必须全库、正文/全文比较完整、实际比较数量等于可比库数量且非零；
`originality_gate.verdict` 为 `PASS` 或有有效逐段复核的 `PASS_WITH_MANUAL_REVIEW`。
同时复用原创性生产脚本的 `originality_report_issues` 校验 `audit_basis_sha256`；候选、语料、
提取/覆盖或重合证据改变后，不能沿用旧的逐段原创性复核。
`corpus_source` 必须记录实际语料目录、发现范围和每个成员文件的哈希，并与逐篇比较记录一致；
最终检查会重新枚举目录，语料增删或修改后须重跑。人工解释放行还须以 `manual_review_file:{path,sha256}`
绑定真实复核 JSON；该文件撤回、删除、改变或与报告内嵌记录不一致时，旧 PASS 立即失效。
`NOT_RUN`、语料为空、摘要单独通过、提取不完整或旧稿报告均阻断，不能承诺商业查重率或 AIGC 比例。

language-audit 的 `ai_usage` 对本生成流程固定如实填写 `used:true`，并实际检查
`disclosure_checked`、`details_checked`；`details:{path,sha256}` 绑定
`附件/.../AI工具使用详情.pdf`。详情可以是待参赛队最终核验的初稿，但用途、采纳和人工修改情况必须
真实，不得把尚未完成的人工检查写成完成。论文不能使用“未使用 AI”声明。
`participant_verification` 在首次交付前记 `pending`；明确 simulation 项目可记
`not_applicable_simulation`。AI 内部复核允许支撑首稿交付，不能替代已有方法结果确认、队员逐项
核验或最终提交批准；这些状态不由本门禁签发。最终审查仍按正式项目要求执行。

首次门禁记录全部输入文件哈希到 `assurance.input_sha256`；总稿、PDF、基线、证据矩阵、自动报告、
复核记录或 AI 详情改变后须刷新对应检查和首稿门禁。预编译章节检查用
`audit_section_chain.py --phase content`，不依赖尚未产生的首稿；最终章节检查默认 `--phase final`，
核验全部阶段及本轮首稿质量复核，并实际重新验证编译依赖和当前页数政策，避免“先通过初稿才能审初稿”
的循环。编译记录及全部阶段输入绑定还见首次门禁顶层 `input_sha256` 与 `compile_manifest`。
