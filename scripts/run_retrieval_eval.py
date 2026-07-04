#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retriever.evaluation import evaluate_cases, format_eval_report, load_eval_cases
from src.retriever.hybrid_search import hybrid_search_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run retrieval ranking evaluation cases.")
    parser.add_argument("--db", required=True, help="Path to project_index.sqlite")
    parser.add_argument("--cases", required=True, help="JSON case file or directory")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"project index database not found: {db_path}", file=sys.stderr)
        return 2

    cases = load_eval_cases(args.cases)
    if not cases:
        print(f"no retrieval eval cases found: {args.cases}", file=sys.stderr)
        return 2

    outcomes = evaluate_cases(db_path, cases, hybrid_search_project)
    print(format_eval_report(outcomes))
    return 0 if all(outcome.passed for outcome in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
