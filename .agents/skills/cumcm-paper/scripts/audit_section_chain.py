#!/usr/bin/env python3
"""Validate CUMCM section-chain manifest and stage gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


REQUIRED_STAGES = [
    "outline",
    "restatement",
    "analysis",
    "assumptions",
    "notation",
    "model-writing",
    "results-validation",
    "evaluation",
    "references",
    "abstract",
    "language-audit",
]
OPTIONAL_STAGES = ["appendix"]
FIRST_DRAFT_GATE_REL = "审查/首份可交付初稿门禁.json"
FORMULA_READABILITY_REL = "审查/公式可读性审计.json"
ALLOWED_QUESTION_ROLES = {"core", "support", "transition"}
ALLOWED_CHAIN_TYPES = {
    "foundational-mechanism",
    "critical-feasibility",
    "boundary-optimization",
    "composite-piecewise",
    "capacity-upper-bound",
    "experimental-inference",
    "sequential-decision",
    "spatial-layout",
    "uncertainty-feedback",
    "custom",
}
ALLOWED_PROGRESSION_AXES = {
    "foundation",
    "mechanism-regime",
    "information-state",
    "actor-count",
    "spatial-fidelity",
    "parameter-uncertainty",
    "independent",
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def generic_question_title(value: object) -> bool:
    """Reject per-question headings that name only the question and a generic action."""
    if not isinstance(value, str):
        return False
    compact = re.sub(r"[\s：:、，,。；;]+", "", value)
    return bool(re.fullmatch(
        r"问题[一二三四五六七八九十\d]+(?:的)?(?:模型的?)?"
        r"(?:建立与求解|建模与求解|求解与分析|模型求解|求解)",
        compact,
    ))


def validate_question_architecture(manifest: dict) -> list[str]:
    errors: list[str] = []
    question_ids = manifest.get("question_ids")
    architecture = manifest.get("question_architecture")
    if not isinstance(question_ids, list) or not question_ids:
        return errors
    if not isinstance(architecture, dict):
        return ["question_architecture must be an object"]
    if set(architecture) != set(question_ids):
        errors.append("question_architecture must cover each question_id exactly once")
    for question_id in question_ids:
        item = architecture.get(question_id)
        label = f"question_architecture.{question_id}"
        if not isinstance(item, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        if item.get("role") not in ALLOWED_QUESTION_ROLES:
            errors.append(f"{label}: invalid role")
        chain_type = item.get("chain_type")
        if chain_type not in ALLOWED_CHAIN_TYPES:
            errors.append(f"{label}: invalid chain_type")
        if item.get("progression_axis") not in ALLOWED_PROGRESSION_AXES:
            errors.append(f"{label}: invalid progression_axis")
        if not nonempty_text(item.get("route_summary")):
            errors.append(f"{label}: route_summary is empty")
        subsections = item.get("planned_subsections")
        if not isinstance(subsections, list):
            errors.append(f"{label}: planned_subsections must be a list")
        elif any(not nonempty_text(value) for value in subsections):
            errors.append(f"{label}: planned_subsections contains an empty title")
        elif len(subsections) != len(set(subsections)):
            errors.append(f"{label}: planned_subsections contains duplicate titles")
        elif any(generic_question_title(value) for value in subsections):
            errors.append(
                f"{label}: planned_subsections must not repeat the question number and generic chapter action"
            )
        if chain_type == "custom" and not nonempty_text(item.get("custom_chain")):
            errors.append(f"{label}: custom_chain is required for custom chain_type")
        inheritance = item.get("inheritance")
        if not isinstance(inheritance, dict):
            errors.append(f"{label}: inheritance must be an object")
            continue
        status = inheritance.get("status")
        objects = inheritance.get("objects")
        if status not in {"none", "used"}:
            errors.append(f"{label}: inheritance.status must be none or used")
        if not isinstance(objects, list):
            errors.append(f"{label}: inheritance.objects must be a list")
        elif status == "none" and objects:
            errors.append(f"{label}: inheritance none requires no objects")
        elif status == "used" and not objects:
            errors.append(f"{label}: inheritance used requires objects")
    return errors


def validate_gate(root: Path, stage: str, spec: dict) -> list[str]:
    errors: list[str] = []
    gate_rel = spec.get("gate")
    if not gate_rel:
        return [f"{stage}: missing gate path"]
    gate_path = root / gate_rel
    if not gate_path.exists():
        return [f"{stage}: gate not found: {gate_rel}"]
    try:
        gate = read_json(gate_path)
    except Exception as exc:  # noqa: BLE001
        return [f"{stage}: invalid gate JSON: {exc}"]
    if gate.get("schema_version") != 1:
        errors.append(f"{stage}: gate schema_version must be 1")
    if gate.get("stage") != stage:
        errors.append(f"{stage}: gate stage mismatch")
    if gate.get("status") != "pass":
        errors.append(f"{stage}: status is not pass")
    if gate.get("blocking_issues"):
        errors.append(f"{stage}: blocking_issues is not empty")
    checks = gate.get("checks", [])
    if not checks:
        errors.append(f"{stage}: no checks recorded")
    for check in checks:
        if not check.get("id") or check.get("pass") is not True or not check.get("evidence"):
            errors.append(f"{stage}: incomplete or failed check: {check.get('id', '<missing>')}")
    source_files = spec.get("source_files", gate.get("source_files", []))
    if stage not in {"outline", "language-audit"} and not source_files:
        errors.append(f"{stage}: no source_files recorded")
    for item in source_files:
        if not (root / item).exists():
            errors.append(f"{stage}: source file not found: {item}")
    return errors


def validate_cross_audit(root: Path, kind: str) -> list[str]:
    """Require a passing, current automatic audit for each used visual family."""
    errors: list[str] = []
    report_rel = f"审查/{kind}-style-audit.json"
    registry_rel = f"审查/{kind}-registry.json"
    report_path = root / report_rel
    registry_path = root / registry_rel
    if not registry_path.exists():
        errors.append(f"{kind}: registry not found: {registry_rel}")
        return errors
    if not report_path.exists():
        errors.append(f"{kind}: automatic style audit report not found: {report_rel}")
        return errors
    try:
        report = read_json(report_path)
    except Exception as exc:  # noqa: BLE001
        return [f"{kind}: invalid automatic style audit report: {exc}"]
    if report.get("schema_version") != 1:
        errors.append(f"{kind}: style audit schema_version must be 1")
    if report.get("pass") is not True:
        errors.append(f"{kind}: automatic style audit did not pass")
    if report.get("registry") != registry_rel:
        errors.append(f"{kind}: style audit registry mismatch")
    count_key = "figure_count" if kind == "figure" else "diagram_count"
    if not isinstance(report.get(count_key), int) or report.get(count_key) < 1:
        errors.append(f"{kind}: style audit contains no checked visuals")
    if report_path.stat().st_mtime < registry_path.stat().st_mtime:
        errors.append(f"{kind}: style audit is older than its registry")
    return errors


def validate_first_draft_gate(root: Path) -> list[str]:
    """Require the first-deliverable checkpoint and reject failed-build identity drift."""
    path = root / FIRST_DRAFT_GATE_REL
    if not path.exists():
        return [f"first-draft gate not found: {FIRST_DRAFT_GATE_REL}"]
    try:
        gate = read_json(path)
    except Exception as exc:  # noqa: BLE001
        return [f"invalid first-draft gate JSON: {exc}"]
    errors: list[str] = []
    if gate.get("schema_version") != 1:
        errors.append("first-draft gate schema_version must be 1")
    if gate.get("status") != "PASS_FIRST_DELIVERABLE_DRAFT" or gate.get("pass") is not True:
        errors.append(f"first-draft gate did not release: {gate.get('status')}")
    if gate.get("build_status") != "FIRST_DRAFT_CANDIDATE":
        errors.append("first-draft gate build_status is not FIRST_DRAFT_CANDIDATE")
    if gate.get("deliverable") is not True:
        errors.append("first-draft gate deliverable flag is not true")
    if gate.get("blockers"):
        errors.append("first-draft gate still contains blockers")
    pdf = root / "论文" / "论文.pdf"
    if not pdf.exists() or pdf.stat().st_size == 0:
        errors.append("first-draft gate cannot be bound: 论文/论文.pdf missing or empty")
    else:
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if gate.get("pdf_sha256") != digest:
            errors.append("first-draft gate PDF hash does not match current 论文/论文.pdf")
    high = gate.get("hard_max")
    if not isinstance(high, int) or isinstance(high, bool) or not (1 <= high <= 30):
        errors.append("first-draft gate page policy exceeds the official 30-page maximum")
    return errors


def validate_formula_readability(root: Path) -> list[str]:
    """Bind the formula-readability PASS to the current single TeX manuscript."""
    report_path = root / FORMULA_READABILITY_REL
    tex_path = root / "论文" / "论文.tex"
    if not report_path.exists():
        return [f"formula-readability audit not found: {FORMULA_READABILITY_REL}"]
    try:
        report = read_json(report_path)
    except Exception as exc:  # noqa: BLE001
        return [f"invalid formula-readability audit JSON: {exc}"]
    errors: list[str] = []
    if report.get("schema_version") != 1:
        errors.append("formula-readability audit schema_version must be 1")
    if report.get("pass") is not True or report.get("unresolved_count") != 0:
        errors.append("formula-readability audit has unresolved risks")
    if not tex_path.exists():
        errors.append("formula-readability audit cannot be bound: 论文/论文.tex missing")
    else:
        digest = hashlib.sha256(tex_path.read_bytes()).hexdigest()
        if report.get("tex_sha256") != digest:
            errors.append("formula-readability audit TeX hash does not match current 论文/论文.tex")
    ledger_path = root / "审查" / "公式可读性处置.json"
    ledger_digest = hashlib.sha256(ledger_path.read_bytes()).hexdigest() if ledger_path.exists() else None
    if report.get("resolution_ledger_sha256") != ledger_digest:
        errors.append("formula-readability disposition ledger changed after the audit")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default="审查/section-chain/manifest.json")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    manifest_path = root / args.manifest
    errors: list[str] = []
    if not manifest_path.exists():
        errors.append(f"manifest not found: {args.manifest}")
        manifest = {}
    else:
        try:
            manifest = read_json(manifest_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid manifest JSON: {exc}")
            manifest = {}

    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if not manifest.get("question_ids"):
        errors.append("manifest question_ids is empty")
    errors.extend(validate_question_architecture(manifest))
    stages = manifest.get("stages", {})
    for stage in REQUIRED_STAGES:
        spec = stages.get(stage)
        if not spec:
            errors.append(f"missing stage: {stage}")
            continue
        errors.extend(validate_gate(root, stage, spec))
    for stage in OPTIONAL_STAGES:
        spec = stages.get(stage)
        if spec and spec.get("applicable", True) is not False:
            errors.extend(validate_gate(root, stage, spec))

    errors.extend(validate_first_draft_gate(root))
    errors.extend(validate_formula_readability(root))

    cross = manifest.get("cross_cutting", {})
    for flag, stage in (("figures_used", "figures"), ("diagrams_used", "diagrams")):
        if cross.get(flag):
            spec = stages.get(stage, {"gate": f"审查/section-chain/gates/{stage}.json"})
            errors.extend(validate_gate(root, stage, spec))
            kind = "figure" if stage == "figures" else "diagram"
            errors.extend(validate_cross_audit(root, kind))

    auto_language = root / "审查" / "section-chain" / "language-audit.json"
    if not auto_language.exists():
        errors.append("automatic language audit report not found")
    else:
        try:
            if read_json(auto_language).get("pass") is not True:
                errors.append("automatic language audit did not pass")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"invalid automatic language audit report: {exc}")

    result = {
        "schema_version": 1,
        "pass": not errors,
        "manifest": args.manifest,
        "required_stages": REQUIRED_STAGES,
        "optional_stages": OPTIONAL_STAGES,
        "first_draft_gate": FIRST_DRAFT_GATE_REL,
        "formula_readability_audit": FORMULA_READABILITY_REL,
        "errors": errors,
    }
    out_dir = root / "审查" / "section-chain"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "chain-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = ["# 章节技能链审计", "", f"- 结果：{'PASS' if result['pass'] else 'FAIL'}", ""]
    if errors:
        lines.extend(["## 阻断项", "", *[f"- {item}" for item in errors], ""])
    else:
        lines.extend(["全部阶段门禁、源文件和语言审计均已通过。", ""])
    (out_dir / "chain-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "error_count": len(errors)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
