#!/usr/bin/env python3
"""Check existing, artifact-bound expression/originality/AI-use review records.

This module verifies records, not the truth of a reviewer's judgement.  It never
creates approvals, participant attestations, or estimates AI authorship.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any


TEX_REL = "论文/论文.tex"
MATRIX_REL = "求解/证据矩阵.csv"
ORIGINALITY_REL = "审查/优秀论文对标.json"
GATES = {name: f"审查/section-chain/gates/{name}.json" for name in ("deai", "language-audit")}


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def normalized_digest(path: Path) -> str | None:
    # audit_authentic_expression hashes decoded text, including newline normalization.
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def object_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def load_originality_module():
    script = Path(__file__).resolve().parents[2] / "cumcm" / "scripts" / "benchmark_corpus.py"
    spec = importlib.util.spec_from_file_location("originality_for_first_draft", script)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate_assurance(root: Path, pdf_sha256: str | None) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    inputs: dict[str, str] = {}
    tex = root / TEX_REL
    tex_sha256 = digest(tex)

    def fail(message: str) -> None:
        errors.append(f"first-draft assurance: {message}")

    def local_path(value: Any, label: str) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            fail(f"{label} requires a project-relative file path")
            return None
        path = (root / value).resolve()
        if not path.is_relative_to(root) or Path(value).is_absolute():
            fail(f"{label} must stay within the project")
            return None
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"{label} missing or empty: {value}")
            return None
        inputs[path.relative_to(root).as_posix()] = digest(path)  # type: ignore[assignment]
        return path

    def read_record(relative: str, label: str) -> dict[str, Any]:
        path = local_path(relative, label)
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path else None
        except (OSError, ValueError):
            data = None
        if not isinstance(data, dict):
            fail(f"{label} must be a readable JSON object")
            return {}
        return data

    def bound_file(ref: Any, label: str) -> Path | None:
        if not isinstance(ref, dict):
            fail(f"{label} requires path and sha256")
            return None
        path = local_path(ref.get("path"), label)
        if path and ref.get("sha256") != digest(path):
            fail(f"{label} file hash is stale")
        return path

    def bound_report(gate: dict[str, Any], key: str) -> dict[str, Any]:
        refs = gate.get("audit_reports")
        ref = refs.get(key) if isinstance(refs, dict) else None
        path = bound_file(ref, f"{key} report")
        return read_record(path.relative_to(root).as_posix(), key) if path else {}

    def reviewed(record: Any, label: str, *, semantic: bool = False) -> None:
        if not isinstance(record, dict):
            fail(f"{label} review record is missing")
            return
        for key in ("pass", "full_text_read"):
            if record.get(key) is not True:
                fail(f"{label}.{key} must be an explicit review decision")
        for key in ("reviewer", "reviewed_at", "scope"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                fail(f"{label}.{key} is missing")
        if record.get("reviewer_type") not in {"ai", "participant"}:
            fail(f"{label}.reviewer_type must distinguish ai from participant")
        if record.get("unresolved_issues") != []:
            fail(f"{label} has missing or unresolved review issues")
        evidence = record.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            fail(f"{label} requires concrete evidence locators")
        else:
            for locator in evidence:
                parts = locator.split("#", 1) if isinstance(locator, str) else []
                if len(parts) != 2 or not parts[1].strip():
                    fail(f"{label} evidence must use file#specific-anchor")
                else:
                    evidence_path = local_path(parts[0], f"{label} evidence")
                    if evidence_path:
                        relative = evidence_path.relative_to(root).as_posix()
                        reviewed_hashes = object_value(record.get("evidence_sha256"))
                        if reviewed_hashes.get(relative) != digest(evidence_path):
                            fail(f"{label} reviewed evidence hash is missing or stale: {relative}")
        if semantic:
            for key in ("evidence_matrix_checked", "sources_conditions_claim_strength_checked"):
                if record.get(key) is not True:
                    fail(f"{label}.{key} is incomplete")

    def resolutions(record: dict[str, Any], expected: list[str], label: str) -> None:
        rows = record.get("signal_resolutions", [])
        covered: set[str] = set()
        if not isinstance(rows, list):
            fail(f"{label}.signal_resolutions must be a list")
            rows = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("signal"), str):
                fail(f"{label} has an invalid signal disposition")
                continue
            if row.get("disposition") not in {"retained", "rewritten", "moved", "verified"} or not str(row.get("reason") or "").strip():
                fail(f"{label} disposition lacks a decision and technical reason")
            else:
                covered.add(row["signal"])
        missing = sorted(set(expected) - covered)
        if missing:
            fail(f"{label} has unresolved automatic signals: {', '.join(missing[:12])}")

    def scan_binding(report: dict[str, Any], label: str) -> list[str]:
        source = report.get("paper_source")
        if not isinstance(source, dict) or source.get("path") != TEX_REL or source.get("sha256") != tex_sha256:
            fail(f"{label} intrinsic source hash does not match current source")
        if report.get("pass") is not True or report.get("hard_count") != 0 or report.get("missing_files") != []:
            fail(f"{label} mechanical scan is incomplete or has hard failures")
        records = report.get("records")
        if not isinstance(records, list) or not any(isinstance(row, dict) and str(row.get("file", "")).replace("\\", "/") == TEX_REL and not row.get("skipped") for row in records):
            fail(f"{label} did not scan the single manuscript")
            records = []
        return [f"{label}:records[{i}].soft[{j}]" for i, row in enumerate(records) if isinstance(row, dict) for j, _ in enumerate(list_value(row.get("soft")))]

    local_path(TEX_REL, "single manuscript")
    local_path(MATRIX_REL, "evidence matrix")
    gates = {stage: read_record(path, f"{stage} gate") for stage, path in GATES.items()}
    for stage, gate in gates.items():
        if gate.get("status") != "pass" or gate.get("blocking_issues") != []:
            fail(f"{stage} stage is not complete")
        if gate.get("tex_sha256") != tex_sha256 or not tex_sha256:
            fail(f"{stage} gate hash does not match current source")
        if gate.get("pdf_sha256") != pdf_sha256 or not pdf_sha256:
            fail(f"{stage} gate hash does not match current PDF")

    deai, language = gates["deai"], gates["language-audit"]
    baseline = bound_file(deai.get("baseline"), "frozen deai baseline")
    if baseline == tex:
        fail("frozen deai baseline must be a separate pre-rewrite snapshot")
    if deai.get("evidence_matrix_sha256") != digest(root / MATRIX_REL):
        fail("semantic review evidence-matrix hash is stale")
    authentic = bound_report(deai, "authentic_expression")
    integrity = authentic.get("integrity") if isinstance(authentic.get("integrity"), dict) else {}
    if authentic.get("schema_version") != 2 or not isinstance(object_value(authentic.get("expression_review")).get("findings"), list) or not isinstance(object_value(authentic.get("semantic_review")).get("changes"), list):
        fail("authentic-expression report is incomplete or uses an unsupported schema")
    if authentic.get("paper_sha256") != normalized_digest(tex) or not authentic.get("paper_sha256"):
        fail("authentic-expression intrinsic hash does not match current source")
    if not baseline or integrity.get("baseline_sha256") != normalized_digest(baseline):
        fail("authentic-expression baseline hash is missing or stale")
    if integrity.get("status") not in {"PASS", "REVIEW"}:
        fail("protected-fact integrity requires a baseline and no unresolved failure")
    semantic = deai.get("semantic_fact_review")
    reviewed(semantic, "semantic_fact_review", semantic=True)
    semantic_signals = list_value(object_value(authentic.get("semantic_review")).get("changes"))
    resolutions(semantic if isinstance(semantic, dict) else {}, [f"authentic_expression:semantic_review.changes[{i}]" for i, _ in enumerate(semantic_signals)], "semantic_fact_review")
    voice = bound_report(deai, "corpus_voice")
    style_signals = scan_binding(voice, "corpus_voice")
    expression = object_value(authentic.get("expression_review"))
    style_signals.extend(f"authentic_expression:expression_review.findings[{i}]" for i, _ in enumerate(list_value(expression.get("findings"))))
    prose_review = deai.get("expression_review")
    reviewed(prose_review, "expression_review")
    resolutions(prose_review if isinstance(prose_review, dict) else {}, style_signals, "expression_review")
    if integrity.get("status") == "REVIEW":
        dedup = deai.get("deduplication_review")
        reviewed(dedup, "deduplication_review")
        rows = dedup.get("retained_claims") if isinstance(dedup, dict) else None
        if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) or any(not str(row.get(key) or "").strip() for key in ("removed_location", "retained_location", "claim", "reason")) for row in rows):
            fail("deduplication_review requires removed/retained locations, preserved claims and reasons")
        expected_removals: dict[str, int] = {}
        for category, value in object_value(integrity.get("categories")).items():
            item = object_value(value)
            if item.get("review_required") is not True:
                continue
            for index, removed in enumerate(list_value(item.get("removed"))):
                count = object_value(removed).get("count")
                signal = f"authentic_expression:integrity.categories.{category}.removed[{index}]"
                if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                    fail(f"deduplication integrity signal has an invalid count: {signal}")
                else:
                    expected_removals[signal] = count
        if not expected_removals:
            fail("deduplication REVIEW has no valid protected-fact removal signals")
        covered_removals: set[str] = set()
        for row in list_value(rows):
            item = object_value(row)
            signal = item.get("signal")
            if not isinstance(signal, str) or signal not in expected_removals or item.get("removed_count") != expected_removals[signal] or isinstance(item.get("removed_count"), bool):
                fail("deduplication_review removal signal/count does not match the integrity report")
            elif signal in covered_removals:
                fail(f"deduplication_review has a duplicate removal signal: {signal}")
            else:
                covered_removals.add(signal)
        if set(expected_removals) - covered_removals:
            fail("deduplication_review leaves protected-fact removal signals unresolved")

    scan = bound_report(language, "language_scan")
    language_signals = scan_binding(scan, "language_scan")
    review = language.get("manual_review")
    reviewed(review, "language manual_review")
    resolutions(review if isinstance(review, dict) else {}, language_signals, "language manual_review")

    originality = read_record(ORIGINALITY_REL, "originality audit")
    comparison = object_value(originality.get("similarity"))
    coverage = object_value(comparison.get("coverage"))
    decision = object_value(originality.get("originality_gate"))
    candidate = object_value(originality.get("candidate_pdf"))
    if originality.get("schema_version") != 2:
        fail("originality audit requires schema v2 full-corpus coverage")
    if not isinstance(candidate, dict) or candidate.get("sha256") != pdf_sha256 or not isinstance(decision, dict) or decision.get("candidate_pdf_sha256") != pdf_sha256:
        fail("originality candidate hash does not match current PDF")
    eligible = coverage.get("eligible_count")
    if coverage.get("scope") != "all_local_corpus_pdfs" or coverage.get("complete") is not True or coverage.get("candidate_complete") is not True or not isinstance(eligible, int) or isinstance(eligible, bool) or eligible < 1 or coverage.get("compared_count") != eligible or coverage.get("incomplete_references"):
        fail("originality full-text corpus coverage is incomplete or NOT_RUN")
    if comparison.get("status") not in {"PASS", "WARN_REVIEW"} or decision.get("coverage_complete") is not True or decision.get("verdict") not in {"PASS", "PASS_WITH_MANUAL_REVIEW"}:
        fail("originality verdict is not accepted")
    for issue in load_originality_module().originality_report_issues(originality, root / "论文/论文.pdf"):
        fail(f"originality owner check: {issue}")
    manual_ref = object_value(originality.get("manual_review_file"))
    if isinstance(manual_ref.get("path"), str) and manual_ref["path"].strip():
        manual_path = (root / manual_ref["path"]).resolve()
        # The owner also rechecks external review files. Keep project-local review
        # files in the release snapshot so withdrawal cannot leave a green checkpoint.
        if manual_path.is_relative_to(root) and manual_path.is_file():
            inputs[manual_path.relative_to(root).as_posix()] = digest(manual_path)  # type: ignore[assignment]

    usage = language.get("ai_usage")
    participant_status = "pending"
    if not isinstance(usage, dict) or usage.get("used") is not True:
        fail("AI-assisted generated draft must truthfully record ai_usage.used=true")
    else:
        if usage.get("disclosure_checked") is not True or usage.get("details_checked") is not True:
            fail("AI disclosure and actual-use detail review are incomplete")
        detail = bound_file(usage.get("details"), "AI usage details")
        if detail and (detail.name != "AI工具使用详情.pdf" or not detail.is_relative_to(root / "附件") or not detail.read_bytes().startswith(b"%PDF-")):
            fail("AI usage details must be a PDF named 附件/.../AI工具使用详情.pdf")
        state = read_record(".cumcm_state.json", "workflow state")
        # Stage/status updates are not content changes. Recheck the mode each run,
        # but do not make unrelated workflow bookkeeping invalidate prose reviews.
        inputs.pop(".cumcm_state.json", None)
        participant_status = usage.get("participant_verification", "missing")
        simulation = object_value(state.get("workflow_policy")).get("mode") == "simulation"
        if participant_status not in {"pending", "not_applicable_simulation"} or (participant_status == "not_applicable_simulation" and not simulation):
            fail("first-draft AI review cannot certify participant final verification")
    if tex.is_file():
        source_text = "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in tex.read_text(encoding="utf-8").splitlines())
        markers = [source_text.find(r"\label{" + key + "}") for key in ("body:start", "ai-statement:start", "references:start", "appendix:start")]
        if any(position < 0 for position in markers) or markers != sorted(markers):
            fail("AI declaration must appear between main body and references")
        else:
            statement = source_text[markers[1]:markers[2]]
            if re.search(r"未使用(?:任何)?\s*(?:AI|人工智能)\s*工具", statement) or "本参赛队在竞赛过程中使用了AI工具" not in re.sub(r"\s", "", statement):
                fail("AI-assisted generated draft cannot claim no AI use or omit actual-use declaration")

    return {"pass": not errors, "errors": errors, "input_sha256": inputs,
            "tex_sha256": tex_sha256, "participant_verification": participant_status,
            "review_scope": "internal first-draft assurance; AI review is not participant verification or final submission approval"}
