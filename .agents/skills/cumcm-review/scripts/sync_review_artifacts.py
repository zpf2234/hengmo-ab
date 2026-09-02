#!/usr/bin/env python3
"""Synchronise figure/diagram registries, provenance hashes and an honest scorecard.

Machine-observable facts are VERIFIED.  Human judgements remain REVIEW_REQUIRED;
this command never emits a PASS verdict or invents scores.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIMENSIONS = (
    "题意与口径", "数据理解", "模型适配", "数学严谨", "求解实现", "验证强度",
    "结果价值", "证据追溯", "可复现性", "写作原创", "可视表达", "提交就绪",
)
OBJECTIVE_DIMENSIONS = {"求解实现", "验证强度", "证据追溯", "可复现性", "可视表达", "提交就绪"}
DIAGRAM_WORDS = ("流程", "拓扑", "关系", "机理", "框图", "示意")
VECTOR_SUFFIXES = (".pdf", ".svg")
RASTER_SUFFIXES = (".png",)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk", errors="ignore")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(read_text(path))
    except Exception:  # noqa: BLE001
        return copy.deepcopy(default)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(root: Path, path: Path, role: str) -> dict[str, Any]:
    return {"role": role, "path": rel(root, path), "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def strip_comments(text: str) -> str:
    return re.sub(r"(?m)(?<!\\)%.*$", "", text)


def included_tex_sources(tex_path: Path) -> list[Path]:
    """Return main and recursively included TeX sources in document order."""
    ordered: list[Path] = []
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in visited or not path.exists():
            return
        visited.add(path)
        ordered.append(path)
        text = strip_comments(read_text(path))
        for raw in re.findall(r"\\(?:input|include)\{([^}]+)\}", text):
            child = path.parent / raw
            if child.suffix.lower() != ".tex":
                child = child.with_suffix(".tex")
            visit(child)

    visit(tex_path)
    return ordered


def tex_figure_environments(tex_path: Path) -> list[dict[str, Any]]:
    sources = included_tex_sources(tex_path)
    found: list[dict[str, Any]] = []
    number = 0
    for source in sources:
        text = strip_comments(read_text(source))
        for match in re.finditer(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", text, re.DOTALL):
            block = match.group(1)
            images = re.findall(r"\\includegraphics(?:\[([^\]]*)\])?\{([^}]+)\}", block)
            caption = re.search(r"\\caption(?:\[[^\]]*\])?\{([^}]*)\}", block)
            label = re.search(r"\\label\{([^}]+)\}", block)
            if images and caption and label:
                number += 1
                options, raw = images[0]
                found.append({"ordinal": number, "raw": raw, "options": options or "", "caption": caption.group(1), "label": label.group(1), "source_tex": source})
    return found


def graphic_dirs(root: Path, tex_path: Path) -> list[Path]:
    dirs = [tex_path.parent]
    for source in included_tex_sources(tex_path):
        text = strip_comments(read_text(source))
        for block in re.findall(r"\\graphicspath\{((?:\{[^{}]*\})+)\}", text):
            dirs.extend((source.parent / raw).resolve() for raw in re.findall(r"\{([^{}]+)\}", block))
    dirs.extend(path for path in (root / "求解").glob("问题*/图片") if path.is_dir())
    return list(dict.fromkeys(path.resolve() for path in dirs))


def resolve_graphic(root: Path, dirs: list[Path], raw: str) -> Path | None:
    raw_path = Path(raw)
    suffixes = ("",) if raw_path.suffix else VECTOR_SUFFIXES + RASTER_SUFFIXES
    for directory in dirs:
        for suffix in suffixes:
            candidate = (directory / (raw + suffix)).resolve()
            if candidate.exists() and candidate.is_file():
                return candidate
    for candidate in (root / "求解").glob(f"问题*/图片/{raw_path.name}*"):
        if candidate.is_file() and candidate.suffix.lower() in VECTOR_SUFFIXES + RASTER_SUFFIXES:
            return candidate.resolve()
    return None


def artifact_id(label: str, ordinal: int) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-")
    return value or f"figure-{ordinal}"


def normalized_stem(path: Path | str) -> str:
    stem = Path(path).stem
    return re.sub(r"(?:_final|_preview|_actual|_page|_thumb|_gray)$", "", stem, flags=re.I)


def existing_items(review: Path) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for filename, collection in (("figure-registry.json", "figures"), ("diagram-registry.json", "diagrams")):
        payload = load_json(review / filename, {})
        for item in payload.get(collection, []) if isinstance(payload, dict) else []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                values[item["id"]] = item
    return values


def locate_related(image: Path, suffixes: tuple[str, ...], keywords: tuple[str, ...] = ()) -> Path | None:
    stems = [image.stem, normalized_stem(image)]
    for stem in stems:
        for suffix in suffixes:
            candidate = image.with_name(stem + suffix)
            if candidate.exists():
                return candidate.resolve()
    candidates = sorted(p for p in image.parent.iterdir() if p.is_file() and p.suffix.lower() in suffixes)
    for candidate in candidates:
        if normalized_stem(candidate) == normalized_stem(image):
            return candidate.resolve()
    for keyword in keywords:
        for candidate in candidates:
            if keyword in candidate.stem:
                return candidate.resolve()
    return None


def generator_for(root: Path, image: Path, old: dict[str, Any], is_diagram: bool) -> Path | None:
    fields = ("source", "generator") if is_diagram else ("generator", "source")
    for field in fields:
        value = old.get(field)
        if isinstance(value, str) and (root / value).exists():
            return (root / value).resolve()
    if is_diagram:
        source = locate_related(image, (".tex", ".tikz", ".vsdx", ".drawio", ".py"))
        if source:
            return source
    problem_dir = image.parent.parent
    scripts = sorted(problem_dir.glob("*.py"))
    if scripts:
        return scripts[0].resolve()
    common = root / "求解" / "生成论文图.py"
    return common.resolve() if common.exists() else None


def layout_for(root: Path, image: Path, old: dict[str, Any]) -> Path | None:
    old_layout = old.get("layout")
    if isinstance(old_layout, str) and (root / old_layout).exists():
        return (root / old_layout).resolve()
    aliases = {
        "序贯判定流程": "sprt_flow", "再生决策流程": "regenerative_decision_flow",
        "完整枚举流程": "hierarchical_enumeration_flow", "稳健重优化流程": "robust_reoptimization_flow",
    }
    candidates = sorted(image.parent.glob("*.layout.json"))
    stems = [normalized_stem(image)]
    stems += [alias for cn, alias in aliases.items() if cn in image.stem]
    for candidate in candidates:
        cstem = normalized_stem(candidate.name.replace(".layout", ""))
        if any(stem in cstem or cstem in stem for stem in stems):
            return candidate.resolve()
    return None


def source_data_for(root: Path, image: Path, old: dict[str, Any]) -> list[Path]:
    result: list[Path] = []
    for value in old.get("source_data", []) if isinstance(old.get("source_data"), list) else []:
        if isinstance(value, str) and (root / value).exists():
            result.append((root / value).resolve())
    if result:
        return result
    result_dir = image.parent.parent / "结果"
    if result_dir.exists():
        result = sorted(path.resolve() for path in result_dir.iterdir() if path.is_file() and path.suffix.lower() in {".csv", ".json", ".xlsx"})
    return result


def choose_vector(image: Path) -> Path | None:
    if image.suffix.lower() in VECTOR_SUFFIXES:
        return image
    for suffix in VECTOR_SUFFIXES:
        candidate = image.with_suffix(suffix)
        if candidate.exists():
            return candidate.resolve()
    return None


def provenance_manifest(root: Path, item_id: str, tex_path: Path, image: Path, vector: Path | None,
                        source: Path | None, data: list[Path], layout: Path | None) -> dict[str, Any]:
    records: list[dict[str, Any]] = [file_record(root, tex_path, "tex_figure_source")]
    records += [file_record(root, path, "source_data") for path in data]
    if source:
        records.append(file_record(root, source, "generator_or_editable_source"))
    if layout:
        records.append(file_record(root, layout, "layout_audit"))
    records.append(file_record(root, image, "tex_referenced_artifact"))
    if vector and vector.resolve() != image.resolve():
        records.append(file_record(root, vector, "final_vector_output"))
    missing_roles = []
    if not source:
        missing_roles.append("generator_or_editable_source")
    if not vector:
        missing_roles.append("final_vector_output")
    status = "VERIFIED" if not missing_roles else "INCOMPLETE"
    return {
        "schema_version": 2,
        "artifact_id": item_id,
        "status": status,
        "verified": status == "VERIFIED",
        "verification_scope": "FILE_IDENTITY_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "sha256",
        "source": rel(root, source) if source else None,
        "output": rel(root, vector) if vector else rel(root, image),
        "output_sha256": sha256_file(vector if vector else image),
        "inputs": records,
        "missing_roles": missing_roles,
        "attestation": "Hashes prove byte identity and linkage only; they do not certify scientific or visual quality.",
    }


def connection_from_edge(edge: dict[str, Any], index: int) -> dict[str, Any]:
    source = edge.get("source", edge.get("from_node", edge.get("from")))
    target = edge.get("target", edge.get("to_node", edge.get("to")))
    source_name = source if isinstance(source, str) else f"point:{source}"
    target_name = target if isinstance(target, str) else f"point:{target}"
    meaning = edge.get("meaning") or edge.get("label") or f"{source_name} 到 {target_name} 的连接"
    return {
        "id": str(edge.get("id") or f"e{index:02d}"), "kind": edge.get("kind", "flow_arrow"),
        "source": source_name, "target": target_name,
        "source_anchor": edge.get("source_anchor", "boundary"), "target_anchor": edge.get("target_anchor", "boundary"),
        "directionality": edge.get("directionality", "directed"), "direction": edge.get("direction", "source_to_target"),
        "meaning": meaning, "arrowhead_required": edge.get("arrowhead_required", True),
        "arrowhead_present": edge.get("arrowhead_present", None), "semantics_match": edge.get("semantics_match", None),
        "source_endpoint_error_pt": edge.get("source_endpoint_error_pt"), "target_endpoint_error_pt": edge.get("target_endpoint_error_pt"),
        "non_target_crossings": edge.get("non_target_crossings"), "min_clearance_pt": edge.get("min_clearance_pt"),
        "label_overlap": edge.get("label_overlap"), "label_path_overlap": edge.get("label_path_overlap"),
        "line_continuity_pass": edge.get("line_continuity_pass"), "node_interior_overlap": edge.get("node_interior_overlap"),
        "final_render_pass": edge.get("final_render_pass", None),
    }


def normalise_layout(path: Path) -> dict[str, Any]:
    payload = load_json(path, {})
    if not isinstance(payload, dict):
        return {}
    raw_edges = payload.get("edges", [])
    if not isinstance(raw_edges, list):
        raw_edges = []
    old_connection = payload.get("connection_audit", {})
    old_items = old_connection.get("items", []) if isinstance(old_connection, dict) else []
    source_items = old_items if isinstance(old_items, list) and old_items else raw_edges
    items = [connection_from_edge(item, i) for i, item in enumerate(source_items, 1) if isinstance(item, dict)]
    for item in items:
        for field in ("arrowhead_present", "semantics_match", "source_endpoint_error_pt", "target_endpoint_error_pt",
                      "non_target_crossings", "min_clearance_pt", "label_overlap", "label_path_overlap",
                      "line_continuity_pass", "node_interior_overlap", "final_render_pass"):
            if field not in item:
                item[field] = None
    failed = sum(
        1 for item in items
        if item.get("final_render_pass") is False
        or item.get("semantics_match") is False
        or item.get("line_continuity_pass") is False
        or item.get("label_path_overlap") is True
    )
    pending = sum(
        1 for item in items
        if item.get("final_render_pass") is None
        or item.get("semantics_match") is None
        or item.get("line_continuity_pass") is None
        or item.get("label_path_overlap") is None
    )
    payload["edge_schema_version"] = 1
    payload["connection_audit"] = {"schema_version": 1, "total": len(items), "checked": len(items) - pending, "failed": failed, "review_required": pending, "items": items}
    line_items = []
    for item in items:
        line_items.append({
            "id": f"line:{item['id']}", "kind": item["kind"], "meaning": item["meaning"],
            "directionality": item["directionality"], "expected_direction": item["direction"],
            "arrowhead_required": item["arrowhead_required"], "arrowhead_present": item["arrowhead_present"],
            "semantics_match": item["semantics_match"], "line_continuity_pass": item["line_continuity_pass"],
            "final_render_pass": item["final_render_pass"],
        })
    line_failed = sum(
        1 for item in line_items
        if item["final_render_pass"] is False
        or item["semantics_match"] is False
        or item["line_continuity_pass"] is False
    )
    line_pending = sum(
        1 for item in line_items
        if item["final_render_pass"] is None
        or item["semantics_match"] is None
        or item["line_continuity_pass"] is None
    )
    payload["line_semantics_audit"] = {"schema_version": 1, "total": len(line_items), "checked": len(line_items) - line_pending, "failed": line_failed, "review_required": line_pending, "items": line_items}
    if pending or line_pending:
        payload["pass"] = False
        payload["status"] = "REVIEW_REQUIRED"
    write_json(path, payload)
    return payload


def build_registries(root: Path, update_layouts: bool) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    review = root / "审查"
    tex_path = root / "论文" / "论文.tex"
    figures = tex_figure_environments(tex_path)
    dirs = graphic_dirs(root, tex_path)
    old = existing_items(review)
    fig_items: list[dict[str, Any]] = []
    diagram_items: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for entry in figures:
        item_id = artifact_id(entry["label"], entry["ordinal"])
        image = resolve_graphic(root, dirs, entry["raw"])
        if image is None:
            coverage.append({**entry, "id": item_id, "status": "MISSING_OUTPUT"})
            continue
        previous = old.get(item_id, {})
        is_diagram = any(word in entry["caption"] or word in image.stem for word in DIAGRAM_WORDS)
        vector = choose_vector(image)
        source = generator_for(root, image, previous, is_diagram)
        layout = layout_for(root, image, previous) if is_diagram else None
        if layout and update_layouts:
            normalise_layout(layout)
        data = [] if is_diagram else source_data_for(root, image, previous)
        manifest_rel = f"审查/provenance/{item_id}.json"
        manifest = provenance_manifest(root, item_id, tex_path, image, vector, source, data, layout)
        write_json(root / manifest_rel, manifest)
        generation = {
            "mode": "script", "renderer": "source-file", "tool": source.name if source else "UNRESOLVED",
            "health_pass": None, "spec_path": rel(root, source) if source else "UNRESOLVED",
            "provenance_manifest": manifest_rel,
        }
        common = {
            "id": item_id, "purpose": entry["caption"], "claim_ids": [entry["label"]],
            "tex_figure": {"file": rel(root, entry.get("source_tex", tex_path)), "ordinal": entry["ordinal"], "label": entry["label"],
                           "caption": entry["caption"], "includegraphics": entry["raw"], "options": entry["options"]},
            "vector_output": rel(root, vector if vector else image), "generation": generation,
            "vector_audit": {"true_vector": vector is not None, "aspect_ratio_distortion": previous.get("vector_audit", {}).get("aspect_ratio_distortion")},
        }
        if is_diagram:
            item = {
                **common, "role": "flowchart" if "流程" in entry["caption"] else "relationship",
                "style_family": previous.get("style_family", "tikz" if source and source.suffix.lower() in {".tex", ".tikz"} else "visio"),
                "source": rel(root, source) if source else "UNRESOLVED", "layout": rel(root, layout) if layout else "UNRESOLVED",
                "insert_width_mm": previous.get("insert_width_mm", 120), "final_min_font_pt": previous.get("final_min_font_pt"),
                "visual_review": previous.get("visual_review", {"status": "REVIEW_REQUIRED", "publication_ready": False}),
            }
            diagram_items.append(item)
        else:
            signature_fields = {
                key: copy.deepcopy(previous[key])
                for key in (
                    "signature_figure", "signature_archetype", "core_claim",
                    "ten_second_takeaway", "read_order", "data_linkage", "signature_checks",
                )
                if key in previous
            }
            item = {
                **common, "category": previous.get("category", "other_evidence"),
                "source_data": [rel(root, p) for p in data], "generator": rel(root, source) if source else "UNRESOLVED",
                "insert_width_mm": previous.get("insert_width_mm", 120), "final_min_font_pt": previous.get("final_min_font_pt"),
                "visual_review": previous.get("visual_review", {"status": "REVIEW_REQUIRED", "publication_ready": False}),
                "style": previous.get("style", {"status": "REVIEW_REQUIRED"}),
                "role_specific_checks": previous.get("role_specific_checks", []),
                **signature_fields,
            }
            fig_items.append(item)
        coverage_entry = {key: value for key, value in entry.items() if key != "source_tex"}
        coverage_entry["source_tex"] = rel(root, entry.get("source_tex", tex_path))
        coverage.append({**coverage_entry, "id": item_id, "status": manifest["status"], "registry": "diagram" if is_diagram else "figure", "output": common["vector_output"]})
    registry_status = "FILE_PROVENANCE_VERIFIED_REVIEW_REQUIRED"
    old_fig_registry = load_json(review / "figure-registry.json", {})
    fig_registry = {
        "schema_version": 3,
        "status": registry_status,
        "source_of_truth": "论文/论文.tex figure environments",
        "visual_identity": copy.deepcopy(old_fig_registry.get("visual_identity", {"status": "REVIEW_REQUIRED"})),
        "signature_policy": copy.deepcopy(old_fig_registry.get("signature_policy", {"status": "REVIEW_REQUIRED"})),
        "figures": fig_items,
    }
    dia_registry = {"schema_version": 2, "edge_schema_version": 1, "status": registry_status, "source_of_truth": "论文/论文.tex figure environments", "diagrams": diagram_items}
    return fig_registry, dia_registry, coverage


def objective_checks(root: Path, fig_registry: dict[str, Any], dia_registry: dict[str, Any], coverage: list[dict[str, Any]]) -> dict[str, Any]:
    review = root / "审查"
    evidence = load_json(root / "求解" / "证据审计.json", {})
    automatic = load_json(review / "自动审查.json", {})
    all_items = fig_registry["figures"] + dia_registry["diagrams"]
    provenance_ok = bool(all_items) and all(load_json(root / item["generation"]["provenance_manifest"], {}).get("status") == "VERIFIED" for item in all_items)
    registry_coverage = len(coverage) == len(all_items) and all(item.get("status") != "MISSING_OUTPUT" for item in coverage)
    diagram_layouts = [load_json(root / item["layout"], {}) for item in dia_registry["diagrams"] if item.get("layout") != "UNRESOLVED"]
    diagram_machine_complete = len(diagram_layouts) == len(dia_registry["diagrams"]) and all(
        isinstance(layout.get("connection_audit"), dict) and layout["connection_audit"].get("total", 0) > 0 for layout in diagram_layouts
    )
    pdf = root / "论文" / "论文.pdf"
    return {
        "pdf_exists": pdf.exists() and pdf.stat().st_size > 0,
        "pdf_sha256": sha256_file(pdf) if pdf.exists() and pdf.stat().st_size > 0 else None,
        "solve_evidence_pass": evidence.get("pass") is True,
        "artifact_audit_pass": automatic.get("pass") is True,
        "body_pages": automatic.get("counts", {}).get("body_pages") if isinstance(automatic.get("counts"), dict) else None,
        "tex_figure_count": len(coverage), "registry_item_count": len(all_items),
        "registry_coverage_complete": registry_coverage,
        "provenance_hashes_verified": provenance_ok,
        "diagram_layout_machine_inventory_complete": diagram_machine_complete,
        "all_vectors": bool(all_items) and all(Path(item["vector_output"]).suffix.lower() in VECTOR_SUFFIXES for item in all_items),
    }


def scorecard(root: Path, checks: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    evidence_map = {
        "求解实现": ["求解/任务契约.json", "求解/证据审计.json"],
        "验证强度": ["求解/证据矩阵.csv", "求解/证据审计.json"],
        "证据追溯": ["求解/证据矩阵.csv", "审查/figure-registry.json", "审查/diagram-registry.json", "审查/provenance"],
        "可复现性": ["求解/运行环境.json", "求解/证据审计.json"],
        "可视表达": ["审查/figure-registry.json", "审查/diagram-registry.json", "审查/provenance"],
        "提交就绪": ["论文/论文.pdf", "审查/自动审查.json"],
    }
    dimensions: dict[str, Any] = {}
    for name in DIMENSIONS:
        old_item = previous.get("dimensions", {}).get(name, {}) if isinstance(previous, dict) else {}
        evidence = [value for value in evidence_map.get(name, old_item.get("evidence", [])) if isinstance(value, str) and (root / value).exists()]
        if name in OBJECTIVE_DIMENSIONS:
            dimensions[name] = {"assessment": "AUTO_PREFILLED", "score": None, "evidence": evidence,
                                "objective_metrics": checks, "status": "REVIEW_REQUIRED",
                                "review_note": "Objective evidence is prefilled; a human reviewer must assign the 0-5 score."}
        else:
            dimensions[name] = {"assessment": "SUBJECTIVE", "score": None, "evidence": evidence,
                                "status": "REVIEW_REQUIRED", "review_note": "Subjective judgement cannot be auto-passed."}
    pdf = root / "论文" / "论文.pdf"
    blockers = [name for name, item in dimensions.items() if item["status"] == "REVIEW_REQUIRED"]
    return {
        "schema_version": 2, "verdict": "REVIEW_REQUIRED", "hard_gates_pass": False,
        "automation_policy": "NO_AUTOMATIC_PASS_OR_SUBJECTIVE_SCORE",
        "pdf_binding": {"path": "论文/论文.pdf", "sha256": sha256_file(pdf) if pdf.exists() else None},
        "objective_metrics": checks, "dimensions": dimensions, "total": None,
        "p0_findings": [], "p1_findings": [], "review_required": blockers,
        "residual_risks": ["Machine hashes establish file identity only.", "All 12 scores and final verdict require accountable review."],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--no-layout-update", action="store_true")
    parser.add_argument("--no-scorecard", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    tex = root / "论文" / "论文.tex"
    if not tex.exists():
        parser.error(f"missing {tex}")
    review = root / "审查"
    previous = load_json(review / "评分卡.json", {})
    fig_registry, dia_registry, coverage = build_registries(root, not args.no_layout_update)
    write_json(review / "figure-registry.json", fig_registry)
    write_json(review / "diagram-registry.json", dia_registry)
    write_json(review / "registry-coverage.json", {"schema_version": 1, "tex_source": "论文/论文.tex", "items": coverage})
    checks = objective_checks(root, fig_registry, dia_registry, coverage)
    if not args.no_scorecard:
        write_json(review / "评分卡.json", scorecard(root, checks, previous))
    result = {"pass": checks["registry_coverage_complete"] and checks["provenance_hashes_verified"],
              "figures": len(fig_registry["figures"]), "diagrams": len(dia_registry["diagrams"]),
              "objective_metrics": checks, "scorecard_verdict": "REVIEW_REQUIRED" if not args.no_scorecard else None}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
