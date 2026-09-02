#!/usr/bin/env python3
"""Regression tests for hash-bound first-draft and formula audit reports."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "audit_section_chain.py"
SPEC = importlib.util.spec_from_file_location("section_chain_bindings_under_test", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    cases: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-section-bindings-") as tmp:
        root = Path(tmp)
        paper = root / "论文"
        review = root / "审查"
        paper.mkdir(parents=True)
        tex = paper / "论文.tex"
        pdf = paper / "论文.pdf"
        tex.write_text("正文公式版本一", encoding="utf-8")
        pdf.write_bytes(b"compiled-pdf-version-one")

        write_json(
            review / "公式可读性审计.json",
            {
                "schema_version": 1,
                "pass": True,
                "unresolved_count": 0,
                "tex_sha256": sha256(tex),
                "resolution_ledger_sha256": None,
            },
        )
        write_json(
            review / "首份可交付初稿门禁.json",
            {
                "schema_version": 1,
                "status": "PASS_FIRST_DELIVERABLE_DRAFT",
                "pass": True,
                "build_status": "FIRST_DRAFT_CANDIDATE",
                "deliverable": True,
                "blockers": [],
                "pdf_sha256": sha256(pdf),
                "hard_max": 30,
            },
        )

        cases["current_formula_report_passes"] = not AUDIT.validate_formula_readability(root)
        cases["current_first_draft_report_passes"] = not AUDIT.validate_first_draft_gate(root)

        tex.write_text("正文公式版本二", encoding="utf-8")
        formula_errors = AUDIT.validate_formula_readability(root)
        cases["stale_formula_report_is_rejected"] = any(
            "TeX hash does not match" in item for item in formula_errors
        )

        pdf.write_bytes(b"compiled-pdf-version-two")
        draft_errors = AUDIT.validate_first_draft_gate(root)
        cases["stale_first_draft_report_is_rejected"] = any(
            "PDF hash does not match" in item for item in draft_errors
        )

        gate = json.loads((review / "首份可交付初稿门禁.json").read_text(encoding="utf-8"))
        gate["pdf_sha256"] = sha256(pdf)
        gate["hard_max"] = 35
        write_json(review / "首份可交付初稿门禁.json", gate)
        policy_errors = AUDIT.validate_first_draft_gate(root)
        cases["relaxed_page_policy_is_rejected"] = any(
            "exceeds the official 30-page maximum" in item for item in policy_errors
        )

    failed = [name for name, passed in cases.items() if not passed]
    print(json.dumps({"pass": not failed, "case_count": len(cases), "failed": failed}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
