# Retrieval Evaluation Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable retrieval evaluation baseline so ranking changes can be measured with realistic project questions before they affect assistant answers.

**Architecture:** Add a small evaluation module that loads JSON cases, runs a retrieval function, checks expected paths and noisy paths by rank, and prints a compact report. Keep the evaluator independent from SQLite by accepting a retrieval callable, then add a CLI that wires it to `hybrid_search_project()` for real project-index runs.

**Tech Stack:** Python 3.10+, SQLite, existing `ProjectIndexRepository`, existing `hybrid_search_project`, pytest. No new runtime dependencies.

## Global Constraints

- Target C++ project path is `/Users/cltx/projects/escort_server/doll_escort_game_svr`.
- Treat the target C++ project as read-only by default.
- Do not edit, build, commit, push, clean, delete, or otherwise mutate the target C++ project.
- Current implementation evidence outranks comments, documentation, names, and historical assistant memory.
- Internal model-facing text must be English; final user-facing `answer` text must be Chinese.
- Do not continue Hermes Agent integration work.
- Every implementation, behavior, retrieval ranking, schema, safety boundary, or documentation rule change must update the current dated history file under `docs/superpowers/history/`.
- Run the full test suite before claiming completion.

---

## File Structure

Create or modify these files:

```text
src/retriever/evaluation.py
tests/fixtures/retrieval_eval/escort_route.json
tests/test_retrieval_evaluation.py
scripts/run_retrieval_eval.py
README.md
docs/superpowers/history/2026-07-03-development-history.md
```

Responsibilities:

- `src/retriever/evaluation.py`: Pure evaluation dataclasses and functions. No SQLite dependency.
- `tests/fixtures/retrieval_eval/escort_route.json`: Realistic route/escort retrieval cases.
- `tests/test_retrieval_evaluation.py`: Unit tests for pass/fail behavior, fixture loading, and a seeded hybrid-search regression.
- `scripts/run_retrieval_eval.py`: Local CLI that runs cases against a project-index SQLite database.
- `README.md`: Documents how agents run retrieval eval before ranking changes.
- `docs/superpowers/history/2026-07-03-development-history.md`: Records the implemented change.

---

### Task 1: Add Pure Retrieval Evaluation Model

**Files:**
- Create: `src/retriever/evaluation.py`
- Test: `tests/test_retrieval_evaluation.py`

**Interfaces:**
- Consumes: retrieval result dictionaries with at least `path`; optional `hybrid_score`, `score`, `ranking_reason`.
- Produces:
  - `ExpectedPath(path: str, max_rank: int = 5)`
  - `NoisePath(path: str, disallowed_above_rank: int = 3)`
  - `RetrievalEvalCase(id: str, query: str, expected_paths: list[ExpectedPath], noise_paths: list[NoisePath], limit: int = 8)`
  - `RetrievalEvalOutcome(case_id: str, query: str, passed: bool, failures: list[str], top_paths: list[str], result_count: int)`
  - `evaluate_case(case, results) -> RetrievalEvalOutcome`

- [ ] **Step 1: Write failing tests for pass/fail behavior**

Add to `tests/test_retrieval_evaluation.py`:

```python
from src.retriever.evaluation import ExpectedPath, NoisePath, RetrievalEvalCase, evaluate_case


def test_evaluate_case_passes_when_expected_paths_rank_and_noise_is_low():
    case = RetrievalEvalCase(
        id="escort_route_recalc",
        query="押镖 route 重算 风险",
        expected_paths=[ExpectedPath("src/map_data/sea_route.cpp", max_rank=2)],
        noise_paths=[NoisePath("CMakeLists.txt", disallowed_above_rank=2)],
        limit=5,
    )
    results = [
        {"path": "src/map_data/sea_route.cpp", "hybrid_score": 120.0},
        {"path": "src/rtb_proc/character/rtb_proc_character_recalc_rout.cpp", "hybrid_score": 90.0},
        {"path": "CMakeLists.txt", "hybrid_score": 40.0},
    ]

    outcome = evaluate_case(case, results)

    assert outcome.passed is True
    assert outcome.failures == []
    assert outcome.top_paths == [
        "src/map_data/sea_route.cpp",
        "src/rtb_proc/character/rtb_proc_character_recalc_rout.cpp",
        "CMakeLists.txt",
    ]


def test_evaluate_case_fails_missing_expected_path_and_early_noise():
    case = RetrievalEvalCase(
        id="escort_route_noise",
        query="押镖 route 重算 风险",
        expected_paths=[ExpectedPath("src/map_data/sea_route.cpp", max_rank=2)],
        noise_paths=[NoisePath("CMakeLists.txt", disallowed_above_rank=2)],
        limit=5,
    )
    results = [
        {"path": "CMakeLists.txt", "hybrid_score": 100.0},
        {"path": "linux_prj/route.ini", "hybrid_score": 90.0},
    ]

    outcome = evaluate_case(case, results)

    assert outcome.passed is False
    assert "expected path missing: src/map_data/sea_route.cpp" in outcome.failures
    assert "noise path ranked too high: CMakeLists.txt at rank 1" in outcome.failures
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py -q
```

