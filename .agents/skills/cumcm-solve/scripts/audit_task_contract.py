#!/usr/bin/env python
"""Validate a CUMCM task contract before solve-stage coding begins."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_evidence import audit_contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default="求解/任务契约.json")
    parser.add_argument("--expected-questions", type=int)
    args = parser.parse_args()

    path = Path(args.contract).resolve()
    contract, issues = audit_contract(path)
    count = len(contract.get("问题", [])) if contract else 0
    if args.expected_questions is not None and count != args.expected_questions:
        issues.append(f"expected {args.expected_questions} questions, found {count}")
    result = {"pass": not issues, "contract": str(path), "questions": count, "issues": issues}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
