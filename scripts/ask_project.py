#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph
from src.config import settings
from src.storage.project_index import ProjectIndexRepository


JSON_FIELDS = (
    "answer",
    "request_type",
    "related_paths",
    "approval_required",
    "open_questions",
    "suggested_commands",
    "research_note_id",
    "thread_id",
    "flow_version",
)


def _default_thread_id(question: str) -> str:
    digest = hashlib.sha1(question.encode("utf-8")).hexdigest()[:12]
    return f"cli-{digest}"


def _json_payload(result: dict[str, Any], thread_id: str) -> dict[str, Any]:
    payload = {field: result.get(field) for field in JSON_FIELDS if field in result}
    payload["thread_id"] = thread_id
    payload.setdefault("related_paths", [])
    payload.setdefault("approval_required", False)
    payload.setdefault("open_questions", [])
    payload.setdefault("suggested_commands", [])
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the local project knowledge assistant.")
    parser.add_argument("--question", required=True, help="Project question to ask")
    parser.add_argument("--db", default=settings.PROJECT_INDEX_DB, help="Path to project_index.sqlite")
    parser.add_argument("--project-root", default=settings.TARGET_PROJECT_ROOT, help="Target project root")
    parser.add_argument("--thread-id", default=None, help="Assistant thread id")
    parser.add_argument("--output", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args(argv)

    question = args.question.strip()
    if not question:
        print("question must not be empty", file=sys.stderr)
        return 2

    db_path = Path(args.db).expanduser()
    if not db_path.exists():
        print(f"project index database not found: {db_path}", file=sys.stderr)
        return 2

    project_root = Path(args.project_root).expanduser()
    thread_id = args.thread_id or _default_thread_id(question)

    try:
        repo = ProjectIndexRepository(db_path)
        graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())
        result = graph.invoke(
            {
                "question": question,
                "project_root": str(project_root),
                "index_db_path": str(db_path),
                "thread_id": thread_id,
            },
            {"configurable": {"thread_id": thread_id}},
        )
    except Exception as exc:
        print(f"assistant graph failed: {exc}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(json.dumps(_json_payload(result, thread_id), ensure_ascii=False))
    else:
        print(result.get("answer", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