Expected: FAIL because `src.retriever.evaluation` does not exist.

- [ ] **Step 3: Implement the pure evaluator**

Create `src/retriever/evaluation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py -q
```

Expected: PASS.

---

### Task 2: Add JSON Fixture Loading and Report Formatting

**Files:**
- Modify: `src/retriever/evaluation.py`
- Create: `tests/fixtures/retrieval_eval/escort_route.json`
- Modify: `tests/test_retrieval_evaluation.py`

**Interfaces:**
- Consumes: JSON files containing retrieval eval case dictionaries.
- Produces:
  - `load_eval_cases(path: str | Path) -> list[RetrievalEvalCase]`
  - `evaluate_cases(db_path, cases, retrieval_fn) -> list[RetrievalEvalOutcome]`
  - `format_eval_report(outcomes) -> str`

- [ ] **Step 1: Add a realistic fixture file**

Create `tests/fixtures/retrieval_eval/escort_route.json`:

```json
[
  {
    "id": "escort_route_recalc_business_impl",
    "query": "押镖 route 重算 风险",
    "limit": 8,
    "expected_paths": [
      {"path": "src/map_data/sea_route.cpp", "max_rank": 2}
    ],
    "noise_paths": [
      {"path": "CMakeLists.txt", "disallowed_above_rank": 3},
      {"path": "linux_prj/route.ini", "disallowed_above_rank": 3},
      {"path": "worker_task.AFCfile", "disallowed_above_rank": 3}
    ]
  },
  {
    "id": "escort_client_second_route_query",
    "query": "客户端 查询 二段路线",
    "limit": 8,
    "expected_paths": [
      {"path": "src/task/tcp/process_cli_query_second_route_tcp_task.cpp", "max_rank": 1}
    ],
    "noise_paths": [
      {"path": "CMakeLists.txt", "disallowed_above_rank": 3},
      {"path": "linux_prj/route.ini", "disallowed_above_rank": 3}
    ]
  }
]
```

- [ ] **Step 2: Write failing tests for loading and reports**

Append to `tests/test_retrieval_evaluation.py`:

```python
from pathlib import Path

from src.retriever.evaluation import evaluate_cases, format_eval_report, load_eval_cases


def test_load_eval_cases_reads_fixture_directory():
    cases = load_eval_cases(Path("tests/fixtures/retrieval_eval"))

    assert [case.id for case in cases] == [
        "escort_route_recalc_business_impl",
        "escort_client_second_route_query",
    ]
    assert cases[0].expected_paths[0].path == "src/map_data/sea_route.cpp"
    assert cases[0].noise_paths[0].path == "CMakeLists.txt"


def test_evaluate_cases_and_report_show_failures():
    cases = [
        RetrievalEvalCase(
            id="case-one",
            query="route",
            expected_paths=[ExpectedPath("src/route.cpp", max_rank=1)],
            noise_paths=[NoisePath("CMakeLists.txt", disallowed_above_rank=2)],
            limit=3,
        )
    ]

    def fake_retrieval(db_path, query, limit):
        assert str(db_path) == "/tmp/project_index.sqlite"
        assert query == "route"
        assert limit == 3
        return [{"path": "CMakeLists.txt"}]

    outcomes = evaluate_cases("/tmp/project_index.sqlite", cases, fake_retrieval)
    report = format_eval_report(outcomes)

    assert outcomes[0].passed is False
    assert "case-one: FAIL" in report
    assert "expected path missing: src/route.cpp" in report
    assert "noise path ranked too high: CMakeLists.txt at rank 1" in report
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py -q
```

Expected: FAIL because `load_eval_cases`, `evaluate_cases`, and `format_eval_report` do not exist.

- [ ] **Step 4: Implement loading and reporting**

Append to `src/retriever/evaluation.py`:

```python
import json
from pathlib import Path
from typing import Callable

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
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py -q
```

Expected: PASS.

