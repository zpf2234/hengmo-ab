#!/usr/bin/env python3
"""Verify --fail-on-similarity blocks instead of passing when originality was never proven.

阶段 3 invokes the originality gate as ``benchmark_corpus.py --root . --fail-on-similarity``.
The flag only ever reacted to ``FAIL_HIGH_SIMILARITY``, so every state in which the
comparison did not actually happen -- no candidate paper, a paper whose text layer yields no
abstract, an empty corpus, peers whose text layer is unusable, or a containment score sitting
in the human-review band -- returned 0 and read to the caller as "originality passed". That
is the fail-open pattern this project forbids: automation must not hand out PASS for
something it did not measure.

Fixtures are fully synthetic. Each PDF is drawn with matplotlib so it carries a real text
layer that pypdf can extract, and abstract bodies are exact-length letter runs so the
8-gram containment score lands in a chosen band instead of wherever a real paper happens to
fall. Nothing here reads the local corpus, so the suite runs on a bare checkout.

Exit-code contract pinned by these cases:

- 0  similarity actually ran and cleared the bands (status PASS), or the flag was absent
- 2  status FAIL_HIGH_SIMILARITY (unchanged, kept for existing callers)
- 3  originality is unproven: NOT_RUN, human-review band, empty corpus, unusable peers
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

from benchmark_corpus import originality_report_issues

SCHEMA_VERSION = 2

# Fixture titles carry 摘要/关键词/图/表 markers. Use the same Windows Chinese font family
# as the paper template so the PDF text layer actually retains those markers; suppress a
# warning only for environments where a fallback glyph is still unavailable.
warnings.filterwarnings("ignore", message="Glyph .* missing from font")

# Exit codes the gate must produce.
EXIT_PASS = 0
EXIT_HIGH_SIMILARITY = 2
EXIT_UNPROVEN = 3

ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def filler(seed: str, length: int) -> str:
    """Deterministic letters-only text, unique per seed.

    Letters only, so normalize() in benchmark_corpus keeps every character and the
    n-gram arithmetic in the case table below is exact. No Date.now/random: the same
    seed always yields the same text, which keeps failures reproducible.
    """
    state = sum(ord(char) for char in seed) + len(seed)
    out = []
    for _ in range(length):
        state = (state * 31 + 17) % 104729
        out.append(ALPHABET[state % 26])
    return "".join(out)


# 57 shared characters -> 50 shared 8-grams. Paired with 200 unique characters the
# candidate has 250 8-grams total, so containment = 50/250 = 0.20, inside the
# [0.15, 0.30) human-review band and below the 0.30 failure threshold.
SHARED = filler("shared-overlap-span", 57)


def hard_wrap(text: str, width: int = 95) -> list[str]:
    """Split on a fixed width rather than on spaces, so bodies stay letters-only."""
    return [text[index : index + width] for index in range(0, len(text), width)]


def synth_pdf(path: Path, title: str, abstract: str | None, body: str,
              extra_pages: list[str] | None = None) -> None:
    """Write a PDF whose first page carries title/摘要/关键词 and whose rest carries body."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
            "pdf.fonttype": 42,
            "axes.unicode_minus": False,
        }
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(str(path)) as pdf:
        figure = plt.figure(figsize=(8.27, 11.69))
        # Drawn first so first_nonempty_line() reads it as the title.
        figure.text(0.04, 0.96, title, fontsize=8)
        offset = 0.93
        if abstract is not None:
            figure.text(0.04, offset, "摘要", fontsize=8)
            offset -= 0.02
            for line in hard_wrap(abstract):
                figure.text(0.04, offset, line, fontsize=6)
                offset -= 0.017
            figure.text(0.04, offset - 0.01, "关键词 modelling validation", fontsize=6)
        else:
            # No 摘要 marker: extract_abstract() returns "" even though the text layer works.
            for line in hard_wrap(filler(title, 400)):
                figure.text(0.04, offset, line, fontsize=6)
                offset -= 0.017
        pdf.savefig(figure)
        plt.close(figure)

        for body_page in ([body] if body else []) + (extra_pages or []):
            figure = plt.figure(figsize=(8.27, 11.69))
            offset = 0.96
            for line in hard_wrap(body_page):
                figure.text(0.04, offset, line, fontsize=6)
                offset -= 0.017
            # Figure/table ids keep extraction_quality out of the >10-page "low" branch.
            figure.text(0.04, 0.05, "图 1 表 1", fontsize=6)
            pdf.savefig(figure)
            plt.close(figure)


