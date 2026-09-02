#!/usr/bin/env python3
"""Create non-fabricated national-first review templates for an existing CUMCM project."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

DIMENSIONS = (
    "题意与口径", "数据理解", "模型适配", "数学严谨", "求解实现", "验证强度",
    "结果价值", "证据追溯", "可复现性", "写作原创", "可视表达", "提交就绪",
)
DIAGRAM_WORDS = ("流程", "拓扑", "关系", "机理", "框图", "示意")


def write_json(path: Path, value: object, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256(path: Path) -> str | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_graphic(root: Path, paper_dir: Path, raw: str) -> Path | None:
    raw_path = Path(raw)
    candidates = [paper_dir / raw_path, root / raw_path]
    if raw_path.suffix:
        candidates.extend(root.glob(f"求解/问题*/图片/{raw_path.name}"))
    else:
        for suffix in (".pdf", ".svg", ".png"):
            candidates.extend(root.glob(f"求解/问题*/图片/{raw_path.name}{suffix}"))
    return next((path for path in candidates if path.exists()), None)


def source_for(image: Path) -> Path | None:
    for suffix in (".vsdx", ".tex", ".tikz", ".drawio", ".m", ".py"):
        candidate = image.with_suffix(suffix)
        if candidate.exists():
            return candidate
    for candidate in image.parent.parent.glob("*.py"):
        return candidate
    return None


def normalized_stem(path: Path) -> str:
    return re.sub(r"(?:_final|_preview)$", "", path.stem, flags=re.IGNORECASE)


def layout_for(image: Path) -> Path | None:
    direct = image.with_suffix(".layout.json")
    if direct.exists():
        return direct
    stem = normalized_stem(image)
    simplified = stem.replace("序贯判定流程", "sprt_flow").replace("再生决策流程", "regenerative_decision_flow")
    simplified = simplified.replace("完整枚举流程", "hierarchical_enumeration_flow").replace("稳健重优化流程", "robust_reoptimization_flow")
    candidates = list(image.parent.glob("*.layout.json"))
    return next((path for path in candidates if simplified in path.stem or path.stem in stem), None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--force", action="store_true", help="overwrite existing review templates")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    paper_dir = root / "论文"
    tex_path = paper_dir / "论文.tex"
    if not tex_path.exists():
        parser.error(f"missing {tex_path}")
    tex = tex_path.read_text(encoding="utf-8", errors="ignore")
    review = root / "审查"
    provenance_dir = review / "provenance"
    figures: list[dict] = []
    diagrams: list[dict] = []
    created: list[str] = []

    blocks = re.findall(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", tex, re.DOTALL)
    for number, block in enumerate(blocks, start=1):
        image_match = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", block)
        caption_match = re.search(r"\\caption(?:\[[^\]]*\])?\{([^}]*)\}", block)
        label_match = re.search(r"\\label\{([^}]+)\}", block)
        if not image_match or not caption_match or not label_match:
            continue
        raw, caption, label = image_match.group(1), caption_match.group(1), label_match.group(1)
        image = resolve_graphic(root, paper_dir, raw)
        if image is None:
            continue
        item_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or f"figure-{number}"
        source = source_for(image)
        provenance_path = provenance_dir / f"{item_id}.json"
        provenance = {
            "schema_version": 1,
            "artifact_id": item_id,
            "status": "UNVERIFIED_TEMPLATE",
            "mode": "script" if source and source.suffix.lower() in {".py", ".m"} else "mcp",
            "renderer": None,
            "tool": None,
            "invocation_recorded": False,
            "source": rel(root, source) if source else None,
            "output": rel(root, image),
            "notes": "填写真实调用、规格、版本和产物哈希后再把状态改为 VERIFIED。",
        }
        if write_json(provenance_path, provenance, args.force):
            created.append(rel(root, provenance_path))
        generation = {
            "mode": provenance["mode"],
            "renderer": "UNVERIFIED",
            "tool": "UNVERIFIED",
            "health_pass": False,
            "spec_path": rel(root, source) if source else "UNRESOLVED",
            "provenance_manifest": rel(root, provenance_path),
        }
        is_diagram = any(word in image.stem or word in caption for word in DIAGRAM_WORDS)
        if is_diagram:
            layout = layout_for(image)
            diagrams.append({
                "id": item_id,
                "role": "flowchart" if "流程" in caption else "relationship",
                "purpose": caption,
                "claim_ids": ["TODO-CLAIM-ID"],
                "style_family": "visio" if source and source.suffix.lower() in {".vsdx", ".drawio"} else "tikz",
                "source": rel(root, source) if source else "UNRESOLVED",
                "vector_output": rel(root, image),
                "layout": rel(root, layout) if layout else "UNRESOLVED",
                "insert_width_mm": 120,
                "final_min_font_pt": 0,
                "generation": generation,
                "vector_audit": {"true_vector": image.suffix.lower() in {".pdf", ".svg"}, "aspect_ratio_distortion": None},
                "visual_review": {
                    "actual_size_render": "UNRESOLVED", "full_page_render": "UNRESOLVED",
                    "thumbnail_render": "UNRESOLVED", "grayscale_render": "UNRESOLVED",
                    "publication_ready": False,
                },
            })
        else:
            figures.append({
                "id": item_id,
                "category": "other_evidence",
                "purpose": caption,
                "claim_ids": ["TODO-CLAIM-ID"],
                "source_data": ["UNRESOLVED"],
                "generator": rel(root, source) if source else "UNRESOLVED",
                "vector_output": rel(root, image),
                "insert_width_mm": 120,
                "final_min_font_pt": 0,
                "generation": generation,
                "vector_audit": {"true_vector": image.suffix.lower() in {".pdf", ".svg"}, "aspect_ratio_distortion": None},
                "visual_review": {
                    "actual_size_render": "UNRESOLVED", "full_page_render": "UNRESOLVED",
                    "thumbnail_render": "UNRESOLVED", "grayscale_render": "UNRESOLVED",
                    "publication_ready": False,
                },
                "style": {
                    "background": "white", "color_count": 0, "colorblind_safe": False,
                    "data_geometry_untouched": False, "units_complete": False,
                    "final_page_checked": False, "grayscale_pass": False, "title_inside": False,
                    "decorative_effects": False, "legend_occludes_data": False,
                    "default_software_theme": False, "manual_data_point_editing": False,
                },
                "role_specific_checks": [],
            })

    outputs = {
        review / "figure-registry.json": {"schema_version": 1, "status": "TEMPLATE_NOT_REVIEWED", "figures": figures},
        review / "diagram-registry.json": {"schema_version": 1, "status": "TEMPLATE_NOT_REVIEWED", "diagrams": diagrams},
        review / "内容审查.json": {
            "schema_version": 1, "status": "TEMPLATE_NOT_REVIEWED", "full_text_read": False,
            "sections_reviewed": 0, "total_sections": len(re.findall(r"\\section\{", tex)),
            "p0_findings": ["TODO: 完成全文逐节审查"], "p1_findings": [], "section_reviews": [],
        },
        review / "评分卡.json": {
            "schema_version": 2, "verdict": "REVIEW_REQUIRED",
            "hard_gates_pass": False,
            "automation_policy": "NO_AUTOMATIC_PASS_OR_SUBJECTIVE_SCORE",
            "pdf_binding": {"path": "论文/论文.pdf", "sha256": sha256(paper_dir / "论文.pdf")},
            "dimensions": {name: {"score": None, "evidence": [], "status": "REVIEW_REQUIRED"} for name in DIMENSIONS},
            "total": None, "review_required": list(DIMENSIONS),
            "p0_findings": [], "p1_findings": [],
            "residual_risks": ["模板不得作为 PASS 证据"],
        },
    }
    for path, value in outputs.items():
        if write_json(path, value, args.force):
            created.append(rel(root, path))
    print(json.dumps({"created": created, "tex_figures": len(figures) + len(diagrams), "figures": len(figures), "diagrams": len(diagrams)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
