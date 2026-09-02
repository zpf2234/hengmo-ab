#!/usr/bin/env python3
"""Audit whether displayed formulas can be read without decoding the notation table.

The audit deliberately avoids a fixed quota for symbols, rows, or formula length.
It finds structural risks, then requires each remaining risk to have an explicit
retention decision.  Editing a formula, splitting it, or adding explanations should
make the risk disappear on the next run; only genuinely necessary structures belong
in the retention ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


DISPLAY_RE = re.compile(
    r"\\begin\{(?P<env>(?:equation|align|gather|multline)\*?)\}"
    r"(?P<body>.*?)"
    r"\\end\{(?P=env)\}",
    flags=re.DOTALL,
)
INLINE_MATH_RE = re.compile(
    r"(?<!\\)\$(?!\$)(?P<dollar>.*?)(?<!\\)\$|"
    r"\\\((?P<paren>.*?)\\\)",
    flags=re.DOTALL,
)
HEADING_RE = re.compile(r"\\(?:section|subsection|subsubsection)\*?\{[^}]*\}")
LEAD_SIGNAL_RE = re.compile(
    r"为(?:求|计算|确定|刻画|描述|比较|检验|构造|建立|推导|估计|辨识|约束|得到)|"
    r"根据|依据|结合|考虑|针对|设|令|定义|代入|联立|整理|化简|消去|展开|"
    r"求导|积分|取极限|变换|写成|满足|建立|给出|可得|得到"
)
GENERIC_LEAD_RE = re.compile(
    r"(?:建立|给出)(?:如下|以下)(?:模型|公式)|"
    r"由(?:以下|上述)公式可得|(?:模型|公式)如下"
)
FOLLOW_SIGNAL_RE = re.compile(
    r"其中|式中|这里|表示|对应|说明|表明|意味着|反映|决定|约束|取值|单位|"
    r"因此|于是|由此|代入|整理|联立|消去|下一步|可得|得到"
)
SYMBOL_TABLE_ONLY_RE = re.compile(
    r"(?:式中|其中).{0,10}(?:符号|变量).{0,8}(?:见|参见|查阅|参考).{0,4}(?:表|符号说明)"
)
SYSTEM_CUE_RE = re.compile(r"方程组|约束组|系统|联立|同时满足|分段|各情形|各状态")
RELATION_RE = re.compile(r"(?<![<>])(?:&?=|\\leq?|\\geq?|\\approx|\\sim|<|>)")
DEFINITION_RE = re.compile(r":=|\\coloneqq|\\triangleq|\\equiv")
OPTIMIZATION_RE = re.compile(r"\\(?:argmin|argmax|min|max)(?![A-Za-z])")
AGGREGATE_RE = re.compile(r"\\(?:sum|prod|int|iint|iiint)(?![A-Za-z])")
ORNATE_RE = re.compile(r"\\(?:mathscr|mathfrak)\s*\{")
ACCENT_RE = re.compile(r"\\(?:hat|widehat|bar|overline|tilde|widetilde|vec|dot|ddot)\b")
GREEK_NAMES = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
    "pi", "varpi", "rho", "varrho", "sigma", "varsigma", "tau", "upsilon", "phi",
    "varphi", "chi", "psi", "omega", "Gamma", "Delta", "Theta", "Lambda", "Xi",
    "Pi", "Sigma", "Upsilon", "Phi", "Psi", "Omega",
}
STANDARD_CONSTANTS = {r"\pi", r"\infty"}
ALLOWED_DISPOSITION = "retain"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments_preserve_lines(text: str) -> str:
    return re.sub(
        r"(?m)(?<!\\)%[^\r\n]*",
        lambda match: " " * len(match.group(0)),
        text,
    )


def paper_body_region(text: str) -> tuple[int, int]:
    """Return the auditable paper body, not merely the fifth section.

    The official body anchor is preferred.  Small isolated test documents and
    legacy drafts may not have it, so the first section is a safe fallback that
    avoids scanning preamble definitions as if they were exposition.
    """
    start_match = re.search(r"\\label\{body:start\}", text)
    if start_match:
        start = start_match.end()
    else:
        first_section = re.search(r"\\section\*?\{", text)
        start = first_section.start() if first_section else 0
    tail = text[start:]
    end_match = re.search(
        r"\\label\{ai-statement:start\}|"
        r"\\section\*?\{(?:AI\s*工具使用声明|人工智能工具使用声明)\}|"
        r"\\begin\{thebibliography\}|\\bibliography\{|\\appendix\b",
        tail,
    )
    end = start + end_match.start() if end_match else len(text)
    return start, end


def notation_region(text: str) -> tuple[int, int] | None:
    start_match = re.search(r"\\section\*?\{符号说明\}", text)
    if not start_match:
        return None
    next_section = re.search(r"\\section\*?\{", text[start_match.end():])
    end = start_match.end() + next_section.start() if next_section else len(text)
    return start_match.start(), end


def inside_span(position: int, span: tuple[int, int] | None) -> bool:
    return bool(span and span[0] <= position < span[1])


def remove_simple_command_groups(text: str) -> str:
    patterns = (
        r"\\(?:text|textrm|textnormal|mathrm|operatorname|unit)\*?\s*\{[^{}]*\}",
        r"\\(?:label|ref|eqref|cite|autoref)\*?(?:\[[^\]]*\])?\s*\{[^{}]*\}",
        r"\\mathbb\s*\{[RNCQZ]\}",
        r"\\SI\s*\{[^{}]*\}\s*\{[^{}]*\}",
        r"\\si\s*\{[^{}]*\}",
    )
    previous = None
    while previous != text:
        previous = text
        for pattern in patterns:
            text = re.sub(pattern, " ", text, flags=re.DOTALL)
    return text


def extract_symbols(math: str) -> set[str]:
    cleaned = re.sub(r"\\(?:begin|end)\{[^}]+\}", " ", math)
    cleaned = remove_simple_command_groups(cleaned)
    greek = {f"\\{name}" for name in re.findall(r"\\([A-Za-z]+)", cleaned) if name in GREEK_NAMES}
    cleaned = re.sub(r"\\[A-Za-z@]+\*?", " ", cleaned)
    latin = set(re.findall(r"[A-Za-z]", cleaned))
    return (greek | latin) - STANDARD_CONSTANTS


def inline_symbols(
    text: str,
    absolute_start: int,
    excluded_span: tuple[int, int] | None,
) -> set[str]:
    symbols: set[str] = set()
    for match in INLINE_MATH_RE.finditer(text):
        absolute_position = absolute_start + match.start()
        if inside_span(absolute_position, excluded_span):
            continue
        symbols.update(extract_symbols(match.group("dollar") or match.group("paren") or ""))
    return symbols


def tex_to_prose(text: str) -> str:
    text = re.sub(
        r"\\begin\{(?P<float_env>figure|table|algorithm)\*?\}.*?"
        r"\\end\{(?P=float_env)\*?\}",
        " ",
        text,
        flags=re.DOTALL,
    )
    text = INLINE_MATH_RE.sub(" [符号] ", text)
    text = re.sub(r"\\(?:ref|eqref|cite|label)\*?(?:\[[^\]]*\])?\{[^}]*\}", " ", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[{}&~]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def context_before(text: str, start: int, previous_end: int, width: int = 520) -> tuple[str, str]:
    floor = max(previous_end, start - width)
    snippet = text[floor:start]
    heading = list(HEADING_RE.finditer(snippet))
    if heading:
        snippet = snippet[heading[-1].end():]
    return snippet, tex_to_prose(snippet)


def context_after(text: str, end: int, region_end: int, width: int = 520) -> tuple[str, str]:
    snippet = text[end:min(region_end, end + width)]
    stops: list[int] = []
    for pattern in (
        DISPLAY_RE,
        HEADING_RE,
        re.compile(r"\\begin\{(?:figure|table|algorithm)[^}]*\}"),
    ):
        match = pattern.search(snippet)
        if match:
            stops.append(match.start())
    if stops:
        snippet = snippet[:min(stops)]
    return snippet, tex_to_prose(snippet)


def split_formula_rows(body: str) -> list[str]:
    cleaned = re.sub(r"\\(?:begin|end)\{(?:aligned|split|cases)\}", " ", body)
    return [row.strip() for row in re.split(r"\\\\(?:\[[^\]]*\])?", cleaned) if row.strip()]


def normalized_lhs(row: str) -> str | None:
    match = RELATION_RE.search(row)
    if not match:
        return None
    lhs = row[:match.start()]
    lhs = re.sub(r"\\(?:label|tag)\{[^}]*\}", "", lhs)
    lhs = re.sub(r"[\s{}&]", "", lhs)
    return lhs or None


def has_compound_primary_relations(body: str, lead: str) -> bool:
    if r"\begin{cases}" in body or SYSTEM_CUE_RE.search(lead):
        return False
    rows = split_formula_rows(body)
    lhs_values = {lhs for row in rows if (lhs := normalized_lhs(row))}
    if len(lhs_values) > 1:
        return True
    if len(rows) == 1 and re.search(r"\\q(?:quad|qquad)|[，,；;]", rows[0]):
        fragments = re.split(r"\\q(?:quad|qquad)|[，,；;]", rows[0])
        relation_fragments = [fragment for fragment in fragments if RELATION_RE.search(fragment)]
        return len(relation_fragments) > 1
    return False


def braced_group(text: str, opening: int) -> tuple[str, int] | None:
    if opening >= len(text) or text[opening] != "{":
        return None
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{" and (index == 0 or text[index - 1] != "\\"):
            depth += 1
        elif text[index] == "}" and (index == 0 or text[index - 1] != "\\"):
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index + 1
    return None


def has_nested_script(body: str) -> bool:
    for match in re.finditer(r"[_^]\s*\{", body):
        group = braced_group(body, match.end() - 1)
        if group and re.search(r"[_^]\s*(?:\{|[A-Za-z0-9\\])", group[0]):
            return True
    return False


def has_stacked_accent(body: str) -> bool:
    for match in ACCENT_RE.finditer(body):
        brace = re.search(r"\{", body[match.end():])
        if not brace:
            continue
        opening = match.end() + brace.start()
        group = braced_group(body, opening)
        if group and ACCENT_RE.search(group[0]):
            return True
    return False


def has_semantic_intermediate_risk(body: str) -> bool:
    if DEFINITION_RE.search(body) and (len(split_formula_rows(body)) > 1 or OPTIMIZATION_RE.search(body)):
        return True
    return bool(OPTIMIZATION_RE.search(body) and AGGREGATE_RE.search(body))


def formula_key(body: str, index: int) -> tuple[str, str | None]:
    label = re.search(r"\\label\{([^}]+)\}", body)
    if label:
        return f"eq:{label.group(1)}", label.group(1)
    normalized = re.sub(r"\s+", "", re.sub(r"\\label\{[^}]+\}", "", body))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"formula:{digest}:{index}", None


def excerpt(value: str, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return compact[:limit]


def make_risk(
    key: str,
    kind: str,
    line: int,
    label: str | None,
    message: str,
    lead: str,
    body: str,
    follow: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "risk_id": f"{key}/{kind}",
        "kind": kind,
        "line": line,
        "label": label,
        "message": message,
        "lead_excerpt": excerpt(lead),
        "formula_excerpt": excerpt(body),
        "follow_excerpt": excerpt(follow),
    }
    if details:
        record["details"] = details
    return record


def audit_tex(text: str) -> list[dict[str, Any]]:
    text = strip_comments_preserve_lines(text)
    region_start, region_end = paper_body_region(text)
    excluded_notation = notation_region(text)
    displays = [
        match for match in DISPLAY_RE.finditer(text)
        if region_start <= match.start() < region_end
    ]
    risks: list[dict[str, Any]] = []
    known_symbols: set[str] = set()
    cursor = region_start
    previous_end = region_start

    for index, match in enumerate(displays, start=1):
        known_symbols.update(
            inline_symbols(text[cursor:match.start()], cursor, excluded_notation)
        )
        body = match.group("body")
        body_symbols = extract_symbols(body)
        new_symbols = sorted(body_symbols - known_symbols)
        raw_lead, lead = context_before(text, match.start(), previous_end)
        raw_follow, follow = context_after(text, match.end(), region_end)
        key, label = formula_key(body, index)
        line = text.count("\n", 0, match.start()) + 1

        if len(re.findall(r"[\u4e00-\u9fff]", lead)) < 4 or not LEAD_SIGNAL_RE.search(lead):
            risks.append(make_risk(
                key, "missing_purpose_lead", line, label,
                "公式前未用自然语言说明对象、来源或推导目的",
                lead, body, follow,
            ))
        elif GENERIC_LEAD_RE.search(lead) and len(re.findall(r"[\u4e00-\u9fff]", lead)) < 18:
            risks.append(make_risk(
                key, "generic_formula_lead", line, label,
                "公式引出语只说“如下/可得”，没有交代本题对象与关系",
                lead, body, follow,
            ))

        if SYMBOL_TABLE_ONLY_RE.search(follow):
            risks.append(make_risk(
                key, "symbol_table_only_followup", line, label,
                "公式后只让读者查符号表，没有解释结构、约束或后续用途",
                lead, body, follow,
            ))
        elif len(re.findall(r"[\u4e00-\u9fff]", follow)) < 4 or not FOLLOW_SIGNAL_RE.search(follow):
            risks.append(make_risk(
                key, "missing_followup_explanation", line, label,
                "公式后未解释关键含义、下一步操作或所得结论",
                lead, body, follow,
            ))

        if new_symbols:
            risks.append(make_risk(
                key, "symbols_not_locally_introduced", line, label,
                "公式含有尚未在建模正文中先说明语义的符号，读者需要回查总符号表",
                lead, body, follow,
                {"symbols": new_symbols},
            ))

        if has_compound_primary_relations(body, lead):
            risks.append(make_risk(
                key, "compound_primary_relations", line, label,
                "同一展示式并列多个主关系，且引出语未说明其为同一方程组、约束组或分段关系",
                lead, body, follow,
            ))

        if has_nested_script(body):
            risks.append(make_risk(
                key, "nested_scripts", line, label,
                "检测到上下标内部继续嵌套上下标，应改为单层语义索引或说明保留理由",
                lead, body, follow,
            ))

        if has_stacked_accent(body):
            risks.append(make_risk(
                key, "stacked_accents", line, label,
                "检测到帽号、横线、波浪线或向量记号的嵌套修饰",
                lead, body, follow,
            ))

        if ORNATE_RE.search(body):
            risks.append(make_risk(
                key, "ornate_alphabet", line, label,
                "检测到非惯例花体字母，应换为学科惯用符号或说明其必要性",
                lead, body, follow,
            ))

        if has_semantic_intermediate_risk(body):
            risks.append(make_risk(
                key, "semantic_intermediate_candidate", line, label,
                "核心式同时承担定义、聚合与优化/结果职责，宜先定义有语义的中间量再给主关系",
                lead, body, follow,
            ))

        known_symbols.update(body_symbols)
        cursor = match.end()
        previous_end = match.end()

    return risks


def load_resolutions(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not path.exists():
        return {}, []
    try:
        payload = json.loads(read_text(path))
    except Exception as exc:  # noqa: BLE001
        return {}, [f"处置台账无法读取：{exc}"]
    rows = payload.get("resolutions") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}, ["处置台账必须包含 resolutions 数组"]
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"处置台账第 {index} 项不是对象")
            continue
        risk_id = str(row.get("risk_id", "")).strip()
        if not risk_id:
            errors.append(f"处置台账第 {index} 项缺少 risk_id")
            continue
        if risk_id in records:
            errors.append(f"处置台账 risk_id 重复：{risk_id}")
            continue
        records[risk_id] = row
    return records, errors


def valid_retention(row: dict[str, Any]) -> bool:
    disposition = str(row.get("disposition", "")).strip()
    reason = str(row.get("reason", "")).strip()
    evidence = str(row.get("evidence", "")).strip()
    return disposition == ALLOWED_DISPOSITION and len(reason) >= 8 and len(evidence) >= 4


def close_risks(
    risks: list[dict[str, Any]],
    resolutions: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    retained: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    current_ids = {risk["risk_id"] for risk in risks}
    for risk in risks:
        resolution = resolutions.get(risk["risk_id"])
        if resolution and valid_retention(resolution):
            closed = dict(risk)
            closed["resolution"] = resolution
            retained.append(closed)
        else:
            unresolved.append(risk)
    stale = sorted(set(resolutions) - current_ids)
    return retained, unresolved, stale


def build_report(
    tex_path: Path,
    resolution_path: Path,
) -> dict[str, Any]:
    if not tex_path.exists():
        return {
            "schema_version": 1,
            "pass": False,
            "tex": str(tex_path),
            "tex_sha256": None,
            "risk_count": 0,
            "retained_count": 0,
            "unresolved_count": 1,
            "resolution_errors": ["论文 TeX 不存在"],
            "risks": [],
            "retained": [],
            "unresolved": [{"risk_id": "project/missing_tex", "message": "论文 TeX 不存在"}],
            "stale_resolutions": [],
        }
    tex_bytes = tex_path.read_bytes()
    risks = audit_tex(tex_bytes.decode("utf-8"))
    resolutions, resolution_errors = load_resolutions(resolution_path)
    retained, unresolved, stale = close_risks(risks, resolutions)
    passed = not unresolved and not resolution_errors
    return {
        "schema_version": 1,
        "pass": passed,
        "tex": str(tex_path),
        "tex_sha256": hashlib.sha256(tex_bytes).hexdigest(),
        "resolution_ledger": str(resolution_path),
        "resolution_ledger_sha256": (
            hashlib.sha256(resolution_path.read_bytes()).hexdigest()
            if resolution_path.exists()
            else None
        ),
        "policy": (
            "风险须通过简化、拆式或补充前后解释使其在复跑时消失；确需保留时，"
            "仅接受含正文证据和具体理由的 retain 记录"
        ),
        "risk_count": len(risks),
        "retained_count": len(retained),
        "unresolved_count": len(unresolved),
        "resolution_errors": resolution_errors,
        "risks": risks,
        "retained": retained,
        "unresolved": unresolved,
        "stale_resolutions": stale,
    }


def default_tex(root: Path) -> Path:
    preferred = root / "论文" / "论文.tex"
    if preferred.exists():
        return preferred
    return preferred


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--tex", type=Path)
    parser.add_argument("--resolutions", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    root = args.root.resolve()
    tex_path = args.tex.resolve() if args.tex else default_tex(root)
    resolution_path = (
        args.resolutions.resolve()
        if args.resolutions
        else root / "审查" / "公式可读性处置.json"
    )
    output_path = (
        args.output.resolve()
        if args.output
        else root / "审查" / "公式可读性审计.json"
    )
    report = build_report(tex_path, resolution_path)
    if not args.no_write:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "pass": report["pass"],
        "risk_count": report["risk_count"],
        "retained_count": report["retained_count"],
        "unresolved_count": report["unresolved_count"],
    }, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
