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
import json
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

SCHEMA_VERSION = 1

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


def synth_pdf(path: Path, title: str, abstract: str | None, body: str) -> None:
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

        if body:
            figure = plt.figure(figsize=(8.27, 11.69))
            offset = 0.96
            for line in hard_wrap(body):
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
    corpus.mkdir(parents=True, exist_ok=True)
    paper = root / "论文" / "论文.pdf"
    # Shared 2-grams between candidate title and corpus filename keep title_similarity > 0,
    # which is what lets a peer survive the ranked filter in benchmark_corpus.
    peer_title = "roadway signal timing control"
    peer_name = "(A001)roadway signal timing control.pdf"
    peer_abstract = filler("peer-abstract", 250)

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
    else:  # pragma: no cover - guarded by CASES
        raise ValueError(f"unknown layout {layout}")


# A complete record: an independent reviewer checked the overlapping sentences.
VALID_REVIEW = {
    "pass": True,
    "reviewer": "independent-reviewer-1",
    "scope": "抽查 12 处连续句段与公式表述",
    "date": "2026-08-12",
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
        "NOT_RUN",
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
}


def run_case(script: Path, root: Path, name: str) -> dict:
    layout, expected_code, expected_status, expected_verdict, use_flag, review = CASES[name]
    build_case(root, layout)
    # Empty corpus map: keeps peer selection driven purely by title similarity, so the
    # project's real corpus-map.json cannot perturb the fixtures.
    corpus_map = root / "corpus-map.json"
    corpus_map.write_text("{}", encoding="utf-8")
    manual_path = root / "manual-review.json"
    if review is not None:
        manual_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")
    command = [
        sys.executable,
        str(script),
        "--root",
        str(root),
        "--corpus",
        "corpus",
        "--paper",
        "论文/论文.pdf",
        "--corpus-map",
        str(corpus_map),
        "--manual-review",
        str(manual_path),
        "--no-write",
    ]
    if use_flag:
        command.append("--fail-on-similarity")
    completed = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", check=False
    )
    status = None
    verdict = None
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
        ),
        "stderr": (completed.stderr or "").strip()[-200:],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="审查/similarity-gate-selftest.json")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    script = Path(__file__).resolve().parent / "benchmark_corpus.py"
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="cumcm-similarity-selftest-") as tmp:
        base = Path(tmp)
        for name in CASES:
            results[name] = run_case(script, base / name, name)

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
