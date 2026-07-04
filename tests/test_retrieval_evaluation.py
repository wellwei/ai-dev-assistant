import json
import os
from pathlib import Path
import subprocess
import sys

from src.indexer.models import FileSummary, ProjectFile, SymbolInfo
from src.retriever.evaluation import (
    ExpectedPath,
    NoisePath,
    RetrievalEvalCase,
    evaluate_case,
    evaluate_cases,
    format_eval_report,
    load_eval_cases,
)
from src.retriever.hybrid_search import hybrid_search_project
from src.storage.project_index import ProjectIndexRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUN_RETRIEVAL_EVAL = PROJECT_ROOT / "scripts" / "run_retrieval_eval.py"


def _subprocess_env_without_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def _seed_retrieval_eval_db(db_path: Path) -> None:
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


def _write_eval_case(case_path: Path, expected_path: str) -> None:
    case_path.write_text(
        json.dumps(
            {
                "id": "seeded-cli-case",
                "query": "押镖 route 重算 风险",
                "limit": 5,
                "expected_paths": [{"path": expected_path, "max_rank": 1}],
                "noise_paths": [{"path": "CMakeLists.txt", "disallowed_above_rank": 1}],
            }
        ),
        encoding="utf-8",
    )


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


def test_load_eval_cases_reads_fixture_directory():
    cases = load_eval_cases(Path("tests/fixtures/retrieval_eval"))
    cases_by_id = {case.id: case for case in cases}

    assert set(cases_by_id) == {
        "escort_car_move_core",
        "escort_car_follow_move_task",
        "escort_car_position_sync_stop_state",
        "escort_car_second_route_sync_jump",
        "escort_car_timeout_migration_exit",
        "escort_car_outside_stop_conditions",
        "escort_car_sport_status_change_log",
        "escort_car_follow_distance_radius",
        "escort_route_recalc_business_impl",
        "escort_client_second_route_query",
        "escort_sea_route_map_data",
    }
    assert cases_by_id["escort_car_move_core"].expected_paths[0].path == "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp"
    assert cases_by_id["escort_car_position_sync_stop_state"].expected_paths[0].max_rank == 1
    assert cases_by_id["escort_car_second_route_sync_jump"].noise_paths[0].path == "src/task/tcp/process_undo_escort_car_vertigo_tcp_task.cpp"
    assert cases_by_id["escort_car_sport_status_change_log"].noise_paths[0].disallowed_above_rank == 2
    assert (
        cases_by_id["escort_route_recalc_business_impl"].expected_paths[0].path
        == "src/task/work/cal_cross_map_route_cost_time_complex_task.cpp"
    )
    assert cases_by_id["escort_route_recalc_business_impl"].expected_paths[1].path == "src/task/tcp/process_recalc_route_task.cpp"
    assert cases_by_id["escort_sea_route_map_data"].expected_paths[0].path == "src/map_data/sea_route.cpp"
    assert cases_by_id["escort_route_recalc_business_impl"].noise_paths[0].path == "CMakeLists.txt"


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


def test_retrieval_eval_validates_seeded_hybrid_search(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_retrieval_eval_db(db_path)

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
        cwd=PROJECT_ROOT,
        env=_subprocess_env_without_pythonpath(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "project index database not found" in result.stderr


def test_retrieval_eval_cli_reports_empty_case_directory(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    db_path.touch()
    empty_cases = tmp_path / "empty-cases"
    empty_cases.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(RUN_RETRIEVAL_EVAL),
            "--db",
            str(db_path),
            "--cases",
            str(empty_cases),
        ],
        cwd=PROJECT_ROOT,
        env=_subprocess_env_without_pythonpath(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "no retrieval eval cases found" in result.stderr


def test_retrieval_eval_cli_exits_zero_for_passing_cases(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_retrieval_eval_db(db_path)
    case_path = tmp_path / "passing-case.json"
    _write_eval_case(case_path, "src/map_data/sea_route.cpp")

    result = subprocess.run(
        [
            sys.executable,
            str(RUN_RETRIEVAL_EVAL),
            "--db",
            str(db_path),
            "--cases",
            str(case_path),
        ],
        cwd=PROJECT_ROOT,
        env=_subprocess_env_without_pythonpath(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Retrieval eval: 1/1 passed" in result.stdout
    assert "seeded-cli-case: PASS" in result.stdout


def test_retrieval_eval_cli_exits_one_for_failing_cases(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_retrieval_eval_db(db_path)
    case_path = tmp_path / "failing-case.json"
    _write_eval_case(case_path, "src/missing.cpp")

    result = subprocess.run(
        [
            sys.executable,
            str(RUN_RETRIEVAL_EVAL),
            "--db",
            str(db_path),
            "--cases",
            str(case_path),
        ],
        cwd=PROJECT_ROOT,
        env=_subprocess_env_without_pythonpath(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Retrieval eval: 0/1 passed" in result.stdout
    assert "seeded-cli-case: FAIL" in result.stdout
    assert "expected path missing: src/missing.cpp" in result.stdout
