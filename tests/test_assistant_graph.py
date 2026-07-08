from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph
from src.indexer.models import FileSummary, ProjectFile, ProjectMemory
from src.nodes.assistant_nodes import _detect_gameplay_topics
from src.retriever.vector_search import upsert_embedding
from src.storage.project_index import ProjectIndexRepository
from src.storage.sqlite import connect_db


def _seed_repo(db_path):
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(ProjectFile("src/route.cpp", "/tmp/src/route.cpp", "source", "cpp", 10, 1, "hash"))
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
    return repo


def test_assistant_graph_retrieves_and_displays_project_memories(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    memory_id = repo.insert_project_memory(
        ProjectMemory(
            project_root="/tmp/project",
            memory_type="risk_note",
            subject="Escort route risk",
            summary="Route recalculation may update escort state.",
            related_paths='["src/route.cpp"]',
            confidence="medium",
        )
    )
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算风险在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-project-memory",
        },
        {"configurable": {"thread_id": "thread-project-memory"}},
    )

    assert result["retrieved_project_memories"][0]["id"] == memory_id
    assert memory_id in result["project_memory_ids"]
    assert "Project memory #" in result["analysis"]
    assert "Long-term project memory only" in result["analysis"]
    assert "Project memories" in result["answer"]
    assert "current indexed implementation evidence wins" in result["answer"]
    assert "memory#" in result["answer"]
    assert "Long-term project memory only" not in result["answer"]
    assert "Project memory #" not in result["answer"]


def test_assistant_graph_omits_project_memory_section_when_no_match(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-project-memory-none",
        },
        {"configurable": {"thread_id": "thread-project-memory-none"}},
    )

    assert result.get("retrieved_project_memories", []) == []
    assert result.get("project_memory_ids", []) == []
    assert "Project memories" not in result["answer"]


def test_assistant_graph_project_memory_failure_is_non_blocking(tmp_path, monkeypatch):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)

    def fail_project_memory(*args, **kwargs):
        raise RuntimeError("memory unavailable")

    monkeypatch.setattr("src.nodes.assistant_nodes.search_project_memory", fail_project_memory)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-project-memory-failure",
        },
        {"configurable": {"thread_id": "thread-project-memory-failure"}},
    )

    assert result["retrieved_project_memories"] == []
    assert result["project_memory_ids"] == []
    assert "src/route.cpp" in result["answer"]


def test_assistant_graph_answers_project_question_and_persists_note(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-route",
        },
        {"configurable": {"thread_id": "thread-route"}},
    )

    assert result["request_type"] == "project_qa"
    assert "This is a project question or requirement research request." in result["analysis"]
    assert "这是项目问答" not in result["analysis"]
    assert "Request type: Project Q&A" in result["answer"]
    assert "src/route.cpp" in result["answer"]
    assert "Confidence" in result["answer"]
    assert "comments" in result["answer"] or "names" in result["answer"]
    assert "This is a project question or requirement research request." not in result["answer"]
    assert "结论" not in result["answer"]
    assert result["research_note_id"] is not None

    with connect_db(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM research_notes").fetchone()[0] == 1


def test_assistant_graph_uses_hybrid_vector_context_when_keyword_has_no_match(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    upsert_embedding(
        db_path,
        source_type="file_summary",
        source_id="src/vector_only.cpp",
        source_path="src/vector_only.cpp",
        source_hash="hash-vector",
        text="nebula_anchor semantic_vector",
    )
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "nebula_anchor semantic_vector",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-hybrid-vector",
        },
        {"configurable": {"thread_id": "thread-hybrid-vector"}},
    )

    assert result["retrieved_context"][0]["path"] == "src/vector_only.cpp"
    assert result["retrieved_context"][0]["evidence"] == "vector semantic match"
    assert result["retrieved_context"][0]["vector_score"] > 0
    assert result["related_paths"] == ["src/vector_only.cpp"]
    assert "src/vector_only.cpp" in result["answer"]


