#!/usr/bin/env python3
"""Audit question-level substance and bind pagination feedback to the compiled PDF."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_MANIFEST = "审查/逐问深度清单.json"
DEFAULT_REPORT = "审查/正文深度审计.json"
MANUSCRIPT_REL = "论文/论文.tex"
ALLOWED_RISK_TYPES = {
    "sensitivity",
    "robustness",
    "convergence",
    "constraint-boundary",
    "uncertainty",
    "failure-boundary",
}
ALLOWED_QUESTION_ROLES = {"core", "support", "transition"}
ALLOWED_PROGRESSION_AXES = {
    "foundation",
    "mechanism-regime",
    "information-state",
    "actor-count",
    "spatial-fidelity",
    "parameter-uncertainty",
    "independent",
}
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
ALLOWED_PRESENTATION_MEDIA = {"prose", "formula", "table", "figure", "diagram"}
SEARCH_SCOPE_REQUIRED_CHAIN_TYPES = {
    "critical-feasibility",
    "boundary-optimization",
    "capacity-upper-bound",
}
ACTIVE_CONSTRAINT_REQUIRED_CHAIN_TYPES = {
    "boundary-optimization",
    "capacity-upper-bound",
}
SEARCH_SCOPE_FIELDS = ("basis", "resulting_scope", "boundary_or_counterexample_check")
ACTIVE_CONSTRAINT_FIELDS = (
    "active_constraints",
    "slack_or_multiplier",
    "neighborhood_check",
    "outside_or_counterexample",
)
COMPONENT_FIELDS = {
    "model_specific_derivation": ("summary",),
    "parameter_sources": ("summary",),
    "solver_contract": ("precision", "stopping_condition", "boundary_handling"),
    "result_interpretation": ("key_result", "mechanism", "answer_impact"),
    "independent_validation": (
        "method",
        "independence",
        "metric",
        "threshold",
        "observed",
    ),
    "stress_or_failure_boundary": ("type", "range_or_case", "observed_effect", "decision"),
}
BASE_RESPONSIBILITIES = (
    "requirements",
    "model_specific_derivation",
    "parameter_sources",
    "solver_contract",
    "result_interpretation",
    "independent_validation",
    "stress_or_failure_boundary",
    "final_answer_mapping",
)
CONDITIONAL_RESPONSIBILITIES = (
    "search_scope_justification",
    "active_constraint_check",
)
GENERIC_EVIDENCE = {"已检查", "已完成", "见正文", "正文", "通过", "pass", "ok"}
GENERIC_TASKS = {"完成", "已完成", "写清", "说明", "见证据", "见求解", "pass", "ok"}
GENERIC_SUBSECTIONS = {
    "模型的建立与求解",
    "模型建立与求解",
    "问题分析",
    "结果分析",
    "模型检验",
}
QUOTA_MARKERS = ("页数", "字数", "图数", "公式数", "写满", "凑页", "幅图", "页正文")
QUOTA_AMOUNT_RE = re.compile(
    r"(?:[0-9０-９]+(?:\.[0-9０-９]+)?|[一二两三四五六七八九十百千]+)\s*"
    r"(?:页|字|张图|幅图|个公式|条公式|张图表|幅图表)"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int | None:
    try:
        try:
            from pypdf import PdfReader  # type: ignore
        except ImportError:
            try:
                from PyPDF2 import PdfReader  # type: ignore
            except ImportError:
                import fitz  # type: ignore
                with fitz.open(path) as document:
                    return len(document)
        return len(PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        return None


def label_page(aux_text: str, label: str) -> int | None:
    pattern = rf"\\newlabel\{{{re.escape(label)}\}}\{{\{{[^}}]*\}}\{{(\d+)\}}"
    match = re.search(pattern, aux_text)
    return int(match.group(1)) if match else None


def page_policy(root: Path) -> int:
    state_path = root / ".cumcm_state.json"
    if state_path.exists():
        try:
            policy = read_json(state_path).get("page_policy", {})
            high = policy.get("body_page_max")
            if isinstance(high, int) and not isinstance(high, bool) and 1 <= high <= 30:
                return high
        except Exception:  # noqa: BLE001
            pass
    return 30


def measure_compilation(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    pdf = root / "论文" / "论文.pdf"
    aux = root / "论文" / "论文.aux"
    if not pdf.exists() or pdf.stat().st_size == 0:
        errors.append("compiled PDF missing or empty: 论文/论文.pdf")
    if not aux.exists():
        errors.append("compiled AUX missing: 论文/论文.aux")
    if errors:
        return None, errors
    aux_text = aux.read_text(encoding="utf-8", errors="ignore")
    body_start = label_page(aux_text, "body:start")
    appendix_start = label_page(aux_text, "appendix:start")
    references_start = label_page(aux_text, "references:start")
    if body_start is None:
        errors.append("body:start label missing from 论文/论文.aux")
    if appendix_start is None:
        errors.append("appendix:start label missing from 论文/论文.aux")
    if body_start is not None and appendix_start is not None and appendix_start <= body_start:
        errors.append("appendix:start must be later than body:start")
    total_pages = pdf_page_count(pdf)
    if total_pages is None:
        errors.append("PDF page count unavailable; requires pypdf, PyPDF2 or PyMuPDF")
    if total_pages is not None:
        for label, page in (("body:start", body_start), ("appendix:start", appendix_start), ("references:start", references_start)):
            if page is not None and not 1 <= page <= total_pages:
                errors.append(f"{label} label falls outside the actual PDF")
    owner = Path(__file__).resolve().with_name("compile_paper.py")
    spec = importlib.util.spec_from_file_location("cumcm_compile_binding", owner)
    if spec is None or spec.loader is None:
        errors.append("compiled source receipt verifier unavailable")
        binding = {}
    else:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        binding, binding_errors = module.verify_compilation(root)
        errors.extend(binding_errors)
    if errors:
        return None, errors
    assert body_start is not None and appendix_start is not None and total_pages is not None
    return {
        **binding,
        "body_pages": appendix_start - body_start,
        "total_pdf_pages": total_pages,
        "body_start_page": body_start,
        "appendix_start_page": appendix_start,
        "references_start_page": references_start,
        "pdf_sha256": sha256_file(pdf),
        "pdf": "论文/论文.pdf",
    }, []


def normalized_locator_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def evidence_errors(
    values: Any,
    root: Path,
    label: str,
    *,
    require_manuscript: bool = False,
    forbid_manuscript: bool = False,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(values, list) or not values:
        return [f"{label}: evidence must be a non-empty list"]
    has_manuscript = False
    for index, value in enumerate(values, start=1):
        item_label = f"{label}.evidence[{index}]"
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{item_label}: evidence locator is empty")
            continue
        locator = value.strip()
        if locator.lower() in GENERIC_EVIDENCE:
            errors.append(f"{item_label}: generic evidence is not auditable: {locator}")
            continue
        if "#" not in locator:
            errors.append(f"{item_label}: use relative-path#specific-anchor")
            continue
        relative, anchor = locator.split("#", 1)
        if not relative.strip() or not anchor.strip():
            errors.append(f"{item_label}: both path and anchor are required")
            continue
        normalized_path = normalized_locator_path(relative)
        is_manuscript = normalized_path == MANUSCRIPT_REL
        has_manuscript = has_manuscript or is_manuscript
        if forbid_manuscript and normalized_path.startswith("论文/"):
            errors.append(
                f"{item_label}: prewrite source evidence cannot come from the manuscript"
            )
        evidence_path = Path(relative.strip())
        if evidence_path.is_absolute():
            errors.append(f"{item_label}: evidence path must be project-relative")
        elif not (root / evidence_path).is_file():
            errors.append(f"{item_label}: evidence file not found: {relative.strip()}")
        if anchor.strip().lower() in GENERIC_EVIDENCE:
            errors.append(f"{item_label}: anchor is not specific: {anchor.strip()}")
    if require_manuscript and not has_manuscript:
        errors.append(f"{label}: completed responsibility needs a {MANUSCRIPT_REL}#specific-anchor locator")
    return errors


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def substantive_task_errors(value: Any, label: str) -> list[str]:
    if not nonempty_text(value):
        return [f"{label}: substantive_task is empty"]
    text = value.strip()
    errors: list[str] = []
    if text.lower() in GENERIC_TASKS:
        errors.append(f"{label}: substantive_task is generic rather than question-specific")
    marker = next((item for item in QUOTA_MARKERS if item in text), None)
    if marker is not None:
        errors.append(f"{label}: substantive_task contains a pagination/content quota marker: {marker}")
    amount = QUOTA_AMOUNT_RE.search(text)
    if amount is not None:
        errors.append(
            f"{label}: substantive_task contains a numeric pagination/content quota: {amount.group(0)}"
        )
    return errors


def validate_readiness_item(
    root: Path,
    label: str,
    value: Any,
    *,
    allow_not_applicable: bool,
    required: bool,
) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label}: readiness item must be an object"]
    errors: list[str] = []
    status = value.get("status")
    allowed = {"ready", "not-applicable"} if allow_not_applicable else {"ready"}
    if status not in allowed:
        errors.append(f"{label}: status must be {' or '.join(sorted(allowed))}")
        return errors
    if required and status != "ready":
        errors.append(f"{label}: this question structure requires status ready")
        return errors
    if status == "not-applicable":
        if not nonempty_text(value.get("reason")):
            errors.append(f"{label}: structural not-applicable requires a reason")
        return errors
    errors.extend(substantive_task_errors(value.get("substantive_task"), label))
    errors.extend(
        evidence_errors(
            value.get("source_evidence"),
            root,
            label,
            forbid_manuscript=True,
        )
    )
    return errors


def validate_prewrite_readiness(
    root: Path,
    question_id: str,
    value: Any,
    *,
    search_scope_required: bool,
    active_constraint_required: bool,
    search_scope_applicable: bool,
    active_constraint_applicable: bool,
) -> list[str]:
    label = f"{question_id}.prewrite_readiness"
    if not isinstance(value, dict):
        return [f"{label}: prewrite_readiness must be an object"]
    errors: list[str] = []
    if value.get("status") != "ready":
        errors.append(f"{label}: status must be ready before manuscript drafting")
    gaps = value.get("blocking_gaps")
    if not isinstance(gaps, list):
        errors.append(f"{label}: blocking_gaps must be a list")
    elif gaps:
        errors.append(f"{label}: blocking_gaps must be empty before manuscript drafting")

    responsibilities = value.get("responsibilities")
    if not isinstance(responsibilities, dict):
        errors.append(f"{label}.responsibilities: must be an object")
    else:
        for name in BASE_RESPONSIBILITIES:
            errors.extend(
                validate_readiness_item(
                    root,
                    f"{label}.responsibilities.{name}",
                    responsibilities.get(name),
                    allow_not_applicable=False,
                    required=True,
                )
            )

    conditional = value.get("conditional_responsibilities")
    if not isinstance(conditional, dict):
        errors.append(f"{label}.conditional_responsibilities: must be an object")
    else:
        conditional_specs = {
            "search_scope_justification": (
                search_scope_required,
                search_scope_required or search_scope_applicable,
            ),
            "active_constraint_check": (
                active_constraint_required,
                active_constraint_required or active_constraint_applicable,
            ),
        }
        for name in CONDITIONAL_RESPONSIBILITIES:
            structurally_required, applicable = conditional_specs[name]
            errors.extend(
                validate_readiness_item(
                    root,
                    f"{label}.conditional_responsibilities.{name}",
                    conditional.get(name),
                    allow_not_applicable=True,
                    required=structurally_required or applicable,
                )
            )
    return errors


def validate_component(
    root: Path,
    question_id: str,
    name: str,
    value: Any,
    fields: tuple[str, ...],
    *,
    require_manuscript: bool = False,
) -> list[str]:
    label = f"{question_id}.{name}"
    if not isinstance(value, dict):
        return [f"{label}: component must be an object"]
    errors: list[str] = []
    if value.get("pass") is not True:
        errors.append(f"{label}: pass must be true")
    for field in fields:
        if not nonempty_text(value.get(field)):
            errors.append(f"{label}: {field} is empty")
    if name == "stress_or_failure_boundary" and value.get("type") not in ALLOWED_RISK_TYPES:
        errors.append(
            f"{label}: type must be one of {', '.join(sorted(ALLOWED_RISK_TYPES))}"
        )
    errors.extend(
        evidence_errors(
            value.get("evidence"),
            root,
            label,
            require_manuscript=require_manuscript,
        )
    )
    return errors


def validate_architecture(
    root: Path,
    question_id: str,
    value: Any,
    question_ids: list[str],
    *,
    require_manuscript: bool = False,
    forbid_manuscript: bool = False,
) -> tuple[list[str], str | None]:
    label = f"{question_id}.architecture"
    if not isinstance(value, dict):
        return [f"{label}: architecture must be an object"], None
    errors: list[str] = []
    role = value.get("role")
    chain_type = value.get("chain_type")
    progression_axis = value.get("progression_axis")
    if role not in ALLOWED_QUESTION_ROLES:
        errors.append(
            f"{label}: role must be one of {', '.join(sorted(ALLOWED_QUESTION_ROLES))}"
        )
    if chain_type not in ALLOWED_CHAIN_TYPES:
        errors.append(
            f"{label}: chain_type must be one of {', '.join(sorted(ALLOWED_CHAIN_TYPES))}"
        )
    if progression_axis not in ALLOWED_PROGRESSION_AXES:
        errors.append(
            f"{label}: progression_axis must be one of "
            f"{', '.join(sorted(ALLOWED_PROGRESSION_AXES))}"
        )
    if not nonempty_text(value.get("route_summary")):
        errors.append(f"{label}: route_summary is empty")

    planned_range = value.get("planned_page_range")
    if (
        not isinstance(planned_range, list)
        or len(planned_range) != 2
        or any(
            not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0
            for item in planned_range
        )
        or (
            isinstance(planned_range, list)
            and len(planned_range) == 2
            and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in planned_range)
            and planned_range[0] > planned_range[1]
        )
    ):
        errors.append(
            f"{label}: planned_page_range must be two positive numbers [min, max]"
        )
    if not nonempty_text(value.get("page_basis")):
        errors.append(f"{label}: page_basis is empty")

    planned_subsections = value.get("planned_subsections")
    if not isinstance(planned_subsections, list):
        errors.append(f"{label}: planned_subsections must be a list")
    else:
        normalized: list[str] = []
        for index, title in enumerate(planned_subsections, start=1):
            item_label = f"{label}.planned_subsections[{index}]"
            if not nonempty_text(title):
                errors.append(f"{item_label}: subsection title is empty")
                continue
            title = title.strip()
            normalized.append(title)
            if title in GENERIC_SUBSECTIONS:
                errors.append(
                    f"{item_label}: subsection title is generic rather than question-specific"
                )
        if len(normalized) != len(set(normalized)):
            errors.append(f"{label}: planned_subsections contains duplicate titles")

    inheritance = value.get("inheritance")
    inheritance_label = f"{label}.inheritance"
    if not isinstance(inheritance, dict):
        errors.append(f"{inheritance_label}: inheritance must be an object")
        return errors, chain_type if isinstance(chain_type, str) else None
    status = inheritance.get("status")
    objects = inheritance.get("objects")
    if status not in {"none", "used"}:
        errors.append(f"{inheritance_label}: status must be none or used")
    if not isinstance(objects, list):
        errors.append(f"{inheritance_label}: objects must be a list")
    elif status == "none" and objects:
        errors.append(f"{inheritance_label}: status none requires an empty objects list")
    elif status == "used":
        if not objects:
            errors.append(f"{inheritance_label}: status used requires inherited objects")
        for index, item in enumerate(objects, start=1):
            item_label = f"{inheritance_label}.objects[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: inherited object must be an object")
                continue
            source = item.get("source_question")
            if not nonempty_text(source):
                errors.append(f"{item_label}: source_question is empty")
            elif source not in question_ids:
                errors.append(f"{item_label}: unknown source_question {source}")
            elif source == question_id:
                errors.append(f"{item_label}: source_question cannot be the current question")
            if not nonempty_text(item.get("object")):
                errors.append(f"{item_label}: object is empty")
            if not nonempty_text(item.get("consistency_check")):
                errors.append(f"{item_label}: consistency_check is empty")
            errors.extend(
                evidence_errors(
                    item.get("evidence"),
                    root,
                    item_label,
                    require_manuscript=require_manuscript,
                    forbid_manuscript=forbid_manuscript,
                )
            )
    return errors, chain_type if isinstance(chain_type, str) else None


def validate_argument_plan(
    root: Path,
    question_id: str,
    value: Any,
    required_claim_ids: set[str],
) -> list[str]:
    """Require a complete prewrite argument system, not a page or media quota."""

    label = f"{question_id}.argument_plan"
    if not isinstance(value, dict):
        return [f"{label}: argument_plan must be an object"]
    errors: list[str] = []
    anchor = value.get("structure_anchor")
    if anchor != "A053-structure-only":
        errors.append(
            f"{label}: structure_anchor must be A053-structure-only"
        )
    if not nonempty_text(value.get("adaptation_basis")):
        errors.append(f"{label}: adaptation_basis is empty")

    derivation_path = value.get("derivation_path")
    if not isinstance(derivation_path, list) or not derivation_path:
        errors.append(f"{label}.derivation_path must be a non-empty list")
    else:
        for index, item in enumerate(derivation_path, start=1):
            item_label = f"{label}.derivation_path[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: derivation step must be an object")
                continue
            for field in ("purpose", "relation_or_method"):
                if not nonempty_text(item.get(field)):
                    errors.append(f"{item_label}: {field} is empty")
            errors.extend(
                evidence_errors(
                    item.get("source_evidence"),
                    root,
                    item_label,
                    forbid_manuscript=True,
                )
            )

    result_claims = value.get("result_claims")
    planned_result_claims: list[str] = []
    if not isinstance(result_claims, list) or not result_claims:
        errors.append(f"{label}.result_claims must be a non-empty list")
    else:
        for index, item in enumerate(result_claims, start=1):
            item_label = f"{label}.result_claims[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: result claim must be an object")
                continue
            claim_id = item.get("claim_id")
            if not nonempty_text(claim_id):
                errors.append(f"{item_label}: claim_id is empty")
            else:
                planned_result_claims.append(claim_id.strip())
            for field in ("expected_output", "interpretation_task"):
                if not nonempty_text(item.get(field)):
                    errors.append(f"{item_label}: {field} is empty")
            errors.extend(
                evidence_errors(
                    item.get("source_evidence"),
                    root,
                    item_label,
                    forbid_manuscript=True,
                )
            )
    if set(planned_result_claims) != required_claim_ids:
        errors.append(
            f"{label}.result_claims must cover every requirement claim_id exactly once"
        )
    elif len(planned_result_claims) != len(set(planned_result_claims)):
        errors.append(f"{label}.result_claims contains duplicate claim_id values")

    validation_plan = value.get("validation_plan")
    validation_label = f"{label}.validation_plan"
    if not isinstance(validation_plan, dict):
        errors.append(f"{validation_label}: validation_plan must be an object")
    else:
        for field in ("main_risk", "independent_check", "boundary_or_stress_check"):
            if not nonempty_text(validation_plan.get(field)):
                errors.append(f"{validation_label}: {field} is empty")
        errors.extend(
            evidence_errors(
                validation_plan.get("source_evidence"),
                root,
                validation_label,
                forbid_manuscript=True,
            )
        )

    presentation_plan = value.get("presentation_plan")
    presented_claims: set[str] = set()
    seen_purposes: set[tuple[str, str, str]] = set()
    if not isinstance(presentation_plan, list) or not presentation_plan:
        errors.append(f"{label}.presentation_plan must be a non-empty list")
    else:
        for index, item in enumerate(presentation_plan, start=1):
            item_label = f"{label}.presentation_plan[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{item_label}: presentation item must be an object")
                continue
            claim_id = item.get("claim_id")
            medium = item.get("medium")
            purpose = item.get("purpose")
            if not nonempty_text(claim_id):
                errors.append(f"{item_label}: claim_id is empty")
            elif claim_id not in required_claim_ids:
                errors.append(f"{item_label}: unknown claim_id {claim_id}")
            else:
                presented_claims.add(claim_id)
            if medium not in ALLOWED_PRESENTATION_MEDIA:
                errors.append(
                    f"{item_label}: medium must be one of "
                    f"{', '.join(sorted(ALLOWED_PRESENTATION_MEDIA))}"
                )
            if not nonempty_text(purpose):
                errors.append(f"{item_label}: purpose is empty")
            if nonempty_text(claim_id) and isinstance(medium, str) and nonempty_text(purpose):
                signature = (claim_id.strip(), medium, purpose.strip())
                if signature in seen_purposes:
                    errors.append(
                        f"{item_label}: duplicate medium and purpose for the same claim"
                    )
                seen_purposes.add(signature)
            errors.extend(
                evidence_errors(
                    item.get("source_evidence"),
                    root,
                    item_label,
                    forbid_manuscript=True,
                )
            )
    if presented_claims != required_claim_ids:
        errors.append(f"{label}.presentation_plan must cover every requirement claim_id")
    return errors


def validate_conditional_gate(
    root: Path,
    question_id: str,
    name: str,
    value: Any,
    fields: tuple[str, ...],
    required: bool,
    *,
    require_manuscript: bool = False,
) -> list[str]:
    label = f"{question_id}.{name}"
    if not isinstance(value, dict):
        return [f"{label}: gate must be an object"]
    errors: list[str] = []
    applicable = value.get("applicable")
    if not isinstance(applicable, bool):
        errors.append(f"{label}: applicable must be true or false")
        return errors
    if required and not applicable:
        errors.append(f"{label}: applicable must be true for this chain_type")
    if applicable:
        for field in fields:
            if not nonempty_text(value.get(field)):
                errors.append(f"{label}: {field} is empty")
        errors.extend(
            evidence_errors(
                value.get("evidence"),
                root,
                label,
                require_manuscript=require_manuscript,
            )
        )
    return errors


def matrix_text(root: Path) -> tuple[str, list[str]]:
    path = root / "求解" / "证据矩阵.csv"
    if not path.exists():
        return "", ["求解/证据矩阵.csv missing"]
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=encoding), []
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore"), []


def manifest_shape(
    payload: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    question_ids = payload.get("question_ids")
    questions = payload.get("questions")
    if not isinstance(question_ids, list) or not question_ids:
        return ["question_ids must be a non-empty list"], [], {}
    if any(not nonempty_text(item) for item in question_ids):
        errors.append("question_ids contains an empty or non-string id")
    if len(set(question_ids)) != len(question_ids):
        errors.append("question_ids contains duplicates")
    if not isinstance(questions, dict):
        return errors + ["questions must be an object"], question_ids, {}
    if set(question_ids) != set(questions):
        missing = sorted(set(question_ids) - set(questions))
        extra = sorted(set(questions) - set(question_ids))
        if missing:
            errors.append(f"questions missing ids: {', '.join(missing)}")
        if extra:
            errors.append(f"questions contains undeclared ids: {', '.join(extra)}")
    return errors, question_ids, questions


def validate_requirements(
    root: Path,
    question_id: str,
    requirements: Any,
    claims_text: str,
) -> tuple[list[str], list[str], dict[str, str]]:
    errors: list[str] = []
    requirement_ids: list[str] = []
    requirement_claims: dict[str, str] = {}
    if not isinstance(requirements, list) or not requirements:
        return [f"{question_id}.requirements must be a non-empty list"], [], {}
    for index, item in enumerate(requirements, start=1):
        label = f"{question_id}.requirements[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: requirement must be an object")
            continue
        requirement_id = item.get("id")
        claim_id = item.get("claim_id")
        if not nonempty_text(requirement_id):
            errors.append(f"{label}: id is empty")
        elif requirement_id in requirement_ids:
            errors.append(f"{label}: duplicate id {requirement_id}")
        else:
            requirement_ids.append(requirement_id)
        if not nonempty_text(item.get("prompt_item")):
            errors.append(f"{label}: prompt_item is empty")
        if not nonempty_text(claim_id):
            errors.append(f"{label}: claim_id is empty")
        elif claims_text and claim_id not in claims_text:
            errors.append(f"{label}: claim_id not found in evidence matrix: {claim_id}")
        if nonempty_text(requirement_id) and nonempty_text(claim_id):
            requirement_claims[requirement_id] = claim_id
        errors.extend(
            evidence_errors(
                item.get("evidence"),
                root,
                label,
                forbid_manuscript=True,
            )
        )
    return errors, requirement_ids, requirement_claims


def validate_prewrite_questions(payload: dict[str, Any], root: Path) -> list[str]:
    errors, question_ids, questions = manifest_shape(payload)
    if not question_ids or not questions:
        return errors

    page_plan = payload.get("body_page_plan")
    if not isinstance(page_plan, dict):
        errors.append("body_page_plan must be an object")
    else:
        official_max = page_plan.get("official_body_max")
        if (
            not isinstance(official_max, int)
            or isinstance(official_max, bool)
            or not 1 <= official_max <= 30
        ):
            errors.append("body_page_plan.official_body_max must be an integer from 1 to 30")
        shared_range = page_plan.get("shared_sections_page_range")
        if (
            not isinstance(shared_range, list)
            or len(shared_range) != 2
            or any(
                not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0
                for item in shared_range
            )
            or (
                isinstance(shared_range, list)
                and len(shared_range) == 2
                and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in shared_range)
                and shared_range[0] > shared_range[1]
            )
        ):
            errors.append(
                "body_page_plan.shared_sections_page_range must be two positive numbers [min, max]"
            )
        if not nonempty_text(page_plan.get("basis")):
            errors.append("body_page_plan.basis is empty")

        question_ranges = []
        for question_id in question_ids:
            question = questions.get(question_id)
            architecture = question.get("architecture") if isinstance(question, dict) else None
            planned = architecture.get("planned_page_range") if isinstance(architecture, dict) else None
            if (
                isinstance(planned, list)
                and len(planned) == 2
                and all(
                    isinstance(item, (int, float))
                    and not isinstance(item, bool)
                    and item > 0
                    for item in planned
                )
                and planned[0] <= planned[1]
            ):
                question_ranges.append(planned)
        if (
            len(question_ranges) == len(question_ids)
            and isinstance(shared_range, list)
            and len(shared_range) == 2
            and all(
                isinstance(item, (int, float))
                and not isinstance(item, bool)
                and item > 0
                for item in shared_range
            )
            and isinstance(official_max, int)
            and not isinstance(official_max, bool)
        ):
            planned_upper = shared_range[1] + sum(item[1] for item in question_ranges)
            if planned_upper > official_max:
                errors.append(
                    "body_page_plan: planned upper bound exceeds the official body-page maximum"
                )

    claims_text, claim_errors = matrix_text(root)
    errors.extend(claim_errors)
    for question_id in question_ids:
        question = questions.get(question_id)
        if not isinstance(question, dict):
            errors.append(f"{question_id}: question entry must be an object")
            continue
        architecture_errors, chain_type = validate_architecture(
            root,
            question_id,
            question.get("architecture"),
            question_ids,
            forbid_manuscript=True,
        )
        errors.extend(architecture_errors)
        requirement_errors, _, requirement_claims = validate_requirements(
            root, question_id, question.get("requirements"), claims_text
        )
        errors.extend(requirement_errors)
        errors.extend(
            validate_argument_plan(
                root,
                question_id,
                question.get("argument_plan"),
                set(requirement_claims.values()),
            )
        )

        search_gate = question.get("search_scope_justification")
        active_gate = question.get("active_constraint_check")
        search_applicable = (
            search_gate.get("applicable") is True if isinstance(search_gate, dict) else False
        )
        active_applicable = (
            active_gate.get("applicable") is True if isinstance(active_gate, dict) else False
        )
        if not isinstance(search_gate, dict) or not isinstance(
            search_gate.get("applicable"), bool
        ):
            errors.append(
                f"{question_id}.search_scope_justification: applicable must be true or false"
            )
        if not isinstance(active_gate, dict) or not isinstance(
            active_gate.get("applicable"), bool
        ):
            errors.append(
                f"{question_id}.active_constraint_check: applicable must be true or false"
            )
        errors.extend(
            validate_prewrite_readiness(
                root,
                question_id,
                question.get("prewrite_readiness"),
                search_scope_required=chain_type in SEARCH_SCOPE_REQUIRED_CHAIN_TYPES,
                active_constraint_required=chain_type
                in ACTIVE_CONSTRAINT_REQUIRED_CHAIN_TYPES,
                search_scope_applicable=search_applicable,
                active_constraint_applicable=active_applicable,
            )
        )
    return errors


def validate_completed_questions(
    payload: dict[str, Any],
    root: Path,
    selected_question_ids: list[str] | None = None,
) -> list[str]:
    errors, question_ids, questions = manifest_shape(payload)
    if not question_ids or not questions:
        return errors
    selected = question_ids if selected_question_ids is None else selected_question_ids
    unknown = [item for item in selected if item not in question_ids]
    if unknown:
        errors.append(f"selected question ids are unknown: {', '.join(unknown)}")
    claims_text, claim_errors = matrix_text(root)
    errors.extend(claim_errors)
    for question_id in selected:
        if question_id not in questions:
            continue
        question = questions.get(question_id)
        if not isinstance(question, dict):
            errors.append(f"{question_id}: question entry must be an object")
            continue
        architecture = question.get("architecture")
        chain_type = architecture.get("chain_type") if isinstance(architecture, dict) else None
        errors.extend(
            validate_conditional_gate(
                root,
                question_id,
                "search_scope_justification",
                question.get("search_scope_justification"),
                SEARCH_SCOPE_FIELDS,
                chain_type in SEARCH_SCOPE_REQUIRED_CHAIN_TYPES,
                require_manuscript=True,
            )
        )
        errors.extend(
            validate_conditional_gate(
                root,
                question_id,
                "active_constraint_check",
                question.get("active_constraint_check"),
                ACTIVE_CONSTRAINT_FIELDS,
                chain_type in ACTIVE_CONSTRAINT_REQUIRED_CHAIN_TYPES,
                require_manuscript=True,
            )
        )
        requirement_errors, requirement_ids, requirement_claims = validate_requirements(
            root, question_id, question.get("requirements"), claims_text
        )
        errors.extend(requirement_errors)

        for component, fields in COMPONENT_FIELDS.items():
            errors.extend(
                validate_component(
                    root,
                    question_id,
                    component,
                    question.get(component),
                    fields,
                    require_manuscript=True,
                )
            )

        mappings = question.get("final_answer_mapping")
        mapped_ids: list[str] = []
        if not isinstance(mappings, list) or not mappings:
            errors.append(f"{question_id}.final_answer_mapping must be a non-empty list")
        else:
            for index, item in enumerate(mappings, start=1):
                label = f"{question_id}.final_answer_mapping[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{label}: mapping must be an object")
                    continue
                requirement_id = item.get("requirement_id")
                claim_id = item.get("claim_id")
                if not nonempty_text(requirement_id):
                    errors.append(f"{label}: requirement_id is empty")
                else:
                    mapped_ids.append(requirement_id)
                    if requirement_id not in requirement_ids:
                        errors.append(f"{label}: unknown requirement_id {requirement_id}")
                if not nonempty_text(claim_id):
                    errors.append(f"{label}: claim_id is empty")
                elif requirement_claims.get(requirement_id) not in {None, claim_id}:
                    errors.append(f"{label}: claim_id does not match the requirement")
                elif claims_text and claim_id not in claims_text:
                    errors.append(f"{label}: claim_id not found in evidence matrix: {claim_id}")
                if not nonempty_text(item.get("final_answer")):
                    errors.append(f"{label}: final_answer is empty")
                errors.extend(
                    evidence_errors(
                        item.get("evidence"),
                        root,
                        label,
                        require_manuscript=True,
                    )
                )
        if set(mapped_ids) != set(requirement_ids) or len(mapped_ids) != len(requirement_ids):
            errors.append(
                f"{question_id}: final_answer_mapping must cover each requirement exactly once"
            )
    return errors


def validate_compile_feedback(
    payload: dict[str, Any],
    root: Path,
    measurements: dict[str, Any] | None,
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    high = page_policy(root)
    feedback = payload.get("compile_feedback")
    if not isinstance(feedback, dict):
        return ["compile_feedback must be an object"], warnings, {}
    iterations = feedback.get("iterations")
    if not isinstance(iterations, list) or not iterations:
        return ["compile_feedback.iterations must contain an actual compiled-PDF record"], warnings, {}
    for index, item in enumerate(iterations, start=1):
        label = f"compile_feedback.iterations[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: iteration must be an object")
            continue
        if item.get("iteration") != index:
            errors.append(f"{label}: iteration number must be {index}")
        for field in ("body_pages", "total_pdf_pages"):
            value = item.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"{label}: {field} must be a positive integer")
        digest = item.get("pdf_sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None:
            errors.append(f"{label}: pdf_sha256 must be a 64-character hexadecimal digest")
        if isinstance(item.get("actions"), list):
            for action_index, action in enumerate(item["actions"], start=1):
                errors.extend(
                    substantive_task_errors(
                        action,
                        f"{label}.actions[{action_index}]",
                    )
                )
        body_pages = item.get("body_pages")
        missing = item.get("missing_depth_items")
        actions = item.get("actions")
        expected_status = (
            "INTERNAL_REVIEW_CANDIDATE"
            if isinstance(body_pages, int)
            and body_pages <= high
            and isinstance(missing, list)
            and not missing
            and isinstance(actions, list)
            and not actions
            else "INTERNAL_FAILED_BUILD"
        )
        if item.get("build_status") != expected_status:
            errors.append(
                f"{label}: build_status must be {expected_status}; "
                "a failed build is never a draft"
            )
        # Content and pagination never grant first-delivery authority by themselves.
        expected_deliverable = False
        if item.get("deliverable") is not expected_deliverable:
            errors.append(
                f"{label}: deliverable must be {str(expected_deliverable).lower()}"
            )

    if measurements is None:
        errors.append("compiled-PDF measurements are unavailable")
        return errors, warnings, {}
    latest = iterations[-1] if isinstance(iterations[-1], dict) else {}
    if isinstance(latest.get("missing_depth_items"), list) and latest["missing_depth_items"]:
        errors.append("latest compile feedback records unresolved depth items")
    if isinstance(latest.get("actions"), list) and latest["actions"]:
        errors.append("latest compile feedback records unresolved revision actions")
    for field in ("body_pages", "total_pdf_pages", "pdf_sha256"):
        if latest.get(field) != measurements.get(field):
            errors.append(f"latest compile feedback does not match current PDF: {field}")

    body_pages = measurements["body_pages"]
    page_status = ""
    if body_pages > high:
        page_status = "BLOCK_BODY_ABOVE_OFFICIAL_MAX"
        errors.append(f"body above hard maximum: {body_pages} > {high}")
    else:
        page_status = "PASS_OFFICIAL_BODY_LIMIT"

    pagination = {
        **measurements,
        "body_definition": "appendix:start - body:start",
        "body_includes": ["main_text", "ai_tool_usage_statement", "references"],
        "body_excludes": ["abstract", "appendix"],
        "hard_max": high,
        "page_status": page_status,
        "total_pdf_page_target": None,
    }
    return errors, warnings, pagination


def validate_payload(
    payload: Any,
    root: Path,
    phase: str,
    measurements: dict[str, Any] | None = None,
    selected_question_ids: list[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    pagination: dict[str, Any] = {}
    if not isinstance(payload, dict):
        errors.append("manifest root must be an object")
        payload = {}
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    readiness_errors = validate_prewrite_questions(payload, root)
    errors.extend(readiness_errors)
    completion_errors: list[str] = []
    if phase in {"question", "content", "final"}:
        completion_errors = validate_completed_questions(
            payload,
            root,
            selected_question_ids if phase == "question" else None,
        )
        errors.extend(completion_errors)
    if phase == "final":
        compile_errors, compile_warnings, pagination = validate_compile_feedback(
            payload, root, measurements
        )
        errors.extend(compile_errors)
        warnings.extend(compile_warnings)
    errors = list(dict.fromkeys(errors))
    prewrite_ready = not readiness_errors
    question_complete = phase == "question" and not readiness_errors and not completion_errors
    content_complete = (
        phase in {"content", "final"} and not readiness_errors and not completion_errors
    )
    status = {
        "prewrite": "PASS_PREWRITE_READINESS" if not errors else "BLOCK_PREWRITE_READINESS",
        "question": "PASS_QUESTION_CONTENT" if not errors else "BLOCK_QUESTION_CONTENT",
        "content": "PASS_ALL_QUESTION_CONTENT" if not errors else "BLOCK_ALL_QUESTION_CONTENT",
        "final": "PASS_DEPTH_AND_PAGINATION" if not errors else "BLOCK_DEPTH_AND_PAGINATION",
    }.get(phase, "BLOCK_UNKNOWN_PHASE")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "status": status,
        "pass": not errors,
        "prewrite_ready": prewrite_ready,
        "question_complete": question_complete,
        "content_complete": content_complete,
        "selected_question_ids": selected_question_ids or [],
        "question_count": len(payload.get("question_ids", []))
        if isinstance(payload.get("question_ids"), list)
        else 0,
        "pagination": pagination,
        "errors": errors,
        "warnings": warnings,
    }


def discover_question_ids(root: Path, explicit: list[str]) -> list[str]:
    if explicit:
        return list(dict.fromkeys(item.strip() for item in explicit if item.strip()))
    chain = root / "审查" / "section-chain" / "manifest.json"
    if chain.exists():
        try:
            values = read_json(chain).get("question_ids", [])
            if isinstance(values, list) and all(nonempty_text(item) for item in values):
                return list(dict.fromkeys(values))
        except Exception:  # noqa: BLE001
            pass
    return [path.name for path in sorted((root / "求解").glob("问题*")) if path.is_dir()]


def empty_component(fields: tuple[str, ...]) -> dict[str, Any]:
    return {"pass": False, **{field: "" for field in fields}, "evidence": []}


def empty_readiness_item() -> dict[str, Any]:
    return {"status": "blocked", "substantive_task": "", "source_evidence": []}


def initial_payload(question_ids: list[str]) -> dict[str, Any]:
    questions: dict[str, Any] = {}
    for question_id in question_ids:
        question = {
            "architecture": {
                "role": "",
                "chain_type": "",
                "progression_axis": "",
                "route_summary": "",
                "planned_page_range": [],
                "page_basis": "",
                "planned_subsections": [],
                "inheritance": {"status": "", "objects": []},
            },
            "argument_plan": {
                "structure_anchor": "A053-structure-only",
                "adaptation_basis": "",
                "derivation_path": [],
                "result_claims": [],
                "validation_plan": {
                    "main_risk": "",
                    "independent_check": "",
                    "boundary_or_stress_check": "",
                    "source_evidence": [],
                },
                "presentation_plan": [],
            },
            "search_scope_justification": {
                "applicable": False,
                **{field: "" for field in SEARCH_SCOPE_FIELDS},
                "evidence": [],
            },
            "active_constraint_check": {
                "applicable": False,
                **{field: "" for field in ACTIVE_CONSTRAINT_FIELDS},
                "evidence": [],
            },
            "prewrite_readiness": {
                "status": "blocked",
                "blocking_gaps": [],
                "responsibilities": {
                    name: empty_readiness_item() for name in BASE_RESPONSIBILITIES
                },
                "conditional_responsibilities": {
                    name: {
                        "status": "blocked",
                        "substantive_task": "",
                        "reason": "",
                        "source_evidence": [],
                    }
                    for name in CONDITIONAL_RESPONSIBILITIES
                },
            },
            "requirements": [],
            **{
                name: empty_component(fields)
                for name, fields in COMPONENT_FIELDS.items()
            },
            "final_answer_mapping": [],
        }
        questions[question_id] = question
    return {
        "schema_version": SCHEMA_VERSION,
        "question_ids": question_ids,
        "body_page_plan": {
            "official_body_max": 30,
            "shared_sections_page_range": [],
            "basis": "",
        },
        "questions": questions,
        "compile_feedback": {"iterations": []},
    }


def record_compile(
    payload: dict[str, Any],
    measurements: dict[str, Any],
    missing: list[str],
    actions: list[str],
    root: Path | None = None,
) -> None:
    feedback = payload.setdefault("compile_feedback", {})
    iterations = feedback.setdefault("iterations", [])
    if not isinstance(iterations, list):
        iterations = []
        feedback["iterations"] = iterations
    high = page_policy(root) if root is not None else 30
    body_pages = measurements["body_pages"]
    content_ready = body_pages <= high and not missing and not actions
    entry = {
        "iteration": len(iterations) + 1,
        "body_pages": body_pages,
        "total_pdf_pages": measurements["total_pdf_pages"],
        "pdf_sha256": measurements["pdf_sha256"],
        "build_status": "INTERNAL_REVIEW_CANDIDATE" if content_ready else "INTERNAL_FAILED_BUILD",
        "deliverable": False,
        "missing_depth_items": missing,
        "actions": actions,
    }
    if iterations and isinstance(iterations[-1], dict) and (
        iterations[-1].get("pdf_sha256") == measurements["pdf_sha256"]
    ):
        entry["iteration"] = len(iterations)
        iterations[-1] = entry
    else:
        iterations.append(entry)


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# 正文深度审计",
        "",
        f"- 结果：{'PASS' if result['pass'] else 'FAIL'}",
        f"- 阶段：{result['phase']}",
        f"- 状态：{result['status']}",
        f"- 成文前准备度：{'READY' if result['prewrite_ready'] else 'BLOCKED'}",
        f"- 问题数：{result['question_count']}",
    ]
    pagination = result.get("pagination", {})
    if pagination:
        lines.extend(
            [
                f"- 正文页数：{pagination.get('body_pages')}",
                f"- PDF 总页数：{pagination.get('total_pdf_pages')}",
                f"- 页数状态：{pagination.get('page_status')}",
            ]
        )
    lines.extend(["", "## 阻断项", ""])
    lines.extend([f"- {item}" for item in result["errors"]] or ["- 无"])
    lines.extend(["", "## 警告", ""])
    lines.extend([f"- {item}" for item in result["warnings"]] or ["- 无"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--output", default=DEFAULT_REPORT)
    parser.add_argument(
        "--phase",
        choices=("prewrite", "question", "content", "final"),
        default="final",
    )
    parser.add_argument("--init", action="store_true")
    parser.add_argument("--question-id", action="append", default=[])
    parser.add_argument("--record-compile", action="store_true")
    parser.add_argument("--missing-depth-item", action="append", default=[])
    parser.add_argument("--action", action="append", default=[])
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    if args.phase == "question" and not args.question_id and not args.init:
        parser.error("--phase question requires at least one --question-id")
    if args.record_compile and args.phase != "final":
        parser.error("--record-compile requires --phase final")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(args.root).resolve()
    manifest_path = root / args.manifest
    if args.init:
        if manifest_path.exists():
            print(json.dumps({"created": False, "reason": "manifest already exists"}, ensure_ascii=False))
            return 0
        question_ids = discover_question_ids(root, args.question_id)
        if not question_ids:
            print(json.dumps({"created": False, "error": "no question ids discovered"}, ensure_ascii=False))
            return 1
        if args.no_write:
            print(json.dumps({"created": False, "question_ids": question_ids}, ensure_ascii=False))
            return 0
        write_json(manifest_path, initial_payload(question_ids))
        print(json.dumps({"created": True, "question_ids": question_ids}, ensure_ascii=False))
        return 0

    if not manifest_path.exists():
        payload: Any = {}
        load_errors = [f"depth manifest not found: {args.manifest}"]
    else:
        try:
            payload = read_json(manifest_path)
            load_errors = []
        except Exception as exc:  # noqa: BLE001
            payload = {}
            load_errors = [f"depth manifest unreadable: {exc}"]

    measurements: dict[str, Any] | None = None
    measurement_errors: list[str] = []
    if args.phase == "final" or args.record_compile:
        measurements, measurement_errors = measure_compilation(root)
    if args.record_compile:
        if args.no_write:
            parser.error("--record-compile cannot be combined with --no-write")
        if load_errors or measurement_errors or not isinstance(payload, dict) or measurements is None:
            print(
                json.dumps(
                    {"recorded": False, "errors": load_errors + measurement_errors},
                    ensure_ascii=False,
                )
            )
            return 1
        record_compile(payload, measurements, args.missing_depth_item, args.action, root)
        write_json(manifest_path, payload)

    result = validate_payload(
        payload,
        root,
        args.phase,
        measurements,
        args.question_id if args.phase == "question" else None,
    )
    result["manifest"] = args.manifest
    result["manifest_sha256"] = sha256_file(manifest_path) if manifest_path.exists() else None
    result["errors"] = load_errors + measurement_errors + result["errors"]
    result["pass"] = not result["errors"]
    if not args.no_write:
        output = root / args.output
        write_json(output, result)
        output.with_suffix(".md").write_text(markdown_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "pass": result["pass"],
                "phase": result["phase"],
                "status": result["status"],
                "error_count": len(result["errors"]),
                "body_pages": result.get("pagination", {}).get("body_pages"),
                "page_status": result.get("pagination", {}).get("page_status"),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
