# LaTeX 模板与排版规范

## 官方硬约束

以 [official-rules.md](official-rules.md) 和当年官网为准：

- A4，页边距至少 2.5 cm；
- 电子版第一页为摘要专用页；
- 摘要原则上不超过一页；
- 正文不要目录；项目构建口径计算的正文区包含正文主体、AI 工具使用声明和参考文献，不含摘要与附录，
  必须不超过 30 页或当年更低的官方页数上限；官方格式要求正文从第四页开始；
- 从附录首页起不设页数上限，只检查文件大小、完整性和可读性；
- 摘要、正文、附录和支撑材料不得出现身份信息；
- 论文与支撑材料满足当年文件格式和大小限制；
- 附录列支撑材料并包含全部建模源程序。

不要把经验性字数、总页数或图表数量写成官方规则；图表数量由待证明命题、不可替代证据职责和正文解读决定。

## 单一总稿

复制 assets/latex-template/论文.tex 为 论文/论文.tex。所有章节正文、参考文献和纸面附录都直接
写入这个总稿；章节子技能只能更新总稿中的对应 section，不得创建独立章节 TeX，也不得使用
\input、\include 或 subfiles 拼装正文。format.cls、字体、图片和附件仍可作为外部资产。

```latex
\PassOptionsToPackage{quiet}{xeCJK}
\documentclass[withoutpreface,bwprint]{format}
\usepackage{ctex}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{siunitx}
\usepackage{url}

\newcolumntype{C}{>{\centering\arraybackslash}X}
\newcolumntype{L}{>{\raggedright\arraybackslash}X}
\newcolumntype{R}{>{\raggedleft\arraybackslash}X}

\title{论文标题}

\begin{document}
\maketitle
\begin{abstract}
% 先写统一对象与总体主线；每问用 abstractquestion 环境形成稳定段距。
\begin{abstractquestion}{一}
我们采用\keymethod{核心方法}完成……，得到\keyresult{核心结果}，并由……验证。
\end{abstractquestion}
\keywords{关键词一\quad 关键词二\quad 关键词三}
\label{abstract:end}
\end{abstract}

% 官方规范：不要目录。
\label{body:start}
\section{问题重述}
% 本节正文直接写入总稿。
\section{问题分析}
\section{模型假设}
\section{符号说明}
\section{模型的建立与求解}
% 问题层默认使用“问题一”“问题二”；每问按需要设置 0--3 个简短三级标题。
% 每问把推导、求解、结果解释、独立验证/边界和直接作答形成闭环，不机械拆成同名小节。
% 只有题目确实需要跨问检验且存在两类以上实质内容时，在此增加紧凑的结果检验一级章。
\section{模型评价、改进与推广}
\label{ai-statement:start}
\section*{AI工具使用声明}
% 二选一原文：
% 本参赛队在竞赛过程中未使用任何AI工具。
% 本参赛队在竞赛过程中使用了AI工具，主要用于〖简要用途，如语言润色、代码调试等〗，详细使用情况见支撑材料。
\label{references:start}
\begin{thebibliography}{99}
% 参考文献直接写入总稿。
\end{thebibliography}
\clearpage
\label{appendix:start}
\appendix
\renewcommand{\thesection}{附录\arabic{section}}
\renewcommand{\thesubsection}{附录\arabic{section}.\arabic{subsection}}
\section{支撑材料清单}
\section{完整程序代码}
\section{补充材料}
\end{document}
```

论文/ 顶层只允许一个 `论文.tex`；不得保留 `0.摘要.tex`、`1.问题重述.tex` 等章节文件。
保留 `\label{body:start}`、`\label{ai-statement:start}`、`\label{references:start}` 与
`\label{appendix:start}`。AI 声明位于参考文献之前，二者不强制另起一页；自动审计以
`appendix:start - body:start` 计算项目正文区页数，并与官方“正文不超过 30 页”硬约束对照。

模板的 12pt 宋体正文、14pt 黑体一级标题、18pt 基线、五号图表题注和 Cambria Math 属于版式选择，
不是组委会强制格式。2026 规范明确规定字号、字体、行距、颜色不统一要求；若赛区另有要求，
在保持 A4、四边至少 2.5cm、摘要一页、正文无目录且不超过 30 页等全国硬约束的前提下覆盖这些默认值。

各问题章节连续排版。不得在问题一、问题二或其他分问章节的开头、结尾设置 `\newpage`、
`\clearpage` 或仅为截断章节而添加的 `\FloatBarrier`。若页尾剩余空间足以容纳一级标题及
至少两行正文，下一问应直接接排。摘要环境结束和附录开始允许固定换页；AI 声明与参考文献
不因章名强制换页。
确需阻止单张图跨越问题边界时，优先调整该图的浮动位置或使用 `[H]`，不得用分问题强制
换页掩盖浮动体布局。

摘要中的每问统一使用 `abstractquestion` 环境控制段前段后距。核心方法使用
`\keymethod{...}`，最终结果使用 `\keyresult{...}`，正文直接结论使用
`\keyconclusion{...}`；关键词整行采用黑体，标签与关键词内容均加粗。禁止用整段
`\textbf`、连续空行或手工 `\vspace` 复制视觉效果。

## 标题层级与符号章

- 一级标题显示为中文序数，二级、三级标题分别使用两段和三段编号；
- 编号标题不超过三级；`\paragraph{...}` 只能作为不编号的段内引导语；
- 一级标题承担论证阶段；第五章的问题层二级标题可直接使用“问题一”“问题二”。三级标题只需
  展示一个中心，优先使用简洁的学科表达，不强制同时写出对象、变量和方法；
