from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class ExpectedPath:
    path: str
    max_rank: int = 5


@dataclass(frozen=True)
class NoisePath:
    path: str
    disallowed_above_rank: int = 3


@dataclass(frozen=True)
class RetrievalEvalCase:
    id: str
    query: str
    expected_paths: list[ExpectedPath]
    noise_paths: list[NoisePath] = field(default_factory=list)
    limit: int = 8


@dataclass(frozen=True)
class RetrievalEvalOutcome:
    case_id: str
    query: str
    passed: bool
    failures: list[str]
    top_paths: list[str]
    result_count: int


def _rank_by_path(results: list[dict[str, Any]]) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for index, item in enumerate(results, start=1):
        path = str(item.get("path") or "")
        if path and path not in ranks:
            ranks[path] = index
    return ranks


def evaluate_case(case: RetrievalEvalCase, results: list[dict[str, Any]]) -> RetrievalEvalOutcome:
    limited_results = results[: case.limit]
    ranks = _rank_by_path(limited_results)
    failures: list[str] = []

    for expected in case.expected_paths:
        rank = ranks.get(expected.path)
        if rank is None:
            failures.append(f"expected path missing: {expected.path}")
        elif rank > expected.max_rank:
            failures.append(f"expected path ranked too low: {expected.path} at rank {rank}, max {expected.max_rank}")

    for noise in case.noise_paths:
        rank = ranks.get(noise.path)
        if rank is not None and rank <= noise.disallowed_above_rank:
            failures.append(f"noise path ranked too high: {noise.path} at rank {rank}")

    return RetrievalEvalOutcome(
        case_id=case.id,
        query=case.query,
        passed=not failures,
        failures=failures,
        top_paths=[str(item.get("path") or "") for item in limited_results],
        result_count=len(limited_results),
    )


RetrievalFn = Callable[[str | Path, str, int], list[dict[str, Any]]]


def _case_from_dict(data: dict[str, Any]) -> RetrievalEvalCase:
    return RetrievalEvalCase(
        id=str(data["id"]),
        query=str(data["query"]),
        expected_paths=[
            ExpectedPath(path=str(item["path"]), max_rank=int(item.get("max_rank", 5)))
            for item in data.get("expected_paths", [])
        ],
        noise_paths=[
            NoisePath(
                path=str(item["path"]),
                disallowed_above_rank=int(item.get("disallowed_above_rank", 3)),
            )
            for item in data.get("noise_paths", [])
        ],
        limit=int(data.get("limit", 8)),
    )


def load_eval_cases(path: str | Path) -> list[RetrievalEvalCase]:
    root = Path(path)
    files = sorted(root.glob("*.json")) if root.is_dir() else [root]
    cases: list[RetrievalEvalCase] = []
    for file_path in files:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else [raw]
        cases.extend(_case_from_dict(item) for item in items)
    return cases


def evaluate_cases(
    db_path: str | Path,
    cases: list[RetrievalEvalCase],
    retrieval_fn: RetrievalFn,
) -> list[RetrievalEvalOutcome]:
    outcomes: list[RetrievalEvalOutcome] = []
    for case in cases:
        results = retrieval_fn(db_path, case.query, case.limit)
        outcomes.append(evaluate_case(case, results))
    return outcomes


def format_eval_report(outcomes: list[RetrievalEvalOutcome]) -> str:
    passed = sum(1 for outcome in outcomes if outcome.passed)
    lines = [f"Retrieval eval: {passed}/{len(outcomes)} passed"]
    for outcome in outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        lines.append(f"- {outcome.case_id}: {status}")
        lines.append(f"  query: {outcome.query}")
        lines.append(f"  top_paths: {', '.join(outcome.top_paths) if outcome.top_paths else '<none>'}")
        for failure in outcome.failures:
            lines.append(f"  failure: {failure}")
    return "\n".join(lines)
