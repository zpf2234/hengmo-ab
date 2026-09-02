#!/usr/bin/env python3
"""Focused regressions for figure census, track isolation, score/PDF binding and provenance."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("audit_artifacts", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load audit_artifacts")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    skills = Path(__file__).resolve().parents[2]
    audit = load_module(skills / "cumcm-review/scripts/audit_artifacts.py")
    cases: dict[str, bool] = {}
    tex = r"""
    \begin{figure}[H]\includegraphics{a.pdf}\caption{A}\label{fig:a}\end{figure}
    \begin{figure}\includegraphics{b.pdf}\caption{B}\end{figure}
    """
    figures = audit.tex_formal_figures(tex)
    cases["tex_census_requires_caption_label"] = len(figures) == 1 and figures[0]["label"] == "fig:a"
    cases["percentile_interpolates"] = audit.percentile([21, 22, 23], 0.25) == 21.5
    cases["low_figure_density_is_review_only"] = (
        audit.classify_figure_density_reference(0.20, 0.50, 0.90) == "REVIEW_LOW"
    )
    cases["high_figure_density_is_review_only"] = (
        audit.classify_figure_density_reference(1.20, 0.50, 0.90) == "REVIEW_HIGH"
    )
    cases["missing_density_benchmark_is_nonblocking_reference_gap"] = (
        audit.classify_figure_density_reference(0.20, None, None)
        == "REFERENCE_UNAVAILABLE"
    )
    cases["generic_question_heading_rejected"] = audit.is_generic_problem_heading(
        "问题一模型的建立与求解"
    )
    cases["specific_question_heading_allowed"] = not audit.is_generic_problem_heading(
        "盘入速度递推与碰撞时刻定位"
    )

    with tempfile.TemporaryDirectory(prefix="cumcm-artifact-gates-") as tmp:
        root = Path(tmp)
        (root / "论文").mkdir()
        (root / "审查/provenance").mkdir(parents=True)
        pdf = root / "论文/论文.pdf"
        pdf.write_bytes(b"PDF-A")
        evidence = root / "evidence.txt"
        evidence.write_text("ok", encoding="utf-8")
        dimensions = {
            name: {"score": 5 if name in {"可视表达", "提交就绪", "题意与口径"} else 4,
                   "evidence": ["evidence.txt"]}
            for name in audit.SCORE_DIMENSIONS
        }
        # 3*5 + 9*4 = 51; raise two dimensions to reach 57.
        for name in ("数据理解", "模型适配", "数学严谨", "求解实现", "验证强度", "结果价值"):
            dimensions[name]["score"] = 5
        total = sum(item["score"] for item in dimensions.values())
        card = {
            "verdict": "PASS_NATIONAL_FIRST_CANDIDATE", "hard_gates_pass": True,
            "pdf_binding": {"path": "论文/论文.pdf", "sha256": sha256(pdf)},
            "dimensions": dimensions, "total": total, "p0_findings": [], "p1_findings": [],
        }
        card_path = root / "审查/评分卡.json"
        card_path.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        cases["valid_score_and_pdf_binding"] = not audit.validate_national_scorecard(root, card_path, pdf, sha256(pdf))
        pdf.write_bytes(b"PDF-B")
        binding_errors = audit.validate_national_scorecard(root, card_path, pdf, sha256(pdf))
        cases["changed_pdf_breaks_binding"] = any("SHA-256" in item for item in binding_errors)

        vector = root / "论文/a.pdf"
        vector.write_bytes(b"VECTOR")
        source = root / "source.csv"
        source.write_bytes(b"x,y\n1,2\n")
        manifest = root / "审查/provenance/a.json"
        manifest.write_text(json.dumps({
            "status": "VERIFIED", "output": "论文/a.pdf", "output_sha256": sha256(vector),
            "inputs": [{"path": "source.csv", "role": "source_data", "sha256": sha256(source)}],
        }), encoding="utf-8")
        item = {"vector_output": "论文/a.pdf", "generation": {"provenance_manifest": "审查/provenance/a.json"}}
        cases["valid_provenance_hash"] = not audit.validate_provenance(root, item)
        vector.write_bytes(b"CHANGED")
        cases["changed_vector_breaks_provenance"] = any(
            "SHA-256" in value for value in audit.validate_provenance(root, item)
        )

        zip_root = root / "zip-valid"
        (zip_root / "附件").mkdir(parents=True)
        with zipfile.ZipFile(zip_root / "附件/支撑材料.zip", "w") as handle:
            handle.writestr("AI工具使用详情.pdf", b"%PDF-test")
            handle.writestr("代码/main.py", b"print('ok')")
        support = audit.audit_support_archives(zip_root, True, 20 * 1024 * 1024, 20.0)
        cases["zip_ai_details_verified"] = support["hard_errors"] == []

        missing_ai_root = root / "zip-missing-ai"
        (missing_ai_root / "附件").mkdir(parents=True)
        with zipfile.ZipFile(missing_ai_root / "附件/支撑材料.zip", "w") as handle:
            handle.writestr("代码/main.py", b"print('ok')")
        support = audit.audit_support_archives(missing_ai_root, True, 20 * 1024 * 1024, 20.0)
        cases["zip_missing_ai_details_rejected"] = any(
            "AI工具使用详情.pdf" in value for value in support["hard_errors"]
        )

        residue_root = root / "zip-residue"
        (residue_root / "附件").mkdir(parents=True)
        with zipfile.ZipFile(residue_root / "附件/支撑材料.zip", "w") as handle:
            handle.writestr("代码/main.py", b"print('ok')")
            handle.writestr("结果/metrics.json", b"{}")
            handle.writestr("运行/debug.log", b"trace")
        support = audit.audit_support_archives(residue_root, False, 20 * 1024 * 1024, 20.0)
        cases["zip_internal_residue_rejected"] = any(
            "internal/residual members" in value for value in support["hard_errors"]
        )

        required_json_root = root / "zip-required-json"
        (required_json_root / "附件").mkdir(parents=True)
        (required_json_root / "审查").mkdir(parents=True)
        with zipfile.ZipFile(required_json_root / "附件/支撑材料.zip", "w") as handle:
            handle.writestr("代码/main.py", b"print('ok')")
            handle.writestr("结果/result.json", b"{}")
        (required_json_root / "审查/附件JSON白名单.json").write_text(
            json.dumps({
                "members": [{"path": "结果/result.json", "reason": "赛题明确要求提交 JSON 答案"}],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        support = audit.audit_support_archives(required_json_root, False, 20 * 1024 * 1024, 20.0)
        cases["zip_required_json_allowlist_passes"] = support["hard_errors"] == []

        rar_root = root / "rar-no-review"
        (rar_root / "附件").mkdir(parents=True)
        (rar_root / "附件/支撑材料.rar").write_bytes(b"RAR-test")
        support = audit.audit_support_archives(rar_root, True, 20 * 1024 * 1024, 20.0)
        cases["rar_without_hash_bound_review_rejected"] = any(
            "RAR" in value for value in support["hard_errors"]
        )

        reviewed_rar_root = root / "rar-reviewed"
        (reviewed_rar_root / "附件").mkdir(parents=True)
        (reviewed_rar_root / "审查").mkdir(parents=True)
        rar_path = reviewed_rar_root / "附件/支撑材料.rar"
        rar_path.write_bytes(b"RAR-reviewed")
        review = {
            "schema_version": 1,
            "archives": [{
                "path": "附件/支撑材料.rar",
                "sha256": sha256(rar_path),
                "members": ["AI工具使用详情.pdf", "代码/main.py"],
                "inspected_with": "WinRAR member-list inspection",
                "reviewed_by": "submission-reviewer",
                "reviewed_at": "2026-08-27T22:00:00+08:00",
                "pass": True,
            }],
        }
        (reviewed_rar_root / "审查/RAR内容复核.json").write_text(
            json.dumps(review, ensure_ascii=False), encoding="utf-8"
        )
        support = audit.audit_support_archives(reviewed_rar_root, True, 20 * 1024 * 1024, 20.0)
        cases["rar_hash_bound_review_passes"] = support["hard_errors"] == []
        rar_path.write_bytes(b"RAR-tampered")
        support = audit.audit_support_archives(reviewed_rar_root, True, 20 * 1024 * 1024, 20.0)
        cases["rar_tamper_breaks_review_binding"] = any(
            "SHA-256 mismatch" in value for value in support["hard_errors"]
        )

    result = {"pass": all(cases.values()), "cases": cases}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
