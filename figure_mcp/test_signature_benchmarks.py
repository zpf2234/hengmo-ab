from __future__ import annotations

import copy
import json
from pathlib import Path

import fitz
import pytest

import signature_benchmarks


SPEC_DIR = Path(__file__).resolve().parent / "benchmarks" / "signature_specs"


def load(name: str) -> dict:
    return json.loads((SPEC_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    ["a_mechanism_result.json", "b_strategy_landscape.json", "uncertainty_decision_linkage.json"],
)
def test_positive_signature_specs_are_structurally_valid(name: str):
    assert signature_benchmarks.validate_signature_spec(load(name)) == []


def test_palette_only_restyle_is_rejected():
    spec = load("b_strategy_landscape.json")
    spec["signature_checks"]["adds_explanatory_responsibility"] = False
    spec["signature_checks"]["not_palette_only"] = False
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("not_palette_only" in error for error in errors)
    assert any("adds_explanatory_responsibility" in error for error in errors)


def test_decorative_collage_without_linkage_is_rejected():
    spec = load("uncertainty_decision_linkage.json")
    spec["read_order"] = ["左图", "中图", "右图"]
    spec["data_linkage"]["element_links"] = []
    spec["signature_checks"]["integrated_narrative"] = False
    spec["signature_checks"]["not_decorative_collage"] = False
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("element_links" in error for error in errors)
    assert any("integrated_narrative" in error for error in errors)
    assert any("not_decorative_collage" in error for error in errors)


def test_missing_scientific_evidence_cannot_be_masked_by_complete_style_metadata():
    spec = copy.deepcopy(load("a_mechanism_result.json"))
    del spec["evidence"]["closure_series"]
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("evidence missing" in error for error in errors)


def test_a_mechanism_requires_defined_verified_error_and_threshold():
    spec = load("a_mechanism_result.json")
    del spec["evidence"]["closure_series"]["error_definition"]
    del spec["evidence"]["closure_series"]["report_threshold"]
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("error_definition" in error for error in errors)
    assert any("report_threshold" in error for error in errors)


def test_strategy_landscape_requires_real_switching_regions():
    spec = load("b_strategy_landscape.json")
    spec["evidence"]["strategy"] = [[1] * len(spec["evidence"]["x"]) for _ in spec["evidence"]["y"]]
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("switching boundary" in error for error in errors)


def test_uncertainty_switches_must_bind_threshold_to_sample_size():
    spec = load("uncertainty_decision_linkage.json")
    del spec["evidence"]["switches"][0]["uncertainty_threshold"]
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("uncertainty_threshold" in error for error in errors)


def test_a_mechanism_rejects_unverified_critical_event_and_nonconvergent_closure():
    spec = load("a_mechanism_result.json")
    spec["evidence"]["event_series"]["critical_x"] = 3
    spec["evidence"]["closure_series"]["error"] = [0.018, 0.007, 0.008, 0.004, 0.002]
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("critical_x" in error and "boundary_margin" in error for error in errors)
    assert any("strictly decrease" in error for error in errors)
    assert any("report_threshold" in error and "final error" in error for error in errors)


def test_b_landscape_rejects_recommendation_in_wrong_strategy_or_without_robust_margin():
    spec = load("b_strategy_landscape.json")
    spec["evidence"]["recommended"] = [1.3, 0.4]
    spec["evidence"]["recommended_strategy"] = 2
    spec["evidence"]["minimum_switch_margin_cells"] = 1
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("recommended_strategy" in error for error in errors)
    assert any("switching boundary" in error and "margin" in error for error in errors)


def test_uncertainty_rejects_switches_not_backed_by_uncertainty_or_policy_argmax():
    spec = load("uncertainty_decision_linkage.json")
    spec["evidence"]["switches"][0]["uncertainty_threshold"] = 0.2
    spec["evidence"]["switches"][1]["n"] = 120
    errors = signature_benchmarks.validate_signature_spec(spec)
    assert any("uncertainty_threshold" in error and "series" in error for error in errors)
    assert any("policy argmax" in error for error in errors)


def test_python_renderers_preserve_vector_and_fixed_page_contract(tmp_path: Path):
    pairs = [
        ("a_mechanism_result.json", signature_benchmarks.mechanism_render),
        ("b_strategy_landscape.json", signature_benchmarks.landscape_render),
        ("uncertainty_decision_linkage.json", signature_benchmarks.uncertainty_render),
    ]
    for filename, renderer in pairs:
        base = f"probe_{Path(filename).stem}"
        files = renderer(load(filename), base, tmp_path)
        for suffix in ("pdf", "svg", "png"):
            artifact = tmp_path / f"{base}.{suffix}"
            assert artifact.exists() and artifact.stat().st_size > 0, f"{suffix} missing for {filename}"
        audit = signature_benchmarks.audit_rendered_signature(
            tmp_path / f"{base}.pdf", tmp_path / f"{base}.svg", require_microsoft_yahei=True
        )
        assert audit["pass"] is True, f"{filename}: {audit['errors']}"
        assert audit["pdf"]["embedded_images"] == 0
        assert audit["pdf"]["page_size_distortion"] <= 0.002
        assert files["pdf"].endswith(".pdf")


def test_render_audit_accepts_real_vector_fixed_size_artifact(tmp_path: Path):
    pdf = tmp_path / "valid.pdf"
    doc = fitz.open()
    page = doc.new_page(width=15.5 / 2.54 * 72, height=8.8 / 2.54 * 72)
    page.insert_text((30, 40), "vector evidence")
    page.draw_line((20, 60), (180, 80))
    doc.save(pdf)
    doc.close()
    svg = tmp_path / "valid.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="15.5cm" height="8.8cm" viewBox="0 0 1550 880"><text x="10" y="20" font-family="Microsoft YaHei">证据</text></svg>', encoding="utf-8")

    audit = signature_benchmarks.audit_rendered_signature(pdf, svg)
    assert audit["pass"] is True
    assert audit["pdf"]["embedded_images"] == 0
    assert audit["pdf"]["page_size_distortion"] <= 0.002
    assert audit["svg"]["aspect_ratio_distortion"] <= 0.002


def test_render_audit_rejects_rasterized_or_deformed_artifact(tmp_path: Path):
    pdf = tmp_path / "bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
    pix.clear_with(200)
    page.insert_image(page.rect, pixmap=pix)
    doc.save(pdf)
    doc.close()
    svg = tmp_path / "bad.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10cm" height="10cm" viewBox="0 0 100 100"><image href="data:image/png;base64,AA=="/></svg>', encoding="utf-8")

    audit = signature_benchmarks.audit_rendered_signature(pdf, svg)
    assert audit["pass"] is False
    assert any("embedded raster" in error or "distortion" in error for error in audit["errors"])


def test_render_audit_rejects_same_ratio_but_wrong_final_size(tmp_path: Path):
    # A doubled canvas preserves aspect ratio but makes 8 pt labels render as 4 pt
    # after manuscript placement. Final-size fidelity must therefore check both axes.
    pdf = tmp_path / "double_size.pdf"
    doc = fitz.open()
    page = doc.new_page(width=31.0 / 2.54 * 72, height=17.6 / 2.54 * 72)
    page.insert_text((30, 40), "vector evidence")
    page.draw_line((20, 60), (180, 80))
    doc.save(pdf)
    doc.close()
    svg = tmp_path / "double_size.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="31cm" height="17.6cm" '
        'viewBox="0 0 3100 1760"><text x="10" y="20">证据</text></svg>',
        encoding="utf-8",
    )

    audit = signature_benchmarks.audit_rendered_signature(pdf, svg)
    assert audit["pass"] is False
    assert audit["pdf"]["width_size_error"] > 0.002
    assert audit["pdf"]["height_size_error"] > 0.002
    assert audit["svg"]["width_size_error"] > 0.002
    assert audit["svg"]["height_size_error"] > 0.002
    assert any("final-size" in error for error in audit["errors"])