- 符号说明设置为独立一级章，严格使用“符号｜含义｜单位”三列；“含义”按内容写物理含义或数学含义；
- 标题后默认直接放符号表；必要文字只说明共同约定或适用范围，保持一至两句且不作评价；
- 单位列不得留空，无单位项统一写“—”，不写“无量纲”；
- 默认第五个一级标题为“模型的建立与求解”；已确认分问或模块结构时按其组织推导和求解，不要求机械归入一个总章。

第五章不采用固定的“模型建立—算法求解—结果分析—模型检验”四连标题。
按 [逐问题意理解与建模入口](../../cumcm/references/per-question-understanding.md)，每问标题后
先写一段概述，说明任务、决定性关系和求解主线，再进入下级小节或公式。每问按需要设置 0--3 个
简短三级标题，并在正文中完成结果解释、独立验证、
风险边界和直接作答。核心问完整展开，支撑问和过渡问按实际贡献压缩，不平均分配篇幅。

符号表示例：

```latex
\section{符号说明}

\begin{table}[htbp]
  \centering
  \caption{主要符号及其含义}
  \label{tab:symbols}
  \begin{tabularx}{\textwidth}{C L C}
    \toprule
    \textbf{符号} & \textbf{含义} & \textbf{单位} \\
    \midrule
    $t$ & 任务开始后的时刻 & \si{\second} \\
    $\eta$ & 方案综合评价指标 & — \\
    \bottomrule
  \end{tabularx}
\end{table}
```

唯一正文模板资产为：

```text
.agents/skills/cumcm-paper/assets/latex-template/论文.tex
```

逐问结果后必须能定位必要的复算、对照、扰动或边界检验。只有题目确实需要跨问检验，且存在两类以上实质内容时，
设置独立一级章“结果检验”或信息等价的标题；否则合并到对应问题。算术核对、口径统一、证据边界和模型链总结留在审查文件。
不得只用一句“结果合理”代替检验，也不得为保留章名伪造实验。

## 表格选择

- 单页短表：`table` + `tabularx`；
- 需要跨页的结果表：`longtable`；
- 宽表优先重排字段、拆成有逻辑的两表或移入附录，不缩小到不可读；
- 数值列统一小数位并按小数点对齐，单位写在表头；
- `\caption` 在 `\label` 前，正文必须引用并解释表格。

短表示例：

```latex
\begin{table}[htbp]
  \centering
  \caption{模型验证结果}
  \label{tab:validation}
  \begin{tabularx}{\textwidth}{LCCC}
    \toprule
    方法 & 指标 & 结果 & 判定 \\
    \midrule
    步长收敛 & 相对误差（\%） & 0.42 & 通过 \\
    \bottomrule
  \end{tabularx}
\end{table}
```

跨页表示例：

```latex
\begin{longtable}{p{0.18\textwidth}p{0.24\textwidth}p{0.46\textwidth}}
  \caption{完整结果表}\label{tab:full-results}\\
  \toprule
  编号 & 指标 & 结果 \\
  \midrule
  \endfirsthead
  \caption[]{完整结果表（续）}\\
  \toprule
  编号 & 指标 & 结果 \\
  \midrule
  \endhead
  \bottomrule
  \endfoot
  1 & 示例 & 示例结果 \\
\end{longtable}
```

## 图片与公式

- 图片路径相对 `论文/`，优先引用求解阶段生成的 PDF/SVG/PNG；
- 统一图宽和字体尺度，避免在 LaTeX 中拉伸变形；
- 行内公式不编号，所有独立展示公式必须编号；禁止 `\[...\]` 和 `equation*` 等无编号环境；
- 引出展示公式的最后一句以中文冒号“：”结束；
- 同组并列坐标、约束、状态方程或分段条件用
  `\left\{\begin{aligned}...\end{aligned}\right.` 排列并共用一个编号；
- 段内 `\paragraph{...}` 或列表项加粗短语承担引导作用时，以中文冒号结束；
- 公式主体末尾不保留句号、逗号、分号或中文标点，编号后不追加标点；
- 多行公式使用 `aligned`、`split` 或 `multline`，不得越过正文边界；
- 符号首次出现即定义，单位和有效数字保持一致。

推荐写法：

```latex
由运动学关系可得：
\begin{equation}
  \bm x(t)=\bm x_0+\bm v t
  \label{eq:motion}
\end{equation}
```

正文引用写作“由式 \eqref{eq:motion} 可得”。不要在 `\end{equation}` 前后添加标点。

## 编译与检查

先创建 `论文/论文.tex`、写入摘要并编译；之后每完成 1--2 个 section，仍在同一总稿中保存并
编译一次，不把整篇长稿留到最后一次性落盘，也不把 section 拆成独立 TeX。

```bash
python .agents/skills/cumcm-paper/scripts/audit_single_tex_delivery.py --root . --phase source
```

```bash
xelatex -interaction=nonstopmode 论文.tex
xelatex -interaction=nonstopmode 论文.tex
```

- 摘要末尾必须保留 `\label{abstract:end}`；从 `.aux` 检查其所在页，确保摘要不超过一页；
- `\label{body:start}` 与 `\label{appendix:start}` 必须进入 `.aux`，且 `appendix:start` 晚于
  `body:start`；`ai-statement:start` 必须早于 `references:start`；
- 检查 unresolved reference/citation、Overfull、Float too large 和缺字警告；
- 逐页渲染 PDF，检查空白、重叠、截断、低清图、断裂表头和页码；
- 不通过缩小页边距、字号或行距规避官方页数限制。
