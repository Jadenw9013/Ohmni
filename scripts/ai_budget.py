#!/usr/bin/env python3
"""Local operator tool for the AI request budget. There is no HTTP equivalent.

    python scripts/ai_budget.py show  [--path FILE]
    python scripts/ai_budget.py reset --day YYYY-MM-DD [--path FILE]

`show` prints the effective limits (from OHMNI_AI_* environment variables) and
today's admitted count. `reset` deletes one UTC day's count, for a presenter's
preflight on a machine they control. It never contacts a deployed server.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from ohmni.application.request_budget import BudgetUnavailable, RequestBudget, reset_day

DEFAULT_PATH = Path(os.environ.get("OHMNI_OUTPUT_DIR") or ROOT / "out" / "demo-jobs") / "ai-request-budget.sqlite3"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("show", "reset"))
    parser.add_argument("--path", type=Path, default=None, help=f"budget database (default {DEFAULT_PATH})")
    parser.add_argument("--day", help="UTC day to reset, YYYY-MM-DD")
    args = parser.parse_args(argv)
    budget = RequestBudget.from_environment(args.path or DEFAULT_PATH)
    try:
        if args.command == "show":
            print(json.dumps({**budget.describe(), "admitted_today": budget.admitted_today()}, indent=2))
            return 0
        if not args.day:
            parser.error("reset requires --day")
        removed = reset_day(budget.path, args.day)
        print(f"Removed {removed} admitted requests recorded for {args.day} in {budget.path}")
        return 0
    except BudgetUnavailable:
        print("The budget database could not be read or written.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
