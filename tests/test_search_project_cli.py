import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from src.indexer.models import FileSummary, ProjectFile
from src.storage.project_index import ProjectIndexRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEARCH_PROJECT = PROJECT_ROOT / "scripts" / "search_project.py"


def _subprocess_env_without_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def _seed_repo(db_path: Path) -> None:
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


def _run_cli(*args: str):
    return subprocess.run(
        [sys.executable, str(SEARCH_PROJECT), *args],
        cwd=PROJECT_ROOT,
        env=_subprocess_env_without_pythonpath(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_search_project_cli_json_returns_ranked_stable_fields(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli(
        "--db",
        str(db_path),
        "--query",
        "押镖 route 重算 风险",
        "--output",
        "json",
        "--limit",
        "5",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["query"] == "押镖 route 重算 风险"
    assert payload["db"] == str(db_path)
    assert payload["limit"] == 5
    assert payload["result_count"] >= 1
    first = payload["results"][0]
    assert first["rank"] == 1
    assert first["path"] == "src/map_data/sea_route.cpp"
    for key in [
        "file_type",
        "language",
        "summary",
        "key_points",
        "ranking_reason",
        "score",
        "hybrid_score",
        "keyword_score",
        "vector_score",
        "confidence",
        "evidence",
        "risks",
        "inconsistencies",
    ]:
        assert key in first
    assert "answer" not in payload
    assert "analysis" not in payload
    assert "research_note_id" not in payload
    assert "thread_id" not in payload


def test_search_project_cli_text_prints_ranked_paths_without_answer(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli("--db", str(db_path), "--query", "押镖 route 重算 风险", "--output", "text")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "1. src/map_data/sea_route.cpp" in result.stdout
    assert "score:" in result.stdout
    assert "reason:" in result.stdout
    assert "summary:" in result.stdout
    assert "结论" not in result.stdout
    assert "建议" not in result.stdout


def test_search_project_cli_empty_query_exits_two(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli("--db", str(db_path), "--query", "   ")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "query must not be empty" in result.stderr


def test_search_project_cli_missing_db_exits_two(tmp_path):
    missing_db = tmp_path / "missing.sqlite"

    result = _run_cli("--db", str(missing_db), "--query", "押镖 route")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "project index database not found" in result.stderr


def test_search_project_cli_invalid_limit_exits_two(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli("--db", str(db_path), "--query", "押镖 route", "--limit", "0")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "limit must be between 1 and 50" in result.stderr


def test_search_project_cli_does_not_persist_research_notes(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli("--db", str(db_path), "--query", "押镖 route 重算 风险", "--output", "json")

    assert result.returncode == 0
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM research_notes").fetchone()[0] == 0


def test_search_project_cli_returns_zero_for_no_matches(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli("--db", str(db_path), "--query", "zzzz_unmatched_token", "--output", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["result_count"] == 0
    assert payload["results"] == []

    text_result = _run_cli("--db", str(db_path), "--query", "zzzz_unmatched_token", "--output", "text")

    assert text_result.returncode == 0
    assert "No indexed project paths matched the query." in text_result.stdout
