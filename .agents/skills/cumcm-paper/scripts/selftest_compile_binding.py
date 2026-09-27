#!/usr/bin/env python3
"""Isolated build-receipt regressions; --real-compiler adds actual XeLaTeX execution."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def module(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


BUILD = module("build_binding_test", "compile_paper.py")
DEPTH = module("depth_binding_test", "audit_question_depth.py")
SOURCE = r"""\documentclass{article}
\begin{document}
\label{body:start}A minimal test manuscript.\input{test-data.tex}
\newpage\label{references:start}References.
\newpage\label{appendix:start}Appendix.
\end{document}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-write", action="store_true", help="Reports are always stdout-only")
    parser.add_argument("--real-compiler", action="store_true")
    args = parser.parse_args()
    results = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-compile-binding-test-") as temporary:
        root = Path(temporary)
        paper = root / "论文"
        paper.mkdir()
        (root / "审查").mkdir()
        files = {BUILD.SOURCE: SOURCE, "论文/test-data.tex": "Test data.",
                 "论文/论文.pdf": "%PDF-test-fixture", "论文/论文.aux": "test fixture AUX"}
        for relative, text in files.items():
            (root / relative).write_text(text, encoding="utf-8")
        # Explicitly synthetic receipt for validation-only tests; not a real build.
        fixture = {"schema_version": 1, "producer": "compile_paper.py", "status": "compiled",
                   "test_fixture": True,
                   "source": {"path": BUILD.SOURCE, "sha256": BUILD.digest(root / BUILD.SOURCE)},
                   "passes": [{"pass": 1, "exit_code": 0}, {"pass": 2, "exit_code": 0}],
                   "input_sha256": {relative: BUILD.digest(root / relative) for relative in (BUILD.SOURCE, "论文/test-data.tex")},
                   "outputs": {key: {"path": relative, "sha256": BUILD.digest(root / relative)} for key, relative in BUILD.OUTPUTS.items()}}
        receipt = root / BUILD.RECEIPT
        receipt.write_text(json.dumps(fixture), encoding="utf-8")
        results["synthetic_receipt_self_consistent"] = not BUILD.verify_compilation(root)[1]
        for index, relative in enumerate(files):
            path = root / relative
            original = path.read_bytes()
            path.write_bytes(original + b"\nchanged")
            results[f"changed_artifact_{index}_blocks"] = bool(BUILD.verify_compilation(root)[1])
            path.write_bytes(original)
        source = root / BUILD.SOURCE
        stat = source.stat()
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 10_000_000))
        results["same_bytes_new_mtime_allowed"] = not BUILD.verify_compilation(root)[1]
        try:
            BUILD.compile_project(root, [sys.executable, "-c", "raise SystemExit(1)"])
            results["failed_rebuild_revokes_receipt"] = False
        except ValueError:
            results["failed_rebuild_revokes_receipt"] = not receipt.exists() and (paper / "论文.pdf").exists()
        results["old_pdf_without_receipt_blocks"] = bool(BUILD.verify_compilation(root)[1])
        if args.real_compiler:
            executable = shutil.which("xelatex")
            if executable is None:
                results["real_two_pass_compilation"] = False
            else:
                # Remove synthetic outputs only within this owned TemporaryDirectory.
                for relative in BUILD.OUTPUTS.values():
                    (root / relative).unlink()
                BUILD.compile_project(root, [executable])
                binding, errors = BUILD.verify_compilation(root)
                measured, measure_errors = DEPTH.measure_compilation(root)
                results["real_two_pass_compilation"] = not errors and binding.get("compilation_binding_verified") is True
                results["real_source_dependency_recorded"] = "论文/test-data.tex" in json.loads(receipt.read_text(encoding="utf-8"))["input_sha256"]
                results["real_pdf_aux_measured"] = not measure_errors and measured["body_pages"] == 2 and measured["total_pdf_pages"] == 3
                (paper / "test-data.tex").write_text("Different data after the build.", encoding="utf-8")
                results["real_stale_dependency_blocks_measurement"] = bool(DEPTH.measure_compilation(root)[1])
                # External assets are not silently classified as untracked system files.
                with tempfile.TemporaryDirectory(prefix="cumcm-external-input-test-") as external_dir:
                    external = Path(external_dir) / "external.tex"
                    external.write_text("External test data.", encoding="utf-8")
                    source.write_text(SOURCE.replace("test-data.tex", external.as_posix()), encoding="utf-8")
                    BUILD.compile_project(root, [executable])
                    results["external_dependency_recorded"] = str(external.resolve()) in json.loads(receipt.read_text(encoding="utf-8"))["input_sha256"]
                    external.write_text("Changed external test data.", encoding="utf-8")
                    results["external_dependency_change_blocks"] = bool(BUILD.verify_compilation(root)[1])
    print(json.dumps({"pass": all(results.values()), "case_count": len(results),
                      "real_compiler_requested": args.real_compiler, "cases": results}, ensure_ascii=False))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
