#!/usr/bin/env python3
"""Regression tests for the first-draft compile-and-revise gate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path


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
    deliverable = body_pages <= 30 and not missing and not actions
    return {
        "iteration": 1,
        "body_pages": body_pages,
        "total_pdf_pages": body_pages + 12,
        "pdf_sha256": digest,
        "build_status": "FIRST_DRAFT_CANDIDATE" if deliverable else "INTERNAL_FAILED_BUILD",
        "deliverable": deliverable,
        "missing_depth_items": missing,
        "actions": actions,
    }


def prepare(root: Path, *, body_pages: int, digest: str = "a" * 64, stage_status: str = "pass", content_complete: bool = True, missing: list[str] | None = None, actions: list[str] | None = None) -> None:
    write_json(
        root / ".cumcm_state.json",
        {"page_policy": {"body_page_max": 30}},
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


def case(body_pages: int, expected_status: str, **kwargs) -> dict:
    digest = kwargs.get("digest", "a" * 64)
    content_complete = kwargs.get("content_complete", True)
    prewrite_ready = kwargs.pop("prewrite_ready", True)
    with tempfile.TemporaryDirectory(prefix="cumcm-first-draft-") as tmp:
        root = Path(tmp)
        prepare(root, body_pages=body_pages, **kwargs)
        result = GATE.evaluate(
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
        prepare(root, body_pages=23, digest="a" * 64)
        result = GATE.evaluate(
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
            {"page_policy": {"body_page_max": 35}},
        )
        result = GATE.evaluate(
            root,
            measurements={
                "body_pages": 31,
                "total_pdf_pages": 43,
                "body_start_page": 2,
                "appendix_start_page": 33,
                "references_start_page": 31,
                "pdf_sha256": "a" * 64,
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
        result = GATE.evaluate(
            root,
            measurements={
                "body_pages": 23,
                "total_pdf_pages": 35,
                "body_start_page": 2,
                "appendix_start_page": 25,
                "references_start_page": 23,
                "pdf_sha256": "a" * 64,
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
        result = GATE.evaluate(
            root,
            measurements={
                "body_pages": 18,
                "total_pdf_pages": 30,
                "body_start_page": 2,
                "appendix_start_page": 20,
                "references_start_page": 18,
                "pdf_sha256": "a" * 64,
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
    }
    result = {"schema_version": 1, "pass": all(item["pass"] for item in cases.values()), "case_count": len(cases), "cases": cases}
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": result["pass"], "case_count": len(cases)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
