from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph
from src.indexer.models import FileSummary, ProjectFile, ProjectMemory
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
    assert "长期项目记忆" in result["answer"]
    assert "当前实现索引证据优先" in result["answer"]
    assert "memory#" in result["answer"]
    assert "Long-term project memory only" not in result["answer"]
    assert "Project memory #" not in result["answer"]
    assert "current implementation evidence wins" not in result["answer"]


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
    assert "长期项目记忆" not in result["answer"]


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
    assert "src/route.cpp" in result["answer"]
    assert "置信度" in result["answer"]
    assert "注释" in result["answer"] or "命名" in result["answer"]
    assert "This is a project question or requirement research request." not in result["answer"]
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

    assert "关键函数/符号" in result["answer"]
    assert "escort_car_move6" in result["answer"]
    assert "stop_escort_car_outside_conditions" in result["answer"]
    assert "calc_escort_car_sport_result" in result["answer"]
    assert "Key points:" not in result["answer"]


def test_assistant_graph_answers_gameplay_movement_combat_mount_context_in_chinese(tmp_path):
    db_path = tmp_path / "project_index.sqlite"
    repo = ProjectIndexRepository(db_path)
    repo.init()
    files = [
        (
            "src/rtb_proc/character/character_move.cpp",
            "Handles character movement position sync.",
            "sync_character_position, update_move_position",
            "movement, position, sync",
        ),
        (
            "src/rtb_proc/battle/rtb_proc_battle_damage.cpp",
            "Applies battle damage and hp changes.",
            "apply_battle_damage, calc_damage_result",
            "battle, damage",
        ),
        (
            "src/rtb_proc/character/rtb_proc_character_horse.cpp",
            "Handles mount state and speed sync.",
            "mount_up, dismount, sync_mount_position",
            "mount, movement, sync",
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
    graph = create_assistant_graph(repo=repo, checkpointer=InMemorySaver())

    result = graph.invoke(
        {
            "question": "移动位置同步、战斗伤害、坐骑逻辑分别在哪里？",
            "project_root": "/tmp/project",
            "index_db_path": str(db_path),
            "thread_id": "thread-gameplay-domains",
        },
        {"configurable": {"thread_id": "thread-gameplay-domains"}},
    )

    assert "src/rtb_proc/character/character_move.cpp" in result["answer"]
    assert "src/rtb_proc/battle/rtb_proc_battle_damage.cpp" in result["answer"]
    assert "src/rtb_proc/character/rtb_proc_character_horse.cpp" in result["answer"]
    assert "关键函数/符号" in result["answer"]
    assert "sync_character_position" in result["answer"]
    assert "apply_battle_damage" in result["answer"]
    assert "mount_up" in result["answer"]
    assert "This is a project question" not in result["answer"]
    assert "Key points:" not in result["answer"]


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
    assert "建议" in result["answer"]
    assert "需要审批" in result["answer"]
    assert "不要直接修改" in result["answer"]
    assert "This is a development-advice request." not in result["answer"]


def test_assistant_graph_keeps_unclear_internal_text_english_and_user_answer_chinese(tmp_path):
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
    assert "当前索引中没有找到足够信息" in result["answer"]
    assert "The user question is empty or unclear" not in result["answer"]


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
    assert "历史调研记忆" in second["answer"]
    assert "Prior research" not in second["answer"]


def test_create_graph_does_not_create_checkpoint_directory_during_factory(tmp_path, monkeypatch):
    from src import graph as graph_module

    monkeypatch.chdir(tmp_path)

    app = graph_module.create_graph()

    assert type(app).__name__ == "CompiledStateGraph"
    assert not (tmp_path / "checkpoints").exists()