# A body long enough that normalize(full_text) clears the 1000-character floor in
# extract_pdf, so extraction_quality is "ok" and corpus_extraction_limited stays False.
LONG_BODY = 1200
# Short enough to force extraction_quality == "low" for the unusable-peer case.
SHORT_BODY = 40


def build_case(root: Path, layout: str) -> None:
    """Lay out one synthetic project. Corpus lives in corpus/, candidate in 论文/论文.pdf."""
    corpus = root / "corpus"
    if layout != "missing_corpus":
        corpus.mkdir(parents=True, exist_ok=True)
    paper = root / "论文" / "论文.pdf"
    # Shared 2-grams between candidate title and corpus filename keep title_similarity > 0,
    # which is what lets a peer survive the ranked filter in benchmark_corpus.
    peer_title = "roadway signal timing control"
    peer_name = "(A001)roadway signal timing control.pdf"
    peer_abstract = filler("peer-abstract", 250)
    candidate_abstract = filler("cand-abstract", 250)

    if layout == "high":
        abstract = SHARED + filler("peer-body", 200)
        synth_pdf(corpus / peer_name, peer_title, abstract, filler("pb", LONG_BODY))
        # Byte-identical abstract -> containment 1.0.
        synth_pdf(paper, peer_title + " study", abstract, filler("cb", LONG_BODY))
    elif layout == "band":
        synth_pdf(
            corpus / peer_name,
            peer_title,
            SHARED + filler("peer-body", 200),
            filler("pb", LONG_BODY),
        )
        synth_pdf(
            paper,
            peer_title + " study",
            SHARED + filler("cand-body", 200),
            filler("cb", LONG_BODY),
        )
    elif layout == "distinct":
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("pb", LONG_BODY))
        synth_pdf(
            paper,
            peer_title + " study",
            filler("cand-abstract", 250),
            filler("cb", LONG_BODY),
        )
    elif layout == "missing_paper":
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("pb", LONG_BODY))
        # No candidate written at all.
    elif layout == "no_abstract":
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("pb", LONG_BODY))
        # Text layer works but carries no 摘要 marker.
        synth_pdf(paper, peer_title + " study", None, filler("cb", LONG_BODY))
    elif layout == "empty_corpus":
        synth_pdf(
            paper,
            peer_title + " study",
            filler("cand-abstract", 250),
            filler("cb", LONG_BODY),
        )
    elif layout == "unusable_peers":
        # Peer text layer too thin to compare -> extraction_quality "low".
        synth_pdf(corpus / peer_name, peer_title, filler("p", 30), filler("pb", SHORT_BODY))
        synth_pdf(
            paper,
            peer_title + " study",
            filler("cand-abstract", 250),
            filler("cb", LONG_BODY),
        )
    elif layout == "copied_body":
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("cb", LONG_BODY))
        synth_pdf(paper, peer_title, candidate_abstract, filler("cb", LONG_BODY))
    elif layout == "reference_no_abstract":
        synth_pdf(corpus / peer_name, peer_title, None, filler("pb", LONG_BODY))
        synth_pdf(paper, peer_title, candidate_abstract, filler("cb", LONG_BODY))
    elif layout in {"body_not_abstract_winner", "body_outside_top_k", "cross_track_body"}:
        first_abstract = SHARED + filler("peer-body", 200) if layout == "body_not_abstract_winner" else peer_abstract
        abstract = SHARED + filler("cand-body", 200) if layout == "body_not_abstract_winner" else candidate_abstract
        synth_pdf(corpus / peer_name, peer_title, first_abstract, filler("pb", LONG_BODY))
        other_name = "(B999)zqxv wfjh.pdf" if layout == "cross_track_body" else "(A999)zqxv wfjh.pdf"
        synth_pdf(corpus / other_name, "zqxv wfjh", filler("other-abstract", 250), filler("cb", LONG_BODY))
        synth_pdf(paper, peer_title, abstract, filler("cb", LONG_BODY))
        if layout == "cross_track_body":
            (root / "题目").mkdir(parents=True, exist_ok=True)
            (root / "题目" / "A题.txt").write_text("synthetic track marker", encoding="utf-8")
    elif layout in {"partial_candidate", "partial_reference", "corrupt_reference"}:
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("pb", LONG_BODY),
                  [""] if layout == "partial_reference" else None)
        synth_pdf(paper, peer_title, candidate_abstract, filler("cb", LONG_BODY),
                  [""] if layout == "partial_candidate" else None)
        if layout == "corrupt_reference":
            (corpus / "unreadable.pdf").write_bytes(b"not a PDF")
    elif layout == "missing_corpus":
        synth_pdf(paper, peer_title, candidate_abstract, filler("cb", LONG_BODY))
    elif layout == "self_in_corpus":
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("pb", LONG_BODY))
        synth_pdf(corpus / "candidate.pdf", peer_title, candidate_abstract, filler("cb", LONG_BODY))
    elif layout == "duplicate_bytes":
        synth_pdf(paper, peer_title, candidate_abstract, filler("cb", LONG_BODY))
        (corpus / peer_name).write_bytes(paper.read_bytes())
    elif layout == "appendix_dilution":
        synth_pdf(corpus / peer_name, peer_title, peer_abstract, filler("cb", LONG_BODY))
        synth_pdf(paper, peer_title, candidate_abstract, filler("cb", LONG_BODY),
                  ["参考文献\n" + filler("references-unique", LONG_BODY)] +
                  [filler(f"appendix-{index}", LONG_BODY) for index in range(14)])
    else:  # pragma: no cover - guarded by CASES
        raise ValueError(f"unknown layout {layout}")


