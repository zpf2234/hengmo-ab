#!/usr/bin/env python
"""Freeze CUMCM answer artifacts before hidden-reference evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

INCLUDE_DIRS = ("题目", "数据", "求解")
INCLUDE_FILES = (Path("论文") / "论文.pdf",)
EXCLUDED_PARTS = {"__pycache__", ".git", "审查"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def collect(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in INCLUDE_DIRS:
        base = root / dirname
        if base.exists():
            files.extend(
                p for p in base.rglob("*")
                if p.is_file() and not any(part in EXCLUDED_PARTS for part in p.parts)
            )
    for relative in INCLUDE_FILES:
        path = root / relative
        if path.is_file():
            files.append(path)
    return sorted(set(files), key=lambda p: p.relative_to(root).as_posix())


def manifest_digest(files: list[dict]) -> str:
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/盲测冻结清单.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = root / args.output

    if args.verify:
        if not output.exists():
            print(json.dumps({"pass": False, "issues": [f"missing: {output}"]}, ensure_ascii=False))
            return 1
        old = json.loads(output.read_text(encoding="utf-8"))
        issues: list[str] = []
        for item in old.get("files", []):
            path = root / item.get("path", "")
            if not path.is_file():
                issues.append(f"missing frozen file: {item.get('path')}")
            elif sha256(path) != item.get("sha256"):
                issues.append(f"changed frozen file: {item.get('path')}")
        current = collect(root)
        current_paths = {p.relative_to(root).as_posix() for p in current}
        old_paths = {item.get("path") for item in old.get("files", [])}
        for extra in sorted(current_paths - old_paths):
            issues.append(f"new controlled file after freeze: {extra}")
        result = {"pass": not issues, "issues": issues, "manifest_sha256": old.get("manifest_sha256")}
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not issues else 1

    paths = collect(root)
    required = [root / "求解" / "任务契约.json", root / "求解" / "证据矩阵.csv", root / "论文" / "论文.pdf"]
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    if missing:
        print(json.dumps({"pass": False, "issues": [f"missing required: {p}" for p in missing]}, ensure_ascii=False))
        return 1
    files = [
        {"path": p.relative_to(root).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)}
        for p in paths
    ]
    manifest = {
        "schema_version": 1,
        "status": "FROZEN_BEFORE_REFERENCE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reference_visible_during_solve": False,
        "answer_frozen_before_reference": True,
        "file_count": len(files),
        "files": files,
        "manifest_sha256": manifest_digest(files),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pass": True, "output": str(output), "file_count": len(files), "manifest_sha256": manifest["manifest_sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
