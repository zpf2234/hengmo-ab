#!/usr/bin/env python
"""Validate task contracts from independent cross-archetype routing tests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS_DIR / "cumcm-solve" / "scripts"))

from audit_evidence import audit_contract  # noqa: E402


DEFAULT_ARCHETYPES = {"机理", "几何", "统计", "优化", "决策", "逆问题"}


def evaluate(path: Path) -> dict:
    contract, issues = audit_contract(path)
    archetypes = set()
    if contract:
        for question in contract.get("问题", []):
            archetypes.update(question.get("原型", []))
    return {
        "path": str(path.resolve()),
        "pass": not issues,
        "title": contract.get("赛题标题") if contract else None,
        "archetypes": sorted(archetypes),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", nargs="+", required=True)
    parser.add_argument("--min-contracts", type=int, default=6)
    parser.add_argument("--required-archetypes", nargs="*", default=sorted(DEFAULT_ARCHETYPES))
    parser.add_argument("--output")
    args = parser.parse_args()

    items = [evaluate(Path(path)) for path in args.contracts]
    covered = set().union(*(set(item["archetypes"]) for item in items)) if items else set()
    required = set(args.required_archetypes)
    issues = []
    if len(items) < args.min_contracts:
        issues.append(f"contracts below minimum: {len(items)} < {args.min_contracts}")
    if any(not item["pass"] for item in items):
        issues.append("one or more contracts are invalid")
    missing_archetypes = sorted(required - covered)
    if missing_archetypes:
        issues.append(f"archetypes not covered: {', '.join(missing_archetypes)}")
    titles = [item["title"] for item in items if item["title"]]
    if len(set(titles)) != len(titles):
        issues.append("duplicate problem titles in routing suite")

    result = {
        "pass": not issues,
        "contract_count": len(items),
        "covered_archetypes": sorted(covered),
        "required_archetypes": sorted(required),
        "issues": issues,
        "contracts": items,
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        print(f"Wrote {Path(args.output).resolve()}")
    else:
        print(payload)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
