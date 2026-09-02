#!/usr/bin/env python3
"""Fail closed when orchestrator prose contradicts the gates that are actually implemented.

The orchestrator SKILL.md is always loaded, so a rule written there is the rule an agent
obeys. When that prose hardcodes a quantity or treats corpus density as a release floor, the
paper is driven toward a visual quota instead of the claim/evidence needs of the current
problem. This audit compares the orchestrator's stated limits against the implemented
claim-driven authority and refuses to pass when they disagree.

Checked invariants:

- absolute_figure_quota: the orchestrator must not lock the body figure count to a fixed
  absolute range. Figure count has no floor or ceiling.
- figure_count_authority: if the orchestrator states figure-count guidance at all, it must
  name the authority:待证明命题、不可替代/互补证据职责和正文解读；语料密度只作非阻断参照。
- rule_numbering: the 核心原则 list must not repeat a number or nest one numbered rule
  inside another; a mis-nested rule silently reads as a continuation of its parent.
- page_policy_mismatch: the single official body-page definition uses the maximum in
  .cumcm_state.json when that file exists. The official body has a 30-page ceiling and no
  project lower-bound gate. This check rejects stale hard ranges and ceiling drift.

The two figure-count invariants also run against every sibling cumcm-*/SKILL.md and
cumcm-*/STAGE.md. Reference
Markdown is scanned for absolute quotas as well: a stale hard range in a routed reference can
override clean SKILL.md prose once that reference is loaded. Reference files may contain corpus
statistics, but their count guidance must still name the claim/evidence authority;
rule_numbering and page_policy stay scoped to procedural skill and stage files.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA_VERSION = 2

# A hardness marker plus a figure-count expression on the same line is an absolute quota.
HARDNESS_MARKERS = ("硬性", "硬锁", "锁定", "严格限制", "固定为", "配额", "强制凑")
FIGURE_SUBJECTS = ("图形数量", "插图数量", "图数", "图片数量", "图表数量")
# "16 ~ 22 幅", "16--22 幅", "16-22幅", "18 幅", "20 张图"
FIGURE_COUNT_RE = re.compile(r"\d+\s*(?:~|--|—|-|至|到)?\s*\d*\s*(?:幅|张图)")
# Signature/subfigure planning ranges are soft by design and carry an exemption path.
SOFT_CONTEXT = ("特色", "主视觉", "子图", "面板", "subfigure", "Subfigures")

FIGURE_AUTHORITY_TOKENS = ("证据职责", "待证明命题", "不可替代", "信息增益")

PAGE_RANGE_RE = re.compile(r"(\d{2})\s*(?:~|--|—|-|至|到)\s*(\d{2})\s*页")

RULE_RE = re.compile(r"^(\d+)([A-Z]?)\.\s")
NESTED_RULE_RE = re.compile(r"^\s+(\d+)([A-Z]?)\.\s+\S")


def core_principles_block(lines: list[str]) -> tuple[int, int]:
    """Return [start, end) line indices of the 核心原则 section, or (0, len) if absent."""
    start = None
    for index, line in enumerate(lines):
        if line.startswith("## ") and "核心原则" in line:
            start = index + 1
            break
    if start is None:
        return 0, len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            return start, index
    return start, len(lines)


def check_figure_quota(lines: list[str], findings: list[dict]) -> bool:
    """True when the orchestrator makes any figure-count claim."""
    states_figure_count = False
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        has_subject = any(token in line for token in FIGURE_SUBJECTS)
        count_match = FIGURE_COUNT_RE.search(line)
        if not has_subject and count_match is None:
            continue
        if any(token in line for token in SOFT_CONTEXT):
            # Signature-figure and subfigure planning ranges stay soft on purpose.
            continue
        if not has_subject:
            continue
        states_figure_count = True
        marker = next((token for token in HARDNESS_MARKERS if token in line), None)
        if marker is not None and count_match is not None:
            findings.append(
                {
                    "pattern": "absolute_figure_quota",
                    "line": number,
                    "marker": marker,
                    "quantity": count_match.group(0).strip(),
                    "text": line,
                    "detail": (
                        "loaded skill prose locks body figure count to a fixed absolute range; "
                        "figure count has no quota and is decided by claim/evidence duties"
                    ),
                }
            )
    return states_figure_count


def check_figure_authority(text: str, states_figure_count: bool, findings: list[dict]) -> None:
    if not states_figure_count:
        return
    if any(token in text for token in FIGURE_AUTHORITY_TOKENS):
        return
    findings.append(
        {
            "pattern": "figure_count_authority",
            "detail": (
                "orchestrator states figure-count guidance without naming the computed "
                "authority (待证明命题 / 证据职责 / 不可替代性 / 信息增益)"
            ),
        }
    )


def check_rule_numbering(lines: list[str], findings: list[dict]) -> None:
    start, end = core_principles_block(lines)
    seen: dict[str, int] = {}
    previous = 0
    for offset in range(start, end):
        raw = lines[offset]
        number = offset + 1
        nested = NESTED_RULE_RE.match(raw)
        if nested is not None:
            findings.append(
                {
                    "pattern": "rule_numbering",
                    "line": number,
                    "rule": nested.group(1) + nested.group(2),
                    "text": raw.strip(),
                    "detail": "numbered rule is indented under another rule and reads as its continuation",
                }
            )
            continue
        match = RULE_RE.match(raw)
        if match is None:
            continue
        key = match.group(1) + match.group(2)
        if key in seen:
            findings.append(
                {
                    "pattern": "rule_numbering",
                    "line": number,
                    "rule": key,
                    "first_seen_line": seen[key],
                    "detail": f"rule number {key} is used more than once",
                }
            )
        else:
            seen[key] = number
        current = int(match.group(1))
        if current < previous:
            findings.append(
                {
                    "pattern": "rule_numbering",
                    "line": number,
                    "rule": key,
                    "detail": f"rule number {key} goes backwards after {previous}",
                }
            )
        previous = max(previous, current)


def check_page_policy(text: str, state_path: Path, findings: list[dict]) -> dict | None:
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        findings.append(
            {
                "pattern": "page_policy_mismatch",
                "detail": f"page policy unreadable: {exc}",
                "state": str(state_path),
            }
        )
        return None
    policy = state.get("page_policy") if isinstance(state, dict) else None
    if not isinstance(policy, dict):
        return None
    high = policy.get("body_page_max")
    if not isinstance(high, int) or isinstance(high, bool) or not 1 <= high <= 30:
        findings.append(
            {
                "pattern": "page_policy_mismatch",
                "policy_max": high,
                "detail": "body_page_max must be an integer from 1 through the official 30-page ceiling",
            }
        )
        return None
    ranges = {(int(a), int(b)) for a, b in PAGE_RANGE_RE.findall(text)}
    if ranges:
        findings.append(
            {
                "pattern": "page_policy_mismatch",
                "policy_max": high,
                "prose_ranges": [list(item) for item in sorted(ranges)],
                "detail": "body-page prose must state only the official maximum, not a lower-bound range",
            }
        )
    return {"policy_max": high, "prose_ranges": sorted(list(item) for item in ranges)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--skill",
        default=None,
        help="orchestrator SKILL.md; defaults to the cumcm skill next to this script",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="project state json; defaults to <root>/.cumcm_state.json",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="directory holding sibling cumcm-* skills/stages; defaults to the orchestrator's parent",
    )
    parser.add_argument("--output", default="审查/总控一致性审查.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    skill_path = (
        Path(args.skill).resolve()
        if args.skill
        else Path(__file__).resolve().parents[1] / "SKILL.md"
    )
    state_path = Path(args.state).resolve() if args.state else root / ".cumcm_state.json"

    findings: list[dict] = []
    states_figure_count = False
    page_report = None
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        states_figure_count = check_figure_quota(lines, findings)
        check_figure_authority(text, states_figure_count, findings)
        check_rule_numbering(lines, findings)
        page_report = check_page_policy(text, state_path, findings)
    else:
        # Fail closed: a missing orchestrator cannot be declared consistent.
        findings.append(
            {"pattern": "skill_missing", "detail": "orchestrator SKILL.md not found"}
        )

    # Figure-count invariants also apply to every sibling skill or routed stage the agent loads.
    skills_dir = (
        Path(args.skills_dir).resolve() if args.skills_dir else skill_path.parent.parent
    )
    skills_scanned: list[dict] = []
    references_scanned: list[dict] = []
    if skills_dir.is_dir():
        module_paths = sorted(
            list(skills_dir.glob("cumcm*/SKILL.md"))
            + list(skills_dir.glob("cumcm*/STAGE.md"))
        )
        for sub_path in module_paths:
            if sub_path.resolve() == skill_path.resolve():
                continue
            sub_text = sub_path.read_text(encoding="utf-8")
            before = len(findings)
            sub_states = check_figure_quota(sub_text.splitlines(), findings)
            check_figure_authority(sub_text, sub_states, findings)
            for item in findings[before:]:
                item["skill"] = sub_path.parent.name
                item["module_file"] = sub_path.name
            skills_scanned.append(
                {
                    "skill": sub_path.parent.name,
                    "module_file": sub_path.name,
                    "states_figure_count": sub_states,
                    "finding_count": len(findings) - before,
                }
            )
        for reference_path in sorted(skills_dir.glob("cumcm*/references/**/*.md")):
            reference_text = reference_path.read_text(encoding="utf-8")
            before = len(findings)
            reference_states = check_figure_quota(reference_text.splitlines(), findings)
            check_figure_authority(reference_text, reference_states, findings)
            for item in findings[before:]:
                item["reference"] = reference_path.relative_to(skills_dir).as_posix()
            references_scanned.append(
                {
                    "reference": reference_path.relative_to(skills_dir).as_posix(),
                    "states_figure_count": reference_states,
                    "finding_count": len(findings) - before,
                }
            )

    result = {
        "schema_version": SCHEMA_VERSION,
        "pass": not findings,
        "skill": str(skill_path),
        "states_figure_count": states_figure_count,
        "page_policy": page_report,
        "skills_scanned": skills_scanned,
        "references_scanned": references_scanned,
        "finding_count": len(findings),
        "findings": findings,
    }
    if not args.no_write:
        output = root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "pass": result["pass"],
                "finding_count": len(findings),
                "patterns": sorted({item["pattern"] for item in findings}),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