def test_assistant_graph_falls_back_to_keyword_search_when_hybrid_fails(tmp_path, monkeypatch):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)

    def fail_hybrid(*args, **kwargs):
        raise RuntimeError("hybrid unavailable")

    monkeypatch.setattr("src.nodes.assistant_nodes.hybrid_search_project", fail_hybrid)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-hybrid-fallback",
        },
        {"configurable": {"thread_id": "thread-hybrid-fallback"}},
    )

    assert result["retrieved_context"][0]["path"] == "src/route.cpp"
    assert "src/route.cpp" in result["answer"]


def test_assistant_graph_answer_surfaces_key_symbols_for_movement_context(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    repo.upsert_file(
        ProjectFile(
            "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            "/tmp/src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            "source",
            "cpp",
            10,
            1,
            "hash-move",
        )
    )
    repo.upsert_summary(
        FileSummary(
            path="src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            summary="Handles escort car movement stop and status transitions.",
            responsibilities="escort car movement",
            key_points="escort_car_move6, stop_escort_car_outside_conditions, calc_escort_car_sport_result",
            dependencies="escort, route",
            risks="verify frame side effects",
            evidence="symbol scan; side effects: state_write",
            inconsistencies="none",
            confidence="medium",
        )
    )
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖车 离线 死亡 上马 停止",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-movement-symbols",
        },
        {"configurable": {"thread_id": "thread-movement-symbols"}},
    )

    assert "Key symbols" in result["answer"]
    assert "escort_car_move6" in result["answer"]
    assert "stop_escort_car_outside_conditions" in result["answer"]
    assert "calc_escort_car_sport_result" in result["answer"]
    assert "Key points:" not in result["answer"]


def test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_english_topic_sections(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    files = [
        (
            "src/task/sync/process_sync_rs_task.cpp",
            "Processes role server position synchronization and broadcasts sync data.",
            "process_sync_position, sync_role_position, write_instance_position",
            "movement, position, sync",
        ),
        (
            "src/task/tcp/process_cli_role_move_tcp_task.cpp",
            "Handles client role movement packets and position updates.",
            "process_role_move, validate_move_position, update_move_position",
            "movement, move, position",
        ),
        (
            "src/battle_calculate/battle_calculate.cpp",
            "Calculates battle damage, hp changes, and attack statistics.",
            "update_damage_me_data, update_obj_hp, calculate_damage",
            "battle, combat, damage, hp",
        ),
        (
            "src/battle_calculate/effect_calculate_process.cpp",
            "Processes damage effects, restore effects, and fatal battle effects.",
            "process_effect__hp, battle_effect__fatal, process_effect__restore",
            "battle, damage, effect, hp",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state transitions and mounted movement speed.",
            "mount_up, dismount, sync_mount_position",
            "mount, horse, ride, speed, sync",
        ),
        (
            "src/task/tcp/process_cli_summoning_mount_tcp_task.cpp",
            "Handles client mount summon requests and mount state updates.",
            "process_mount_summon, summon_mount, update_mount_state",
            "mount, summon, horse",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_persist_attack.cpp",
            "Handles persistent attack checks and can dominate generic battle queries.",
            "check_normal_skill_config, persist_attack, attack_state",
            "battle, attack, skill",
        ),
        (
            "src/task/work/battle_statistics_complex_task.cpp",
            "Aggregates battle statistics and combat notifications.",
            "battle_statistics, collect_damage_stats, notify_battle_result",
            "battle, statistics, damage",
        ),
    ]
    for index, (path, summary, key_points, responsibilities) in enumerate(files):
        repo.upsert_file(
            ProjectFile(
                path,
                f"/tmp/{path}",
                "source",
                "cpp",
                10,
                index + 1,
                f"hash-{index}",
            )
        )
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=responsibilities,
                key_points=key_points,
                dependencies="gameplay",
                risks="verify implementation details before editing",
                evidence="symbol scan; implementation summary",
                inconsistencies="none",
                confidence="medium",
            )
        )
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-gameplay-movement-combat-mount",
        },
        {"configurable": {"thread_id": "thread-gameplay-movement-combat-mount"}},
    )

    answer = result["answer"]
    related_paths = result["related_paths"]

    assert "Movement / position sync" in answer
    assert "Combat damage" in answer
    assert "Mount logic" in answer
    assert "Current indexed evidence" in answer

    assert "src/task/sync/process_sync_rs_task.cpp" in answer
    assert "src/battle_calculate/battle_calculate.cpp" in answer
    assert "src/rtb_proc/character/rtb_proc_character_horse.cpp" in answer
    assert "Key symbols" in answer
    assert "process_sync_position" in answer
    assert "update_damage_me_data" in answer
    assert "mount_up" in answer

    assert any("sync" in path or "move" in path for path in related_paths)
    assert any("battle" in path or "damage" in path for path in related_paths)
    assert any("horse" in path or "mount" in path for path in related_paths)
    assert len(related_paths) == len(dict.fromkeys(related_paths))

    assert "topic_groups" not in result
    assert "结论" not in answer
    assert "关键函数/符号" not in answer
    assert "This is a project question" not in answer
    assert "Key points:" not in answer



