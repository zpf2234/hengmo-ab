#!/usr/bin/env python3
"""Regression tests for the single-master-TeX delivery auditor."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from audit_single_tex_delivery import audit


VALID_SOURCE = r"""
\documentclass{article}
\begin{document}
\label{body:start}
\section{问题重述}
\includegraphics{figure.pdf}
\label{ai-statement:start}
\section*{AI工具使用声明}
\label{references:start}
\begin{thebibliography}{9}\end{thebibliography}
\clearpage
\label{appendix:start}
\appendix
\end{document}
"""


def make_project(root: Path, *, final: bool = False) -> None:
    paper = root / "论文"
    paper.mkdir(parents=True)
    (paper / "论文.tex").write_text(VALID_SOURCE, encoding="utf-8")
    if final:
        (paper / "论文.pdf").write_bytes(b"%PDF-1.7\n")
        attachments = root / "附件"
        attachments.mkdir()
        (attachments / "支撑材料.zip").write_bytes(b"fixture")


def expect_failure(name: str, root: Path, fragment: str, phase: str = "source") -> str:
    report = audit(root, phase)
    if report["status"] != "FAIL":
        raise AssertionError(f"{name}: invalid project unexpectedly passed")
    if not any(fragment in error for error in report["errors"]):
        raise AssertionError(
            f"{name}: expected error containing {fragment!r}, got {report['errors']}"
        )
    return name


def main() -> int:
    passed: list[str] = []
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root, final=True)
        report = audit(root, "final")
        if report["status"] != "PASS":
            raise AssertionError(f"valid final project failed: {report['errors']}")
        passed.append("valid_single_master")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root)
        (root / "论文" / "1.问题重述.tex").write_text("split", encoding="utf-8")
        passed.append(
            expect_failure("split_chapter_file", root, "chapter TeX files")
        )

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root)
        master = root / "论文" / "论文.tex"
        master.write_text(
            VALID_SOURCE.replace(
                r"\section{问题重述}",
                "\\input{1.问题重述.tex}\n\\section{问题重述}",
            ),
            encoding="utf-8",
        )
        passed.append(expect_failure("chapter_input", root, "chapter import"))

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root)
        master = root / "论文" / "论文.tex"
        master.write_text(
            VALID_SOURCE.replace(
                r"\label{ai-statement:start}",
                "\\section{模型的建立与求解}\n"
                "\\subsection{问题一：投影定位}\n"
                "\\subsubsection{核心区域}\n"
                "正文。\n"
                "\\label{ai-statement:start}",
            ),
            encoding="utf-8",
        )
        passed.append(
            expect_failure(
                "abrupt_question_heading",
                root,
                "must begin with a prose route paragraph",
            )
        )

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root)
        master = root / "论文" / "论文.tex"
        master.write_text(
            VALID_SOURCE.replace(
                r"\label{ai-statement:start}",
                "\\section{模型的建立与求解}\n"
                "\\subsection{问题一：投影定位}\n"
                "先由轴向投影定位目标区域，再计算方向量并输出分段边界。\n"
                "\\subsubsection{核心区域}\n"
                "正文。\n"
                "\\label{ai-statement:start}",
            ),
            encoding="utf-8",
        )
        report = audit(root, "source")
        if report["status"] != "PASS":
            raise AssertionError(f"route paragraph project failed: {report['errors']}")
        passed.append("question_route_paragraph")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root)
        manifest_dir = root / "审查" / "section-chain"
        manifest_dir.mkdir(parents=True)
        manifest = {
            "paper_source": "论文/论文.tex",
            "stages": {
                "analysis": {"source_files": ["论文/2.问题分析.tex"]}
            },
        }
        (manifest_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False),
            encoding="utf-8",
        )
        passed.append(
            expect_failure("manifest_split_source", root, "split sources")
        )

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        make_project(root)
        (root / "论文" / "论文.pdf").write_bytes(b"%PDF-1.7\n")
        (root / "附件").mkdir()
        passed.append(
            expect_failure(
                "empty_attachments",
                root,
                "actual support deliverables",
                phase="final",
            )
        )

    print(
        json.dumps(
            {"status": "PASS", "case_count": len(passed), "cases": passed},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
