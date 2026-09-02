#!/usr/bin/env python3
"""Positive and tamper-negative tests for provenance v2, registry and scorecard policy."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    skills = Path(__file__).resolve().parents[2]
    sync = load(skills / "cumcm-review/scripts/sync_review_artifacts.py", "sync_review_artifacts")
    audit = load(skills / "cumcm-review/scripts/audit_artifacts.py", "audit_artifacts")
    cases: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-provenance-v2-") as tmp:
        root = Path(tmp)
        (root / "论文").mkdir()
        (root / "求解/问题1/图片").mkdir(parents=True)
        (root / "求解/问题1/结果").mkdir(parents=True)
        (root / "审查/provenance").mkdir(parents=True)
        tex = root / "论文/论文.tex"
        tex.write_text(r"\begin{figure}\includegraphics{a.pdf}\caption{A}\label{fig:a}\end{figure}", encoding="utf-8")
        source = root / "求解/问题1/问题1_求解.py"
        source.write_text("print('a')\n", encoding="utf-8")
        data = root / "求解/问题1/结果/a.csv"
        data.write_text("x,y\n1,2\n", encoding="utf-8")
        vector = root / "求解/问题1/图片/a.pdf"
        vector.write_bytes(b"%PDF-vector-A")
        manifest = sync.provenance_manifest(root, "fig:a", tex, vector, vector, source, [data], None)
        manifest_path = root / "审查/provenance/a.json"
        sync.write_json(manifest_path, manifest)
        item = {"vector_output": "求解/问题1/图片/a.pdf", "generation": {"provenance_manifest": "审查/provenance/a.json"}}
        cases["valid_full_input_provenance"] = not audit.validate_provenance(root, item)
        original_source = source.read_bytes()
        try:
            source.write_bytes(original_source + b"# tamper\n")
            errors = audit.validate_provenance(root, item)
            cases["tampered_source_rejected"] = any("input SHA-256" in value for value in errors)
        finally:
            source.write_bytes(original_source)
        cases["restored_source_passes"] = not audit.validate_provenance(root, item)
        original_vector = vector.read_bytes()
        try:
            vector.write_bytes(original_vector + b"TAMPER")
            errors = audit.validate_provenance(root, item)
            cases["tampered_vector_rejected"] = any("output SHA-256" in value for value in errors)
        finally:
            vector.write_bytes(original_vector)
        card = sync.scorecard(root, {"registry_coverage_complete": True}, {})
        cases["scorecard_never_auto_passes"] = (
            card["verdict"] == "REVIEW_REQUIRED" and card["hard_gates_pass"] is False
            and card["total"] is None and all(item["status"] == "REVIEW_REQUIRED" for item in card["dimensions"].values())
        )
        layout_path = root / "layout.json"
        sync.write_json(layout_path, {"edges": [{"from": "a", "to": "b", "label": "next"}]})
        layout = sync.normalise_layout(layout_path)
        edge = layout["connection_audit"]["items"][0]
        cases["edge_schema_unified_fail_closed"] = (
            layout["edge_schema_version"] == 1 and edge["source"] == "a" and edge["target"] == "b"
            and edge["final_render_pass"] is None and layout["pass"] is False
        )
    result = {"pass": all(cases.values()), "cases": cases}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
