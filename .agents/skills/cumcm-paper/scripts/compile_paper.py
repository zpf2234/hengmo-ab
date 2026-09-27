#!/usr/bin/env python3
"""Compile the single manuscript twice and bind source dependencies to PDF/AUX.

This is a build receipt, not a quality verdict. There is deliberately no command
to sign an existing PDF without executing the compiler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

RECEIPT = "审查/编译绑定.json"
SOURCE = "论文/论文.tex"
OUTPUTS = {"pdf": "论文/论文.pdf", "aux": "论文/论文.aux"}
GENERATED = {".aux", ".out", ".toc", ".log", ".fls", ".nav", ".snm", ".vrb"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_inputs(root: Path, fls: Path) -> dict[str, str]:
    """Hash recorder inputs, including external assets and TeX environment files."""
    lines = fls.read_text(encoding="utf-8", errors="replace").splitlines()
    paper = root / "论文"
    outputs = {(paper / line[7:].strip().strip('"')).resolve() for line in lines if line.startswith("OUTPUT ")}
    inputs: dict[str, str] = {}
    for line in lines:
        if not line.startswith("INPUT "):
            continue
        path = (paper / line[6:].strip().strip('"')).resolve()
        if path in outputs or path.suffix.lower() in GENERATED:
            continue
        if not path.is_file():
            raise ValueError(f"recorded input missing: {path}")
        key = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        if key not in inputs:
            inputs[key] = digest(path)
    if SOURCE not in inputs:
        raise ValueError("compiler recorder did not include the single manuscript")
    return dict(sorted(inputs.items()))


def compile_project(root: Path, compiler: list[str], timeout: int = 240) -> dict[str, Any]:
    root = root.resolve()
    receipt = root / RECEIPT
    # Revoke only this generated receipt. A failed rebuild must not preserve approval
    # for a leftover PDF. Source files and the previous PDF are never deleted here.
    receipt.unlink(missing_ok=True)
    source = root / SOURCE
    if not source.is_file():
        raise ValueError(f"missing source: {SOURCE}")
    initial_source = digest(source)
    args = [*compiler, "-recorder", "-interaction=nonstopmode", "-halt-on-error", "论文.tex"]
    fls = root / "论文/论文.fls"
    passes = []
    before = None
    for index in range(2):
        prior = {key: (path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else None
                 for key, rel in OUTPUTS.items() for path in [root / rel]}
        result = subprocess.run(args, cwd=root / "论文", capture_output=True, timeout=timeout, check=False)
        if result.returncode != 0:
            tail = result.stdout.decode("utf-8", errors="replace")[-2500:]
            raise ValueError(f"compiler pass {index + 1} failed ({result.returncode}): {tail}")
        for key, rel in OUTPUTS.items():
            path = root / rel
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"compiler did not produce {rel}")
            if prior[key] == (path.stat().st_mtime_ns, path.stat().st_size):
                raise ValueError(f"compiler did not refresh {rel}")
        if not fls.is_file():
            raise ValueError("compiler recorder .fls is missing")
        current = project_inputs(root, fls)
        if digest(source) != initial_source:
            raise ValueError("manuscript changed during compilation; rerun with stable inputs")
        if before is not None and current != before:
            raise ValueError("project dependencies changed between compiler passes; rerun")
        before = current
        passes.append({"pass": index + 1, "exit_code": result.returncode})
    data = {
        "schema_version": 1, "producer": "compile_paper.py", "status": "compiled",
        "source": {"path": SOURCE, "sha256": initial_source},
        "compiler": {"command": args}, "passes": passes, "input_sha256": before,
        "outputs": {key: {"path": rel, "sha256": digest(root / rel)} for key, rel in OUTPUTS.items()},
        "scope": "all recorder inputs except generated intermediates; external assets and TeX environment files are hash-bound",
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(receipt)
    return data


def verify_compilation(root: Path) -> tuple[dict[str, Any], list[str]]:
    root = root.resolve()
    errors: list[str] = []
    path = root / RECEIPT
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, ["compiled source receipt missing or unreadable; run compile_paper.py"]
    if not isinstance(data, dict):
        return {}, ["compiled source receipt is not an object"]
    if data.get("schema_version") != 1 or data.get("producer") != "compile_paper.py" or data.get("status") != "compiled":
        errors.append("compiled source receipt version/producer/status is invalid")
    passes = data.get("passes")
    if not isinstance(passes, list) or len(passes) != 2 or any(not isinstance(item, dict) or item.get("pass") != index or item.get("exit_code") != 0 for index, item in enumerate(passes, 1)):
        errors.append("compiled source receipt must record two successful compiler passes")

    def verify_file(relative: Any, expected: Any, *, allow_external: bool = False) -> None:
        if not isinstance(relative, str) or (Path(relative).is_absolute() and not allow_external):
            errors.append("compiled dependency must be a project-relative path")
            return
        local = (root / relative).resolve()
        if (not allow_external and not local.is_relative_to(root)) or not local.is_file() or digest(local) != expected:
            errors.append(f"compiled input/output hash is stale or missing: {relative}")

    inputs = data.get("input_sha256")
    source = data.get("source")
    if not isinstance(inputs, dict) or SOURCE not in inputs or not isinstance(source, dict) or source.get("path") != SOURCE or source.get("sha256") != inputs.get(SOURCE):
        errors.append("compiled source is not bound to recorder inputs")
    if isinstance(inputs, dict):
        for relative, expected in inputs.items():
            verify_file(relative, expected, allow_external=True)
    outputs = data.get("outputs")
    for key, relative in OUTPUTS.items():
        item = outputs.get(key) if isinstance(outputs, dict) else None
        if not isinstance(item, dict) or item.get("path") != relative:
            errors.append(f"compiled receipt missing output: {relative}")
        else:
            verify_file(relative, item.get("sha256"))
    return {
        "tex_sha256": source.get("sha256") if isinstance(source, dict) else None,
        "compilation_binding_verified": not errors,
        "compile_manifest": {"path": RECEIPT, "sha256": digest(path)},
    }, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--compiler", default="xelatex")
    parser.add_argument("--timeout-seconds", type=int, default=240)
    args = parser.parse_args()
    executable = shutil.which(args.compiler)
    try:
        # Revoke before checking availability as well: failed rebuild attempts cannot
        # leave an old build receipt looking current.
        root = Path(args.root).resolve()
        (root / RECEIPT).unlink(missing_ok=True)
        if executable is None:
            raise ValueError(f"compiler unavailable: {args.compiler}")
        compile_project(root, [str(Path(executable).resolve())], args.timeout_seconds)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"pass": True, "receipt": RECEIPT}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