def test_gameplay_topic_detection_uses_ascii_token_boundaries():
    topics = _detect_gameplay_topics("remove damage table config")

    assert [topic["topic_id"] for topic in topics] == ["combat_damage"]


def test_gameplay_topic_detection_requires_mount_context_for_speed_only_question():
    topics = _detect_gameplay_topics("移动速度在哪里？")

    assert [topic["topic_id"] for topic in topics] == ["movement_position_sync"]


def test_assistant_graph_preserves_escort_constraints_in_multi_topic_context(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    files = [
        (
            "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp",
            "Handles escort car movement position synchronization and server-side status transitions.",
            "escort_car_move6, sync_escort_car_position, calc_escort_car_sport_result",
            "escort car movement position sync server side",
        ),
        (
            "src/task/tcp/process_cli_role_move_tcp_task.cpp",
            "Handles generic client role movement packets and position updates.",
            "process_role_move, validate_move_position, update_move_position",
            "movement, move, position",
        ),
        (
            "src/battle_calculate/battle_calculate.cpp",
            "Calculates battle damage, hp changes, and attack statistics.",
            "update_damage_me_data, update_obj_hp, calculate_damage",
            "battle, combat, damage, hp",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state transitions and mounted movement speed.",
            "mount_up, dismount, sync_mount_position",
            "mount, horse, ride, speed, sync",
        ),
    ]
    for index, (path, summary, key_points, responsibilities) in enumerate(files):
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, index + 1, f"hash-escort-{index}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=responsibilities,
                key_points=key_points,
                dependencies="gameplay",
                risks="verify implementation details before editing",
                evidence="symbol scan; implementation summary; side effects: state_write",
                inconsistencies="none",
                confidence="medium",
            )
        )
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖车移动、战斗伤害、坐骑逻辑分别在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-escort-constrained-multi-topic",
        },
        {"configurable": {"thread_id": "thread-escort-constrained-multi-topic"}},
    )

    answer = result["answer"]
    movement_section = answer.split("Combat damage", 1)[0]
    assert "Movement / position sync" in answer
    assert "src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp" in movement_section
    assert "escort_car_move6" in movement_section
    assert result["related_paths"].count("src/rtb_proc/escort_car/rtb_proc_escort_car_move.cpp") == 1
    assert "topic_duplicate" not in answer
    assert "topic_groups" not in result


