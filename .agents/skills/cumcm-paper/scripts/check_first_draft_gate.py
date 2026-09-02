#!/usr/bin/env python3
"""Release the first deliverable draft after complete content and a compliant build.

A build above the official body-page maximum is an internal failed build.  A shorter
build is not rejected by page count alone; question-level completeness remains a
separate hard gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_REL = "审查/首份可交付初稿门禁.json"
MANIFEST_REL = "审查/逐问深度清单.json"
REQUIRED_DRAFT_STAGES = (
    "restatement",
    "analysis",
    "assumptions",
    "notation",
    "model-writing",
    "results-validation",
    "evaluation",
    "references",
    "appendix",
    "abstract",
)


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def load_depth_module():
    script = Path(__file__).resolve().parent / "audit_question_depth.py"
    spec = importlib.util.spec_from_file_location("cumcm_question_depth_for_first_draft", script)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def page_policy(root: Path) -> int:
    state = read_json(root / ".cumcm_state.json")
    if isinstance(state, dict):
        policy = state.get("page_policy")
        if isinstance(policy, dict):
            high = policy.get("body_page_max")
            if isinstance(high, int) and not isinstance(high, bool) and 1 <= high <= 30:
                return high
    return 30


def stage_gate_errors(root: Path) -> list[str]:
    errors: list[str] = []
    for stage in REQUIRED_DRAFT_STAGES:
        path = root / "审查" / "section-chain" / "gates" / f"{stage}.json"
        gate = read_json(path)
        if not isinstance(gate, dict):
            errors.append(f"draft stage gate missing or unreadable: {path.relative_to(root)}")
            continue
        if gate.get("stage") != stage:
            errors.append(f"draft stage gate mismatch: {stage}")
        if gate.get("status") != "pass" or gate.get("blocking_issues"):
            errors.append(f"draft stage is not complete: {stage}")
    return errors


def evaluate(
    root: Path,
    *,
    measurements: dict[str, Any] | None = None,
    content_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the first-deliverable-draft release gate.

    ``measurements`` and ``content_result`` are injectable only for isolated tests.
    Production CLI calls always measure the current PDF/AUX and revalidate the current
    depth manifest directly, avoiding stale report files.
    """

    root = root.resolve()
    high = page_policy(root)
    blockers: list[str] = []
    manifest_path = root / MANIFEST_REL
    payload = read_json(manifest_path)
    depth = load_depth_module()

    if not isinstance(payload, dict):
        blockers.append(f"depth manifest missing or unreadable: {MANIFEST_REL}")
        payload = {}

    if content_result is None:
        content_result = depth.validate_payload(payload, root, "content", None)
    if content_result.get("prewrite_ready") is not True:
        blockers.append("prewrite readiness audit is incomplete")
    if content_result.get("content_complete") is not True or content_result.get("pass") is not True:
        blockers.append("question-depth content audit is incomplete")
        blockers.extend(str(item) for item in content_result.get("errors", [])[:20])

    blockers.extend(stage_gate_errors(root))

    measurement_errors: list[str] = []
    if measurements is None:
        measurements, measurement_errors = depth.measure_compilation(root)
    blockers.extend(measurement_errors)

    feedback = payload.get("compile_feedback") if isinstance(payload, dict) else None
    iterations = feedback.get("iterations") if isinstance(feedback, dict) else None
    latest = iterations[-1] if isinstance(iterations, list) and iterations and isinstance(iterations[-1], dict) else None
    if latest is None:
        blockers.append("compile feedback has no actual compiled-PDF iteration")
    else:
        unresolved_missing = latest.get("missing_depth_items")
        unresolved_actions = latest.get("actions")
        if isinstance(unresolved_missing, list) and unresolved_missing:
            blockers.append("latest compile feedback records unresolved depth items")
        if isinstance(unresolved_actions, list) and unresolved_actions:
            blockers.append("latest compile feedback records unresolved revision actions")

    body_pages = measurements.get("body_pages") if isinstance(measurements, dict) else None
    total_pages = measurements.get("total_pdf_pages") if isinstance(measurements, dict) else None
    pdf_sha256 = measurements.get("pdf_sha256") if isinstance(measurements, dict) else None
    if latest is not None and isinstance(measurements, dict):
        for field in ("body_pages", "total_pdf_pages", "pdf_sha256"):
            if latest.get(field) != measurements.get(field):
                blockers.append(f"latest compile feedback does not match current PDF: {field}")

    expected_build_status: str | None = None
    expected_deliverable: bool | None = None
    if isinstance(body_pages, int):
        missing = latest.get("missing_depth_items") if latest else None
        actions = latest.get("actions") if latest else None
        expected_deliverable = (
            body_pages <= high
            and isinstance(missing, list)
            and not missing
            and isinstance(actions, list)
            and not actions
        )
        expected_build_status = (
            "FIRST_DRAFT_CANDIDATE" if expected_deliverable else "INTERNAL_FAILED_BUILD"
        )
        if latest is not None and latest.get("build_status") != expected_build_status:
            blockers.append(
                "compile record build_status violates failed-build/draft identity contract"
            )
        if latest is not None and latest.get("deliverable") is not expected_deliverable:
            blockers.append(
                "compile record deliverable flag violates failed-build/draft identity contract"
            )

    stage_failures = [item for item in blockers if item.startswith("draft stage")]
    content_failures = [
        item
        for item in blockers
        if item.startswith("question-depth") or item.startswith("prewrite readiness")
    ]
    binding_failures = [
        item
        for item in blockers
        if "compiled-PDF" in item
        or "current PDF" in item
        or "compiled PDF" in item
        or "compiled AUX" in item
        or "label" in item
        or item.startswith("depth manifest")
        or item.startswith("compile record")
    ]

    status: str
    if binding_failures:
        status = "BLOCK_FIRST_DELIVERABLE_NOT_COMPILED_OR_STALE"
    elif content_failures:
        status = "BLOCK_FIRST_DELIVERABLE_CONTENT_INCOMPLETE"
    elif stage_failures:
        status = "BLOCK_FIRST_DELIVERABLE_STAGE_INCOMPLETE"
    elif not isinstance(body_pages, int):
        blockers.append("official body page count unavailable")
        status = "BLOCK_FIRST_DELIVERABLE_NOT_COMPILED_OR_STALE"
    elif body_pages > high:
        blockers.append(
            f"internal failed build exceeds maximum: {body_pages} > {high}; "
            "automatic compression must continue in the same run"
        )
        status = "CONTINUE_INTERNAL_BUILD_ABOVE_MAX"
    elif blockers:
        status = "BLOCK_FIRST_DELIVERABLE_INCOMPLETE"
    else:
        status = "PASS_FIRST_DELIVERABLE_DRAFT"

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "pass": status == "PASS_FIRST_DELIVERABLE_DRAFT",
        "root": str(root),
        "body_page_definition": "appendix:start - body:start",
        "body_pages": body_pages,
        "total_pdf_pages": total_pages,
        "pdf_sha256": pdf_sha256,
        "hard_max": high,
        "compile_iteration_count": len(iterations) if isinstance(iterations, list) else 0,
        "required_draft_stages": list(REQUIRED_DRAFT_STAGES),
        "prewrite_ready": content_result.get("prewrite_ready") is True,
        "content_complete": content_result.get("content_complete") is True,
        "build_status": latest.get("build_status") if latest else None,
        "recorded_deliverable": latest.get("deliverable") if latest else False,
        "deliverable": status == "PASS_FIRST_DELIVERABLE_DRAFT",
        "blockers": list(dict.fromkeys(blockers)),
        "next_action": (
            "Do not expose this build as a draft or version. In the same generation run, "
            "return to each recorded substantive gap, close it, compile twice, record the "
            "new PDF, and rerun this gate automatically."
            if status != "PASS_FIRST_DELIVERABLE_DRAFT"
            else "This is the first deliverable draft; it may advance to de-AI editing, language audit, recompilation, and final review."
        ),
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# 首份可交付初稿门禁",
        "",
        f"- 状态：{result['status']}",
        f"- 正文页数：{result.get('body_pages')}",
        f"- PDF 总页数：{result.get('total_pdf_pages')}",
        f"- 正文页数上限：{result['hard_max']}",
        f"- 编译记录轮数：{result['compile_iteration_count']}",
        "",
        "## 阻断项",
        "",
    ]
    lines.extend([f"- {item}" for item in result["blockers"]] or ["- 无"])
    lines.extend(["", "## 下一动作", "", result["next_action"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default=REPORT_REL)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(args.root).resolve()
    result = evaluate(root)
    if not args.no_write:
        output = root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output.with_suffix(".md").write_text(markdown_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "pass": result["pass"],
                "status": result["status"],
                "body_pages": result["body_pages"],
                "blocker_count": len(result["blockers"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
