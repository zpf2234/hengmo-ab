#!/usr/bin/env python3
"""Record and verify the two explicit user approvals in the semi-automatic workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
DEFAULT_RECORD = "审查/用户确认节点.json"
STATE_FILE = ".cumcm_state.json"
STAGES = ("method-result", "outline-page")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("confirmation record root must be an object")
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def project_workflow_mode(root: Path) -> str:
    state_path = root / STATE_FILE
    if not state_path.is_file():
        return "semi-automatic"
    try:
        state = read_json(state_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return "semi-automatic"
    policy = state.get("workflow_policy")
    if isinstance(policy, dict) and policy.get("mode") == "simulation":
        return "simulation"
    if state.get("workflow_mode") == "simulation":
        return "simulation"
    return "semi-automatic"


def initial_record(root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "semi-automatic",
        "workflow_mode": project_workflow_mode(root),
        "method_result_confirmation": {"status": "pending"},
        "outline_page_confirmation": {"status": "pending"},
    }


def stage_key(stage: str) -> str:
    return "method_result_confirmation" if stage == "method-result" else "outline_page_confirmation"


def file_digest(root: Path, relative: str) -> dict[str, str]:
    target = (root / relative).resolve()
    try:
        normalized = target.relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"evidence must stay inside project root: {relative}") from exc
    if not target.is_file():
        raise ValueError(f"evidence file does not exist: {relative}")
    return {
        "path": normalized,
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    }


def validate_stage(root: Path, record: dict[str, Any], stage: str) -> list[str]:
    errors: list[str] = []
    item = record.get(stage_key(stage))
    if not isinstance(item, dict) or item.get("status") != "confirmed":
        return [f"{stage}: explicit user confirmation is missing"]
    note = item.get("confirmation_note")
    if not isinstance(note, str) or not note.strip():
        errors.append(f"{stage}: confirmation_note is empty")
    artifacts = item.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"{stage}: no evidence artifacts are bound")
        return errors
    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, dict):
            errors.append(f"{stage}: artifacts[{index}] is invalid")
            continue
        relative = artifact.get("path")
        expected = artifact.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            errors.append(f"{stage}: artifacts[{index}] lacks path or sha256")
            continue
        try:
            current = file_digest(root, relative)["sha256"]
        except ValueError as exc:
            errors.append(f"{stage}: {exc}")
            continue
        if current != expected:
            errors.append(f"{stage}: confirmed evidence changed: {relative}")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--record-file", default=DEFAULT_RECORD)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--init", action="store_true")
    action.add_argument("--record", choices=STAGES)
    action.add_argument("--phase", choices=("paper-plan", "draft"))
    parser.add_argument("--confirmation-note")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    record_path = root / args.record_file

    if args.init:
        existed = record_path.exists()
        payload = initial_record(root)
        if existed:
            payload = read_json(record_path)
        elif not args.no_write:
            write_json(record_path, payload)
        print(json.dumps({"pass": True, "created": not existed and not args.no_write}, ensure_ascii=False))
        return 0

    if args.phase and project_workflow_mode(root) == "simulation":
        required = ["method-result"] if args.phase == "paper-plan" else list(STAGES)
        print(json.dumps({
            "pass": True,
            "phase": args.phase,
            "mode": "simulation",
            "confirmation_required": False,
            "skipped_confirmations": required,
        }, ensure_ascii=False))
        return 0

    try:
        payload = read_json(record_path)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"pass": False, "errors": [f"confirmation record unreadable: {exc}"]}, ensure_ascii=False))
        return 1
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("mode") != "semi-automatic":
        print(json.dumps({"pass": False, "errors": ["confirmation record schema or mode is invalid"]}, ensure_ascii=False))
        return 1

    if args.record:
        if not isinstance(args.confirmation_note, str) or not args.confirmation_note.strip():
            print(json.dumps({"pass": False, "errors": ["--confirmation-note is required"]}, ensure_ascii=False))
            return 1
        if not args.evidence:
            print(json.dumps({"pass": False, "errors": ["at least one --evidence file is required"]}, ensure_ascii=False))
            return 1
        if args.record == "outline-page":
            prior_errors = validate_stage(root, payload, "method-result")
            if prior_errors:
                print(json.dumps({"pass": False, "errors": prior_errors}, ensure_ascii=False))
                return 1
        try:
            artifacts = [file_digest(root, relative) for relative in args.evidence]
        except ValueError as exc:
            print(json.dumps({"pass": False, "errors": [str(exc)]}, ensure_ascii=False))
            return 1
        payload[stage_key(args.record)] = {
            "status": "confirmed",
            "confirmed_at_utc": datetime.now(timezone.utc).isoformat(),
            "confirmation_note": args.confirmation_note.strip(),
            "artifacts": artifacts,
        }
        if not args.no_write:
            write_json(record_path, payload)
        print(json.dumps({"pass": True, "recorded": args.record, "artifact_count": len(artifacts)}, ensure_ascii=False))
        return 0

    required = ["method-result"] if args.phase == "paper-plan" else list(STAGES)
    errors = [error for stage in required for error in validate_stage(root, payload, stage)]
    print(json.dumps({"pass": not errors, "phase": args.phase, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