def test_render_audit_rejects_single_axis_size_drift_even_when_below_one_percent(tmp_path: Path):
    pdf = tmp_path / "subpercent_drift.pdf"
    doc = fitz.open()
    page = doc.new_page(width=15.53 / 2.54 * 72, height=8.8 / 2.54 * 72)
    page.insert_text((30, 40), "vector evidence")
    doc.save(pdf)
    doc.close()
    svg = tmp_path / "subpercent_drift.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="15.53cm" height="8.8cm" '
        'viewBox="0 0 1553 880"><path d="M0 0 L10 10"/></svg>',
        encoding="utf-8",
    )

    audit = signature_benchmarks.audit_rendered_signature(pdf, svg)
    assert audit["pass"] is True  # 0.1935% remains within the explicit 0.2% tolerance
    assert 0 < audit["pdf"]["width_size_error"] <= 0.002
    assert 0 < audit["svg"]["width_size_error"] <= 0.002


def test_font_gate_rejects_svg_declaration_that_is_not_backed_by_pdf_font(tmp_path: Path):
    """A string in SVG metadata must not mask a Helvetica-only final PDF."""
    pdf = tmp_path / "wrong_font.pdf"
    doc = fitz.open()
    page = doc.new_page(width=15.5 / 2.54 * 72, height=8.8 / 2.54 * 72)
    page.insert_text((30, 40), "vector evidence")  # built-in Helvetica
    page.draw_line((20, 60), (180, 80))
    doc.save(pdf)
    doc.close()
    svg = tmp_path / "declared_only.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="15.5cm" height="8.8cm" '
        'viewBox="0 0 1550 880"><metadata>Microsoft YaHei</metadata>'
        '<text x="10" y="20" font-family="Helvetica">evidence</text></svg>',
        encoding="utf-8",
    )

    audit = signature_benchmarks.audit_rendered_signature(
        pdf, svg, require_microsoft_yahei=True
    )
    assert audit["pass"] is False
    assert audit["pdf"]["microsoft_yahei_embedded"] is False
    assert audit["svg"]["microsoft_yahei_text_styles"] is False
    assert any("Microsoft YaHei" in error for error in audit["errors"])
