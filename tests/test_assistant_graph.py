from langgraph.checkpoint.memory import InMemorySaver

from src.assistant_graph import create_assistant_graph
from src.indexer.models import FileSummary, ProjectFile
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
