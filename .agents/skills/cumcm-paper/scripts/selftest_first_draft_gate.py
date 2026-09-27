#!/usr/bin/env python3
"""Regression tests for the first-draft compile-and-revise gate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path


PDF_BYTES = b"synthetic compiled PDF fixture, not a manuscript"
PDF_SHA256 = hashlib.sha256(PDF_BYTES).hexdigest()


SCRIPT = Path(__file__).resolve().parent / "check_first_draft_gate.py"
SPEC = importlib.util.spec_from_file_location("first_draft_gate_under_test", SCRIPT)
assert SPEC and SPEC.loader
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compile_record(body_pages: int, digest: str, *, missing: list[str] | None = None, actions: list[str] | None = None) -> dict:
    missing = missing or []
    actions = actions or []
    complete = body_pages <= 30 and not missing and not actions
    return {
        "iteration": 1,
        "body_pages": body_pages,
        "total_pdf_pages": body_pages + 12,
        "pdf_sha256": digest,
        "build_status": "INTERNAL_REVIEW_CANDIDATE" if complete else "INTERNAL_FAILED_BUILD",
        "deliverable": False,
        "missing_depth_items": missing,
        "actions": actions,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_measurements(root: Path, measurements: dict) -> dict:
    """Explicit mock receipt only; real compilation is tested by the compiler suite."""
    return {**measurements, "tex_sha256": sha256(root / "论文/论文.tex"), "compilation_binding_verified": True,
            "compile_manifest": {"path": "审查/编译绑定.json", "sha256": sha256(root / "审查/编译绑定.json")}}


def evaluate_fixture(root: Path, *, measurements: dict, content_result: dict) -> dict:
    return GATE.evaluate(root, measurements=fixture_measurements(root, measurements), content_result=content_result)


def prepare_assurance(root: Path, pdf_digest: str) -> None:
    """Synthetic simulation records only; these are not actual manuscript reviews."""
    tex = root / "论文/论文.tex"
    tex.parent.mkdir(parents=True, exist_ok=True)
    pdf = root / "论文/论文.pdf"
    if not pdf.exists():
        pdf.write_bytes(PDF_BYTES)
    write_json(root / "审查/编译绑定.json", {"fixture": True, "scope": "synthetic receipt mock, not an actual build"})
    tex.write_text("% synthetic first-draft assurance fixture\n" + r"\label{body:start}" + "\n样例正文\n" + r"\label{ai-statement:start}" + "\nAI工具使用声明\n本参赛队在竞赛过程中使用了AI工具，主要用于测试样例，详细使用情况见支撑材料。\n" + r"\label{references:start}" + "\n" + r"\label{appendix:start}", encoding="utf-8")
    matrix = root / "求解/证据矩阵.csv"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text("claim_id,description\nFIXTURE,synthetic-only\n", encoding="utf-8")
    baseline = root / "审查/deai-baseline/论文.tex"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_bytes(tex.read_bytes())
    details = root / "附件/AI工具使用详情.pdf"
    details.parent.mkdir(parents=True, exist_ok=True)
    details.write_bytes(b"%PDF-synthetic-fixture-not-a-submission")

    source = {"path": "论文/论文.tex", "sha256": sha256(tex)}
    mechanical = {"fixture": True, "pass": True, "paper_source": source, "hard_count": 0, "soft_count": 0, "files_scanned": 1, "missing_files": [], "records": [{"file": "论文/论文.tex", "hard": [], "soft": []}]}
    paths = {"authentic_expression": "审查/section-chain/authentic-expression-audit.json", "corpus_voice": "审查/section-chain/corpus-voice-audit.json", "language_scan": "审查/section-chain/language-audit.json"}
    write_json(root / paths["authentic_expression"], {"fixture": True, "schema_version": 2, "paper_sha256": hashlib.sha256(tex.read_text(encoding="utf-8").encode("utf-8")).hexdigest(), "integrity": {"status": "PASS", "baseline_sha256": hashlib.sha256(baseline.read_text(encoding="utf-8").encode("utf-8")).hexdigest()}, "expression_review": {"findings": []}, "semantic_review": {"changes": []}})
    for key in ("corpus_voice", "language_scan"):
        write_json(root / paths[key], mechanical)
    refs = {key: {"path": value, "sha256": sha256(root / value)} for key, value in paths.items()}
    review = {"fixture": True, "pass": True, "full_text_read": True, "reviewer": "synthetic fixture reviewer, not an actual approval", "reviewer_type": "ai", "reviewed_at": "2026-09-08T00:00:00Z", "scope": "synthetic regression only", "unresolved_issues": [], "evidence": ["论文/论文.tex#body:start"], "evidence_sha256": {"论文/论文.tex": sha256(tex)}, "signal_resolutions": []}
    shared = {"fixture": True, "schema_version": 1, "status": "pass", "blocking_issues": [], "tex_sha256": sha256(tex), "pdf_sha256": pdf_digest}
    write_json(root / "审查/section-chain/gates/deai.json", {**shared, "stage": "deai", "baseline": {"path": "审查/deai-baseline/论文.tex", "sha256": sha256(baseline)}, "evidence_matrix_sha256": sha256(matrix), "audit_reports": {key: refs[key] for key in ("authentic_expression", "corpus_voice")}, "semantic_fact_review": {**review, "evidence_matrix_checked": True, "sources_conditions_claim_strength_checked": True}, "expression_review": review})
    write_json(root / "审查/section-chain/gates/language-audit.json", {**shared, "stage": "language-audit", "audit_reports": {"language_scan": refs["language_scan"]}, "manual_review": review, "ai_usage": {"used": True, "disclosure_checked": True, "details_checked": True, "details": {"path": "附件/AI工具使用详情.pdf", "sha256": sha256(details)}, "participant_verification": "not_applicable_simulation"}})
    write_json(root / "审查/优秀论文对标.json", {"fixture": True, "schema_version": 2, "candidate_pdf": {"path": "论文/论文.pdf", "sha256": pdf_digest}, "similarity": {"status": "PASS", "coverage": {"scope": "all_local_corpus_pdfs", "eligible_count": 2, "compared_count": 2, "complete": True, "candidate_complete": True}}, "originality_gate": {"verdict": "PASS", "coverage_complete": True, "candidate_pdf_sha256": pdf_digest}})
    originality_path = root / "审查/优秀论文对标.json"
    originality = json.loads(originality_path.read_text(encoding="utf-8"))
    corpus = root / "fixture-corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    for index in (1, 2):
        (corpus / f"reference-{index}.pdf").write_bytes(f"%PDF-synthetic-reference-fixture-{index}".encode("ascii"))
    originality_owner = GATE.load_assurance_module().load_originality_module()
    originality["corpus_source"] = originality_owner.capture_corpus_source(corpus, pdf)
    originality["similarity"]["per_reference"] = [dict(row) for row in originality["corpus_source"]["members"]]
    basis = originality_owner.compute_audit_basis(pdf_digest, originality["similarity"])
    originality["audit_basis_sha256"] = basis
    originality["originality_gate"]["audit_basis_sha256"] = basis
    write_json(originality_path, originality)


def prepare(root: Path, *, body_pages: int, digest: str = PDF_SHA256, stage_status: str = "pass", content_complete: bool = True, missing: list[str] | None = None, actions: list[str] | None = None, assurance: bool = True) -> None:
    write_json(
        root / ".cumcm_state.json",
        {"fixture": True, "workflow_policy": {"mode": "simulation"}, "page_policy": {"body_page_max": 30}},
    )
    write_json(
        root / "审查/逐问深度清单.json",
        {"schema_version": 1, "compile_feedback": {"iterations": [compile_record(body_pages, digest, missing=missing, actions=actions)]}},
    )
    write_json(
        root / "审查/正文深度审计.json",
        {
            "schema_version": 1,
            "phase": "content",
            "pass": content_complete,
            "content_complete": content_complete,
            "errors": [] if content_complete else ["q2.independent_validation missing"],
        },
    )
    for stage in GATE.REQUIRED_DRAFT_STAGES:
        write_json(
            root / f"审查/section-chain/gates/{stage}.json",
            {
                "schema_version": 1,
                "stage": stage,
                "status": stage_status,
                "blocking_issues": [] if stage_status == "pass" else ["incomplete"],
            },
        )
    if assurance:
        prepare_assurance(root, digest)


def case(body_pages: int, expected_status: str, **kwargs) -> dict:
    digest = kwargs.get("digest", PDF_SHA256)
    content_complete = kwargs.get("content_complete", True)
    prewrite_ready = kwargs.pop("prewrite_ready", True)
    with tempfile.TemporaryDirectory(prefix="cumcm-first-draft-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=body_pages, **kwargs)
        result = evaluate_fixture(
            root,
            measurements={
                "body_pages": body_pages,
                "total_pdf_pages": body_pages + 12,
                "body_start_page": 2,
                "appendix_start_page": body_pages + 2,
                "references_start_page": body_pages,
                "pdf_sha256": digest,
                "pdf": "论文/论文.pdf",
            },
            content_result={
                "pass": content_complete,
                "prewrite_ready": prewrite_ready,
                "content_complete": content_complete,
                "errors": [] if content_complete else ["q2.independent_validation missing"],
            },
        )
    return {
        "expected_status": expected_status,
        "actual_status": result["status"],
        "pass": result["status"] == expected_status,
        "blockers": result["blockers"],
    }


def stale_case() -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-first-draft-stale-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23, digest=PDF_SHA256)
        result = evaluate_fixture(
            root,
            measurements={
                "body_pages": 23,
                "total_pdf_pages": 35,
                "body_start_page": 2,
                "appendix_start_page": 25,
                "references_start_page": 23,
                "pdf_sha256": "b" * 64,
                "pdf": "论文/论文.pdf",
            },
            content_result={
                "pass": True,
                "prewrite_ready": True,
                "content_complete": True,
                "errors": [],
            },
        )
    expected = "BLOCK_FIRST_DELIVERABLE_NOT_COMPILED_OR_STALE"
    return {
        "expected_status": expected,
        "actual_status": result["status"],
        "pass": result["status"] == expected,
        "blockers": result["blockers"],
    }


def invalid_page_policy_case() -> dict:
    """A project cannot relax the official 30-page maximum."""
    with tempfile.TemporaryDirectory(prefix="cumcm-first-draft-policy-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=31)
        write_json(
            root / ".cumcm_state.json",
            {"fixture": True, "workflow_policy": {"mode": "simulation"}, "page_policy": {"body_page_max": 35}},
        )
        result = evaluate_fixture(
            root,
            measurements={
                "body_pages": 31,
                "total_pdf_pages": 43,
                "body_start_page": 2,
                "appendix_start_page": 33,
                "references_start_page": 31,
                "pdf_sha256": PDF_SHA256,
                "pdf": "论文/论文.pdf",
            },
            content_result={
                "pass": True,
                "prewrite_ready": True,
                "content_complete": True,
                "errors": [],
            },
        )
    expected = "CONTINUE_INTERNAL_BUILD_ABOVE_MAX"
    return {
        "expected_status": expected,
        "actual_status": result["status"],
        "pass": result["status"] == expected and result["hard_max"] == 30,
        "blockers": result["blockers"],
    }


def incomplete_closing_stage_case() -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-first-draft-closing-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23)
        write_json(
            root / "审查/section-chain/gates/abstract.json",
            {
                "schema_version": 1,
                "stage": "abstract",
                "status": "fail",
                "blocking_issues": ["final abstract missing"],
            },
        )
        result = evaluate_fixture(
            root,
            measurements={
                "body_pages": 23,
                "total_pdf_pages": 35,
                "body_start_page": 2,
                "appendix_start_page": 25,
                "references_start_page": 23,
                "pdf_sha256": PDF_SHA256,
                "pdf": "论文/论文.pdf",
            },
            content_result={
                "pass": True,
                "prewrite_ready": True,
                "content_complete": True,
                "errors": [],
            },
        )
    expected = "BLOCK_FIRST_DELIVERABLE_STAGE_INCOMPLETE"
    return {
        "expected_status": expected,
        "actual_status": result["status"],
        "pass": result["status"] == expected,
        "blockers": result["blockers"],
    }


def failed_build_cannot_masquerade_as_draft_case() -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-first-draft-identity-") as tmp:
        root = Path(tmp)
        prepare(
            root,
            body_pages=18,
            missing=["q1: 边界复核尚未进入正文"],
            actions=["补入已冻结的边界复算、关键读数和答案影响"],
        )
        path = root / "审查/逐问深度清单.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["compile_feedback"]["iterations"][0]["build_status"] = "FIRST_DRAFT_CANDIDATE"
        payload["compile_feedback"]["iterations"][0]["deliverable"] = True
        write_json(path, payload)
        result = evaluate_fixture(
            root,
            measurements={
                "body_pages": 18,
                "total_pdf_pages": 30,
                "body_start_page": 2,
                "appendix_start_page": 20,
                "references_start_page": 18,
                "pdf_sha256": PDF_SHA256,
                "pdf": "论文/论文.pdf",
            },
            content_result={
                "pass": True,
                "prewrite_ready": True,
                "content_complete": True,
                "errors": [],
            },
        )
    expected = "BLOCK_FIRST_DELIVERABLE_NOT_COMPILED_OR_STALE"
    return {
        "expected_status": expected,
        "actual_status": result["status"],
        "pass": result["status"] == expected and result["deliverable"] is False,
        "blockers": result["blockers"],
    }


def assurance_case(relative: str, mutate, expected_fragment: str, *, rebind_report: str | None = None) -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-first-assurance-fixture-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23)
        path = root / relative
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            mutate(payload)
            write_json(path, payload)
        else:
            mutate(path)
        if rebind_report:
            stage, key = rebind_report.split(":", 1)
            gate_path = root / f"审查/section-chain/gates/{stage}.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            gate["audit_reports"][key]["sha256"] = sha256(path)
            write_json(gate_path, gate)
        result = evaluate_fixture(root, measurements={"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": PDF_SHA256}, content_result={"pass": True, "prewrite_ready": True, "content_complete": True, "errors": []})
    return {"pass": not result["pass"] and any(expected_fragment in item for item in result["blockers"]), "actual_status": result["status"], "blockers": result["blockers"]}


def reviewed_signal_case(*, participant_pending: bool = False, deduplication: bool = False, missed_removal: bool = False) -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-reviewed-signal-fixture-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23)
        language_path = root / "审查/section-chain/gates/language-audit.json"
        language = json.loads(language_path.read_text(encoding="utf-8"))
        if participant_pending:
            # Explicit synthetic fixture exercising formal policy without asserting
            # any real participant approval or changing the two upstream checkpoints.
            write_json(root / ".cumcm_state.json", {"fixture": True, "workflow_policy": {"mode": "competition"}, "page_policy": {"body_page_max": 30}})
            language["ai_usage"]["participant_verification"] = "pending"
        else:
            scan_path = root / "审查/section-chain/language-audit.json"
            scan = json.loads(scan_path.read_text(encoding="utf-8"))
            scan["records"][0]["soft"] = [{"pattern": "technical_term_review"}]
            scan["soft_count"] = 1
            write_json(scan_path, scan)
            language["audit_reports"]["language_scan"]["sha256"] = sha256(scan_path)
            language["manual_review"]["signal_resolutions"] = [{"signal": "language_scan:records[0].soft[0]", "disposition": "retained", "reason": "synthetic fixture represents a required technical term"}]
        write_json(language_path, language)
        if deduplication:
            authentic_path = root / "审查/section-chain/authentic-expression-audit.json"
            authentic = json.loads(authentic_path.read_text(encoding="utf-8"))
            authentic["integrity"]["status"] = "REVIEW"
            authentic["integrity"]["categories"] = {"numbers": {"review_required": True, "removed": [{"token": "12", "count": 1}] + ([{"token": "34", "count": 1}] if missed_removal else [])}}
            write_json(authentic_path, authentic)
            deai_path = root / "审查/section-chain/gates/deai.json"
            deai = json.loads(deai_path.read_text(encoding="utf-8"))
            deai["audit_reports"]["authentic_expression"]["sha256"] = sha256(authentic_path)
            deai["deduplication_review"] = {**deai["expression_review"], "retained_claims": [{"signal": "authentic_expression:integrity.categories.numbers.removed[0]", "removed_count": 1, "removed_location": "synthetic baseline duplicate", "retained_location": "synthetic retained result", "claim": "FIXTURE", "reason": "synthetic duplicate-only case"}]}
            write_json(deai_path, deai)
        result = evaluate_fixture(root, measurements={"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": PDF_SHA256}, content_result={"pass": True, "prewrite_ready": True, "content_complete": True, "errors": []})
    passed = (not result["pass"] and any("removal signals unresolved" in item for item in result["blockers"])) if missed_removal else (result["pass"] is True and result["recorded_deliverable"] is False and result["deliverable"] is True)
    return {"pass": passed, "actual_status": result["status"], "blockers": result["blockers"]}


def compilation_binding_case(field: str, value) -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-compilation-binding-fixture-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23)
        measurements = fixture_measurements(root, {"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": PDF_SHA256})
        measurements[field] = value
        result = GATE.evaluate(root, measurements=measurements, content_result={"pass": True, "prewrite_ready": True, "content_complete": True})
    return {"pass": not result["pass"] and any("compiled PDF" in error for error in result["blockers"]), "actual_status": result["status"], "blockers": result["blockers"]}


def changed_reviewed_source_case() -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-semantic-source-fixture-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23)
        evidence = root / "求解/参数来源.md"
        evidence.write_text("synthetic parameter 12.34 under specified conditions", encoding="utf-8")
        gate_path = root / "审查/section-chain/gates/deai.json"
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        semantic = gate["semantic_fact_review"]
        semantic["evidence"].append("求解/参数来源.md#given_parameter")
        semantic["evidence_sha256"]["求解/参数来源.md"] = sha256(evidence)
        write_json(gate_path, gate)
        kwargs = {"measurements": {"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": PDF_SHA256}, "content_result": {"pass": True, "prewrite_ready": True, "content_complete": True}}
        before = evaluate_fixture(root, **kwargs)
        evidence.write_text("synthetic parameter 99.99; original conditions no longer apply", encoding="utf-8")
        after = evaluate_fixture(root, **kwargs)
    return {"pass": before["pass"] and not after["pass"] and any("reviewed evidence hash" in item for item in after["blockers"]), "actual_status": after["status"], "blockers": after["blockers"]}


def manual_originality_case(action: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="cumcm-originality-review-fixture-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=23)
        report_path = root / "审查/优秀论文对标.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["similarity"]["status"] = "WARN_REVIEW"
        report["originality_gate"].update(verdict="PASS_WITH_MANUAL_REVIEW", manual_review_pass=True)
        basis = GATE.load_assurance_module().load_originality_module().compute_audit_basis(PDF_SHA256, report["similarity"])
        report["audit_basis_sha256"] = basis
        report["originality_gate"]["audit_basis_sha256"] = basis
        manual_path = root / "审查/原创性人工复核.json"
        manual = {"fixture": True, "pass": True, "reviewer": "synthetic fixture AI reviewer, not an actual approval", "reviewer_type": "ai", "scope": "synthetic overlapping-page review", "candidate_pdf_sha256": PDF_SHA256, "audit_basis_sha256": basis, "date": "2026-09-08", "reviewed_at": "2026-09-08T00:00:00Z", "full_text_read": True, "unresolved_issues": []}
        write_json(manual_path, manual)
        report["manual_review"] = manual
        report["manual_review_file"] = {"path": str(manual_path), "sha256": sha256(manual_path)}
        write_json(report_path, report)
        kwargs = {"measurements": {"body_pages": 23, "total_pdf_pages": 35, "pdf_sha256": PDF_SHA256}, "content_result": {"pass": True, "prewrite_ready": True, "content_complete": True}}
        before = evaluate_fixture(root, **kwargs)
        if action == "withdraw":
            write_json(manual_path, {**manual, "pass": False, "unresolved_issues": ["synthetic review withdrawn"]})
        elif action == "remove":
            manual_path.unlink()
        after = evaluate_fixture(root, **kwargs)
    passed = (before["pass"] and after["pass"] and "审查/原创性人工复核.json" in after["input_sha256"]) if action == "keep" else (before["pass"] and not after["pass"] and any("originality owner check" in item for item in after["blockers"]))
    return {"pass": passed, "actual_status": after["status"], "blockers": after["blockers"], "before_blockers": before["blockers"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/first-draft-gate-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    cases = {
        "short_complete_build_releases": case(
            12,
            "PASS_FIRST_DELIVERABLE_DRAFT",
        ),
        "short_build_with_real_gap_still_blocks": case(
            12,
            "BLOCK_FIRST_DELIVERABLE_INCOMPLETE",
            missing=["q2: 独立验证强度不足"],
            actions=["补充异构复算、阈值与结果解释"],
        ),
        "quota_revision_action_is_rejected": case(
            12,
            "BLOCK_FIRST_DELIVERABLE_INCOMPLETE",
            missing=["q2: 参数来源说明不足"],
            actions=["补 500 字背景"],
        ),
        "content_gap_blocks_before_pagination_release": case(
            23,
            "BLOCK_FIRST_DELIVERABLE_CONTENT_INCOMPLETE",
            content_complete=False,
        ),
        "prewrite_gap_blocks_before_pagination_release": case(
            23,
            "BLOCK_FIRST_DELIVERABLE_CONTENT_INCOMPLETE",
            prewrite_ready=False,
        ),
        "failed_draft_stage_blocks": case(
            23,
            "BLOCK_FIRST_DELIVERABLE_STAGE_INCOMPLETE",
            stage_status="fail",
        ),
        "official_range_with_content_and_stages_releases": case(
            23,
            "PASS_FIRST_DELIVERABLE_DRAFT",
        ),
        "over_limit_blocks": case(
            31,
            "CONTINUE_INTERNAL_BUILD_ABOVE_MAX",
        ),
        "stale_pdf_binding_blocks": stale_case(),
        "project_policy_cannot_relax_official_maximum": invalid_page_policy_case(),
        "closing_sections_must_exist_before_first_draft_release": incomplete_closing_stage_case(),
        "internal_failed_build_cannot_masquerade_as_draft": failed_build_cannot_masquerade_as_draft_case(),
        "old_content_only_build_is_not_deliverable": assurance_case("审查/section-chain/gates/deai.json", lambda x: x.pop("semantic_fact_review"), "semantic_fact_review review record is missing"),
        "missing_baseline_blocks": assurance_case("审查/deai-baseline/论文.tex", lambda p: p.unlink(), "baseline missing"),
        "changed_tex_requires_new_assurance": assurance_case("论文/论文.tex", lambda p: p.write_text(p.read_text(encoding="utf-8") + " changed fixture", encoding="utf-8"), "current source"),
        "changed_baseline_blocks": assurance_case("审查/deai-baseline/论文.tex", lambda p: p.write_text("different synthetic baseline", encoding="utf-8"), "baseline file hash is stale"),
        "unresolved_semantics_blocks": assurance_case("审查/section-chain/gates/deai.json", lambda x: x["semantic_fact_review"].update(unresolved_issues=["conditional claim became unconditional"]), "unresolved review issues"),
        "mechanical_scan_is_not_semantic_review": assurance_case("审查/section-chain/gates/deai.json", lambda x: x["semantic_fact_review"].update(sources_conditions_claim_strength_checked=False), "claim_strength_checked is incomplete"),
        "missing_reviewer_identity_blocks": assurance_case("审查/section-chain/gates/deai.json", lambda x: x["semantic_fact_review"].pop("reviewer_type"), "reviewer_type must distinguish"),
        "not_run_originality_blocks": assurance_case("审查/优秀论文对标.json", lambda x: x["similarity"].update(status="NOT_RUN"), "originality verdict is not accepted"),
        "stale_originality_blocks": assurance_case("审查/优秀论文对标.json", lambda x: x["candidate_pdf"].update(sha256="b" * 64), "originality candidate hash"),
        "partial_originality_blocks": assurance_case("审查/优秀论文对标.json", lambda x: x["similarity"]["coverage"].update(compared_count=1), "coverage is incomplete"),
        "abstract_only_originality_blocks": assurance_case("审查/优秀论文对标.json", lambda x: x.update(schema_version=1), "requires schema v2"),
        "rebound_old_language_scan_blocks": assurance_case("审查/section-chain/language-audit.json", lambda x: x["paper_source"].update(sha256="b" * 64), "intrinsic source hash", rebind_report="language-audit:language_scan"),
        "rebound_old_voice_scan_blocks": assurance_case("审查/section-chain/corpus-voice-audit.json", lambda x: x["paper_source"].update(sha256="b" * 64), "intrinsic source hash", rebind_report="deai:corpus_voice"),
        "integrity_not_run_blocks": assurance_case("审查/section-chain/authentic-expression-audit.json", lambda x: x["integrity"].update(status="NOT_RUN"), "protected-fact integrity", rebind_report="deai:authentic_expression"),
        "failed_integrity_cannot_be_signed_away": assurance_case("审查/section-chain/authentic-expression-audit.json", lambda x: x["integrity"].update(status="FAIL"), "protected-fact integrity", rebind_report="deai:authentic_expression"),
        "dedup_needs_retained_claim_review": assurance_case("审查/section-chain/authentic-expression-audit.json", lambda x: x["integrity"].update(status="REVIEW"), "deduplication_review", rebind_report="deai:authentic_expression"),
        "language_signal_needs_disposition": assurance_case("审查/section-chain/language-audit.json", lambda x: x["records"][0].update(soft=[{"pattern": "empty_praise"}]), "unresolved automatic signals", rebind_report="language-audit:language_scan"),
        "semantic_signal_needs_disposition": assurance_case("审查/section-chain/authentic-expression-audit.json", lambda x: x["semantic_review"].update(changes=[{"group": "strength"}]), "unresolved automatic signals", rebind_report="deai:authentic_expression"),
        "no_ai_usage_record_is_false_for_generated_draft": assurance_case("审查/section-chain/gates/language-audit.json", lambda x: x["ai_usage"].update(used=False), "ai_usage.used=true"),
        "no_ai_declaration_cannot_pass": assurance_case("论文/论文.tex", lambda p: p.write_text(p.read_text(encoding="utf-8").replace("本参赛队在竞赛过程中使用了AI工具", "本参赛队在竞赛过程中未使用任何AI工具"), encoding="utf-8"), "cannot claim no AI use"),
        "missing_ai_details_blocks": assurance_case("附件/AI工具使用详情.pdf", lambda p: p.unlink(), "AI usage details missing"),
        "ai_review_cannot_attest_participant_verification": assurance_case("审查/section-chain/gates/language-audit.json", lambda x: x["ai_usage"].update(participant_verification="completed"), "cannot certify participant"),
        "proper_signal_disposition_can_pass": reviewed_signal_case(),
        "reviewed_deduplication_can_pass": reviewed_signal_case(deduplication=True),
        "AI_internal_review_does_not_add_participant_checkpoint": reviewed_signal_case(participant_pending=True),
        "changed_evidence_matrix_reopens_semantics": assurance_case("求解/证据矩阵.csv", lambda p: p.write_text("claim_id,description\nFIXTURE,changed\n", encoding="utf-8"), "evidence-matrix hash is stale"),
        "changed_supporting_source_cannot_resign_old_semantic_review": changed_reviewed_source_case(),
        "unverified_compilation_blocks": compilation_binding_case("compilation_binding_verified", False),
        "current_tex_must_match_compiled_tex": compilation_binding_case("tex_sha256", "b" * 64),
        "missing_controlled_compilation_receipt_blocks": compilation_binding_case("compile_manifest", None),
        "missing_review_evidence_hash_blocks": assurance_case("审查/section-chain/gates/deai.json", lambda x: x["semantic_fact_review"].pop("evidence_sha256"), "reviewed evidence hash"),
        "missing_originality_basis_blocks": assurance_case("审查/优秀论文对标.json", lambda x: x.pop("audit_basis_sha256"), "originality owner check"),
        "every_protected_removal_requires_review": reviewed_signal_case(deduplication=True, missed_removal=True),
        "changed_originality_corpus_member_blocks": assurance_case("fixture-corpus/reference-1.pdf", lambda p: p.write_bytes(b"%PDF-changed-synthetic-reference"), "originality owner check"),
        "added_originality_corpus_member_blocks": assurance_case("fixture-corpus/reference-1.pdf", lambda p: p.with_name("reference-3.pdf").write_bytes(b"%PDF-new-synthetic-reference"), "originality owner check"),
        "missing_originality_corpus_snapshot_blocks": assurance_case("审查/优秀论文对标.json", lambda x: x.pop("corpus_source"), "originality owner check"),
        "bound_originality_review_can_pass": manual_originality_case("keep"),
        "withdrawn_originality_review_blocks": manual_originality_case("withdraw"),
        "removed_originality_review_blocks": manual_originality_case("remove"),
    }
    result = {"schema_version": 2, "fixture": True, "pass": all(item["pass"] for item in cases.values()), "case_count": len(cases), "cases": cases}
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(cases), "failed": [key for key, value in cases.items() if not value["pass"]]}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