def test_assistant_graph_allows_shared_evidence_in_multiple_topic_sections(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    files = [
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state transitions, movement speed, and position synchronization.",
            "mount_up, dismount, sync_mount_position, update_mount_speed",
            "movement position sync mount horse ride speed",
        ),
        (
            "src/task/sync/process_sync_rs_task.cpp",
            "Processes role server position synchronization and broadcasts sync data.",
            "process_sync_position, sync_role_position",
            "movement position sync",
        ),
        (
            "src/battle_calculate/battle_calculate.cpp",
            "Calculates battle damage and hp changes.",
            "update_damage_me_data, calculate_damage",
            "battle damage hp",
        ),
    ]
    for index, (path, summary, key_points, responsibilities) in enumerate(files):
        repo.upsert_file(ProjectFile(path, f"/tmp/{path}", "source", "cpp", 10, index + 1, f"hash-shared-{index}"))
        repo.upsert_summary(
            FileSummary(
                path=path,
                summary=summary,
                responsibilities=responsibilities,
                key_points=key_points,
                dependencies="gameplay",
                risks="verify implementation details before editing",
                evidence="symbol scan; implementation summary; side effects: state_write",
                inconsistencies="none",
                confidence="medium",
            )
        )
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-shared-topic-evidence",
        },
        {"configurable": {"thread_id": "thread-shared-topic-evidence"}},
    )

    answer = result["answer"]
    movement_section = answer.split("Combat damage", 1)[0]
    mount_section = answer.split("Mount logic", 1)[1]
    shared_path = "src/rtb_proc/character/rtb_proc_character_horse.cpp"
    assert shared_path in movement_section
    assert shared_path in mount_section
    assert result["related_paths"].count(shared_path) == 1
    assert "topic_duplicate" not in answer


def test_assistant_graph_classifies_development_advice(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "我要修改押镖路线重算逻辑，影响哪些文件？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-dev",
        },
        {"configurable": {"thread_id": "thread-dev"}},
    )

    assert result["request_type"] == "development_advice"
    assert result["selected_workflow"]["workflow_id"] == "development_advice_readonly"
    assert result["approval_required"] is True
    assert "This is a development-advice request." in result["analysis"]
    assert result["suggested_commands"] == [
        "Read the relevant files locally to confirm implementation evidence.",
        "If a build is needed, ask the user before running company project build commands.",
    ]
    assert "Recommendation" in result["answer"]
    assert "approval required" in result["answer"]
    assert "Do not directly modify the target C++ project" in result["answer"]
    assert "This is a development-advice request." not in result["answer"]


def test_assistant_graph_keeps_unclear_answer_agent_facing_english(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-unclear",
        },
        {"configurable": {"thread_id": "thread-unclear"}},
    )

    assert result["analysis"] == "The user question is empty or unclear; ask for the module, requirement, or file scope."
    assert result["open_questions"] == ["Which business area, file, or requirement do you want to investigate?"]
    assert "The current index does not contain enough information" in result["answer"]
    assert "The user question is empty or unclear" not in result["answer"]
    assert "当前索引" not in result["answer"]


def test_assistant_graph_adds_default_flow_version(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-flow-version",
        },
        {"configurable": {"thread_id": "thread-flow-version"}},
    )

    assert result["flow_version"] == "2026-07-02.foundation-v1"


def test_create_assistant_graph_ignores_langgraph_factory_config_dict(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    _seed_repo(db_path)

    graph = create_assistant_graph({})
    result = graph.invoke(
        {
            "question": "押镖 route 重算在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-factory-config",
        },
        {"configurable": {"thread_id": "thread-factory-config"}},
    )

    assert type(graph).__name__ == "CompiledStateGraph"
    assert result["request_type"] == "project_qa"
    assert "src/route.cpp" in result["answer"]


def test_assistant_graph_reuses_prior_research_memory(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = _seed_repo(db_path)
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    first = graph.invoke(
        {
            "question": "押镖 route 重算风险在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-memory-1",
        },
        {"configurable": {"thread_id": "thread-memory-1"}},
    )
    second = graph.invoke(
        {
            "question": "继续看押镖路线风险，之前调研过什么？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-memory-2",
        },
        {"configurable": {"thread_id": "thread-memory-2"}},
    )

    assert first["research_note_id"] is not None
    assert second["retrieved_memory"][0]["id"] == first["research_note_id"]
    assert first["research_note_id"] in second["source_note_ids"]
    assert "Prior research memory" in second["answer"]
    assert "Historical assistant conclusion" in second["answer"]


def test_create_graph_does_not_create_checkpoint_directory_during_factory(tmp_path, monkeypatch):
    from src import graph as graph_module

    monkeypatch.chdir(tmp_path)

    app = graph_module.create_graph()

    assert type(app).__name__ == "CompiledStateGraph"
    assert not (tmp_path / "checkpoints").exists()
