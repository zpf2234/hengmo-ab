#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoGebra TikZ Sanitizer (sanitize_ggb_tikz.py)
---------------------------------------------
专门针对 GeoGebra (GGB) 导出的 TikZ / PGF 代码进行清洗与提纯的脚本。
灵感来自 GeoTikTrim (ggb-tikz-code-filter)，优化要点：
1. 坐标精度裁剪：将 15+ 位浮点数四舍五入至 2~3 位有效小数，减小文件体积并加快编译；
2. 裁剪与宏清理：自动剥离无用外围 \clip rectangle 与 GGB 临时色彩定义 (\definecolor{ududff} 等)；
3. 样式映射：把 GGB 随机自定义颜色替换为 CUMCM 论文标准语义色彩 (黑/灰/冷蓝主路径)；
4. 作用域解耦：清理 \begin{scriptsize} 等非必要排版容器，方便后续接入 paper-tikz MCP。

使用示例：
    python sanitize_ggb_tikz.py --input raw_ggb.tex --output clean_ggb.tex --decimals 3
"""

import argparse
import re
import sys
from pathlib import Path


def round_float_match(match, decimals=3):
    """把正则匹配到的长浮点数舍入为指定小数位数"""
    val_str = match.group(0)
    try:
        val = float(val_str)
        # 如果舍入后是整数形式且无必要保留 .0，可适当格式化
        rounded = f"{val:.{decimals}f}".rstrip('0').rstrip('.') if '.' in f"{val:.{decimals}f}" else f"{int(val)}"
        return rounded
    except ValueError:
        return val_str


def sanitize_ggb_tikz(content: str, decimals: int = 3, remove_clip: bool = True,
                      map_colors: bool = True, strip_scriptsize: bool = True) -> str:
    lines = content.splitlines()
    cleaned_lines = []
    
    stats = {
        "rounded_floats": 0,
        "removed_clips": 0,
        "removed_colors": 0,
        "mapped_styles": 0,
        "removed_scopes": 0
    }

    # 正则规则
    # 1. 匹配 4 位及以上小数点的数字（包括负号）
    float_pattern = re.compile(r'-?\d+\.\d{4,}')
    
    # 2. 匹配 GGB 自动生成的颜色定义 \definecolor{ududff}{rgb}{...}
    color_def_pattern = re.compile(r'^\s*\\definecolor\{[a-zA-Z0-9_]+\}\{(?:rgb|cmyk|HTML)\}\{.*?\}\s*$')
    
    # 3. 匹配 \clip(...) rectangle (...);
    clip_pattern = re.compile(r'^\s*\\clip\s*\([^\)]+\)\s*rectangle\s*\([^\)]+\)\s*;\s*$')

    # 4. 常见 GGB 颜色替换映射
    color_map = {
        "uuuuuu": "black!75",
        "ududff": "blue!70!black",
        "xdxdff": "black!85",
        "ffqqqq": "red!70!black",
        "zzttqq": "gray!60",
        "qqqqff": "blue!80!black"
    }

    for line in lines:
        stripped = line.strip()

        # 处理 \definecolor
        if map_colors and color_def_pattern.match(stripped):
            stats["removed_colors"] += 1
            continue

        # 处理 \clip rectangle
        if remove_clip and clip_pattern.match(stripped):
            stats["removed_clips"] += 1
            continue

        # 处理 \begin{scriptsize} 和 \end{scriptsize}
        if strip_scriptsize and stripped in (r"\begin{scriptsize}", r"\end{scriptsize}"):
            stats["removed_scopes"] += 1
            continue

        # 样式颜色映射
        if map_colors:
            for ggb_col, cumcm_col in color_map.items():
                if ggb_col in line:
                    line = line.replace(ggb_col, cumcm_col)
                    stats["mapped_styles"] += 1

        # 浮点数保留小数位数
        matches = float_pattern.findall(line)
        if matches:
            stats["rounded_floats"] += len(matches)
            line = float_pattern.sub(lambda m: round_float_match(m, decimals), line)

        cleaned_lines.append(line)

    clean_content = "\n".join(cleaned_lines)
    return clean_content, stats


def main():
    parser = argparse.ArgumentParser(description="Sanitize and clean GeoGebra exported TikZ code for CUMCM.")
    parser.add_argument("-i", "--input", help="Path to input TikZ/TeX file (reads stdin if omitted)", default=None)
    parser.add_argument("-o", "--output", help="Path to output TikZ/TeX file (prints to stdout if omitted)", default=None)
    parser.add_argument("-d", "--decimals", type=int, default=3, help="Number of decimal places to retain (default: 3)")
    parser.add_argument("--keep-clip", action="store_true", help="Do not remove \\clip rectangle lines")
    parser.add_argument("--no-color-map", action="store_true", help="Do not map or remove GGB color definitions")
    parser.add_argument("--keep-scriptsize", action="store_true", help="Do not strip scriptsize environments")

    args = parser.parse_args()

    if args.input:
        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[Error] Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        content = in_path.read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    cleaned, stats = sanitize_ggb_tikz(
        content=content,
        decimals=args.decimals,
        remove_clip=not args.keep_clip,
        map_colors=not args.no_color_map,
        strip_scriptsize=not args.keep_scriptsize
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(cleaned, encoding="utf-8")
        print(f"[Success] Cleaned TikZ written to {args.output}", file=sys.stderr)
        print(f"[Stats] {stats}", file=sys.stderr)
    else:
        print(cleaned)


if __name__ == "__main__":
    main()
