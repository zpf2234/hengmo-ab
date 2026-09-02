# 高教杯优秀论文 Python/TikZ/Visio 绘图控制

两个绘图 MCP、一个 Python 数据图后端和一个语义路由 MCP（stdio）：

- `figure_router_server.py`：判断是否需要插图、图型、绘图后端、正文落点与证据要求。
- `python_figure.py`：数据曲线、轨迹、热力图、三维曲面与仿真结果的主渲染模块（非 MCP）；输出 `.py/.json/.pdf/.svg/.png` 契约。
- `tikz_server.py`：精确二维几何、角度、尺寸、公式关系；输出 `.tex/.json/.pdf/.svg`。
- `visio_server.py`：流程图、问题关系、技术路线、模型结构；输出可编辑 `.vsdx` 以及 `.pdf/.svg/.png/.json`。

## 运行环境

- Python 3.10 及以上，并安装仓库根目录 `requirements.txt` 中的依赖；
- XeLaTeX 与 dvisvgm：建议加入系统 `PATH`；
- Visio：仅 `visio_server.py` 需要，未安装时仍可使用 Python 与 TikZ 路线；
- MATLAB：只用于保留的兼容路线，主数据图不依赖 MATLAB。

如果渲染器没有加入 `PATH`，可分别设置 `HENGMO_XELATEX_EXE`、`HENGMO_DVISVGM_EXE`、
`HENGMO_VISIO_EXE` 或 `HENGMO_MATLAB_EXE` 指向本机可执行文件。

## 设计原则

1. 不做鼠标键盘屏幕模拟；Python 数据图直接运行脚本，TikZ 走编译器，Visio 走 COM。
2. 所有图优先交付可编辑源文件和 PDF/SVG 矢量结果；数据图的可编辑源就是生成它的 Python 脚本与结构化数据。
3. 统一白底、微软雅黑、克制蓝橙配色、论文版心宽度和线宽（由 `python_figure.apply_style` 固化）。
4. 数值点只从结构化数据生成，不在 Visio 中手工挪动。
5. 复杂混合图：Python/TikZ 生成矢量主体面板，Visio 只负责关系组织与版面合成。
6. 流程图采用信息增益门禁：只有非平凡关系确实难以由短文、公式或表格清楚表达时才路由；三步线性过程、单个判断和“国一模式”都不自动触发。
7. 物理尺寸即契约：`python_figure.save_figure` 不使用 `bbox_inches="tight"`，画布尺寸不被内容重排；特色图审计同时核对目标宽度、目标高度和纵横比，三项误差上限均为 0.2%。

## A/B 特色主视觉 benchmark

`benchmarks/signature_specs/` 提供跨赛题、非 2024B 专用的三类结构化规格：

- `a_mechanism_result.json`：A 类机理—临界事件—误差闭合；
- `b_strategy_landscape.json`：B 类策略区域—价值等高线—推荐点；
- `uncertainty_decision_linkage.json`：A/B 通用不确定性收缩—阈值穿越—策略切换。

运行 `python signature_benchmarks.py` 会先检查核心命题、十秒结论、语义阅读链和数据联动，再用
matplotlib 真实渲染 `.json/.pdf/.svg/.png` 并做矢量、最终宽高与纵横比审计。`pytest -q test_signature_benchmarks.py`
包含仅换配色、装饰性拼图和缺科学证据的负回归；这些情况即使视觉风格完整也不能通过。

## Codex 配置

Windows 原生命令使用 `codex mcp add` 加入；配置名称固定为：

- `paper-tikz`
- `paper-visio`
- `paper-figure-router`

接入后用 `codex mcp list` 核对，并逐一真实调用 health tool；配置名称存在不等于后端可用。