# A complete record: an independent reviewer checked the overlapping sentences.
VALID_REVIEW = {
    "pass": True,
    "reviewer": "independent-reviewer-1",
    "reviewer_type": "ai",
    "scope": "抽查 12 处连续句段与公式表述",
    "date": "2026-08-12",
    "candidate_pdf_sha256": "bind-to-fixture",
    "audit_basis_sha256": "bind-to-audit",
}
# pass=True with no accountable reviewer or scope: not enough for a discretionary release.
BARE_REVIEW = {"pass": True}
# A filed review that failed must block, not be ignored.
FAILED_REVIEW = {
    "pass": False,
    "reviewer": "independent-reviewer-1",
    "scope": "抽查 12 处连续句段",
}

# name -> (layout, expected exit, expected status, expected verdict, use flag, review record)
CASES: dict[str, tuple[str, int, str, str, bool, dict | None]] = {
    "distinct_paper_passes": ("distinct", EXIT_PASS, "PASS", "PASS", True, None),
    "high_similarity_blocks": (
        "high",
        EXIT_HIGH_SIMILARITY,
        "FAIL_HIGH_SIMILARITY",
        "FAIL_HIGH_SIMILARITY",
        True,
        None,
    ),
    "human_review_band_blocks": (
        "band",
        EXIT_UNPROVEN,
        "WARN_REVIEW",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        None,
    ),
    "missing_paper_blocks": (
        "missing_paper",
        EXIT_UNPROVEN,
        "NOT_RUN",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        None,
    ),
    "no_abstract_blocks": (
        "no_abstract",
        EXIT_UNPROVEN,
        "WARN_REVIEW",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        None,
    ),
    "empty_corpus_blocks": (
        "empty_corpus",
        EXIT_UNPROVEN,
        "WARN_REVIEW",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        None,
    ),
    "unusable_peers_block": (
        "unusable_peers",
        EXIT_UNPROVEN,
        "WARN_REVIEW",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        None,
    ),
    "stage0_tolerates_missing_paper": (
        "missing_paper",
        EXIT_PASS,
        "NOT_RUN",
        "BLOCK_ORIGINALITY_UNPROVEN",
        False,
        None,
    ),
    # benchmarking.md allows the human-review band to be released by an independent review.
    "manual_review_releases_band": (
        "band",
        EXIT_PASS,
        "WARN_REVIEW",
        "PASS_WITH_MANUAL_REVIEW",
        True,
        VALID_REVIEW,
    ),
    "manual_review_without_reviewer_blocks": (
        "band",
        EXIT_UNPROVEN,
        "WARN_REVIEW",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        BARE_REVIEW,
    ),
    "failed_manual_review_blocks": (
        "band",
        EXIT_UNPROVEN,
        "WARN_REVIEW",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        FAILED_REVIEW,
    ),
    # A manual note must never release genuine high similarity.
    "manual_review_cannot_release_high_similarity": (
        "high",
        EXIT_HIGH_SIMILARITY,
        "FAIL_HIGH_SIMILARITY",
        "FAIL_HIGH_SIMILARITY",
        True,
        VALID_REVIEW,
    ),
    # NOT_RUN is never releasable: there is nothing for a reviewer to have checked.
    "manual_review_cannot_release_not_run": (
        "missing_paper",
        EXIT_UNPROVEN,
        "NOT_RUN",
        "BLOCK_ORIGINALITY_UNPROVEN",
        True,
        VALID_REVIEW,
    ),
    "dissimilar_abstract_copied_body_blocks": ("copied_body", 2, "FAIL_HIGH_SIMILARITY", "FAIL_HIGH_SIMILARITY", True, None),
    "reference_without_abstract_still_compared": ("reference_no_abstract", 0, "PASS", "PASS", True, None),
    "body_match_not_abstract_winner_blocks": ("body_not_abstract_winner", 2, "FAIL_HIGH_SIMILARITY", "FAIL_HIGH_SIMILARITY", True, None),
    "body_copy_outside_top_k_blocks": ("body_outside_top_k", 2, "FAIL_HIGH_SIMILARITY", "FAIL_HIGH_SIMILARITY", True, None),
    "cross_track_body_copy_blocks": ("cross_track_body", 2, "FAIL_HIGH_SIMILARITY", "FAIL_HIGH_SIMILARITY", True, None),
    "partial_candidate_blocks": ("partial_candidate", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True, None),
    "partial_reference_blocks": ("partial_reference", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True, None),
    "corrupt_reference_not_silently_skipped": ("corrupt_reference", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True, None),
    "manual_cannot_release_partial_coverage": ("partial_reference", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True, VALID_REVIEW),
    "missing_corpus_reported_unproven": ("missing_corpus", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True, None),
    "self_path_excluded": ("self_in_corpus", 0, "PASS", "PASS", True, None),
    "duplicate_bytes_elsewhere_not_excluded": ("duplicate_bytes", 2, "FAIL_HIGH_SIMILARITY", "FAIL_HIGH_SIMILARITY", True, None),
    "appendix_does_not_dilute_body_copy": ("appendix_dilution", 2, "FAIL_HIGH_SIMILARITY", "FAIL_HIGH_SIMILARITY", True, None),
    "stale_manual_review_blocks": ("band", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True,
                                    {**VALID_REVIEW, "candidate_pdf_sha256": "0" * 64}),
    "changed_corpus_invalidates_same_candidate_review": ("band", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True, VALID_REVIEW),
    "reviewer_type_missing_blocks": ("band", 3, "WARN_REVIEW", "BLOCK_ORIGINALITY_UNPROVEN", True,
                                     {key: value for key, value in VALID_REVIEW.items() if key != "reviewer_type"}),
}


