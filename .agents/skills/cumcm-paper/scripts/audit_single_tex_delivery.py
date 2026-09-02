#!/usr/bin/env python3
"""Audit the single-master-TeX and paper-plus-attachments delivery contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MASTER_RELATIVE = Path("论文") / "论文.tex"
PDF_RELATIVE = Path("论文") / "论文.pdf"
ATTACHMENTS_RELATIVE = Path("附件")

FORBIDDEN_CHAPTER_IMPORTS = {
    "input": re.compile(r"\\input\s*\{", re.IGNORECASE),
    "include": re.compile(r"\\include\s*\{", re.IGNORECASE),
    "subfile": re.compile(r"\\subfile\s*\{", re.IGNORECASE),
}

REQUIRED_MARKERS = {
    "document_start": r"\begin{document}",
    "document_end": r"\end{document}",
    "restatement_section": r"\section{问题重述}",
    "body_page_anchor": r"\label{body:start}",
    "ai_statement_anchor": r"\label{ai-statement:start}",
    "references_anchor": r"\label{references:start}",
    "appendix_page_anchor": r"\label{appendix:start}",
}

MODEL_SECTION_RE = re.compile(r"\\section\s*\{模型的建立与求解\}")
NEXT_SECTION_RE = re.compile(r"\\section\*?\s*\{")
QUESTION_SUBSECTION_RE = re.compile(
    r"\\subsection\s*\{(?P<title>问题[一二三四五六七八九十0-9]+[^{}]*)\}"
)
NEXT_SUBSECTION_RE = re.compile(r"\\subsection\s*\{")
ABRUPT_QUESTION_START_RE = re.compile(
    r"^\s*(?:\\subsubsection\s*\{|\\begin\s*\{|\\\[|\\(?:equation|align)\b)"
)


def strip_comments(source: str) -> str:
    """Remove TeX comments while preserving escaped percent signs."""
    cleaned: list[str] = []
    for line in source.splitlines():
        stop = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            slash_count = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                slash_count += 1
                cursor -= 1
            if slash_count % 2 == 0:
                stop = index
                break
        cleaned.append(line[:stop])
    return "\n".join(cleaned)


def _load_manifest(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid section manifest: {exc}")
        return None
    if not isinstance(document, dict):
        errors.append("section manifest root must be an object")
        return None
    return document


def _question_route_errors(source: str) -> list[str]:
    """Detect question headings that jump directly into a lower-level block."""
    model_match = MODEL_SECTION_RE.search(source)
    if model_match is None:
        return []
    model_tail = source[model_match.end() :]
    next_section = NEXT_SECTION_RE.search(model_tail)
    model_body = model_tail[: next_section.start()] if next_section else model_tail

    errors: list[str] = []
    question_matches = list(QUESTION_SUBSECTION_RE.finditer(model_body))
    for index, question_match in enumerate(question_matches):
        next_question_start = (
            question_matches[index + 1].start()
            if index + 1 < len(question_matches)
            else len(model_body)
        )
        subsection_boundary = NEXT_SUBSECTION_RE.search(
            model_body, question_match.end()
        )
        block_end = min(
            next_question_start,
            subsection_boundary.start() if subsection_boundary else len(model_body),
        )
        leading = model_body[question_match.end() : block_end]
        while True:
            label_match = re.match(r"^\s*\\label\s*\{[^{}]+\}", leading)
            if label_match is None:
                break
            leading = leading[label_match.end() :]
        if not leading.strip() or ABRUPT_QUESTION_START_RE.match(leading):
            errors.append(
                "question subsection must begin with a prose route paragraph "
                f"before lower-level headings, equations, figures, or tables: "
                f"{question_match.group('title')}"
            )
    return errors


def audit(root: Path, phase: str) -> dict[str, Any]:
    root = root.resolve()
    paper_dir = root / "论文"
    master = root / MASTER_RELATIVE
    errors: list[str] = []

    if not paper_dir.is_dir():
        errors.append("missing paper directory: 论文/")
        top_level_tex: list[str] = []
    else:
        top_level_tex = sorted(path.name for path in paper_dir.glob("*.tex"))
        unexpected = [name for name in top_level_tex if name != "论文.tex"]
        if unexpected:
            errors.append(
                "top-level chapter TeX files are forbidden; merge into 论文/论文.tex: "
                + ", ".join(unexpected)
            )

    source = ""
    if not master.is_file():
        errors.append("missing single master source: 论文/论文.tex")
    else:
        source = strip_comments(master.read_text(encoding="utf-8"))
        for import_name, pattern in FORBIDDEN_CHAPTER_IMPORTS.items():
            if pattern.search(source):
                errors.append(
                    f"forbidden chapter import command in 论文/论文.tex: {import_name}"
                )
        for marker_id, marker in REQUIRED_MARKERS.items():
            if marker not in source:
                errors.append(f"missing required master marker: {marker_id}")
        errors.extend(_question_route_errors(source))
        ordered_markers = [
            source.find(REQUIRED_MARKERS[marker_id])
            for marker_id in (
                "body_page_anchor",
                "ai_statement_anchor",
                "references_anchor",
                "appendix_page_anchor",
            )
        ]
        if all(position >= 0 for position in ordered_markers) and ordered_markers != sorted(ordered_markers):
            errors.append("master markers must follow body -> AI statement -> references -> appendix order")

    manifest_path = root / "审查" / "section-chain" / "manifest.json"
    manifest = _load_manifest(manifest_path, errors)
    if manifest is not None:
        if manifest.get("paper_source") != MASTER_RELATIVE.as_posix():
            errors.append("manifest.paper_source must equal 论文/论文.tex")
        stages = manifest.get("stages", {})
        if not isinstance(stages, dict):
            errors.append("manifest.stages must be an object")
        else:
            for stage_id, stage in stages.items():
                if not isinstance(stage, dict):
                    errors.append(f"manifest stage {stage_id} must be an object")
                    continue
                source_files = stage.get("source_files", [])
                if not isinstance(source_files, list):
                    errors.append(
                        f"manifest stage {stage_id}.source_files must be a list"
                    )
                    continue
                foreign = [
                    item
                    for item in source_files
                    if item != MASTER_RELATIVE.as_posix()
                ]
                if foreign:
                    errors.append(
                        f"manifest stage {stage_id} references split sources: {foreign}"
                    )

    if phase == "final":
        pdf_path = root / PDF_RELATIVE
        if not pdf_path.is_file() or pdf_path.stat().st_size == 0:
            errors.append("missing or empty compiled paper: 论文/论文.pdf")
        attachments = root / ATTACHMENTS_RELATIVE
        if not attachments.is_dir():
            errors.append("missing attachments directory: 附件/")
            attachment_files: list[str] = []
        else:
            attachment_files = sorted(
                str(path.relative_to(root)).replace("\\", "/")
                for path in attachments.rglob("*")
                if path.is_file()
            )
            if not attachment_files:
                errors.append("附件/ must contain the actual support deliverables")
    else:
        attachment_files = []

    return {
        "status": "PASS" if not errors else "FAIL",
        "phase": phase,
        "root": str(root),
        "paper_source": MASTER_RELATIVE.as_posix(),
        "top_level_tex_files": top_level_tex,
        "attachment_files": attachment_files,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--phase", choices=("source", "final"), default="source")
    args = parser.parse_args()
    report = audit(args.root, args.phase)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