---

### Task 3: Add Seeded Hybrid-Search Regression

**Files:**
- Modify: `tests/test_retrieval_evaluation.py`

**Interfaces:**
- Consumes: `ProjectIndexRepository`, `ProjectFile`, `FileSummary`, `SymbolInfo`, `hybrid_search_project`, `evaluate_cases`.
- Produces: A regression test proving the eval runner can validate real hybrid-search results against a seeded SQLite index.

- [ ] **Step 1: Write the seeded regression test**

Append to `tests/test_retrieval_evaluation.py`:

```python
from src.indexer.models import FileSummary, ProjectFile, SymbolInfo
from src.retriever.hybrid_search import hybrid_search_project
from src.storage.project_index import ProjectIndexRepository


def test_retrieval_eval_validates_seeded_hybrid_search(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()

    repo.upsert_file(ProjectFile("src/map_data/sea_route.cpp", "/tmp/src/map_data/sea_route.cpp", "source", "cpp", 10, 1.0, "hash-src"))
    repo.upsert_summary(
        FileSummary(
            path="src/map_data/sea_route.cpp",
            summary="Implements escort route recalculation from implementation evidence.",
            responsibilities="escort route recalculation",
            key_points="recalc_route_main_work_handler",
            dependencies="map, route",
            risks="verify state writes",
            evidence="symbol scan; side effects: state_write,network_send",
            inconsistencies="none",
            confidence="medium",
            confidence_score=0.62,
        )
    )
    repo.replace_symbols(
        "src/map_data/sea_route.cpp",
        [
            SymbolInfo(
                path="src/map_data/sea_route.cpp",
                symbol_type="function",
                name="recalc_route_main_work_handler",
                signature="int recalc_route_main_work_handler(Context*)",
                line_start=20,
                line_end=40,
                summary="Recalculates escort route.",
                observed_behavior="updates route state and sends route packet",
                side_effects="state_write,network_send",
                confidence="medium",
            )
        ],
    )

    repo.upsert_file(ProjectFile("CMakeLists.txt", "/tmp/CMakeLists.txt", "build", "cmake", 10, 1.0, "hash-cmake"))
    repo.upsert_summary(
        FileSummary(
            path="CMakeLists.txt",
            summary="Build config mentions escort route recalc terms repeatedly.",
            responsibilities="build config",
            key_points="route recalc escort",
            dependencies="route",
            risks="not implementation evidence",
            evidence="config text",
            inconsistencies="none",
            confidence="low",
            confidence_score=0.2,
        )
    )

    cases = [
        RetrievalEvalCase(
            id="seeded-escort-route",
            query="押镖 route 重算 风险",
            expected_paths=[ExpectedPath("src/map_data/sea_route.cpp", max_rank=1)],
            noise_paths=[NoisePath("CMakeLists.txt", disallowed_above_rank=1)],
            limit=5,
        )
    ]

    outcomes = evaluate_cases(db_path, cases, hybrid_search_project)

    assert outcomes[0].passed is True, format_eval_report(outcomes)
```

- [ ] **Step 2: Run the seeded regression test**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py::test_retrieval_eval_validates_seeded_hybrid_search -q
```

Expected: PASS if current ranking keeps business implementation ahead of build noise.

---

### Task 4: Add Local Retrieval Eval CLI

**Files:**
- Create: `scripts/run_retrieval_eval.py`
- Modify: `tests/test_retrieval_evaluation.py`

**Interfaces:**
- Consumes:
  - `--db`: path to project-index SQLite database.
  - `--cases`: JSON file or directory of JSON files.
- Produces:
  - Human-readable report on stdout.
  - Exit code `0` when all cases pass.
  - Exit code `1` when any case fails.

- [ ] **Step 1: Write CLI behavior tests**

Append to `tests/test_retrieval_evaluation.py`:

```python
import subprocess
import sys


def test_retrieval_eval_cli_reports_missing_db(tmp_path):
    missing_db = tmp_path / "missing.sqlite"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_retrieval_eval.py",
            "--db",
            str(missing_db),
            "--cases",
            "tests/fixtures/retrieval_eval",
        ],
        cwd="/Users/cltx/projects/langgraph",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "project index database not found" in result.stderr
```

- [ ] **Step 2: Run CLI test and verify it fails**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py::test_retrieval_eval_cli_reports_missing_db -q
```

Expected: FAIL because `scripts/run_retrieval_eval.py` does not exist.

- [ ] **Step 3: Implement the CLI**

Create `scripts/run_retrieval_eval.py`:

