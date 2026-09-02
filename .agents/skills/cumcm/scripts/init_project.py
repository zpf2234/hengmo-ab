#!/usr/bin/env python
"""Initialize the standard CUMCM workspace layout."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DIRS = ["题目", "数据", "求解", "论文", "附件", "审查"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="CUMCM project root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in DIRS:
        (root / name).mkdir(exist_ok=True)

    state = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "layout": DIRS,
        "contract": "CUMCM 2026 electronic paper: abstract first page, no table of contents, paper <=20MB, support archive <=20MB.",
        "page_policy": {
            "body_definition": "body:start through the page before appendix:start; includes AI statement and references; excludes abstract and appendix",
            "body_page_max": 30,
            "ai_statement_before_references": True,
            "references_start_on_new_page": False,
            "appendix_and_after_page_limit": None,
        },
        "workflow_policy": {
            "mode": "semi-automatic",
            "confirmation_record": "审查/用户确认节点.json",
            "method_result_confirmation_required": True,
            "outline_page_confirmation_required": True,
        },
        "delivery_contract": {
            "paper_master": "论文/论文.tex",
            "paper_pdf": "论文/论文.pdf",
            "single_master_tex": True,
            "chapter_tex_imports_forbidden": True,
            "attachments_directory": "附件",
        },
    }
    state_path = root / ".cumcm_state.json"
    if not state_path.exists():
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Initialized CUMCM workspace: {root}")
    for name in DIRS:
        print(f"- {name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
