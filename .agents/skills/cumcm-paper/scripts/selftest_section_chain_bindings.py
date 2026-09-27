#!/usr/bin/env python3
"""Regression tests for hash-bound first-draft and formula audit reports."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "audit_section_chain.py"
SPEC = importlib.util.spec_from_file_location("section_chain_bindings_under_test", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
FIXTURE_SPEC = importlib.util.spec_from_file_location("first_draft_fixture_for_chain", SCRIPT.parent / "selftest_first_draft_gate.py")
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def first_draft_errors(root: Path) -> list[str]:
    return AUDIT.validate_first_draft_gate(root, measurements=FIXTURE.fixture_measurements(root, {"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": sha256(root / "论文/论文.pdf")}))


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
        FIXTURE.prepare(root, body_pages=23, digest=sha256(pdf))

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
            FIXTURE.evaluate_fixture(root, measurements={"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": sha256(pdf)}, content_result={"pass": True, "content_complete": True, "prewrite_ready": True}),
        )

        cases["current_formula_report_passes"] = not AUDIT.validate_formula_readability(root)
        cases["current_first_draft_report_passes"] = not first_draft_errors(root)
        state_path = root / ".cumcm_state.json"
        original_state = state_path.read_text(encoding="utf-8")
        state = json.loads(original_state)
        state["page_policy"]["body_page_max"] = 20
        write_json(state_path, state)
        cases["stricter_current_page_policy_reopens_draft"] = any("policy" in item for item in first_draft_errors(root))
        state_path.write_text(original_state, encoding="utf-8")
        state = json.loads(original_state)
        state["stage"] = "final-review"
        write_json(state_path, state)
        cases["status_bookkeeping_does_not_stale_content_reviews"] = not first_draft_errors(root)
        state_path.write_text(original_state, encoding="utf-8")

        stage_specs = {}
        for stage in AUDIT.REQUIRED_STAGES + AUDIT.OPTIONAL_STAGES:
            relative = f"审查/section-chain/gates/{stage}.json"
            stage_specs[stage] = {"source_files": ["论文/论文.tex"], "gate": relative}
            if stage not in {"deai", "language-audit"}:
                write_json(root / relative, {"schema_version": 1, "stage": stage, "status": "pass", "blocking_issues": [], "checks": [{"id": "fixture", "pass": True, "evidence": "synthetic test only"}]})
        write_json(review / "section-chain/manifest.json", {"schema_version": 1, "fixture": True, "question_ids": ["q1"], "question_architecture": {"q1": {"role": "core", "chain_type": "custom", "custom_chain": "synthetic test", "progression_axis": "foundation", "route_summary": "synthetic fixture only", "planned_subsections": [], "inheritance": {"status": "none", "objects": []}}}, "stages": stage_specs, "cross_cutting": {}})
        first_path = review / "首份可交付初稿门禁.json"
        first_path.unlink()
        content_cli = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--phase", "content", "--no-write"], capture_output=True, text=True, encoding="utf-8", check=False)
        cases["precompile_content_check_has_no_first_draft_cycle"] = content_cli.returncode == 0
        cases["content_no_write_does_not_create_final_audit"] = not (review / "section-chain/chain-audit.json").exists() and not (review / "section-chain/chain-audit-content.json").exists()
        # Restore a new fixture checkpoint after the intentional stage-file edits.
        write_json(first_path, FIXTURE.evaluate_fixture(root, measurements={"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": sha256(pdf)}, content_result={"pass": True, "content_complete": True, "prewrite_ready": True}))

        original = (review / "首份可交付初稿门禁.json").read_text(encoding="utf-8")
        gate = json.loads(original)
        gate["schema_version"] = 1
        write_json(review / "首份可交付初稿门禁.json", gate)
        cases["content_only_v1_report_cannot_release"] = any("schema_version must be 2" in item for item in first_draft_errors(root))
        (review / "首份可交付初稿门禁.json").write_text(original, encoding="utf-8")

        review_path = review / "section-chain/gates/deai.json"
        review_original = review_path.read_text(encoding="utf-8")
        changed_review = json.loads(review_original)
        changed_review["semantic_fact_review"]["unresolved_issues"] = ["synthetic unresolved condition"]
        write_json(review_path, changed_review)
        cases["same_pdf_changed_semantic_review_reopens_gate"] = any("input changed" in item for item in first_draft_errors(root))
        review_path.write_text(review_original, encoding="utf-8")

        tex.write_text("正文公式版本二", encoding="utf-8")
        formula_errors = AUDIT.validate_formula_readability(root)
        cases["stale_formula_report_is_rejected"] = any(
            "TeX hash does not match" in item for item in formula_errors
        )
        cases["same_pdf_changed_tex_reopens_first_draft"] = any("TeX hash does not match" in item for item in first_draft_errors(root))

        pdf.write_bytes(b"compiled-pdf-version-two")
        draft_errors = first_draft_errors(root)
        cases["stale_first_draft_report_is_rejected"] = any(
            "PDF hash does not match" in item for item in draft_errors
        )

        gate = json.loads((review / "首份可交付初稿门禁.json").read_text(encoding="utf-8"))
        gate["pdf_sha256"] = sha256(pdf)
        gate["hard_max"] = 35
        write_json(review / "首份可交付初稿门禁.json", gate)
        policy_errors = first_draft_errors(root)
        cases["relaxed_page_policy_is_rejected"] = any(
            "exceeds the official 30-page maximum" in item for item in policy_errors
        )

    failed = [name for name, passed in cases.items() if not passed]
    print(json.dumps({"pass": not failed, "case_count": len(cases), "failed": failed}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