```python
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
    outcomes = evaluate_cases(db_path, cases, hybrid_search_project)
    print(format_eval_report(outcomes))
    return 0 if all(outcome.passed for outcome in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI test and verify it passes**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py::test_retrieval_eval_cli_reports_missing_db -q
```

Expected: PASS.

- [ ] **Step 5: Run the CLI against the workspace project index**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/python /Users/cltx/projects/langgraph/scripts/run_retrieval_eval.py --db /Users/cltx/projects/langgraph/checkpoints/project_index.sqlite --cases /Users/cltx/projects/langgraph/tests/fixtures/retrieval_eval
```

Expected: The command prints a retrieval eval report. If it fails because the local index is stale or missing, refresh the index only with user approval when the run would scan the company target project.

---

### Task 5: Document the Evaluation Workflow and History Entry

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/history/2026-07-03-development-history.md`

**Interfaces:**
- Produces: Agent-readable instructions for when and how to run retrieval eval.

- [ ] **Step 1: Add README retrieval evaluation section**

Add this section after `## Retrieval and Memory` in `README.md`:

````markdown
## Retrieval Evaluation

Run retrieval evaluation before and after ranking, synonym, embedding, or memory-retrieval changes:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/python /Users/cltx/projects/langgraph/scripts/run_retrieval_eval.py --db /Users/cltx/projects/langgraph/checkpoints/project_index.sqlite --cases /Users/cltx/projects/langgraph/tests/fixtures/retrieval_eval
```

Use the report to check that expected business implementation files remain near the top and config/build/noise files do not move ahead of them. If the real project index is stale or missing, ask the user before refreshing it.
````

- [ ] **Step 2: Add history entry**

Append a new section to `docs/superpowers/history/2026-07-03-development-history.md`:

```markdown
### Retrieval Evaluation Baseline

- Change summary: Added a retrieval evaluation baseline for measuring ranking quality.
- Completed or modified functionality:
  - Added pure retrieval eval dataclasses and pass/fail evaluation logic.
  - Added JSON fixture loading and report formatting.
  - Added seeded hybrid-search regression coverage.
  - Added a local CLI for running eval cases against `project_index.sqlite`.
  - Documented the eval workflow in the README.
- Affected files or modules:
  - `src/retriever/evaluation.py`
  - `scripts/run_retrieval_eval.py`
  - `tests/fixtures/retrieval_eval/escort_route.json`
  - `tests/test_retrieval_evaluation.py`
  - `README.md`
  - `docs/superpowers/history/2026-07-03-development-history.md`
- Verification: Focused retrieval evaluation tests and full test-suite run.
- Follow-ups: Add more real user queries and expand the fixture set before major ranking rewrites.
```

- [ ] **Step 3: Run documentation grep check**

Run:

```bash
rg -n "Retrieval Evaluation|run_retrieval_eval|Retrieval Evaluation Baseline" README.md docs/superpowers/history/2026-07-03-development-history.md
```

Expected: Output includes the README section, CLI command, and history entry.

---

### Task 6: Full Verification

**Files:**
- No new files.

**Interfaces:**
- Produces: final confidence that the retrieval eval baseline does not regress existing behavior.

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retrieval_evaluation.py -q
```

Expected: all tests in `tests/test_retrieval_evaluation.py` pass.

- [ ] **Step 2: Run retriever tests**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests/test_retriever.py -q
```

Expected: all existing retriever tests pass.

- [ ] **Step 3: Run full suite**

Run:

```bash
PYTHONPATH=/Users/cltx/projects/langgraph /Users/cltx/projects/langgraph/venv/bin/pytest /Users/cltx/projects/langgraph/tests -q
```

Expected: the full suite passes.

- [ ] **Step 4: Review git status**

Run:

```bash
git status --short
```

Expected: only intentional files from this plan are changed, plus any pre-existing dirty worktree changes already present before execution.

---

## Self-Review

- Spec coverage: The plan covers the requested next improvement direction: measurable retrieval ranking quality before deeper memory, agent, Docker, or skill work.
- Safety coverage: The plan does not edit, build, or mutate the target C++ project. The only optional real-project operation is reading an existing SQLite index.
- Test coverage: The plan includes unit tests for pass/fail evaluation, fixture loading, report formatting, seeded hybrid search, CLI error handling, and full-suite verification.
- Type consistency: The dataclass names and function names are introduced in Task 1 and reused consistently in later tasks.
- Placeholder scan: The plan contains concrete files, code, commands, and expected outcomes.
