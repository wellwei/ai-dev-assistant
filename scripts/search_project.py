#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings
from src.retriever.hybrid_search import hybrid_search_project
from src.retriever.keyword_search import search_project_index


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_result(item: dict[str, Any], rank: int) -> dict[str, Any]:
    hybrid_score = _safe_float(item.get("hybrid_score"))
    keyword_score = _safe_float(item.get("keyword_score"))
    vector_score = _safe_float(item.get("vector_score"))
    keyword_only_score = _safe_float(item.get("score"))
    score = hybrid_score if hybrid_score is not None else keyword_only_score
    return {
        "rank": rank,
        "path": item.get("path") or "",
        "file_type": item.get("file_type") or "",
        "language": item.get("language") or "",
        "summary": item.get("summary") or "",
        "key_points": item.get("key_points") or "",
        "ranking_reason": item.get("ranking_reason") or "",
        "score": score,
        "hybrid_score": hybrid_score,
        "keyword_score": keyword_score,
        "vector_score": vector_score,
        "confidence": item.get("confidence") or "",
        "evidence": item.get("evidence") or "",
        "risks": item.get("risks") or "",
        "inconsistencies": item.get("inconsistencies") or "",
    }


def _json_payload(query: str, db_path: Path, limit: int, results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "query": query,
        "db": str(db_path),
        "limit": limit,
        "result_count": len(results),
        "results": results,
    }


def _format_score(value: float | None) -> str:
    if value is None:
        return "none"
    return f"{value:.4g}"


def _format_text(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No indexed project paths matched the query."
    lines: list[str] = []
    for item in results:
        lines.append(f"{item['rank']}. {item['path']}")
        lines.append(
            "   score: "
            f"{_format_score(item['score'])} "
            f"hybrid={_format_score(item['hybrid_score'])} "
            f"keyword={_format_score(item['keyword_score'])} "
            f"vector={_format_score(item['vector_score'])} "
            f"confidence={item['confidence']}"
        )
        lines.append(f"   reason: {item['ranking_reason']}")
        lines.append(f"   summary: {item['summary']}")
        if item["key_points"]:
            lines.append(f"   key_points: {item['key_points']}")
        if item["evidence"]:
            lines.append(f"   evidence: {item['evidence']}")
        if item["risks"]:
            lines.append(f"   risks: {item['risks']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _search(db_path: Path, query: str, limit: int) -> list[dict[str, Any]]:
    try:
        return hybrid_search_project(db_path, query, limit=limit)
    except Exception:
        return search_project_index(db_path, query, limit=limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Search ranked project index paths without synthesizing an answer.")
    parser.add_argument("--query", required=True, help="Project search query")
    parser.add_argument("--db", default=settings.PROJECT_INDEX_DB, help="Path to project_index.sqlite")
    parser.add_argument("--limit", type=int, default=8, help="Maximum ranked results to return, 1-50")
    parser.add_argument("--output", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args(argv)

    query = args.query.strip()
    if not query:
        print("query must not be empty", file=sys.stderr)
        return 2
    if args.limit < 1 or args.limit > 50:
        print("limit must be between 1 and 50", file=sys.stderr)
        return 2

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"project index database not found: {db_path}", file=sys.stderr)
        return 2

    try:
        results = [_normalize_result(item, index + 1) for index, item in enumerate(_search(db_path, query, args.limit))]
    except Exception as exc:
        print(f"project search failed: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps(_json_payload(query, db_path, args.limit, results), ensure_ascii=False))
    else:
        print(_format_text(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