def run_case(script: Path, root: Path, name: str, audit_python: str = sys.executable) -> dict:
    layout, expected_code, expected_status, expected_verdict, use_flag, review = CASES[name]
    build_case(root, layout)
    # Empty corpus map: keeps peer selection driven purely by title similarity, so the
    # project's real corpus-map.json cannot perturb the fixtures.
    corpus_map = root / "corpus-map.json"
    corpus_map.write_text("{}", encoding="utf-8")
    manual_path = root / "manual-review.json"
    paper_relative = "corpus/candidate.pdf" if layout == "self_in_corpus" else "论文/论文.pdf"
    paper_path = root / paper_relative
    if review is not None:
        record = dict(review)
        if record.get("candidate_pdf_sha256") == "bind-to-fixture":
            record["candidate_pdf_sha256"] = hashlib.sha256(paper_path.read_bytes()).hexdigest() if paper_path.exists() else "missing"
        manual_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    command = [
        audit_python,
        str(script),
        "--root",
        str(root),
        "--corpus",
        "corpus",
        "--paper",
        paper_relative,
        "--corpus-map",
        str(corpus_map),
        "--manual-review",
        str(manual_path),
        "--top-k",
        "1",
        "--no-write",
    ]
    if use_flag:
        command.append("--fail-on-similarity")
    if review is not None and record.get("audit_basis_sha256") == "bind-to-audit":
        initial = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
        initial_payload = next((json.loads(line) for line in initial.stdout.splitlines() if line.startswith("{")), {})
        record["audit_basis_sha256"] = initial_payload.get("audit_basis_sha256")
        manual_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    if name == "changed_corpus_invalidates_same_candidate_review":
        # Same candidate bytes, new readable reference exposing another WARN-band span.
        synth_pdf(root / "corpus" / "new-reference.pdf", "new source",
                  filler("new-source-prefix", 200) + filler("cand-body", 200)[:57],
                  filler("new-source-body", LONG_BODY))
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", check=False
    )
    status = None
    verdict = None
    payload = {}
    for line in (completed.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        status = (payload.get("similarity") or {}).get("status")
        verdict = (payload.get("originality_gate") or {}).get("verdict")
    similarity = payload.get("similarity") or {}
    coverage = similarity.get("coverage") or {}
    checks = {"schema_v2": payload.get("schema_version") == 2,
              "all_corpus_scope": coverage.get("scope") == "all_local_corpus_pdfs",
              "basis_binding": bool(payload.get("audit_basis_sha256"))
                  and payload.get("audit_basis_sha256") == (payload.get("originality_gate") or {}).get("audit_basis_sha256")}
    checks["source_snapshot_present"] = (payload.get("corpus_source") or {}).get("discovery") == "top_level_pdf_files_all_tracks"
    if expected_verdict in {"PASS", "PASS_WITH_MANUAL_REVIEW"}:
        checks["live_consumer_accepts_producer"] = not originality_report_issues(payload, paper_path)
    if name == "changed_corpus_invalidates_same_candidate_review":
        checks["stale_review_same_pdf_new_corpus"] = (record["audit_basis_sha256"] != payload.get("audit_basis_sha256")
                                                     and coverage.get("eligible_count") == 2)
    if paper_path.exists():
        expected_sha = hashlib.sha256(paper_path.read_bytes()).hexdigest()
        checks["pdf_sha_binding"] = (payload.get("candidate_pdf") or {}).get("sha256") == expected_sha
        checks["gate_sha_binding"] = (payload.get("originality_gate") or {}).get("candidate_pdf_sha256") == expected_sha
    if layout in {"body_not_abstract_winner", "body_outside_top_k", "cross_track_body"}:
        checks["all_refs_despite_top_k"] = coverage.get("compared_count") == 2 and len(payload.get("peers") or []) == 1
        checks["body_not_abstract_winner"] = similarity.get("closest_body_paper") != similarity.get("closest_paper")
    if layout in {"copied_body", "body_not_abstract_winner", "body_outside_top_k", "cross_track_body", "appendix_dilution"}:
        hits = [hit for row in similarity.get("per_reference", []) for hit in row.get("overlaps", [])]
        checks["actionable_body_page_location"] = any(hit["candidate"]["page"] == 2 and hit["reference"]["page"] == 2
                                                        and hit["matched_normalized_chars"] >= 80 for hit in hits)
        checks["bounded_excerpt"] = all(len(hit[side]["excerpt"]) <= 160 for hit in hits for side in ("candidate", "reference"))
    if layout in {"partial_candidate", "partial_reference", "corrupt_reference"}:
        checks["incomplete_coverage_blocks"] = coverage.get("complete") is False
    if layout == "corrupt_reference":
        checks["unreadable_in_denominator"] = coverage.get("eligible_count") == 2 and len(coverage.get("incomplete_references", [])) == 1
    if layout == "self_in_corpus":
        checks["self_path_excluded"] = len(coverage.get("excluded_self", [])) == 1 and coverage.get("eligible_count") == 1
    if layout == "appendix_dilution":
        checks["body_metric_undiluted"] = similarity.get("body_containment", 0) >= 0.9 and similarity.get("full_text_containment", 1) < 0.1
    if layout == "reference_no_abstract":
        checks["reference_abstract_unavailable_not_body_failure"] = (coverage.get("complete") is True
            and coverage.get("compared_count") == 1 and coverage.get("abstract_compared_count") == 0
            and similarity.get("max_containment") is None and similarity.get("full_text_containment") is not None)
    return {
        "expected_exit": expected_code,
        "actual_exit": completed.returncode,
        "expected_status": expected_status,
        "actual_status": status,
        "expected_verdict": expected_verdict,
        "actual_verdict": verdict,
        "pass": (
            completed.returncode == expected_code
            and status == expected_status
            and verdict == expected_verdict
            and all(checks.values())
        ),
        "checks": checks,
        "stderr": (completed.stderr or "").strip()[-200:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/similarity-gate-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--audit-python", default=sys.executable,
                        help="optional alternate runtime for PDF audit; fixture generation stays in this runtime")
    args = parser.parse_args()

    script = Path(__file__).resolve().parent / "benchmark_corpus.py"
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-similarity-selftest-") as tmp:
        base = Path(tmp)
        for name in CASES:
            results[name] = run_case(script, base / name, name, args.audit_python)

    result = {
        "schema_version": SCHEMA_VERSION,
        "pass": all(item["pass"] for item in results.values()),
        "case_count": len(results),
        "cases": results,
    }
    if not args.no_write:
        output = Path(args.root).resolve() / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = sorted(name for name, item in results.items() if not item["pass"])
    print(
        json.dumps(
            {"pass": result["pass"], "case_count": len(results), "failed": failed},
            ensure_ascii=False,
        )
    )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
