import json
import os
from pathlib import Path
import subprocess
import sys

from src.indexer.models import FileSummary, ProjectFile
from src.storage.project_index import ProjectIndexRepository

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASK_PROJECT = PROJECT_ROOT / "scripts" / "ask_project.py"


def _subprocess_env_without_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def _seed_repo(db_path: Path) -> None:
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(ProjectFile("src/route.cpp", "/tmp/src/route.cpp", "source", "cpp", 10, 1.0, "hash"))
    repo.upsert_summary(
        FileSummary(
            path="src/route.cpp",
            summary="Handles escort route recalculation based on implementation evidence.",
            responsibilities="route recalculation",
            key_points="recalc_route_main_work_handler",
            dependencies="map, route",
            risks="names and comments may be stale",
            evidence="symbol scan; side effects: state_write",
            inconsistencies="side_effect_hidden",
            confidence="medium",
        )
    )


def _seed_multi_topic_repo(db_path: Path) -> None:
    repo = ProjectIndexRepository(db_path)
    repo.init()
    files = [
        (
            "src/task/sync/process_sync_rs_task.cpp",
            "Processes role server position synchronization and broadcasts sync data.",
            "process_sync_position, sync_role_position",
            "movement, position, sync",
        ),
        (
            "src/battle_calculate/battle_calculate.cpp",
            "Calculates battle damage and hp changes.",
            "update_damage_me_data, update_obj_hp",
            "battle, combat, damage, hp",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state transitions and mounted speed sync.",
            "mount_up, dismount, sync_mount_position",
            "mount, horse, speed, sync",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_persist_attack.cpp",
            "Handles persistent attack checks and generic battle state.",
            "persist_attack, attack_state",
            "battle, attack, skill",
        ),
    ]
    for path, summary, key_points, dependencies in files:
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, 1.0, f"hash-{path}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=summary,
                key_points=key_points,
                dependencies=dependencies,
                risks="verify implementation",
                evidence="symbol scan; side effects: state_write,network_send",
                inconsistencies="none",
                confidence="medium",
            )
        )


def _run_cli(*args: str):
    return subprocess.run(
        [sys.executable, str(ASK_PROJECT), *args],
        cwd=PROJECT_ROOT,
        env=_subprocess_env_without_pythonpath(),
        text=True,
        capture_output=True,
        check=False,
    )


def test_assistant_cli_reports_missing_db(tmp_path):
    missing_db = tmp_path / "missing.sqlite"

    result = _run_cli("--question", "押镖 route 重算在哪里？", "--db", str(missing_db))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "project index database not found" in result.stderr


def test_assistant_cli_rejects_empty_question(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli("--question", "", "--db", str(db_path))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "question must not be empty" in result.stderr


def test_assistant_cli_text_outputs_english_agent_answer(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli(
        "--question",
        "押镖 route 重算在哪里？",
        "--db",
        str(db_path),
        "--project-root",
        "/tmp/project",
        "--thread-id",
        "cli-text-test",
        "--output",
        "text",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert "src/route.cpp" in result.stdout
    assert "Confidence" in result.stdout
    assert "Request type: Project Q&A" in result.stdout
    assert "This is a project question" not in result.stdout
    assert "置信度" not in result.stdout


def test_assistant_cli_json_outputs_machine_contract(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli(
        "--question",
        "押镖 route 重算在哪里？",
        "--db",
        str(db_path),
        "--project-root",
        "/tmp/project",
        "--thread-id",
        "cli-json-test",
        "--output",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["answer"]
    assert "src/route.cpp" in payload["answer"]
    assert payload["request_type"] == "project_qa"
    assert payload["related_paths"] == ["src/route.cpp"]
    assert payload["approval_required"] is False
    assert payload["thread_id"] == "cli-json-test"
    assert payload["flow_version"] == "2026-07-02.foundation-v1"
    assert "analysis" not in payload
    assert "retrieved_context" not in payload
    assert "retrieved_memory" not in payload
    assert "retrieved_project_memories" not in payload


def test_assistant_cli_json_keeps_contract_for_multi_topic_english_answer(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_multi_topic_repo(db_path)

    result = _run_cli(
        "--question",
        "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？",
        "--db",
        str(db_path),
        "--project-root",
        "/tmp/project",
        "--thread-id",
        "cli-multi-topic-test",
        "--output",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert set(payload) == {
        "answer",
        "request_type",
        "related_paths",
        "approval_required",
        "open_questions",
        "suggested_commands",
        "research_note_id",
        "thread_id",
        "flow_version",
    }
    assert "topic_groups" not in payload
    assert payload["request_type"] == "project_qa"
    assert payload["thread_id"] == "cli-multi-topic-test"
    assert "Movement / position sync" in payload["answer"]
    assert "Combat damage" in payload["answer"]
    assert "Mount logic" in payload["answer"]
    assert any("sync" in path for path in payload["related_paths"])
    assert any("battle" in path or "damage" in path for path in payload["related_paths"])
    assert any("horse" in path or "mount" in path for path in payload["related_paths"])
    assert "结论" not in payload["answer"]


def test_assistant_cli_development_advice_preserves_readonly_gate(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    result = _run_cli(
        "--question",
        "我要修改押镖路线重算逻辑，影响哪些文件？",
        "--db",
        str(db_path),
        "--project-root",
        "/tmp/project",
        "--thread-id",
        "cli-dev-test",
        "--output",
        "json",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    payload = json.loads(result.stdout)
    assert payload["request_type"] == "development_advice"
    assert payload["approval_required"] is True
    assert "approval required" in payload["answer"]
    assert "Do not directly modify the target C++ project" in payload["answer"]
    assert "This is a development-advice request" not in payload["answer"]
    assert payload["suggested_commands"] == [
        "Read the relevant files locally to confirm implementation evidence.",
        "If a build is needed, ask the user before running company project build commands.",
    ]
